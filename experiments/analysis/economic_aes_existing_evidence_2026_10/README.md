# Existing AES evidence: conditional economic analysis

Assessment: **READY WITH EXPLICIT LIMITATIONS**. This is an audit and secondary analysis, not a scientific manuscript, investment recommendation, measured energy study or complete TCO analysis.

Primary evidence is the five September 30, 2026 paired AES-128 sessions on the Intel i5-10300H / GTX 1650 Ti. Local records take precedence over preparation-era README statements. The October cross-platform, Windows EVP, Oracle ARM and T4 page-batching campaigns are separately inventoried; their observations are never substituted into the historical estimates.

No benchmark, encryption validation run, compilation, dependency installation, commit or push was performed. Existing input artifacts are read only. All new outputs are in this directory.

## Reproduction

From the repository root, with ordinary Python 3.10+ (standard library only; do not use `-O`):

```text
python experiments/analysis/economic_aes_existing_evidence_2026_10/audit_existing.py
python experiments/analysis/economic_aes_existing_evidence_2026_10/audit_supplementary.py
```

The first script independently reconstructs the historical data, verifies source/validation hashes, pairing, full sample grids, CSV/JSON agreement, session summaries, original aggregate values and manuscript rounding, and writes economic CSVs and the SVG. It never imports experiment implementations. The second inventories local records and archives, checks the previous cross-platform audit's input hashes, and rechecks CPU/page statistics using inspected pure statistical modules. It imports no benchmark runner, native library or GPU engine. Bytecode writes are disabled.

Reproduction needs the local ignored result directories and archives, not just a GitHub clone. The supplementary manifest retains original absolute paths from the earlier audit; on another machine, preserve the relative tree and adapt those manifest paths through a reviewed copy inside this output directory. No network is required for either analysis. `git_provenance.json` is a fixed receipt from the separate public-source check, not refreshed by offline reproduction.

The scripts overwrite only their own derived outputs beside the scripts. Markdown files are authored audit interpretations. Hash manifests enumerate consumed evidence; hashes establish consistency, not protection against coordinated alteration. Numerical comparisons use relative tolerance 1e-10 and absolute tolerance 1e-15; identities, seeds, counts and validation flags are exact. Failed assertions block a successful result and must be investigated, not disabled.

## Reading order and data dictionary

1. `DATASET_AUDIT.md`, `CPU_THREADING_AUDIT.md`, `MEASUREMENT_BOUNDARIES.md` establish provenance and scope.
2. `RECONSTRUCTED_RESULTS.csv`: all 60 original groups (ECB retained for audit completeness; only CTR enters the economic model). Throughput is median of five per-session medians of individual rates. Times are separately aggregated. Nine manuscript comparison cells are populated; blank cells mean no supplied reference.
3. `RECONSTRUCTED_SESSION_RESULTS.csv`: 300 original session groups, including raw locations, both throughput estimators and pipeline kernel components.
4. `SESSION_ECONOMIC_INDICATORS.csv`: 150 CTR session/path/size rows. Time ratios and rate ratios remain distinct.
5. `ECONOMIC_THRESHOLDS.csv`: 20 GPU profile/scope/size groups, with paired-session median, minimum, maximum and sample SD. `aggregate_rate_price_threshold` drives the normalized sensitivity model. `time_ratio_price_threshold_*` preserves the original paired-time estimator. No range is a confidence interval.
6. `SENSITIVITY_ANALYSIS.csv`: 120 scenarios (five sizes, two GPU profiles, two scopes, six hourly ratios). CPU cost is normalized to 1/hour. Resident scenarios are compute-only and cannot be used for host-memory offloading decisions.
7. `sensitivity_decision.svg`: baseline pipeline decision map, all five sizes, unrounded aggregate-rate thresholds. Full scenario values and session variation remain in CSV.
8. `DATASET_INVENTORY.csv`, `SUPPLEMENTARY_CHECKS.csv`, `SUPPLEMENTARY_RESULTS.csv` and manifests preserve discovery and supplementary verification.
9. `CLAIM_EVIDENCE_MATRIX.csv` and `ECONOMIC_STUDY_READINESS.md` define permitted claims and author decisions.

Payload MiB uses 2^20 bytes. MB/s and GB use 10^6 and 10^9 bytes. Seconds/GB extrapolates repeated batches at the observed batch rate, not a measured contiguous 1 GB message. All observations concern encryption; no authentication or decryption cost is modeled.
