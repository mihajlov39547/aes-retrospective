# Readiness and methodological risk — 2026-10-27

The integrated framework is implemented and ready for the **Colab T4 smoke gate**.
No five-session campaign was launched. Local GPU smoke timings are diagnostics,
not T4 performance evidence or an answer to whether the historical speedup survives.

## Inspection and preservation

Reviewed Phase 1 CPU code and completed native Windows/Oracle records, the
historical CUDA adapters/protocol, the T4 archive and the existing estimator code
(read-only). `review_existing.py` reproduces the historical 4.761336931964933×:
baseline CUDA, 32 MiB CTR, median of five session ratios of median times against
the old allocating PyCryptodome AES-NI interval. This distinction is retained
alongside per-repetition paired ratios. Both historical CUDA kernel hashes match
the reused sources in every archived T4 session.

All implementation changes are under `experiments/colab_cpu_gpu_validation/`.
Historical datasets, completed Windows/Oracle studies, existing CPU/CUDA sources,
and the SJEE manuscript were not modified. Reused CPU/CUDA C sources, input
generator, launches and GPU timing functions remain unchanged.

## Local validation

* **12 automated tests pass on native Windows**, including native OpenSSL and
  PyCryptodome correctness, target rejection, corruption rejection, schedule/input
  determinism, boundary-separated summaries, pairing checks, distinct estimators,
  five-session synthetic aggregation, preserved slowdowns/outliers/residuals,
  overwrite refusal, and a real GPU end-to-end smoke subprocess.
* Each CPU implementation passes its 37 cases, including NIST ECB/CTR and all five
  sizes. Each CUDA profile passes the historical 18 cases, counter-wrap rejection,
  and ten mode/size equality checks. Smoke also validates every actual output.
* Native local GPU: **NVIDIA GeForce GTX 1650 Ti**, compute capability 7.5, driver
  617.42 (CUDA driver API 13040), runtime 12.9, CuPy 13.6.0. It is accepted only by
  an explicit exact-name local-smoke flag, is labelled `local_diagnostic=true`,
  and cannot be selected for study mode.
* Native local CPU: Python 3.12.10, PyCryptodome 3.23.0, OpenSSL 3.6.5 with verified
  EVP DLL bindings; CPUID AES and OpenSSL's effective AES bit are enabled.
* Linux x86-64 WSL: the experiment's separate EVP library builds with GCC 13.3.0
  and warnings as errors. CPU correctness and numerical tests pass. The optional
  GPU integration unit test is skipped there; Linux/T4 GPU execution is still pending.
* Bash setup/runner scripts pass syntax checks. No full Colab setup was executed
  locally; it must run in the target runtime against its detected CUDA toolkit.

Retained local smoke evidence (ignored generated output):

`results/smoke-6aac4411-abe6-4aa6-a6e8-c7f5a6210e24/smoke-2003-d5b9710f-7e4a-47f0-8346-702e12196df1/`

It contains 72 raw rows, 32 boundary summaries, 48 speedup comparisons, component
diagnostics, passed validation, execution order, metadata and source snapshots.
Earlier local smoke artifacts are retained as well. The tests use temporary
directories for separate automated smoke runs. `results/existing_evidence_review.json`
records the read-only inspection of completed evidence and hashes.

## Remaining gates and limits

There are **no unresolved ciphertext or numerical correctness failures in the
local tests**. A real Linux x86-64 T4 smoke run remains mandatory before study.
The CUDA 13/CuPy 14 target variant is supported by the setup matrix and original
API design but has not been executed by this new integration locally. It must
pass the same target smoke gate; no unsupported toolkit/device is silently used.

The primary OpenSSL-transform / baseline-CUDA-prepared-pipeline comparison has a
reproducible, declared scope but is not an identical wrapper boundary: EVP timing
is inside C; GPU timing includes launches/events/synchronization. GPU allocation,
pinning/staging and key preparation are excluded. CPU operation-envelope ratios
are secondary asymmetric diagnostics, not complete application end-to-end claims.
Residuals cannot identify pure copying or contention costs. CPU AES capability
and permitted OpenSSL dispatch are checked, but actual instructions are not traced.

Historical messages, CPU output allocation, runtime/software versions and timing
estimator choices differ. New observations can determine whether the GPU is
competitive under the declared new protocol; they cannot be statistically paired
with the earlier campaign or prove that a faster CPU baseline makes old records
incorrect. Cloud contention, DVFS, thermal state, pinned-memory effects, limited
replication and lack of instruction tracing remain methodological risks.

Use the exact setup → smoke → later study commands in [README.md](README.md).
Both the strict target smoke and a fresh smoke at study startup must succeed.
