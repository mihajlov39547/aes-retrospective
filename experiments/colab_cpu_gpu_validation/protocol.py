"""Protocol constants, deterministic schedule and fail-closed target checks."""
import hashlib
import json
import random
import re

SCHEMA = 1
SIZES = [1024, 16384, 1048576, 16777216, 33554432]
SEEDS = [2003, 2004, 2005, 2006, 2007]
CPU_BACKENDS = ('pycryptodome', 'openssl_default')
GPU_BACKENDS = ('cuda_baseline', 'cuda_optimized_v1')
JOBS = [(b, 'cpu') for b in CPU_BACKENDS] + [(b, m) for b in GPU_BACKENDS for m in ('resident', 'pipeline')]
COMPARISONS = {
    'prepared_cpu_transform_over_gpu_pipeline': ('cpu_transform_ns', 'gpu_pipeline_ns'),
    'cpu_operation_over_prepared_gpu_pipeline': ('cpu_operation_ns', 'gpu_pipeline_ns'),
    'isolated_cpu_transform_over_gpu_resident': ('cpu_transform_ns', 'gpu_resident_ns'),
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def schedule(seed, sizes, warmups, repeats):
    rng = random.Random(seed)
    sizes = list(sizes)
    rng.shuffle(sizes)
    rows = []
    for size in sizes:
        modes = ['CTR', 'ECB']
        rng.shuffle(modes)
        for mode in modes:
            for repeat in range(-warmups, repeats):
                jobs = list(JOBS)
                rng.shuffle(jobs)
                for backend, measurement in jobs:
                    rows.append(dict(bytes=size, mode=mode, repeat=repeat, warmup=repeat < 0,
                        backend=backend, measurement=measurement, execution_index=len(rows),
                        pair_id=f'{seed}:{size}:{mode}:{repeat}'))
    return rows


def target_check(gpu, system, architecture, study, local_name=None):
    if str(gpu['compute_capability']) != '75':
        raise RuntimeError('Expected compute capability 7.5; no fallback')
    if local_name:
        if study:
            raise RuntimeError('A local diagnostic device cannot run a study')
        if gpu['gpu_name'] != local_name:
            raise RuntimeError('Local smoke GPU name does not exactly match the requested device')
    elif gpu['gpu_name'] not in ('Tesla T4', 'NVIDIA Tesla T4', 'NVIDIA T4'):
        raise RuntimeError('Expected NVIDIA Tesla T4; no automatic device substitution')
    elif system != 'Linux' or architecture.lower() not in ('x86_64', 'amd64'):
        raise RuntimeError('Target requires Linux x86-64')


def aes_capabilities(info):
    # x86 CPUID AES is ECX bit 25, in the upper half of OpenSSL's first 64-bit word.
    match = re.search(r'OPENSSL_ia32cap=0x([0-9a-fA-F]+)', info['openssl_cpu_settings'])
    return dict(cpu_aes_available=info['cpu_aes_available'],
                openssl_aes_capability_enabled=bool(int(match.group(1), 16) & (1 << 57)) if match else None,
                instruction_execution='not traced; CPUID and effective capability mask only')


def software_check(runtime, cupy, pycryptodome, numpy):
    expected = {12: '13.6.0', 13: '14.0.1'}
    if (expected.get(runtime // 1000) != cupy or pycryptodome != '3.23.0' or numpy != '2.2.6'):
        raise RuntimeError('Target software differs from the pinned CUDA-family requirements; rerun setup or revise protocol explicitly')
