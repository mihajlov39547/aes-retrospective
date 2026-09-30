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
pilot analysis.

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
CUDA and optimized CUDA using the same 18 NIST SP 800-38A F.1.1/F.5.1 and
differential tests: one/multiple blocks, launch boundaries, partial CTR tails,
and counter carry through 8/32/64/120 bits. Full wrap rejection is tested on all
four factories; all output hashes must agree across paths. Any failure saves a
failed validation record without raw/summary output. Each timed output is checked
outside timers. A deliberately corrupted optimized path is rejected by smoke.
Both kernels are validated even if only one profile is selected for timing.
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

Each pair produces two CPU rows and, with both profiles/measurements, four GPU
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
both kernels and local transitive imports), validation hash, clock definitions,
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

Proposed controlled pilot, to be run manually, not during preparation:

```powershell
.\.venv\Scripts\python.exe scripts\aes_cuda_cpu_gpu.py --run --purpose pilot --profile baseline optimized --measurements resident pipeline --resident-iterations 1 --host-memory pinned --modes ECB CTR --sizes 1024 16384 1048576 16777216 33554432 --warmup 5 --repeats 10 --seed 2003
```

Ten repeats reduce pilot cost while still revealing timing dispersion and paired
anomalies across all five sizes; five warmups exercise each job. Full pilot has
600 raw rows / 60 summary rows. Review correctness first, then dispersion and
order effects, before choosing the final protocol. Proposed eventual study is
five independent processes, seeds 2003--2007, warmup5/repeats20, fixed ascending
size order; not approved or executed here. CLI supports those parameters, but
study must wait for explicit human approval after pilot review. No LaTeX change.
