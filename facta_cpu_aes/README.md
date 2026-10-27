# Facta Universitatis — independent CPU AES manuscript

**Title:** When AES Throughput Depends on the CPU Execution Path: Evidence from x86-64 and Arm64

This is an independent manuscript **draft** based only on historical CPU experiments and retrospective material. It was not submitted to a journal. It is **not** a revision of the currently submitted SJEE manuscript about CUDA AES-CTR page processing.

## Documents

- `main.tex`, `facta.sty`, `content/`: fully rewritten English LaTeX manuscript.
- `main.pdf`: compiled reference proof (8 pages, including bibliography).
- `facta_draft.docx`: editable Word export for further formatting against the official journal DOC template; **it has not been validated as an exact journal template**.
- `figures/`: three newly generated plots, none reused from SJEE.
- `evidence/`: read-only copied Chapter 9 source for auditing and exported CPU campaign session summaries from source archives.
- `EVIDENCE_AND_OVERLAP.md`: mapping of the findings to evidence and journal overlap warnings.

## Build

Run `pdflatex main.tex` twice. The file `facta.sty` retains only minimal typographic conventions from the supplied source style but switches to an A4 single-column layout; it does not claim to be the official Facta Universitatis Word layout.

The journal requires a **Word submission**, an abstract of 50–150 words, and generally no more than 15 typed pages including at most eight figures/tables. The provided DOCX is an editable draft: copy it into the official journal's supplied DOC template and check all styles, equations, citations and figures before submitting.

## Scientific boundaries

1. No GPU, GPU-resident, CUDA page batching, or host-device transfer results reused from SJEE.
2. The older CBC/GCM and Oracle CPU measurements are retrospective; no new experiments were conducted.
3. T600 was part of the historical Windows GPU campaign but not an equivalent OpenSSL EVP CPU study; no unsupported quantitative claim was made for it.
4. OpenSSL `armcap=0` masks multiple capabilities and cannot isolate the contribution of the AES extension alone.
5. Windows and Oracle timings are separate platform observations, never paired between computers.
6. If SJEE includes the same exact CPU baseline observations, disclosure/citation of related submitted work may be required. Verify substantial overlap before submission.

**Verification to do before submission:** reconcile all numbers with the original archive summaries; inspect each DOCX page in the official template; check citation bibliographic metadata; inspect journal rules and copyright/warranty paperwork; disclose relevant overlapping submissions to the editor.

## Build and references

On Windows PowerShell run `./build.ps1` (or `./build.ps1 -Clean`); on Linux use `bash build.sh` (or `bash build.sh --clean`). Requires `pdflatex` from MiKTeX/TeX Live; run from the project root. The build is self-contained and does **not** require BibTeX: citations are keyed by `\\cite{...}` and reference entries are maintained in `content/07_references.tex` with `\\bibitem{...}`. Do not copy the SJEE build script or its full bibliography verbatim, as its section/file layout and citation selection differ. A `.bib` database can be introduced separately when converting to the journal's official Word template.
