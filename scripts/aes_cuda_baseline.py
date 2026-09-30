"""Unoptimized AES-128 CUDA baseline. CPU reference is correctness-only."""
from __future__ import annotations

import hashlib
import json
import os
import importlib.metadata
import ctypes
import random
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from common import ROOT, parser, positive, print_plan, save_run, stats

KERNEL = ROOT / 'experiments' / 'aes_cuda_baseline.cu'
SIZES = [1024, 16384, 1048576, 16777216, 104857600]
SOURCE = 'https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38a.pdf'
KEY = bytes.fromhex('2b7e151628aed2a6abf7158809cf4f3c')
COUNTER = bytes.fromhex('f0f1f2f3f4f5f6f7f8f9fafbfcfdfeff')
PLAIN = bytes.fromhex('6bc1bee22e409f96e93d7e117393172a ae2d8a571e03ac9c9eb76fac45af8e51 '
                      '30c81c46a35ce411e5fbc1191a0a52ef f69f2445df4f9b17ad2b417be66c3710')
EXPECTED = {
    'ECB': bytes.fromhex('3ad77bb40d7a3660a89ecaf32466ef97 f5d3d58503b9699de785895a96fdbaaf '
                         '43b1cd7f598ece23881b00e3ed030688 7b0c785e27e8ad3f8223207104725dd4'),
    'CTR': bytes.fromhex('874d6191b620e3261bef6864990db6ce 9806f66b7970fdff8617187bb9fffdff '
                         '5ae4df3edbd5d35e5b4f09020db03eab 1e031dda2fbe03d1792170a0f3009cee')}
METRICS = ('kernel_throughput_MB_s', 'end_to_end_throughput_MB_s', 'kernel_seconds',
           'end_to_end_seconds', 'h2d_ns', 'kernel_ns', 'd2h_ns', 'transfer_ns', 'end_to_end_ns')
METHOD = {
    'implementation': 'Readable byte-oriented AES-128; one thread per block; 128 threads per CUDA block, not tuned.',
    'ECB': 'Independent-block validation/primitive benchmark, not recommended data protection.',
    'CTR': 'No separate nonce; full 128-bit big-endian initial counter plus block index; reject wrap; partial final block supported.',
    'kernel_timer': 'CUDA events, elapsed milliseconds converted to ns; conversion does not imply ns resolution.',
    'transfer_timer': 'perf_counter_ns around synchronous pageable host H2D/D2H copies, including synchronization.',
    'end_to_end_timer': 'perf_counter_ns from H2D start through completed D2H; includes launch, events and synchronization overhead.',
    'excluded': 'Compilation, allocation, key expansion/upload, counter upload, CPU reference, validation, result checks and export.',
    'allocation': 'Preallocated device input/output and pageable host output; CUDA default stream; no overlap.',
    'throughput': 'Payload bytes / 1e6 / seconds, decimal MB/s; kernel and end-to-end separate.',
    'design': 'Seeded data/key/counter and shuffled modes per size/repetition; new key per message; warmups excluded.',
    'study_protocol': 'Not locked; controlled pilot first. No CPU timing or speedup.',
    'hardware_execution_path': 'CuPy RawKernel CUDA, validated on detected device before timing.',
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, default=str, allow_nan=False) + '\n', encoding='utf-8')


def check_input(mode, key, counter, size):
    if mode not in EXPECTED or len(key) != 16 or len(counter) != 16 or size <= 0:
        raise ValueError('Expected ECB/CTR, AES-128 key, 16-byte counter and positive size.')
    if mode == 'ECB' and size % 16:
        raise ValueError('ECB size must be divisible by 16; use --modes CTR for arbitrary sizes.')
    if mode == 'CTR' and int.from_bytes(counter, 'big') + (size + 15)//16 > 2**128:
        raise ValueError('CTR counter space exhausted; wrapping is forbidden.')


def reference(mode, key, counter, data):
    from Crypto.Cipher import AES
    check_input(mode, key, counter, len(data))
    options = dict(nonce=b'', initial_value=int.from_bytes(counter, 'big')) if mode == 'CTR' else {}
    return AES.new(key, getattr(AES, 'MODE_' + mode), use_aesni=False, **options).encrypt(data)


class GPU:
    def __init__(self):
        self.dll_handles = []
        # Optional NVIDIA wheels supply DLLs on Windows without a full Toolkit.
        # Only this process is affected; honor an explicitly configured CUDA_PATH.
        if os.name == 'nt':
            for package, folder in [('nvidia-cuda-runtime-cu12','cuda_runtime'),
                                    ('nvidia-cuda-nvrtc-cu12','cuda_nvrtc')]:
                try:
                    base = Path(importlib.metadata.distribution(package).locate_file('nvidia')) / folder
                except importlib.metadata.PackageNotFoundError:
                    continue
                if (base/'bin').is_dir():
                    self.dll_handles.append(os.add_dll_directory(str(base/'bin')))
                    if folder == 'cuda_nvrtc':
                        # NVRTC dynamically loads its builtins DLL by basename.
                        for builtin in (base/'bin').glob('nvrtc-builtins*.dll'):
                            self.dll_handles.append(ctypes.WinDLL(str(builtin)))
                    if folder == 'cuda_runtime':
                        os.environ.setdefault('CUDA_PATH', str(base))
        import cupy as cp
        import numpy as np
        self.cp, self.np = cp, np
        if cp.cuda.runtime.getDeviceCount() < 1:
            raise RuntimeError('No CUDA device available.')
        self.stream = cp.cuda.Stream.null
        self.module = cp.RawModule(code=KERNEL.read_text(encoding='utf-8'), options=('--std=c++11',))
        self.expand = self.module.get_function('expand_key')
        self.kernels = {m: self.module.get_function('aes_' + m.lower()) for m in EXPECTED}
        device = cp.cuda.Device()
        prop = cp.cuda.runtime.getDeviceProperties(device.id)
        name = prop['name']
        self.info = dict(device_id=device.id, gpu_name=name.decode() if isinstance(name, bytes) else name,
                         vram_bytes=prop['totalGlobalMem'], compute_capability=device.compute_capability,
                         driver_version=cp.cuda.runtime.driverGetVersion(),
                         runtime_version=cp.cuda.runtime.runtimeGetVersion(), cupy_version=cp.__version__)
        self.info['cuda_path'] = cp.cuda.get_cuda_path()

    def prepare(self, mode, key, counter, data):
        check_input(mode, key, counter, len(data))
        cp, np = self.cp, self.np
        with self.stream:
            src, dst = cp.empty(len(data), dtype=cp.uint8), cp.empty(len(data), dtype=cp.uint8)
            dk = cp.asarray(np.frombuffer(key, dtype=np.uint8))
            dc = cp.asarray(np.frombuffer(counter, dtype=np.uint8))
            rk = cp.empty(176, dtype=cp.uint8)
            self.expand((1,), (1,), (dk, rk))
            self.stream.synchronize()
        return mode, np.frombuffer(data, dtype=np.uint8), np.empty(len(data), dtype=np.uint8), src, dst, rk, dc

    def launch(self, job):
        mode, host, out, src, dst, rk, counter = job
        args = (src, dst, rk) + ((counter,) if mode == 'CTR' else ()) + (self.np.uint64(host.size),)
        self.kernels[mode](((host.size + 2047)//2048,), (128,), args)

    def encrypt(self, mode, key, counter, data):
        # Validation deliberately does not call measure() or timing events.
        job = self.prepare(mode, key, counter, data)
        with self.stream:
            job[3].set(job[1]); self.launch(job)
            job[4].get(out=job[2], blocking=True)
            self.stream.synchronize()
        return job[2].tobytes()

    def measure(self, job):
        cp = self.cp
        start, stop = cp.cuda.Event(), cp.cuda.Event()
        with self.stream:
            self.stream.synchronize()
            begin = time.perf_counter_ns()
            job[3].set(job[1]); self.stream.synchronize()
            h2d_end = time.perf_counter_ns()
            start.record(); self.launch(job); stop.record(); stop.synchronize()
            d2h_start = time.perf_counter_ns()
            job[4].get(out=job[2], blocking=True); self.stream.synchronize()
            end = time.perf_counter_ns()
        kernel = float(cp.cuda.get_elapsed_time(start, stop)) * 1e6
        if kernel <= 0 or end <= begin:
            raise RuntimeError('Nonpositive timer measurement; refusing throughput.')
        h2d, d2h, elapsed = h2d_end-begin, end-d2h_start, end-begin
        return dict(h2d_ns=h2d, kernel_ns=kernel, d2h_ns=d2h, transfer_ns=h2d+d2h,
                    end_to_end_ns=elapsed, kernel_seconds=kernel/1e9, end_to_end_seconds=elapsed/1e9,
                    kernel_throughput_MB_s=job[1].size*1e3/kernel,
                    end_to_end_throughput_MB_s=job[1].size*1e3/elapsed)


def validate(gpu, session, purpose):
    tests = []
    def case(name, mode, key, counter, data, expected=None):
        item = dict(test=name, mode=mode, source=SOURCE if expected is not None else 'PyCryptodome differential reference',
                    key=key.hex(), initial_counter=counter.hex(), bytes=len(data))
        try:
            cpu = reference(mode, key, counter, data)
            expected = cpu if expected is None else expected
            actual = gpu.encrypt(mode, key, counter, data)
            item.update(expected_ciphertext=expected.hex(), actual_sha256=hashlib.sha256(actual).hexdigest(),
                        actual_ciphertext=actual.hex() if len(actual)<=64 else None,
                        cpu_reference_passed=cpu==expected, cuda_passed=actual==expected,
                        passed=cpu==expected==actual)
        except Exception as exc:
            item.update(passed=False, cpu_reference_passed=False, cuda_passed=False, error=str(exc))
        tests.append(item)
    for mode in EXPECTED:
        for size in (16, 64):
            case('NIST SP 800-38A ' + ('F.1.1' if mode=='ECB' else 'F.5.1'),
                 mode, KEY, COUNTER, PLAIN[:size], EXPECTED[mode][:size])
    rng = random.Random(2003)
    for mode, sizes in [('ECB', (32, 2048, 2064, 16384)), ('CTR', (1, 15, 17, 1000, 1025, 16385))]:
        for size in sizes:
            case('Multiple blocks / launch boundary / partial tail', mode, rng.randbytes(16),
                 (2**64-2).to_bytes(16, 'big'), rng.randbytes(size))
    for bits in (8, 32, 64, 120):
        case(f'Counter carry across {bits} bits', 'CTR', KEY, (2**bits-1).to_bytes(16,'big'), PLAIN)
    return dict(session_id=session, purpose=purpose, timestamp=datetime.now(timezone.utc).isoformat(),
                passed=all(t['passed'] for t in tests), tests=tests,
                counter_policy=METHOD['CTR'], scope='Functional correctness; not side-channel/security validation.')


def summarize(raw):
    rows = []
    for mode, size in sorted({(r['mode'], r['bytes']) for r in raw}):
        group = [r for r in raw if (r['mode'], r['bytes'])==(mode,size)]
        row = dict(session_id=group[0]['session_id'], algorithm='AES-128', backend='cuda', mode=mode, bytes=size, operation='encrypt')
        for metric in METRICS:
            row.update({metric+'_'+k:v for k,v in stats([r[metric] for r in group]).items()})
        rows.append(row)
    return rows


def run(args, gpu=None, validator=validate):
    gpu = GPU() if gpu is None else gpu
    session = str(uuid.uuid4())
    report = validator(gpu, session, args.purpose)
    # Durable gate precedes all performance measurement. Failure has no raw/summary.
    gate = args.output.resolve() / ('aes_cuda_baseline-validation-' + session)
    gate.mkdir(parents=True, exist_ok=False)
    write_json(gate/'validation.json', report)
    if report.get('passed') is not True:
        raise RuntimeError(f'CUDA validation failed; report: {gate}')
    rng, order_rng = random.Random(args.seed), random.Random(args.seed)
    raw, job_order = [], 0
    for size in args.sizes:
        for repeat in range(-args.warmup, args.repeats):
            modes = list(args.modes); order_rng.shuffle(modes)
            for variant_order, mode in enumerate(modes):
                data, key = rng.randbytes(size), rng.randbytes(16)
                # High 64 bits randomized, low 64 zero: ample room for every message.
                counter = rng.randbytes(8) + bytes(8)
                expected = reference(mode, key, counter, data)
                if repeat < 0:
                    actual = gpu.encrypt(mode, key, counter, data)
                else:
                    job = gpu.prepare(mode, key, counter, data)
                    timing = gpu.measure(job)
                    actual = job[2].tobytes()
                if actual != expected:
                    raise RuntimeError('Post-transform correctness check failed; no benchmark output exported.')
                if repeat >= 0:
                    raw.append(dict(session_id=session, mode=mode, algorithm='AES-128', backend='cuda', bytes=size,
                                    repeat=repeat, operation='encrypt', **timing, validation_checked=True,
                                    variant_order=variant_order, job_order=job_order,
                                    nonce_bytes=0, counter_bits=128 if mode=='CTR' else None,
                                    initial_counter=counter.hex() if mode=='CTR' else None))
                    job_order += 1
    directory = save_run('aes_cuda_baseline', args, METHOD, raw, summarize(raw))
    shutil.copy2(gate/'validation.json', directory/'validation.json')
    source = directory/'source'; source.mkdir()
    hashes = {}
    for path in (Path(__file__), Path(__file__).with_name('common.py'),
                 Path(__file__).with_name('aes_cuda_baseline_smoke_check.py'), KERNEL):
        shutil.copy2(path, source/path.name); hashes[path.name] = digest(source/path.name)
    manifest = json.loads((directory/'metadata.json').read_text(encoding='utf-8'))
    manifest.update(session_id=session, gpu=gpu.info, validation_sha256=digest(directory/'validation.json'),
                    validation_file='validation.json', validation_pre_measurement_file=str(gate/'validation.json'),
                    source_sha256=hashes, kernel_sha256=hashes[KERNEL.name],
                    wall_clock_info=vars(time.get_clock_info('perf_counter')))
    write_json(directory/'metadata.json', manifest)
    return directory


def arguments(argv=None):
    p = parser(__doc__)
    p.add_argument('--modes', nargs='+', choices=['ECB','CTR'], default=['ECB','CTR'])
    p.add_argument('--sizes', nargs='+', type=positive, default=SIZES)
    p.add_argument('--warmup', type=int, default=2)
    p.add_argument('--repeats', type=positive, default=10)
    args = p.parse_args(argv)
    if args.warmup < 0 or len(set(args.sizes)) != len(args.sizes) or len(set(args.modes)) != len(args.modes):
        p.error('Warmup must be nonnegative; sizes and modes must be unique.')
    if 'ECB' in args.modes and any(n%16 for n in args.sizes):
        p.error('ECB requires aligned sizes. For partial blocks use --modes CTR separately.')
    return args


def main():
    args = arguments()
    if not print_plan('aes_cuda_baseline', args, METHOD):
        run(args)


if __name__ == '__main__':
    main()
