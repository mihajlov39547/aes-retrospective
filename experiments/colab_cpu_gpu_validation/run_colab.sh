#!/usr/bin/env bash
# Default: correctness/regression tests then strict T4 smoke. --study is explicit.
set -euo pipefail
cd "$(dirname "$0")"
export CUDA_PATH="$(cat build/cuda_path.txt)"
export LD_LIBRARY_PATH="$CUDA_PATH/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
.venv/bin/python -m unittest discover -s . -p 'test_*.py' -v
.venv/bin/python run.py "$@"
