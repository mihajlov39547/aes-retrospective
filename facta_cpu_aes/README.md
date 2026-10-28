# Facta Universitatis â€” independent CPU AES manuscript

**Title:** When AES Throughput Depends on the CPU Execution Path: Evidence from x86-64 and Arm64

This is an independent manuscript **draft** based only on historical CPU experiments and retrospective material. It was not submitted to a journal. It is **not** a revision of the currently submitted SJEE manuscript about CUDA AES-CTR page processing.

## Documents and build

- `main.tex`, `content/`: shared manuscript sources for PDF and DOCX.
- `main.pdf`: PDF proof using the same layout and typography as `sjee/sjee.sty`.
- `main_facta.docx`: Word document generated from a copy of `sjee/SJEE_Template.docx`, preserving its styles and page settings.
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

The optional preview uses LibreOffice, with the same executable fallback as SJEE; `render_facta_docx.ps1 -SofficePath <path>` accepts an explicit executable. It writes `build/docx_preview/main_facta.pdf`; Word pagination may differ.

The PDF wrapper `facta.sty` loads the shared SJEE style directly. The DOCX adapter reuses the SJEE renderer and validator, including vector figures with PNG fallbacks and editable native Word equations. Both builds read metadata, abstract, keywords and body from `content/`. References remain in `content/07_references.tex`; DOCX citation numbers preserve the PDF's manual bibliography order. No Pandoc or separate Word manuscript source is used.

`build/docx/build_report.json` records template/source hashes and validation results; `build/docx/manuscript.json` is generated intermediate data. PDF logs are retained for diagnosis. The original SJEE Word template is never modified.

The SJEE layout is used intentionally as requested. These outputs do not claim compliance with the official Facta Universitatis template. Review the final document in Word before submission.

## Scientific boundaries

1. No GPU, GPU-resident, CUDA page batching, or host-device transfer results reused from SJEE.
2. The older CBC/GCM and Oracle CPU measurements are retrospective; no new experiments were conducted.
3. T600 was part of the historical Windows GPU campaign but not an equivalent OpenSSL EVP CPU study; no unsupported quantitative claim was made for it.
4. OpenSSL `armcap=0` masks multiple capabilities and cannot isolate the contribution of the AES extension alone.
5. Windows and Oracle timings are separate platform observations, never paired between computers.
6. If SJEE includes the same exact CPU baseline observations, disclosure/citation of related submitted work may be required. Verify substantial overlap before submission.

**Verification to do before submission:** reconcile all numbers with the original archive summaries; inspect each DOCX page in the official template; check citation bibliographic metadata; inspect journal rules and copyright/warranty paperwork; disclose relevant overlapping submissions to the editor.
