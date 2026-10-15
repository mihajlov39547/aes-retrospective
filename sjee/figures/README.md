# Focused manuscript evidence and figure

The manuscript uses `aesni_gpu_scopes.pdf`, a vector plot of the retained CUDA
path versus AES-NI. `aesni_gpu_scopes.png` is its high-resolution preview.
Neither the software-only CPU nor optimized-v1 curves are included.

Regenerate from the repository root with:

```powershell
.venv/Scripts/python.exe sjee/prepare_focused_figures.py
```

Python and matplotlib are required. No GPU or benchmark execution is needed.
The script reads original study CSVs (T4 directly from its authoritative tar
archive), checks their recorded hashes, verifies retained estimates against
the independent audit, and writes only within `sjee/`. It selects the archived
`cuda_baseline` implementation; it does not invent a generic GPU estimate or
combine implementation candidates.

`focused_sessions.csv` contains each retained session median;
`focused_paired_speedups.csv` contains CPU/GPU timing ratios per session;
`focused_aggregates.csv` contains medians, ranges, IQRs and CVs;
`focused_evidence.json` records run IDs, raw-file hashes and selection criteria.
The generated `content/focused_results_table.tex` supplies the manuscript table.
All 15 sessions are retained, with 9000 selected raw observations. The original
18000-row campaign also contains paths not reported in the focused article;
its original interleaved order and measurements remain unchanged.

The previous five illustrations were removed from this manuscript directory;
their originals remain untouched in repository `figures/` and the completed
cross-platform analysis. No historical experimental output is modified.
