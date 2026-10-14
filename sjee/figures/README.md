# Manuscript figures

All five manuscript graphics are stored here. The PDF build uses only local
`figures/` paths; no external figure directory is needed. `SOURCES.json` records
repository origins and SHA-256 hashes. The four plots are unchanged vector PDFs;
the framework is the unchanged original JPEG (no vector counterpart was found).

| Figure | Local file | Source |
|---|---|---|
| 1 | `benchmarking_framework_grayscale.jpg` | Repository `figures/` |
| 2 | `02_pipeline_throughput.pdf` | Completed cross-platform analysis |
| 3 | `03_pipeline_speedup_vs_aesni.pdf` | Completed cross-platform analysis |
| 4 | `08_pipeline_resident_ratio.pdf` | Completed cross-platform analysis |
| 5 | `05_session_variability.pdf` | Completed cross-platform analysis |

The analysis plots originate in
`experiments/analysis/cross_platform_2026_10_complete/figures/`. Copies preserve
original bytes, vector content and quality. Do not regenerate or alter numerical
plots during manuscript layout work.

The previous local framework JPEG was a stale, different diagram despite sharing
its filename with the repository original. It has been replaced with the existing
validation-first framework diagram that matches the manuscript caption. The
original outside `sjee/` remains untouched.

All figures use `width=\linewidth`, preserve their aspect ratios, have captions
below the image, and retain their original labels. The PDF figure pages were
visually checked for margins, clipping, labels and placement after consolidation.
The embedded plot provenance footnotes are small; the vector PDFs retain their
resolution when enlarged.

The unused `placeholder.png` is no longer in this directory. Its bytes are
preserved in `sjee/experimental/legacy/figures/placeholder.png`, the location
expected by the historical placeholder experiment. It is not a manuscript figure.
No duplicate manuscript graphics or redundant raster plot exports are retained.

This pass validates the PDF build only. The separate historical DOCX adapters
are not validated for these figure environments or vector PDF inputs.
