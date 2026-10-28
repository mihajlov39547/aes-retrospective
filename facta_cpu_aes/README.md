# Facta Universitatis - independent CPU AES manuscript

**Title:** When AES Throughput Depends on the CPU Execution Path: Evidence from x86-64 and Arm64

This is an independent manuscript **draft** based only on historical CPU experiments and retrospective material. It was not submitted to a journal. It is **not** a revision of the currently submitted SJEE manuscript about CUDA AES-CTR page processing.

## Documents and build

- `main.tex`, `content/`: shared manuscript sources for PDF and DOCX.
- `main.pdf`: PDF proof using the same layout and typography as `sjee/sjee.sty`.
- `main_facta.docx`: Word document generated from `Facta_Template.docx`, adapted from the supplied official Facta DOC template.
- `facta_draft.docx`: retained historical export; use `main_facta.docx` for the current version.
- `figures/`: three CPU plots; `evidence/` and `EVIDENCE_AND_OVERLAP.md`: evidence and overlap documentation.

From the repository root, run:

```powershell
./facta_cpu_aes/build_facta.ps1                  # PDF
./facta_cpu_aes/build_facta_docx.ps1             # DOCX
./facta_cpu_aes/build_facta.ps1 -Target All      # Both
./facta_cpu_aes/build_facta.ps1 -Target All -RenderPreview
```

Scripts also work from other working directories. PDF requires `pdflatex` and `bibtex` on PATH (BibTeX is only run if the manuscript uses a `.bib` database). DOCX requires Python and `pdftocairo`. The interpreter search checks a local `.venv-docx`, then the existing SJEE `.venv-docx`, then `python`; use `-PythonPath` to override. For a separate environment:

```powershell
python -m venv facta_cpu_aes/.venv-docx
./facta_cpu_aes/.venv-docx/Scripts/python.exe -m pip install -r facta_cpu_aes/requirements_docx.txt
```

The optional preview requires Microsoft Word on Windows and `pdfinfo`. It writes `build/docx_preview/main_facta.pdf`, which shows the actual Word layout (13 pages in the checked build). This is separate from `main.pdf`, the existing LaTeX proof using the SJEE layout.

The DOCX renderer uses the official Facta page geometry and written formatting rules, with editable native Word equations and 300 dpi JPEG illustrations. Companion TIFF files are generated in `figures/submission/`. The shared SJEE parser still reads LaTeX and BibTeX; Facta formatting is implemented separately in `facta_docx_layout.py`. No Pandoc or separate Word manuscript source is used.

Both formats read metadata, abstract, keywords and body from `content/`. Name, affiliation and email come from `content/metadata.tex`; the ORCID is stored in `content/author_details.json` and was taken from the existing SJEE author metadata. References are maintained in `references.bib`; use `\cite{key}`. PDF uses BibTeX with `unsrtnat`, while DOCX resolves citations in first-citation order and uses the Facta bibliography style. Both omit uncited entries.

`build/docx/build_report.json` records source/template hashes and structural validation results; `build/docx/manuscript.json` contains parsed source data. `build/docx_preview/render_report.json` records Word pagination. See `TEMPLATE_REVIEW.md` for the style comparison and visual review.

Edit publication headers and footers in `Facta_Template.docx` to retain them across builds. The received-date placeholder in the generated first-page footnote also needs completion. Direct changes to `main_facta.docx` are replaced by a rebuild.

To recreate the template from the supplied legacy DOC, run the following explicitly; this resets template customizations, including publication metadata:

```powershell
./facta_cpu_aes/prepare_facta_template.ps1
```

Normal builds use the committed `Facta_Template.docx` and do not repeat conversion. The original supplied DOC and SJEE template are not modified.

## Scientific boundaries

1. No GPU, GPU-resident, CUDA page batching, or host-device transfer results reused from SJEE.
2. The older CBC/GCM and Oracle CPU measurements are retrospective; no new experiments were conducted.
3. T600 was part of the historical Windows GPU campaign but not an equivalent OpenSSL EVP CPU study; no unsupported quantitative claim was made for it.
4. OpenSSL `armcap=0` masks multiple capabilities and cannot isolate the contribution of the AES extension alone.
5. Windows and Oracle timings are separate platform observations, never paired between computers.
6. If SJEE includes the same exact CPU baseline observations, disclosure/citation of related submitted work may be required. Verify substantial overlap before submission.

**Verification to do before submission:** reconcile all numbers with the original archive summaries; inspect each DOCX page in the official template; check citation bibliographic metadata; inspect journal rules and copyright/warranty paperwork; disclose relevant overlapping submissions to the editor.

## Reproduce the contribution analysis and Figure 2

```powershell
python facta_cpu_aes/analyze_evidence.py
python facta_cpu_aes/plot_windows_boundaries.py
./facta_cpu_aes/build_facta.ps1 -Target All
```

Run these commands from the repository root. The analysis requires only Python's standard library and reads the existing Windows/Oracle CSV summaries plus the two Oracle study archives under `experiments/results/`. It verifies campaign metadata, correctness records and source hashes, reconstructs Oracle operation durations, and writes `build/evidence/audit.json`. It never runs benchmark code. The plot script requires matplotlib (used version: 3.11.2) and regenerates `figures/windows_boundaries.pdf` from the verified Windows summaries. Plot generation is separate from the document build scripts.

See `REVISION_REPORT.md` for the exact ratios, Oracle provenance, second-Windows-system exclusion decision and validation results.
