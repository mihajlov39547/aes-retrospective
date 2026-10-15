# Focused manuscript evidence and figure

## Absolute-throughput comparison

`bulk_throughput.pdf` compares CPU AES-NI, resident GPU execution, and the
prepared-buffer GPU pipeline at 32 MiB, with separate ECB and CTR panels on the
same zero-based scale. Bars are medians of five session throughput medians;
whiskers show the observed session range, not confidence intervals. Colors and
hatches distinguish execution paths in color and grayscale output.

Regenerate this figure independently with:

```powershell
python sjee/prepare_throughput_figure.py
```

The generator reads the original raw records in `experiments/results_orchestrated/`,
including the T4 archive without extraction, and verifies their hashes against
`focused_evidence.json`. It reconstructs 90 session estimates from 1,800 selected
observations and compares each estimate with the previously audited session data.
`bulk_throughput_sessions.csv` contains those estimates and
`bulk_throughput_evidence.json` records the original paths, hashes, estimator,
medians, and ranges. `bulk_throughput.png` is the preview. All outputs stay in
`sjee/`; the original experiment data and existing figure are unchanged.

## Relative-speedup comparison

The manuscript uses `aesni_gpu_scopes.pdf`, a vector plot of the retained CUDA
path versus AES-NI. `aesni_gpu_scopes.png` is its high-resolution preview.
The two panels show ECB and CTR, each combining all three systems. Blue denotes
GTX, orange T600, and green T4; circles, squares, and triangles distinguish the
systems in monochrome. Solid lines show resident execution and dashed lines show
the pipeline. The shared legend identifies
all six curves. Shading retains the observed five-session ranges.
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
