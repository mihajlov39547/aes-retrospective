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

Standard baseline: default CUDA stream, synchronous phases, no overlap or explicitly pinned memory:

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
Summary groups mode and size and retains count, mean, median, sample SD, min, max,
inclusive Q1/Q3, IQR, coefficient of variation (sample SD / mean, a fraction),
and per-metric outlier count/flag plus a combined summary flag. Quartiles use
linear interpolation at `(n-1)*p`. Values outside `[Q1-1.5*IQR,Q3+1.5*IQR]` are
flagged; no raw measurements are removed. With one observation CV is null;
with zero IQR values unequal to the quartile are flagged. Flags do not establish
invalidity or diagnose a cause, particularly for small samples. Unmeasured
metrics and their statistics are null, never artificial zero measurements.
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
.\.venv\Scripts\python.exe scripts\aes_cuda_baseline.py --run --purpose pilot --modes ECB CTR --sizes 1024 16384 1048576 16777216 --warmup 2 --repeats 10 --seed 2003
```

## Large-buffer diagnostics (separate from standard study)

Following unstable 100 MiB pilot measurements, the standard baseline default
sizes are 1 KiB, 16 KiB, 1 MiB and 16 MiB. Larger sizes require the diagnostic
profile. This is an explicit scope decision before study, not removal of selected
samples. Previous 100 MiB pilot files remain unchanged. Their variability does not
establish WDDM, transfers, scheduling or temperature as the cause; kernel times
also varied, so transfer-only attribution would be premature.

New options:

- `--profile baseline|diagnostic` (default baseline). Diagnostic output uses
  `aes_cuda_baseline_diagnostic-<purpose>-<timestamp>` and explicit profile fields.
  Diagnostic study is rejected; only smoke/pilot is allowed.
- `--measurement pipeline|resident|transfer-only` (default pipeline).
- `--host-memory pageable|pinned` (default pageable). Pinned and alternative
  measurements require diagnostic profile; the AES kernel is unchanged.
- `--resident-iterations N` (default 10, positive). Only resident measurement
  uses this number; raw rows record it and the total batch event duration.

Pipeline retains the original H2D/kernel/D2H boundaries. Pinned input and output
are allocated by `cupy.cuda.alloc_pinned_memory`; allocation and input staging
copies are excluded, buffers remain alive through synchronization, and failure
stops the run rather than falling back to pageable memory. This measures transfer
behavior with prepared pinned buffers, not the cost of pinning an application
message. The same KAT gate runs using the chosen host-memory type.

Resident uploads each job once, then encloses N launches of the unchanged AES
kernel in one pair of CUDA events without H2D/D2H between launches. One raw repeat
records batch duration / N as `kernel_ns`; throughput uses this per-launch average.
Input, output, expanded keys and counter are resident for that batch. Each launch
overwrites output from the same input, not from the previous ciphertext. The final
output is downloaded and verified outside events. This is repeated processing of
one synthetic message, not distinct CTR messages reusing a counter. Warmup batches
use the same selected measurement but are not exported. CV/IQR describe variation
between batch averages, not individual launches. Event time can include GPU idle
gaps between host submissions; this is not instruction-cycle timing. Resident
transfer/end-to-end columns are null and must not be interpreted as zero costs.

Transfer-only times H2D then D2H of that input with synchronization and no AES
kernel. Returned bytes are checked against input outside timing. `operation=copy`;
kernel and AEAD/encryption end-to-end fields are null. H2D, D2H and their sum are
reported as times; no misleading encryption throughput is assigned to this path.

Each run records timestamped nvidia-smi temperature, power, memory and P-state
snapshots before/after the measurement loop, selected by GPU PCI bus ID. Unsupported
readings are null; probe failures are recorded and do not block measurements.
These are endpoint context, not continuous monitoring or evidence of causality.

Manual 100 MiB diagnostic pilot examples (not executed during preparation):

```powershell
# Resident kernel batches, pageable staging outside the event interval
.\.venv\Scripts\python.exe scripts\aes_cuda_baseline.py --run --purpose pilot --profile diagnostic --measurement resident --resident-iterations 10 --modes ECB CTR --sizes 104857600 --warmup 5 --repeats 20 --seed 2004

# Comparable transfer-only and pipeline diagnostics, separate output directories
foreach ($memory in @('pageable', 'pinned')) {
    foreach ($measurement in @('transfer-only', 'pipeline')) {
        .\.venv\Scripts\python.exe scripts\aes_cuda_baseline.py --run --purpose pilot --profile diagnostic --measurement $measurement --host-memory $memory --modes ECB CTR --sizes 104857600 --warmup 5 --repeats 20 --seed 2004
        if ($LASTEXITCODE -ne 0) { throw 'Diagnostic pilot failed' }
    }
}
```

Review these as separate scenarios; do not merge with baseline study or infer
causality from one sequential pageable/pinned pair. If needed, repeat in reversed
scenario order in later controlled pilots. Small smoke tests cover all six
measurement/memory combinations, pinned allocation identity, null metrics,
batch scaling, copy-only kernel exclusion and diagnostic CLI isolation.
AES optimization and final CPU/GPU comparison remain deferred.
