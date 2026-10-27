"""Reuse original implementations without copying/editing their timing code or kernels."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CPU_ROOT = REPO / 'experiments/cpu_baseline_validation'
sys.path.append(str(CPU_ROOT))
sys.path.append(str(REPO / 'scripts'))
import core as cpu
import aes_cuda_baseline as cuda_base
import aes_cuda_cpu_gpu as cuda_paired

PROFILES = ('baseline', 'optimized')
BACKENDS = {'baseline': 'cuda_baseline', 'optimized': 'cuda_optimized_v1'}
CPU_BACKENDS = ('pycryptodome', 'openssl_default')
JOBS = [(name, 'cpu') for name in CPU_BACKENDS] + [
    (BACKENDS[p], boundary) for p in PROFILES for boundary in ('resident', 'pipeline')]


def native():
    # Native Windows diagnostics reuse the installed, verified CPU baseline read-only.
    # The Colab/Linux build has its own output directory.
    if sys.platform != 'win32':
        cpu.BUILD_DIR = HERE / 'build'
    return cpu.Native()


def source_paths():
    paths = list(HERE.glob('*.py')) + list(HERE.glob('*.md')) + list(HERE.glob('*.sh')) + list(HERE.glob('*.txt'))
    paths += [CPU_ROOT / n for n in ('core.py', 'native.c', 'windows_native.py')]
    paths += [REPO / 'scripts' / n for n in ('aes_cuda_baseline.py', 'aes_cuda_cpu_gpu.py',
              'aes_acceleration.py', 'cpu_validation.py', 'benchmark.py', 'common.py')]
    paths += [REPO / 'experiments' / n for n in ('aes_cuda_baseline.cu', 'aes_cuda_optimized.cu')]
    return sorted(paths)
