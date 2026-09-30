# CUDA AES-128 baseline

This isolated baseline uses `scripts/aes_cuda_baseline.py` and
`experiments/aes_cuda_baseline.cu`. The older `aes_gpu.py` scaffold is unchanged.
No CPU timings, speedups or optimized CUDA claims are produced.

## Implementation and validation

One thread encrypts one AES-128 block, with a byte-oriented state, ordinary AES
S-box, explicit ShiftRows/MixColumns/AddRoundKey and ten rounds. A single-thread
key-expansion kernel runs outside measurement. The launch uses a fixed 128
threads per CUDA block, without tuning, shared-memory staging or fused T-tables.
ECB is an independent-block primitive benchmark, not recommended data protection.
CTR encrypts a full 128-bit big-endian counter, XORs the payload, and truncates
only the final keystream block. There is no separate nonce prefix. Counter wrap
is rejected before launch. A new synthetic key is generated per job; initial
counters have seeded high 64 bits and zero low 64 bits. These are reproducible
benchmark inputs, not production key generation.

The gate checks NIST SP 800-38A F.1.1 (ECB) and F.5.1 (CTR), one and four blocks,
against published ciphertext and PyCryptodome software AES. Differential checks
cover CUDA launch boundaries, partial CTR lengths (including 1000, 1025, 16385),
and carries across 8, 32, 64 and 120 bits. CPU reference is correctness-only.
Source: https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38a.pdf

A durable `aes_cuda_baseline-validation-<session>/validation.json` precedes every
measurement; failed validation produces no raw/summary files. A successful run
copies that report into its own directory and hashes it. Every warmup and timed
output is also compared with a CPU reference outside timing. No benchmark files
are exported if any comparison fails.

## Timing and outputs

Default CUDA stream, synchronous phases, no overlap or explicitly pinned memory:

- H2D and D2H: host `perf_counter_ns`, including completion synchronization.
- Kernel: CUDA events enclosing only the encryption kernel. Milliseconds are
  converted to ns; this does not imply nanosecond event resolution.
- Transfer: H2D + D2H host times.
- End-to-end: host wall time from H2D start through D2H completion, including
  launch/event/synchronization overhead. It is not the sum of mixed-clock fields.

Compilation, allocation, key expansion/upload, counter upload, reference output,
validation, comparisons and serialization are excluded. Device buffers and pageable
host output are preallocated. Thus end-to-end means the prepared-message
H2D/kernel/D2H path, not full application latency including setup.
Decimal payload MB/s is bytes / 1e6 / seconds, separately for kernel and end-to-end.
Summary groups mode and size and retains count, mean, median, sample SD, min, max.
Warmups are discarded; mode order is seed-shuffled per repetition. Input-size order
is the explicit CLI order. Defaults are preparation defaults, not a locked study.

Runs save metadata, validation, raw/summary CSV, results JSON, dependency lock,
and source snapshots with SHA-256 hashes. GPU runtime API driver version and CUDA
runtime version are distinct fields. Prior CBC measurements cannot serve as a
direct ECB/CTR CPU baseline: a later comparison must remeasure CPU in the same modes,
with the same inputs and protocol. GPU thermal/load behavior remains for pilot review.

## Local dependencies and smoke

The validated Windows environment uses CuPy 13.6.0, CUDA runtime wheel 12.9.79,
and NVRTC wheel 12.9.86. Installation into the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install cupy-cuda12x==13.6.0 nvidia-cuda-runtime-cu12==12.9.79 nvidia-cuda-nvrtc-cu12==12.9.86
.\.venv\Scripts\python.exe scripts\aes_cuda_baseline_smoke_check.py
```

The script registers wheel DLL directories only in its process and honors an
explicit CUDA_PATH. No persistent system configuration is changed. Other hosts
must use compatible CuPy/CUDA packages; see https://docs.cupy.dev/en/stable/install.html.
Smoke uses temporary artifacts, both modes at 1024/16384 bytes and CTR at 1025 bytes,
warmup 1 and repeats 2, plus small functional vectors. An unavailable GPU is a
failure, never a simulated validation pass. Mixed-mode CLI rejects unaligned
sizes; use `--modes CTR` separately for arbitrary lengths.

Manual controlled pilot (not executed during preparation):

```powershell
.\.venv\Scripts\python.exe scripts\aes_cuda_baseline.py --run --purpose pilot --modes ECB CTR --sizes 1024 16384 1048576 16777216 104857600 --warmup 2 --repeats 10 --seed 2003
```

Optimization, resident-data measurements and final CPU/GPU comparison are deferred.
