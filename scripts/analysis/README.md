# Offline paired AES scientific analysis

Run from the repository root with Python 3.10+. Statistics, manifest checks,
CSV and archive handling use the standard library. Plotting needs matplotlib
(already used by this repository). No GPU, CuPy import, benchmark execution,
cloud account or network access is needed. Do not install CUDA for analysis.

```powershell
.\.venv\Scripts\python.exe scripts/analysis/cross_platform.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_analysis.py -v
```

Linux equivalents:

```bash
.venv/bin/python scripts/analysis/cross_platform.py
.venv/bin/python -m unittest discover -s tests -p test_analysis.py -v
```

The default discovers `config.resolved.json` under
`experiments/results_orchestrated/`, inventories runs, and selects the three
explicit run-ID hints from the October 2026 study. Hints never bypass validation.
Defaults write to `experiments/analysis/cross_platform_2026_10/`. Existing output
directories are refused: choose a new path for subsequent analyses.

```bash
python scripts/analysis/cross_platform.py --run t4=/path/to/intact/run --output build/reanalysis
python scripts/analysis/cross_platform.py --archive t4=/path/to/original-colab.tar.gz --output build/archive-analysis
python scripts/analysis/cross_platform.py --root /path/to/studies --run gtx1650ti=/path/to/run1 --run t600=/path/to/run2 --run t4=/path/to/run3 --output /path/to/new-analysis
python scripts/analysis/cross_platform.py --historical-run earlier_windows=/path/to/earlier/complete/orchestrated-study --output build/with-history
```

Recovered October T4 archive (Windows or Linux, from the repository root):

```bash
python scripts/analysis/cross_platform.py --archive "t4=experiments/results_orchestrated/t4-colab/heterogeneous-core-v1-20261014T105540691660Z-9bb918a84386.tar.gz" --output experiments/analysis/cross_platform_2026_10_complete
```

The original incomplete T4 extraction truncated long archive paths at 100
characters. The intact archive uses PAX path metadata; the Python tar reader
preserves it, including names sharing the same legacy 100-byte prefix. No damaged
input is renamed or repaired in place. `IMPORT_RECOVERY.md` distinguishes import
failures from statistical discrepancies. `archive_extraction_receipts.json`
records every member name/size/hash and verifies extracted bytes against the
decompressed stream. The archive hash is checked again at analysis completion.
If necessary, supply `--scratch-root C:\aes-tmp` for a shorter temporary parent;
this addresses destination path length, not a parser ignoring PAX metadata.

Use quotes around `LABEL=PATH` containing spaces. Labels `gtx1650ti`, `t600`,
`t4` identify the requested primary platforms; explicit directories override
their defaults. ZIP and tar archives are read into a temporary workspace, with
path traversal, symlinks, duplicate names and excessive extracted size rejected.
Original files and archives are never renamed or repaired. Archive selection
requires exactly the requested study run. `--no-figures` omits plotting dependencies.
Optional historical runs retain their own role/run ID and are never pooled or
included in primary figures. Legacy native archives are inventoried but not
silently converted into orchestrated runs.

Exit 0 means all three requested primary studies passed. Exit 2 emits the audit
and available validated analyses but flags incomplete/invalid inputs; failed
platforms are visibly unavailable in plots. Fatal configuration errors exit
nonzero without claiming success. Truncated imports are diagnosed, not repaired
or promoted based on a saved `COMPLETED` status.

`core.py` independently reads raw CSV, verifies count/group/repeat/pair/scope/unit
contracts, recomputes extended statistics and aggregates session-level medians.
`cross_platform.py` adds manifest/native hash checks via the existing read-only
verifier and compares every saved statistic/aggregate. `reports.py` renders
tables and eight PNG/vector-PDF figures. No benchmark module is imported.
Median throughput is computed from the individual rates; paired GPU speedup
uses CPU median time / GPU median time within each session, then the median of
five ratios. Other derived contrasts are explicitly named, never substituted
for those original estimators. All data remain in their platform and scope.

CSV outputs carry run/seed/group identities. `session_level_statistics.csv`
contains repetition distributions per session; `independent_aggregates.csv`
contains across-session estimates and variability. `session_contrasts.csv`
contains size/mode/backend comparisons before across-session aggregation.
The IQR uses inclusive linear quantiles, CV uses sample SD/mean and is undefined
at zero mean. No outliers are removed; no significance tests or n=100 session
claims. Numerical tolerance is relative 1e-10 and absolute 1e-15.

The reproducibility manifest records all selected input SHA-256 hashes, analysis
and verifier source hashes, software versions, tolerances, archive identity,
audit checks and generated-file hashes. It verifies selected inputs unchanged
at completion. It intentionally omits wall-clock analysis timestamps. Figure
PDF dates are omitted and SVG hashing is fixed. Floating-point/library rendering
can still differ across Python/matplotlib versions: compare within the documented
tolerances and use the recorded environment for byte-level reproduction.

The generated report's `publication` styling describes presentation quality,
not evidence of statistical significance or generalizability. Consult the
integrity report before using any numerical result.
