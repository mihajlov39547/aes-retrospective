"""Phase 2 adapters: native sequential EVP and page mapping over original CUDA rounds."""
import ctypes as ct
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from time import perf_counter_ns

from protocol import check

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CPU_ROOT = REPO / 'experiments/cpu_baseline_validation'
sys.path.append(str(CPU_ROOT))
sys.path.append(str(REPO / 'scripts'))
spec = importlib.util.spec_from_file_location('page_phase1_cpu', CPU_ROOT / 'core.py')
phase1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phase1)
BUILD = HERE / 'build' / ('windows-x86_64' if os.name == 'nt' else 'linux-x86_64')
phase1.BUILD_DIR = BUILD
import aes_cuda_baseline as legacy


def hash_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class CPU:
    def __init__(self):
        self.native = phase1.Native()
        if self.native.build['batch_source_sha256'] != hash_file(HERE / 'batch_native.c'):
            raise RuntimeError('Batch C source changed; rebuild')
        self.call = self.native.lib.pagebatch_encrypt
        self.call.argtypes = [ct.c_void_p]*4 + [ct.c_size_t, ct.c_uint, ct.POINTER(ct.c_uint64)]
        self.call.restype = ct.c_int

    def metadata(self):
        return self.native.metadata()

    def measure(self, data, key, ivs, page_bytes):
        check(data, key, ivs, page_bytes)
        t = perf_counter_ns()
        output = bytearray(len(data)+16)
        allocation = perf_counter_ns()-t
        t = perf_counter_ns()
        joined = b''.join(ivs)
        output_ptr = (ct.c_ubyte * len(output)).from_buffer(output)
        times = (ct.c_uint64 * 3)()
        arguments = (ct.c_char_p(key), ct.c_char_p(joined), ct.c_char_p(data), output_ptr,
                     page_bytes, len(ivs), times)
        binding = perf_counter_ns()-t
        t = perf_counter_ns()
        ok = self.call(*arguments)
        outer = perf_counter_ns()-t
        if not ok:
            raise RuntimeError('EVP batch rejected/failed')
        metrics = dict(allocation_ns=allocation, binding_ns=binding, setup_ns=times[0],
            cpu_transform_ns=times[1], cleanup_ns=times[2], native_call_ns=outer,
            native_residual_ns=outer-sum(times))
        t = perf_counter_ns()
        result = bytes(memoryview(output)[:len(data)])
        metrics['output_copy_ns'] = perf_counter_ns()-t
        return result, metrics

    def encrypt(self, data, key, ivs, page_bytes):
        return self.measure(data, key, ivs, page_bytes)[0]


def cuda_source():
    return legacy.KERNEL.read_text(encoding='utf-8') + '\n' + (HERE/'page_kernel.cu').read_text(encoding='utf-8')


class GPU(legacy.GPU):
    def __init__(self):
        super().__init__()  # Original platform/CUDA initialization and metadata.
        self.module = self.cp.RawModule(code=cuda_source(), options=('--std=c++11',))
        self.expand = self.module.get_function('expand_key')
        self.kernels = {'CTR': self.module.get_function('aes_ctr')}
        self.pages_kernel = self.module.get_function('aes_ctr_pages')

    def prepare(self, layout, key, ivs, data, page_bytes):
        check(data, key, ivs, page_bytes)
        if layout not in ('pages', 'continuous') or (layout == 'continuous' and len(ivs) != 1):
            raise ValueError('Invalid GPU layout')
        cp, np = self.cp, self.np
        with self.stream:
            src, dst = cp.empty(len(data), dtype=cp.uint8), cp.empty(len(data), dtype=cp.uint8)
            dk = cp.asarray(np.frombuffer(key, dtype=np.uint8))
            divs = cp.asarray(np.frombuffer(b''.join(ivs), dtype=np.uint8))
            rk = cp.empty(176, dtype=cp.uint8)
            self.expand((1,), (1,), (dk, rk))
            self.stream.synchronize()
        host = np.frombuffer(cp.cuda.alloc_pinned_memory(len(data)), dtype=np.uint8, count=len(data))
        out = np.frombuffer(cp.cuda.alloc_pinned_memory(len(data)), dtype=np.uint8, count=len(data))
        host[:] = np.frombuffer(data, dtype=np.uint8)
        # Preserve the original seven-slot timing-driver interface.
        return (layout, page_bytes, len(ivs)), host, out, src, dst, rk, divs

    def launch(self, job):
        (layout, page_bytes, pages), host, out, src, dst, rk, ivs = job
        if layout == 'continuous':
            self.kernels['CTR'](((host.size+2047)//2048,), (128,),
                                (src, dst, rk, ivs, self.np.uint64(host.size)))
        else:
            threads = ((page_bytes+15)//16)*pages
            self.pages_kernel(((threads+127)//128,), (128,),
                (src, dst, rk, ivs, self.np.uint64(page_bytes), self.np.uint32(pages)))

    def encrypt(self, data, key, ivs, page_bytes, layout='pages'):
        job = self.prepare(layout, key, ivs, data, page_bytes)
        with self.stream:
            job[3].set(job[1])
            self.launch(job)
            job[4].get(out=job[2], blocking=True)
            self.stream.synchronize()
        return job[2].tobytes()
