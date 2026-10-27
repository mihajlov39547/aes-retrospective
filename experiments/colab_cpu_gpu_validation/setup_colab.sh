#!/usr/bin/env bash
# Run in Colab CPU+T4 runtime, from a checked-out repository. Does not start benchmarks.
set -euo pipefail
cd "$(dirname "$0")"
test "$(uname -s)" = Linux
test "$(uname -m)" = x86_64
apt-get update -qq
apt-get install -y -qq build-essential pkg-config libssl-dev python3-venv
# Use the detected toolkit family, with explicit supported/pinned CuPy variants.
cuda_root="${CUDA_PATH:-/usr/local/cuda}"
cuda_major="$("$cuda_root/bin/nvcc" --version 2>/dev/null | sed -n 's/.*release \([0-9]*\)\..*/\1/p' || true)"
if [[ "$cuda_major" != 12 && "$cuda_major" != 13 ]]; then
    echo 'CUDA 12.x or 13.x toolkit including NVRTC/headers is required.' >&2
    echo 'Set CUDA_PATH to an installed supported toolkit. No CPU fallback or guessed toolkit is used.' >&2
    exit 1
fi
python3 -m venv .venv
# Never leave two CuPy wheel families in this dedicated environment.
.venv/bin/python -m pip uninstall -y cupy cupy-cuda12x cupy-cuda13x
.venv/bin/python -m pip install -r "requirements-cuda${cuda_major}.txt"
.venv/bin/python build.py
printf '%s\n' "$cuda_root" > build/cuda_path.txt
printf '%s\n' "$cuda_major" > build/cuda_major.txt
echo 'Setup complete. Next: bash run_colab.sh (tests + T4 smoke only).'
