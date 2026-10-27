# Phase 2: independent data-page batching

Isolated AES-128-CTR experiment comparing sequential native OpenSSL EVP with one CUDA launch for 1, 4, 16 or 32 independently encrypted 1 MiB pages. A continuous-buffer control has the same total bytes and plaintext. This is **Parquet-inspired page encryption**, not a complete Parquet-compatible encryption implementation.

Historical experiments, data and manuscript are not modified. No full campaign has been executed for this implementation. See [READINESS.md](READINESS.md), [METHODOLOGY.md](METHODOLOGY.md) and [SCHEMA.md](SCHEMA.md).

## Requirements

Python 3.10–3.12 x64, PyCryptodome, NumPy, CuPy, a compatible NVIDIA driver and CUDA runtime/NVRTC; C compiler and OpenSSL **3** development headers/libraries. CPU AES capability and OpenSSL's AES-NI capability bit must both be present. This is capability evidence, not an instruction trace. CPU encryption is sequential in one calling thread. No CPU thread pool, tuned CUDA kernels, new streams or overlap is used.

`requirements.txt` pins portable Python dependencies; Colab setup selects the wheel for the installed CUDA major. Local Windows tests used existing NumPy 2.5.3; the portable installation pins 2.2.6. Versions are always recorded. Runtime rejects unexpected GPUs: study requires native Linux x86-64 **Tesla T4**, compute capability 7.5, one visible GPU. Only smoke permits the exact local **NVIDIA GeForce GTX 1650 Ti**, also 7.5. GPU errors never fall back to CPU.

## Native Windows local smoke

On the inspected machine, MSVC, OpenSSL 3 development files and Python/CUDA dependencies are already installed. Run from PowerShell:

```powershell
Set-Location C:\Projects\aes
& .\experiments\page_batching_validation\windows.ps1 `
  -Python C:\Projects\aes\.venv\Scripts\python.exe `
  -OpenSSLRoot C:\OpenSSL-Win64 `
  -Output "C:\Projects\aes\experiments\page_batching_validation\results\smoke-$([guid]::NewGuid())"
```

This discovers MSVC, compiles a separate DLL, verifies native x64 OpenSSL import bindings and hashes, runs CPU/unit tests, then runs the GTX smoke. It uses native Windows Python and `C:\OpenSSL-Win64\bin\libcrypto-3-x64.dll`; WSL is not involved. If using a fresh Python environment only, install missing packages:

```powershell
& $Python -m pip install -r experiments/page_batching_validation/requirements.txt
& $Python -m pip install cupy-cuda12x==13.6.0 nvidia-cuda-runtime-cu12==12.9.79 nvidia-cuda-nvrtc-cu12==12.9.86
```

Here `$Python` must be your selected x64 Python executable. The NVIDIA wheels provide runtime/NVRTC DLLs on Windows; a full Toolkit is unnecessary for this RawModule build. Missing MSVC/OpenSSL diagnostics identify the required components; do not substitute an unrelated DLL on PATH.

## Google Colab T4

Select a T4 GPU runtime and place the complete repository (including these uncommitted/new files if applicable) at `/content/aes`. In a `%%bash` cell:

```bash
cd /content/aes
bash experiments/page_batching_validation/colab_setup.sh
```

Compilation of the CUDA source is performed by CuPy NVRTC on GPU initialization, using the original AES source concatenated with the page-mapping kernel. The native OpenSSL wrapper is compiled by GCC. Final smoke, in another `%%bash` cell:

```bash
cd /content/aes
export CUDA_PATH=/usr/local/cuda
P=experiments/page_batching_validation
"$P/.venv/bin/python" "$P/run.py" --output "$P/results/t4-smoke-$(date -u +%Y%m%dT%H%M%SZ)"
```

**Only when ready to launch the full study**, use the following separate command. It is supplied for later execution and has not been run:

```bash
cd /content/aes
export CUDA_PATH=/usr/local/cuda
P=experiments/page_batching_validation
"$P/.venv/bin/python" "$P/run.py" --campaign --output "$P/results/t4-study-$(date -u +%Y%m%dT%H%M%SZ)"
```

Campaign runs a fresh smoke gate, then five separate session processes (2003–2007), each five warm-ups and twenty measured repetitions. All processes stay on the same runtime and share a campaign identity. Do not restart/reconnect the runtime mid-study or combine separately launched studies. Output directories must not exist; no overwrite/resume is implemented. Copy the complete output directory off Colab before disconnecting.

## Tests and aggregation

```powershell
.venv/Scripts/python.exe -m unittest discover -s experiments/page_batching_validation -p test_phase2.py -v
.venv/Scripts/python.exe experiments/page_batching_validation/aggregate.py experiments/page_batching_validation/results/local-smoke-final
```

Replace the Python path with the experiment's `.venv/bin/python` on Linux. Session summaries are also written automatically. For campaign recomputation, pass the five session directories (`.../2003` through `.../2007`) to `aggregate.py`; it prints JSON and refuses mismatched runtime fingerprints, incomplete protocols or repeated session IDs. Raw JSONL/CSV retain warm-ups, every sample, outliers and slowdowns. Speedup above one favors GPU; page/control throughput ratio above one favors independent pages. Decimal MB/s; divide by 1000 for GB/s.
