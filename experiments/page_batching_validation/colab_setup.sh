#!/usr/bin/env bash
set -Eeuo pipefail
trap 'echo "Setup failed at line $LINENO; setup is not complete." >&2' ERR
cd "$(dirname "$0")"
# Colab's runtime Python can differ from Ubuntu's /usr/bin/python3. In
# particular, python3-venv for Ubuntu 24.04 does not seed Colab Python 3.13.
python=$(command -v "${PYTHON:-python3}")
"$python" -c 'import sys; assert (3,10) <= sys.version_info[:2] <= (3,13), "Python 3.10-3.13 required"; print(sys.executable, sys.version)'
export CUDA_PATH="${CUDA_PATH:-/usr/local/cuda}"
release=$("$CUDA_PATH/bin/nvcc" --version)
case "$release" in
  *'release 12.'*) wheel='cupy-cuda12x==13.6.0';;
  *'release 13.'*) wheel='cupy-cuda13x==14.0.1';;
  *) echo 'Supported CUDA toolkit 12.x or 13.x required; refusing fallback' >&2; exit 1;;
esac
sudo apt-get update -qq
sudo apt-get install -y build-essential pkg-config libssl-dev
if [[ -x .venv/bin/python ]]; then
  base_version=$("$python" -c 'import sys; print(sys.version_info[:2])')
  env_version=$(.venv/bin/python -c 'import sys; print(sys.version_info[:2])')
  if [[ "$base_version" != "$env_version" ]]; then
    echo 'Existing .venv uses a different Python. Rename it before retrying; it has not been removed.' >&2
    exit 1
  fi
fi
# Only environment creation/pip probing is recoverable. Installation, build,
# dependency-check and test failures below always stop the script.
if "$python" -m venv .venv && .venv/bin/python -m pip --version; then
  echo 'Created environment with stdlib venv.'
else
  echo 'venv/ensurepip unavailable; seeding the selected Python with virtualenv.'
  bootstrap=$(mktemp -d)
  trap 'rm -rf -- "$bootstrap"' EXIT
  "$python" -m pip install --target "$bootstrap" 'virtualenv==20.35.4'
  PYTHONPATH="$bootstrap" "$python" -m virtualenv --python "$python" --no-periodic-update --no-download .venv
fi
.venv/bin/python -c 'import sys; assert sys.prefix != sys.base_prefix, "Environment is not isolated"; print("Environment:", sys.executable, sys.version)'
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install "$wheel"
.venv/bin/python -m pip check
.venv/bin/python build.py
.venv/bin/python -m unittest discover -s . -p 'test_*.py' -v
echo 'Setup complete: native OpenSSL build and CPU/regression tests passed. GPU smoke remains separate; see README.md.'
