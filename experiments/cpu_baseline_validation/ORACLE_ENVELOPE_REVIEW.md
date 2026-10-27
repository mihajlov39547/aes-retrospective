# Oracle ARM64 operation-envelope review

Read-only analysis on 2026-10-27 of the completed archives in `experiments/results/`.
The files were not extracted over existing datasets, modified, or benchmarked again.
The two archives contain 13 unique sessions: ten study sessions and three smoke
sessions. Duplicate IDs were accepted only with identical raw/metadata hashes.
Only the ten study sessions contribute to the table below.

Both campaigns report `research-server-01`, aarch64, Python 3.12.3, OpenSSL 3.0.13,
and identical archived `run.py`/`core.py` hashes. Notes identify Oracle Neoverse-N1,
2 vCPU. The source timer already brackets the same `measure(...)` assignment for
single-thread and multicore workers. Single-thread operation time can therefore
be recovered directly from its recorded timestamps. These are separate campaigns,
not simultaneous paired single/multicore trials; seed labels below identify the
sessions rather than establish cross-campaign statistical pairing.

**OpenSSL default, AES-128 CTR, 32 MiB per worker; decimal GB/s.** Values are
throughput at each session's median duration (twenty measured repetitions).

| Session seed | Single-thread transform | Single-thread operation envelope | Two-worker aggregate operation envelope |
|---|---:|---:|---:|
| 2003 | 4.030 | 1.060 | 2.032 |
| 2004 | 4.018 | 1.056 | 2.031 |
| 2005 | 4.035 | 1.064 | 2.043 |
| 2006 | 4.033 | 1.059 | 2.015 |
| 2007 | 4.026 | 1.060 | 2.022 |

Thus the original approximately 4.03 versus 2.03 comparison used different
boundaries and byte numerators: 32 MiB / native transform versus 64 MiB / group
operation completion. At the operation boundary the observed rates are about
1.06 versus 2.03 GB/s. No sum of per-worker transform rates is used as measured
aggregate throughput. Both workers' transform session medians remain approximately
4.01 GB/s, but that does not measure their synchronized aggregate completion.

For a concrete decomposition, session seed 2003 gives the following medians in
milliseconds. For two workers, component values select the worker that finishes
last in each repetition; they do not sum both workers' costs.

| Measured or derived quantity | Single-thread | Two-worker group / last-finishing worker |
|---|---:|---:|
| Operation/group envelope | 31.668465 | 33.029244 |
| Last-finishing worker duration | 31.668465 | 33.023604 |
| Output allocation/zero initialization | 9.077925 | 9.398864 |
| Native EVP transform | 8.326863 | 8.369962 |
| Cipher/context setup | 0.016100 | 0.016220 |
| Cipher/context cleanup | 0.001320 | 0.001120 |
| Buffer bindings | 0.020000 | 0.022780 |
| FFI no-op diagnostic | 0.017400 | 0.016620 |
| Native outer call (contains setup/transform/cleanup) | 8.361903 | 8.393702 |
| Native outer-minus-inner residual | 0.010041 | 0.011300 |
| Uninstrumented operation remainder | 14.213118 | 15.166599 |
| Last-finishing worker start lag | 0 | 0.012620 |

The non-overlapping accounted interval is allocation + bindings + no-op + native
outer call. The remainder is worker operation duration minus those components.
Do not add native outer call to its inner transform/setup/cleanup intervals.
Per-sample group envelope equals last-finishing worker duration plus its start
lag. These identities are checked by the analysis and unit tests. Medians do not
generally add, so the rounded table is not an additive partition of median time.

Across the five sessions, single-thread allocation medians range from 9.01–9.16 ms
and uninstrumented remainders from 14.05–14.26 ms. For the two-worker last-finishing
worker, allocation is 9.40–9.55 ms and remainder 14.99–15.26 ms. These are measurable
differences in the instrumented operation, not evidence of any specific cause.
The remainder includes output conversion, input checks, Python/timer bookkeeping,
local-object release and replacement/release of the previous result. Existing
data do not isolate copy/deallocation time, memory-bandwidth contention, cache
effects, scheduler interference, frequency changes or virtualization effects.
No claim that one of those causes explains the remainder is justified here.

Reproduce from repository root, selecting a new output directory:

```powershell
python experiments/cpu_baseline_validation/analyze_archives.py `
  experiments/results/oracle-phase1-single-study.tar.gz `
  experiments/results/oracle-phase1-multicore-study.tar.gz `
  --output experiments/cpu_baseline_validation/analysis-output/oracle-envelope-review-NEW
```

Local derived outputs are in `analysis-output/oracle-envelope-v2/`: per-session
boundary summaries, per-repetition diagnostics, `component_medians.csv`,
`all_session_summaries.csv` and `provenance.json`. All outcomes/extrema are retained;
no outlier filtering is applied. The tool never pools session samples into one
performance distribution or pairs different hosts.

Input archive SHA-256:

* Single: `3b5a7fd89fc68d8c36c624855a1d688c67c714e93dd48aa694fefe314a95c8a0`
* Multicore: `eee5c0ba0ac2c93a4011f254b4939b2b1c563878237b9fc40c9cbce32baf7038`
