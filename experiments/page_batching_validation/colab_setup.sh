#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
sudo apt-get update -qq
sudo apt-get install -y build-essential pkg-config libssl-dev python3-venv
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
export CUDA_PATH="${CUDA_PATH:-/usr/local/cuda}"
release=$("$CUDA_PATH/bin/nvcc" --version)
case "$release" in
  *'release 12.'*) wheel='cupy-cuda12x==13.6.0';;
  *'release 13.'*) wheel='cupy-cuda13x==14.0.1';;
  *) echo 'Supported CUDA toolkit 12.x or 13.x required; refusing fallback' >&2; exit 1;;
esac
.venv/bin/python -m pip install "$wheel"
.venv/bin/python build.py
.venv/bin/python -m unittest discover -s . -p test_phase2.py -v
echo 'Build/tests finished. Run the explicit T4 smoke command in README.md.'
