# Scientific integrity audit

| platform | seed | status | check | detail |
|---|---|---|---|---|
| gtx1650ti | all | PASS | Resolved protocol and manifest | Verified |
| gtx1650ti | all | PASS | Existing read-only artifact verifier | complete |
| gtx1650ti | all | WARN | Working tree | Recorded dirty tree: M .gitignore; ?? experiments/results_orchestrated/; archived active sources are checked separately. |
| gtx1650ti | all | WARN | Platform interpretation | OS release/kernel are captured facts; Windows marketing edition and Colab provider labels are user supplied, not inferred from NT version. |
| gtx1650ti | 2003 | PASS | Raw CSV, 1200 observations / 60 groups, dispatch, sources, all summary statistics | Verified |
| gtx1650ti | 2004 | PASS | Raw CSV, 1200 observations / 60 groups, dispatch, sources, all summary statistics | Verified |
| gtx1650ti | 2005 | PASS | Raw CSV, 1200 observations / 60 groups, dispatch, sources, all summary statistics | Verified |
| gtx1650ti | 2006 | PASS | Raw CSV, 1200 observations / 60 groups, dispatch, sources, all summary statistics | Verified |
| gtx1650ti | 2007 | PASS | Raw CSV, 1200 observations / 60 groups, dispatch, sources, all summary statistics | Verified |
| gtx1650ti | all | PASS | Within-run source equality | All active Python and CUDA snapshots identical over five sessions |
| gtx1650ti | all | PASS | Independent five-session estimators versus all saved aggregate exports | Verified |
| t4 | all | PASS | Resolved protocol and manifest | Verified |
| t4 | all | PASS | Existing read-only artifact verifier | complete |
| t4 | all | WARN | Platform interpretation | OS release/kernel are captured facts; Windows marketing edition and Colab provider labels are user supplied, not inferred from NT version. |
| t4 | 2003 | PASS | Raw CSV, 1200 observations / 60 groups, dispatch, sources, all summary statistics | Verified |
| t4 | 2004 | PASS | Raw CSV, 1200 observations / 60 groups, dispatch, sources, all summary statistics | Verified |
| t4 | 2005 | PASS | Raw CSV, 1200 observations / 60 groups, dispatch, sources, all summary statistics | Verified |
| t4 | 2006 | PASS | Raw CSV, 1200 observations / 60 groups, dispatch, sources, all summary statistics | Verified |
| t4 | 2007 | PASS | Raw CSV, 1200 observations / 60 groups, dispatch, sources, all summary statistics | Verified |
| t4 | all | PASS | Within-run source equality | All active Python and CUDA snapshots identical over five sessions |
| t4 | all | PASS | Independent five-session estimators versus all saved aggregate exports | Verified |
| t600 | all | PASS | Resolved protocol and manifest | Verified |
| t600 | all | PASS | Existing read-only artifact verifier | complete |
| t600 | all | WARN | Platform interpretation | OS release/kernel are captured facts; Windows marketing edition and Colab provider labels are user supplied, not inferred from NT version. |
| t600 | 2003 | PASS | Raw CSV, 1200 observations / 60 groups, dispatch, sources, all summary statistics | Verified |
| t600 | 2004 | PASS | Raw CSV, 1200 observations / 60 groups, dispatch, sources, all summary statistics | Verified |
| t600 | 2005 | PASS | Raw CSV, 1200 observations / 60 groups, dispatch, sources, all summary statistics | Verified |
| t600 | 2006 | PASS | Raw CSV, 1200 observations / 60 groups, dispatch, sources, all summary statistics | Verified |
| t600 | 2007 | PASS | Raw CSV, 1200 observations / 60 groups, dispatch, sources, all summary statistics | Verified |
| t600 | all | PASS | Within-run source equality | All active Python and CUDA snapshots identical over five sessions |
| t600 | all | PASS | Independent five-session estimators versus all saved aggregate exports | Verified |
| cross-platform | all | PASS | Active Python/CUDA source identity | Actual archived source SHA-256 equality; Git commit equality is not assumed. |

PASS means the named check passed, WARN identifies interpretation limits, FAIL excludes that study from validated numerical comparisons. A saved COMPLETED status is not proof of intact imported files.

Independent estimator discrepancies: 0. Structural failures are in this table, not hidden by an empty discrepancy CSV. Numerical tolerance: relative 1e-10, absolute 1e-15; booleans, identities, counts and seed sets are exact.

All numeric rows are traceable by platform/run_id, seed(s), backend, mode, bytes and scope to `experiments/cuda_paired/seed-<seed>/native/raw.csv`. Full input hashes and selected paths are in `reproducibility_manifest.json`. Derived contrasts retain per-session values in `session_contrasts.csv`; no platforms are pooled.
