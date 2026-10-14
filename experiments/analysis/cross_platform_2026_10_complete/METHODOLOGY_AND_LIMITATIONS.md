# Methodology and limitations

The analysis reads raw CSVs directly and never imports benchmark implementations.
The existing read-only verifier supplies a separate integrity gate, not the estimates.
Five sessions (seeds 2003–2007) each contain 1200 rows: five sizes × two modes × six
backend/scope jobs × twenty repetitions. Each session has sixty summary groups.
Five warmups are recorded in configuration and source; warmup observations are not
exported, so their actual execution is supported by provenance rather than raw rows.
AES-NI evidence observes explicit native initialization, not an instruction trace.
All three CUDA candidates pass persisted cryptographic tests; baseline/v1 alone
contribute timed rows. Successful kernel execution in those tests establishes a
working compiled kernel path, not an independent compiler diagnostic log.

Latency, throughput and diagnostic fields are independently summarized with count,
mean, median, sample SD (n−1), inclusive Q1/Q3 at (n−1)p, IQR, extrema, CV=SD/mean
and descriptive Tukey flags. Zero diagnostic means have undefined CV. No outliers
are removed. Throughput is decimal payload MB/s; workload labels use binary MiB.
Median throughput is the median of individual byte/time rates, not the reciprocal
of median time (these differ for even n). Across sessions, use the median of five
session medians. Speedup is the median of five within-session ratios of CPU median
transform time to GPU median resident-kernel or pipeline time. No raw pooling.
The twenty repetitions are nested observations, not 100 independent sessions.
No significance tests or bootstrap intervals are claimed; n=5 describes only these
sessions, not independent machines, cloud allocations or population performance.
Same-seed size/mode contrasts remain within their own platform and session.

CPU encrypt output allocation is inside its wall timer; construction/key schedule
are outside. GPU buffers are preallocated and pinned; compilation, allocation,
pinning, staging, key expansion/upload and reference checks are excluded. Resident
N=1 uses CUDA events around a single launch with transfers outside. Pipeline uses
host wall time from H2D through completed D2H, including launch/synchronization.
The pipeline kernel event component is not a substitute for resident timing.
H2D/D2H are independently recorded host intervals around synchronous copies and
their synchronization. They are not pure PCIe wire time. Event ns conversions do
not imply nanosecond resolution.

Pipeline/resident throughput ratios use within-session throughput medians. Latency
ratios use their respective time medians. Additional pipeline time is their
difference, labeled approximate residual overhead: it mixes timing scopes,
synchronization and execution variability. It is not a measurement of transfer
time. Host component times and GPU event time do not form an exact additive clock
decomposition, and medians of components do not add to a median total.

Size order is fixed ascending; modes/jobs are seeded-shuffled. Therefore allocation,
cache, thermal, clock and elapsed-time effects are confounded with size. Telemetry
before/after whole sessions cannot attribute behavior at 16 MiB. Library versions,
CPU/GPU architectures, clocks, memory, driver models and runtimes differ. This is
not an isolated Windows 10/11 comparison, nor a claim about all laptop/server GPUs.
Windows edition and Colab identity are user labels; captured OS/release/kernel are
reported separately without inferring marketing edition from NT version.

Hashes establish internal consistency, not authenticity against coordinated edits.
Matching application source does not establish identical compiler output or native
library binaries. A recorded dirty tree is disclosed and active archived source
bytes are checked. Analysis needs Python 3.10+ and matplotlib only for figures;
no CUDA runtime, GPU or cloud credentials are needed.

| platform | captured_os | captured_release | captured_kernel | cpu | logical_cpus | gpu | driver | cuda_runtime | cupy | pycryptodome | git |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gtx1650ti | Windows | 10 | 10.0.19045 | Intel(R) Core(TM) i5-10300H CPU @ 2.50GHz | 8 | NVIDIA GeForce GTX 1650 Ti | 610.62 | 12090 | 13.6.0 | 3.23.0 | 5d95ff6b33d3358f80c46055da2678d3ba47d5b1 |
| t4 | Linux | 6.6.122+ | #1 SMP Thu Apr 30 18:17:14 UTC 2026 | Intel(R) Xeon(R) CPU @ 2.00GHz | 2 | Tesla T4 | 580.82.07 | 13000 | 14.0.1 | 4.0.0 | 5d95ff6b33d3358f80c46055da2678d3ba47d5b1 |
| t600 | Windows | 10 | 10.0.22631 | 11th Gen Intel(R) Core(TM) i7-11850H @ 2.50GHz | 16 | NVIDIA T600 Laptop GPU | 581.95 | 12090 | 14.2.0 | 3.24.1 | 7c7fc5202b2e259199abbe6302e66e60abda2e8a |

All numeric rows are traceable by platform/run_id, seed(s), backend, mode, bytes and scope to `experiments/cuda_paired/seed-<seed>/native/raw.csv`. Full input hashes and selected paths are in `reproducibility_manifest.json`. Derived contrasts retain per-session values in `session_contrasts.csv`; no platforms are pooled.
