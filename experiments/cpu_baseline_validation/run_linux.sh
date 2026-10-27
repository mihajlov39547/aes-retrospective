#!/usr/bin/env bash
# Ubuntu x86-64 / Colab / Oracle Ubuntu 24.04 ARM64. No automatic apt changes.
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python build.py
.venv/bin/python -m unittest discover -s . -v
# Always pass the smoke gate before honoring an explicit --study request.
.venv/bin/python run.py
if (( $# > 0 )); then
    .venv/bin/python run.py "$@"
fi
