# Output schema 1

No historical schema is rewritten. New campaign and session directories use UUIDs.
JSON is UTF-8 with finite numbers and null for unavailable values; CSV uses blank
for not-applicable values. Timings are nanoseconds, rates decimal MB/s. CUDA event
values are floating point conversions from milliseconds, not nanosecond precision.

## Campaign

`campaign.json`: `schema_version`, `campaign_id`, `purpose` (`smoke`/`study`),
`status` (`incomplete`/`failed`/`complete`), optional error, `smoke_gate` (child
directory name), `sessions` (five study children, excluding the gate), and
`runtime_fingerprint`. A completed smoke campaign has no study children.

`comparison/session_throughput_distribution.csv/json`: per size/mode/backend/
boundary distribution of five session throughputs at their median durations.
`comparison/session_speedup_distribution.csv/json`: per size/mode/CPU/GPU/
comparison/**estimator** distribution of five session speedups, including
`favorable_sessions` (>1) and `consistent_gpu_gain` (all five >1). Estimators are
`ratio_of_session_medians` and `median_paired_repetition_ratios`; never pool or
average rows across these labels. Each row includes count (5), median, mean,
sample SD, min/max, inclusive Q1/Q3/IQR, CV and descriptive outlier count.

The historical 4.761 result uses the **ratio_of_session_medians** estimator with
baseline CUDA and an older CPU timing boundary. It is not a row in the new campaign.

## Session metadata and provenance

`metadata.json`: protocol version, status/error, IDs, seed, purpose, notes,
UTC start/end, sizes/warmups/repetitions, workers=1, `local_diagnostic`, named
primary CPU/GPU/comparison and `operation_boundary=measure_call_v1`.

`identity` contains hostname/boot ID/OS, CPU model/flags/core count/affinity,
affinity-available logical core count and cgroup v2 `cpu.max` when exposed,
GPU model/device/VRAM/CC/runtime/driver/UUID, Python/NumPy/PyCryptodome/CuPy,
native OpenSSL metadata (effective capabilities, version/build flags, wrapper
hash/build command/compiler, Windows resolved DLL evidence when applicable),
and per-file source SHA-256. Its canonical JSON SHA-256 is `runtime_fingerprint`.
Each study child must match the smoke gate's fingerprint. No pairing across
different fingerprints or campaign/session IDs is accepted.

Additional metadata: full CPU information, Python wall-clock properties, `cupy.show_config`, NVRTC version and
options (`--std=c++11`), `nvcc --version` diagnostic, one resident iteration,
128 threads/block, default stream, relevant environment, Git commit/status,
package freeze, and GPU before/after telemetry. CPU AES CPUID and OpenSSL effective
AES bit are recorded separately from the explicit `instruction_execution=not traced`.

`source/` preserves repository-relative paths for experiment files, reused CPU
code, C source, historical CUDA Python adapters/imports and both CUDA kernels.
The native build manifest is embedded in metadata; rebuild from snapshot sources
and package/system requirements to reproduce. Compiled binary/library versions
are not interchangeable solely because their names are equal.

## Validation and inputs

`validation.json`: top-level `passed`, per-CPU 37-case validation results,
per-CUDA-profile historical 18-case KAT/differential results, wrap-rejection status
and ten all-size/mode ciphertext hashes. Failure produces `passed=false` and error;
no failed session may aggregate.

`inputs.json`: keyed by `MODE:bytes`; synthetic key/counter hex, plaintext SHA-256,
ciphertext SHA-256, and pair hash `SHA256(key || counter || plaintext)`. Plaintext
is reproduced with the unchanged Phase 1 `inputs(seed, size, worker=0)` function.

`planned_order.json`: full shuffled job list, including warmups.
`execution_order.jsonl`: started/completed event per actual job; incomplete jobs
remain visible after failure. Each job records size, mode, repeat, warmup, backend,
measurement, execution index and `pair_id=seed:size:mode:repeat`.

## Raw CSV

One row per job, including warmups. A study session has **1500 rows** (5 sizes ×
2 modes × 25 rounds × 6 jobs); a smoke session has **72 rows** (2 sizes × 2 modes
× 3 rounds × 6 jobs). Jobs are two CPU paths and resident/pipeline for each of two
GPU profiles. There is no separate CPU invocation for its operation metric.

Identity: `schema_version, session_id, campaign_id, runtime_fingerprint, seed,
bytes, mode, repeat, warmup, backend, measurement, execution_index, pair_id,
pair_hash, validation_passed`. Backends are `pycryptodome`, `openssl_default`,
`cuda_baseline`, `cuda_optimized_v1`. Measurements are `cpu`, `resident`, `pipeline`.
Warmups use negative repeat indices and are retained, but excluded from statistics.

CPU fields: `cpu_transform_ns` (alias of preserved `transform_ns`),
`cpu_operation_ns=operation_end_ns-operation_start_ns`, integer timestamps,
`setup_ns, cleanup_ns, allocation_ns, native_call_ns, ffi_noop_ns,
ffi_residual_ns, buffer_binding_ns`. Preserve all diagnostic values including
negative residuals. Components are not summed blindly: native_call overlaps its
setup/transform/cleanup intervals. PyCryptodome FFI is inside its transform and
is not independently estimated.

GPU resident fields: `gpu_resident_ns`, `resident_batch_ns` (equal at one launch).
Pipeline fields: `gpu_pipeline_ns`, `gpu_pipeline_kernel_ns`, `h2d_ns`, `d2h_ns`,
`transfer_ns=h2d_ns+d2h_ns`. The embedded kernel diagnostic is not a resident row.
Unavailable fields are blank, never fabricated zero performance.

## Session summaries

`summary.csv/json`: ID/fingerprint/seed, size/mode/backend/**boundary**, count,
median/mean/sample SD/min/max/Q1/Q3/IQR/CV/outlier count, and
`throughput_MB_s_at_median = bytes*1000/median_ns`. Boundaries are exactly
`cpu_transform_ns`, `cpu_operation_ns`, `gpu_resident_ns`, `gpu_pipeline_ns`.
A study has **80** rows, a smoke **32**. This estimator is not the arithmetic
mean of per-sample throughput and is not median throughput for even sample counts.

`speedups.csv/json`: IDs, size/mode, CPU/GPU, comparison, named numerator and
denominator fields, primary flag, ratio_of_medians, distribution of within-round
CPU/GPU ratios (including median), and favorable_repetitions. A study has **120**
rows, smoke **48**. Pairing requires same session, size, mode, repetition and
pair hash. The primary flag is true only for OpenSSL/baseline-CUDA prepared
transform/pipeline; other paths/comparisons remain separately available.

`components.csv/json`: descriptive distributions of the recorded setup/allocation/
cleanup/binding/FFI and transfer/kernel components, keyed by size/mode/backend/
measurement. Derived `operation_remainder_ns` subtracts only non-overlapping
components: allocation+setup+transform+cleanup for Python; allocation+binding+
no-op+native outer call for EVP. It is an **unattributed remainder**, not pure copy
time. Diagnostic SD/CV and negative residuals are retained; zero-mean CV is null.
Never add overlapping native inner/outer medians or assume medians are additive.

Aggregation is read-only on input raw/metadata. Existing result files cannot be
overwritten. Incomplete sessions, invalid timings, duplicate/missing jobs and
mismatched pairs/fingerprints fail validation. Session-level distributions retain
slowdowns and outliers; no post-hoc pruning or selection occurs.
