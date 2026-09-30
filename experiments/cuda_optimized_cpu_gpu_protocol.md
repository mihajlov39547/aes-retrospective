# Optimized CUDA AES-128 and paired CPU/GPU comparison (preparation)

## Review and isolation

The completed baseline script/kernel and all previous outputs remain unchanged.
`aes_cuda_cpu_gpu.py` reuses the baseline pinned allocations, timing methods,
counter guard, 18-vector validator, telemetry and statistics. It reuses
`aes_acceleration.verify_dispatch(mode)` for ECB and CTR, which explicitly observes
native AES initialization with `use_aesni=False/True`. Both CPU paths must be
available and verified; no `auto` fallback. This is library dispatch evidence,
not an instruction trace.

A new `aes_cuda_optimized.cu` is loaded in a separate CuPy module and exposes
distinct ECB/CTR entry points. Candidate v1 adds forced inlining and explicit
round/column loop unrolling to the byte-oriented baseline. The AES S-box memory
placement, key expansion, 128 threads per CUDA block, one thread per AES block,
CTR full 128-bit big-endian addition and partial-tail handling are unchanged.
Counter exhaustion is rejected on host. Constant-memory S-box was not selected
because divergent lookups need separate evaluation; no T-table, shared-memory,
block-size search, chunking or multi-stream overlap is introduced in v1.
Compiler code generation may already perform similar unrolling; the name
optimized identifies a candidate, not a verified speed advantage. Register
pressure or code size may offset any benefit. No performance conclusion precedes
pilot analysis. The reported pilot `aes_cuda_cpu_gpu-pilot-20260930T202051083522Z`
did not show consistent v1 gains. The subsequent selection retains v1 as the
optimized comparison candidate in the final paired study, without claiming
that it is consistently faster or represents the best possible GPU AES.

## T-table candidate v2

`aes_cuda_ttable.cu` adds the separate `ttable` profile. It uses four big-endian
32-bit state words. In rounds 1--9, table lookups combine SubBytes and MixColumns;
cross-word byte selection performs ShiftRows. A single 256-entry `uint32` Te0
table occupies 1024 bytes of constant memory. Its entries are generated from
the standard AES S-box: `Te0[x] = (2*S[x], S[x], S[x], 3*S[x])`, with products
in GF(2^8) and big-endian byte packing. Rotations by 8/16/24 bits derive the
other column contributions, trading rotation instructions for a smaller table.
The tenth round uses the separate 256-byte constant S-box and omits MixColumns.
Key expansion keeps the baseline byte schedule and 176-byte layout; round words
are loaded explicitly big-endian. ECB and CTR have separate kernel entry points.

This is the conventional table-based AES approach discussed in
[Harrison and Waldron, USENIX Security 2008](https://www.usenix.org/legacy/event/sec08/tech/full_papers/harrison/harrison_html/),
which evaluates 1 KiB and four-table designs and GPU memory placement.
The implementation here is derived from AES arithmetic, not a copy of their code.
Constant memory is the first placement candidate, not an assertion of best placement:
[NVIDIA documents serialization of different constant addresses within a warp](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/index.html#constant-memory).
Shared memory was considered but deferred: naive tables have data-dependent bank
conflicts, while replicated/bank-controlled layouts add resource tradeoffs and
validation complexity. No claim of bank-conflict-free, constant-time or side-channel
resistance is made for v2. No new memory-placement tuning or block-size search was
performed. Large-buffer variance may persist even if the arithmetic kernel improves.

The default remains 128 threads per CUDA block, one thread per AES block, with
unchanged full 128-bit big-endian CTR carry, wrap rejection and partial-tail
handling. There is no multi-stream overlap, chunking or pipeline optimization.
Pinned pipeline and resident timer scopes remain identical across all candidates.

CLI `optimized` still means v1 and its kernel file is unchanged. New output uses
schema 2 and explicit backend labels `cuda_baseline`, `cuda_optimized_v1`, and
`cuda_ttable` (v2). Historical output label `cuda_optimized` denotes v1 and is
not renamed on disk. Metadata records the profile/backend mapping and all three
kernel hashes. Default profiles now include all three; `--profile baseline optimized`
still selects only the two old GPU candidates for timing. Prior pilot artifacts
and completed baseline tables/diagnostics are never edited or pooled into v2.

### Post-pilot selection

According to the reviewed three-profile pilot, v2 `ttable` passed functional
validation but did not improve performance. Its constant-memory T-table path
was weaker than baseline/v1 in the key resident and pipeline measurements.
It is therefore **not selected for the final paired study** and is retained as
a negative pilot candidate. Its kernel, archived sources and pilot results are
preserved; no observations are deleted. This finding applies to this candidate
and platform, not to every T-table implementation.

The final timed GPU profiles are explicitly `baseline optimized` (v1).
Advanced shared-memory bank-conflict-free T-tables and bitsliced/PTX
optimizations remain future work; no new kernel optimization precedes this study.
The existing harness still validates and archives all three kernels before
timing. Thus `ttable` may appear in validation/source metadata, but with the
final commands below it produces no timed raw/summary rows and contributes no
final performance or speedup values. Do not omit `--profile baseline optimized`:
the unchanged CLI defaults still include `ttable`.

## Pairing and validation

For each mode/size/repeat, all CPU and GPU jobs share identical plaintext, key
and CTR initial counter, and one CPU reference ciphertext prepared outside timers.
The key/counter/data RNG is independent of the order RNG. Size order follows CLI;
modes and backend/measurement jobs are shuffled reproducibly each repeat. A new
synthetic message/key/counter is drawn for each pair; backends and resident
iterations replay the identical message. Pair ID and SHA-256 of key+counter+data
audit equality without storing keys. There is no reuse across different plaintext
messages by design; these seeded inputs are exclusively synthetic test material.

Before warmup or any timer, the gate validates CPU software, CPU AES-NI, baseline
CUDA, optimized v1 and T-table v2 using the same 18 NIST SP 800-38A F.1.1/F.5.1 and
differential tests: one/multiple blocks, launch boundaries, partial CTR tails,
and counter carry through 8/32/64/120 bits. Full wrap rejection is tested on all
five factories; all output hashes must agree across paths. Any failure saves a
failed validation record without raw/summary output. Each timed output is checked
outside timers. Deliberately corrupted v1 and v2 paths are rejected by smoke.
All three kernels are validated even if only one profile is selected for timing.
NIST source: https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38a.pdf

## Timing and metrics

- CPU: one `encrypt(data)` transform, output allocation included; cipher
  construction/key schedule excluded. Primary monotonic `perf_counter_ns`; outer
  `process_time_ns` is diagnostic CPU time, not cycles. Ratios >1 on short calls
  are not rejected. No setup+transform metric in v1.
- GPU pipeline: original synchronous pinned H2D -> kernel -> D2H. Host wall time
  measures the full prepared-buffer pipeline, transfers separately; CUDA events
  measure the kernel within it. Allocation/pinning/staging, compilation,
  key expansion/upload and counter preparation are outside timing. Default stream,
  no overlap. GPU preallocation versus CPU output allocation remains an explicit
  implementation-scope asymmetry, not full application startup timing.
- GPU resident: input uploaded and synchronized before events; output downloaded
  and checked after events. Default `--resident-iterations 1` is a single kernel
  launch. N>1 is one event-enclosed batch of N launches on the same input, with
  batch/N as kernel time; do not pool with single-launch data. Host submission gaps
  can appear in event intervals. Resident has null transfer/end-to-end metrics.

Each pair produces two CPU rows and, with all three profiles/both measurements, six GPU
rows. Pipeline rows additionally contain their own kernel-event component, kept
distinct from separately prepared resident measurements. Throughput is decimal
payload MB/s. Summary groups backend/profile, mode, size and measurement, storing
count, mean, median, sample SD, extrema, IQR/CV and descriptive outlier flags.
All raw data are retained. CPU timings are reused as the numerator for paired
GPU measurements within that same session, never from previous studies.

Speedups are session-level ratios of median times (not mean throughput):

1. Isolated = CPU transform median / resident GPU kernel median.
2. Pipeline = CPU transform median / GPU pipeline end-to-end median.

CPU AES-NI is the primary reference; software is supplementary. There is no
speedup assigned to the pipeline kernel component in summary. Future final
aggregation should use median of five session medians for metrics and median of
five session speedup ratios, without pooling raw samples. A newly paired baseline
is measured again; neither the previous CUDA aggregate nor CBC/GCM CPU data are
numerators or denominators. Modes, timed regions and inputs differ from CBC/GCM.

## Workflow and provenance

Output is exclusively `aes_cuda_cpu_gpu-<purpose>-<timestamp>/`. Metadata records
arguments, seed, CPU/GPU/runtime, git state, source snapshots/hashes (including
all three kernels and local transitive imports), validation hash, clock definitions,
and before/after GPU telemetry. Raw rows identify backend, profile, measurement,
memory policy, mode/size, seed, pair identity and execution order. Unsupported
telemetry stays null and never gates validity. CPU load is manually controlled;
no process killing, automatic utilization gates, power-plan or affinity changes.

Standard sizes: 1024, 16384, 1048576, 16777216, 33554432 bytes. 64/100 MiB remain
previous diagnostic/limitations material and are rejected by this comparison CLI.
Their exclusion is inherited from the baseline scope, not selected using new
optimized results. Windows/WDDM scheduling, fixed size order, temperature and
power state remain interpretation limits. No side-channel/security claim is made.

Smoke (only tiny input, temporary output):

```powershell
.\.venv\Scripts\python.exe scripts\aes_cuda_cpu_gpu_smoke_check.py
```

Plan-only (does not initialize CUDA):

```powershell
.\.venv\Scripts\python.exe scripts\aes_cuda_cpu_gpu.py
```

Historical three-profile pilot command (retained for provenance, not the final study):

```powershell
.\.venv\Scripts\python.exe scripts\aes_cuda_cpu_gpu.py --run --purpose pilot --profile baseline optimized ttable --measurements resident pipeline --resident-iterations 1 --host-memory pinned --modes ECB CTR --sizes 1024 16384 1048576 16777216 33554432 --warmup 5 --repeats 10 --seed 2003
```

The three-profile pilot uses ten repeats and produces 800 raw / 80 summary rows.
It is distinct from the selected final protocol below.

## Final paired study commands (manual execution only)

Five independent Python processes, seeds 2003--2007, five warmups and twenty
measured repeats; fixed ascending size order, pinned memory, ECB/CTR, resident
single-launch and pipeline measurements. CPU software and CPU AES-NI are included
automatically. Each session should contain 1200 raw rows and 60 summary rows:
five sizes x two modes x (two CPU jobs + four GPU jobs) x twenty repeats.
No outliers are removed. Existing baseline studies and diagnostic 64/100 MiB
results remain untouched and are not substituted into this newly paired dataset.

The loop below launches one process per seed and stops on failure. It was
prepared as text only; no study was launched during this documentation update.

```powershell
foreach ($studySeed in 2003..2007) {
    .\.venv\Scripts\python.exe scripts\aes_cuda_cpu_gpu.py --run --purpose study --profile baseline optimized --measurements resident pipeline --resident-iterations 1 --host-memory pinned --modes ECB CTR --sizes 1024 16384 1048576 16777216 33554432 --warmup 5 --repeats 20 --seed $studySeed
    if ($LASTEXITCODE -ne 0) { throw "Paired study failed for seed $studySeed" }
}
```
