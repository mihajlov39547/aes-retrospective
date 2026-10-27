# Colab T4 CPU–GPU baseline validation

This isolated experiment asks whether the historical CUDA CTR advantage remains
when its host comparator is optimized OpenSSL EVP. It reuses unchanged Phase 1
CPU code and unchanged historical CUDA implementations. No historical dataset
or SJEE file is modified. **Default execution is smoke only.** A study is a new
same-runtime campaign; it does not statistically pair with Windows, Oracle or
historical Colab observations.

## What is reused and what is primary

* `../cpu_baseline_validation/core.py`: identical SHAKE-256 inputs, AES semantics,
  PyCryptodome preallocated-output measurement, native EVP wrapper and validation.
* `../cpu_baseline_validation/native.c`: compiled unchanged into this experiment's
  Linux `build/`. Windows local diagnostics reuse its existing verified native
  build, including actual DLL-binding checks.
* `../../scripts/aes_cuda_baseline.py` and `aes_cuda_cpu_gpu.py`: original GPU
  preparation, validation, launch and measurement methods. Kernels are the
  unchanged `../aes_cuda_baseline.cu` and `../aes_cuda_optimized.cu`. The optimized
  v1 remains a separately labelled candidate. T-table v2 is not selected, matching
  the historical final campaign; its files and negative results remain intact.
* Both CUDA profiles use 128 threads/block, one AES block/thread, the default CUDA
  stream, pinned prepared host buffers, and **one resident launch** per sample.
  No tuning, new streams, overlapping transfers, or kernel changes are introduced.

The prespecified primary endpoint is **OpenSSL CPU transform time / baseline
CUDA prepared pipeline time**, particularly CTR at 32 MiB. PyCryptodome and
optimized-v1 results are reported separately for every mode/size. No best-kernel
selection is made after seeing timings. [Methodology](methodology.md) explains
why this prepared-buffer comparison is useful and why its implementation-level
timing boundaries are not identical.

## Requirements and supported target

* Linux x86-64, exactly one visible NVIDIA Tesla T4 / NVIDIA T4, compute capability
  **7.5**, accessible `nvidia-smi`, and a compatible NVIDIA driver.
* Python 3.10–3.13, GCC/compatible `cc`, `pkg-config`, OpenSSL **3.x** development
  headers/shared libcrypto, and Python venv. About 2 GiB free host RAM and 1 GiB
  free GPU memory is a reasonable smoke budget; actual allocation failures abort.
* CUDA **12.x or 13.x toolkit**, including NVRTC and headers. `CUDA_PATH` defaults
  to `/usr/local/cuda`; change it explicitly if the toolkit is elsewhere.
* Pinned Python dependencies: PyCryptodome 3.23.0, NumPy 2.2.6; CuPy 13.6.0
  (`cupy-cuda12x`) for CUDA 12 or CuPy 14.0.1 (`cupy-cuda13x`) for CUDA 13. Only one
  CuPy wheel family is installed in this dedicated venv. System library/compiler
  versions are recorded, not assumed to equal the historical campaign. Full
  `pip freeze` and `cupy.show_config()` are saved in every session.

The setup script detects the actual toolkit family and rejects anything outside
the declared 12/13 matrix. It does not install or replace the GPU driver/toolkit.
Strict target smoke/study also reject a Python package set outside that pinned
matrix. Explicit local diagnostics record their installed package versions and
are not accepted as target study data.
If NVRTC/headers are missing, supply a supported toolkit and rerun setup; do not
accept CPU fallback. See [CuPy installation documentation](https://docs.cupy.dev/en/stable/install.html).
Colab GPU types and availability vary; requesting a GPU does not guarantee T4.
See [Colab resource limits](https://research.google.com/colaboratory/intl/en-GB/faq.html).

CPU AES availability is read via native CPUID, alongside raw Linux CPU flags and
OpenSSL's effective x86 capability mask. Study mode requires CPUID AES and the
OpenSSL AES capability bit enabled. Capability overrides in `OPENSSL_ia32cap` or
`OPENSSL_armcap` cause rejection; remove them **before Python starts**. This is
capability/allowed-dispatch evidence, not proof of the executed instruction stream.
Do not describe a missing/disabled AES capability as an AES-NI comparison.

## Exact Colab commands

Choose **Runtime → Change runtime type → T4 GPU**, then clone/upload this repository
into `/content/aes`. Keep all sessions within this same live runtime. From a cell:

```python
%cd /content/aes
!nvidia-smi
!bash experiments/colab_cpu_gpu_validation/setup_colab.sh
```

For an alternate installed toolkit path, set it explicitly on setup, for example:

```python
!CUDA_PATH=/usr/local/cuda-13.0 bash experiments/colab_cpu_gpu_validation/setup_colab.sh
```

The setup script installs CPU development dependencies and the appropriate pinned
Python package set, compiles the unchanged EVP C source, and saves the toolkit
path. It does **not** run measurements. Then run the final target validation:

```python
!bash experiments/colab_cpu_gpu_validation/run_colab.sh --notes 'Colab T4 target smoke'
```

That command runs CPU correctness/numerical tests and a real, strict T4 smoke
session. CUDA compilation occurs through the original CuPy RawModule/NVRTC
before correctness gates and warmups. The optional local-GPU unit test may show
as skipped; the following strict T4 smoke still executes both CUDA paths.
Read `campaign.json`, the session's `metadata.json` and `validation.json`; both
campaign/session must be complete, and validation must pass.

**Only after reviewing that smoke result**, execute the full campaign in a
separate cell (provided for later use; not run during implementation):

```python
!bash experiments/colab_cpu_gpu_validation/run_colab.sh --study --notes 'Colab T4; record runtime tier and competing workload'
```

Study mode first runs another target smoke gate, then five fresh Python subprocess
sessions, seeds **2003–2007**, **five warmups** and **twenty measured repetitions**
per mode/size/backend/boundary. Sizes are **1 KiB, 16 KiB, 1 MiB, 16 MiB, 32 MiB**.
CPU encryption is serial and single-threaded; no multicore CPU aggregate enters
these data. OMP/OpenBLAS/MKL thread requests are set to one, and affinity/available
cores are recorded. Driver service threads may exist but CPU ciphers use one
calling thread. No CPU affinity pinning or frequency control is imposed.

Each child must match the gate's runtime fingerprint: host/boot ID, GPU UUID and
driver, CPU model/flags/affinity, software/library/native binary versions and
source hashes. A runtime restart, device/version/source change, or failed session
aborts the campaign. Do not combine sessions from a replacement runtime to fill
a failed campaign. `--study` has no local-device override. The scripts never
fall back to CPU-only timing. Colab notebook shell cells may not stop later cells
automatically on failure; inspect each exit/output before continuing.

Archive/download the entire new campaign directory before Colab expires:

```python
# Replace the campaign directory with the path printed by run_colab.sh.
!tar -czf /content/colab-cpu-gpu-study.tar.gz -C /content/aes/experiments/colab_cpu_gpu_validation/results STUDY_DIRECTORY
from google.colab import files
files.download('/content/colab-cpu-gpu-study.tar.gz')
```

## Pairing, timing, and validation

The CPU Phase 1 generator is reused exactly: worker 0 SHAKE-256 data/key/counter
from session seed and size, full 128-bit big-endian CTR with no nonce and wrap
rejection. Each mode/size configuration uses one immutable message on all paths,
replayed across repetitions. Keys/counters are synthetic benchmark inputs only.
Modes share data at a given size; CPU/GPU share byte-identical data and key/counter.
Input generation is independent of the execution-order RNG.

Size and mode order and the six backend/measurement jobs per round are seeded
shuffled. Each CPU job yields two distinct metrics from one invocation; each GPU
profile gets separate resident and pipeline jobs. Pair identity includes session,
mode, size, repetition and a hash of key+counter+plaintext. Aggregation rejects
unequal hashes, mixed runtime/session IDs, missing/duplicate jobs, and invalid
timings. Reference encryption and equality checks are outside all accepted timers.

Both CPU paths pass 37 Phase 1 KAT/differential cases. Each selected CUDA profile
passes the historical 18 NIST/partial-tail/counter-carry cases, explicit wrap
rejection, and equality in ECB/CTR at all five workload sizes. Each configuration
passes equality again before warmups, and every warmup/measured output is checked
before its timing row is accepted. Failed/incomplete sessions cannot aggregate.

| Boundary field | Included | Excluded |
|---|---|---|
| `cpu_transform_ns` | PyCryptodome Python `encrypt(..., output=view)` with internal FFI, **or** native C interval around EVP Update+Final | Output allocation, context/key setup, output conversion/checks; outer ctypes call excluded for EVP |
| `cpu_operation_ns` | Original Phase 1 `measure` call/assignment: checks, allocation/zeroing, bindings/no-op diagnostics where applicable, setup, encryption, cleanup, output conversion/object release | Reference/input generation and ciphertext validation |
| `gpu_resident_ns` | Original CUDA event interval around **one** launch on resident buffers, including device-observed launch gaps | H2D before events; D2H/check after events; preparation/key expansion |
| `gpu_pipeline_ns` | Original host wall interval: H2D, sync, launch/events/kernel completion, D2H, final sync | Compilation, host/device allocation/pinning/staging, key expansion/upload, counter upload, Python bytes conversion/check |

All existing CPU component diagnostics (`transform_ns`, setup, allocation, cleanup,
buffer binding, native outer call, FFI no-op and residual) remain in raw data.
GPU H2D, D2H, transfer sum and pipeline's embedded kernel event time remain
diagnostics. Embedded pipeline kernel time is not substituted for a resident
sample. CUDA event ns values are converted from milliseconds; this does not imply
nanosecond resolution. FFI residuals are retained without subtracting them from
reported performance. No false claim of identical Python and C timing is made.

## Results, aggregation, and reproducibility

Versioned output is `results/{smoke|study}-UUID/{smoke|study}-SEED-UUID/`, schema 1.
See [schema.md](schema.md) for field/estimator definitions. Every session includes
raw CSV (warmups retained), validation JSON, planned order JSON and actual event
JSONL, input hashes and key/counter, metadata, source snapshots preserving repository
paths, boundary summaries and paired speedups. Sources include imported CPU/CUDA
Python code and unchanged CUDA/C files. Build command/version, loaded OpenSSL
version/CPU mask, PyCryptodome, CPU/OS/cores, GPU identity, CUDA runtime/driver/NVRTC,
CuPy configuration, package freeze, Git state, clock-related environment and GPU
before/after telemetry are recorded. No `openssl speed` or subprocess encryption
is used for primary timings. Subprocesses only orchestrate independent sessions
and collect metadata.

Per-session summaries report median duration, throughput at median time, sample
SD, CV, extrema, inclusive quartiles/IQR and descriptive outlier count. Outliers,
slowdowns and ratios below one are retained. Speedup is CPU time / GPU time; >1
means the GPU is faster **at those named boundaries**. Every CPU/profile pair has:

1. `prepared_cpu_transform_over_gpu_pipeline`: primary comparison family; only
   OpenSSL versus baseline CUDA is the prespecified primary endpoint.
2. `cpu_operation_over_prepared_gpu_pipeline`: secondary asymmetric service-cost
   diagnostic; **not allocation-inclusive GPU/application end-to-end speedup**.
3. `isolated_cpu_transform_over_gpu_resident`: diagnostic compute interval ratio;
   **never a transfer-inclusive or application end-to-end claim**.

Session reports retain both ratio-of-medians and median-of-per-repetition ratios.
The campaign gives **two separate estimator rows** for each comparison: the
distribution across five session ratios of medians (historical estimator family),
and across five session medians of paired repetition ratios. Both use sessions
as replication units, report range/SD/CV/IQR and counts of favorable sessions.
Neither pools 100 repetitions as independent sessions. No significance test or
confidence claim is manufactured from five sessions.

To regenerate summaries without overwriting existing files:

```bash
cd /content/aes/experiments/colab_cpu_gpu_validation
.venv/bin/python aggregate.py results/CAMPAIGN/SESSION --output results/NEW_SESSION_ANALYSIS
.venv/bin/python aggregate.py results/CAMPAIGN --campaign --output results/NEW_CAMPAIGN_ANALYSIS
```

## Local developer verification

CPU tests require a built baseline (Linux: `python build.py`; Windows: the existing
verified Phase 1 Windows build). Run from repository root:

```powershell
python -m unittest discover -s experiments/colab_cpu_gpu_validation -p 'test_*.py' -v
# Explicit CC7.5 local diagnostic only; cannot be used with --study:
$env:AES_GPU_SMOKE_NAME = 'NVIDIA GeForce GTX 1650 Ti'
python -m unittest discover -s experiments/colab_cpu_gpu_validation -p 'test_*.py' -v
python experiments/colab_cpu_gpu_validation/run.py --local-smoke-gpu 'NVIDIA GeForce GTX 1650 Ti'
```

On a non-T4 host, default target execution fails rather than relabelling the local
GPU. A compatible CC7.5 local GPU can validate algorithms and orchestration only;
it cannot establish T4 throughput. See [readiness.md](readiness.md).
