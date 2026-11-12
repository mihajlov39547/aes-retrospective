# JART manuscript revision — Phases 1 and 2

## Phase 2 — author information and declarations

Updated `main.tex` and rebuilt `main.pdf` following the [official JART submission guidelines](https://jart.icat.unam.mx/index.php/jart/about/submissions). The guidelines require full author information and funding/conflict disclosures in the manuscript; no specific initial-submission layout is prescribed.

Added Marko Mihajlović's supplied faculty, university, city/country, email and ORCID immediately below the title on page 1, and set the PDF author metadata. Added the exact author-supplied unfunded-work and no-conflict statements under **Funding** and **Conflict of interest**, immediately after Conclusion and before References on page 9. No ECOSwarm funding was attributed to this work. Scientific text, numerical results and bibliography were preserved.

Rebuilt with XeLaTeX/Biber and passed the updated document checks: author details on the first page, declaration wording/order, resolved citations, figure/table ordering, intact links, page bounds and no LaTeX warnings. Visually inspected the first page and declaration/reference pages. Current PDF: **10 pages; 32,990 characters including spaces; 28,380 excluding whitespace**, using the counting convention below. No submission was initiated or administrative form prepared.

## Phase 1 record

Completed 12 November 2026. The revised scientific manuscript is `main.tex`, with compiled `main.pdf`, `references.bib`, and three vector PDF figures in `figures/`. This is a scientific working draft, not a final journal submission package.

## Starting point and preservation

Revised the existing English `univerzitetska-misao/mihajlovic2026validiran.tex`, retaining its experimental evidence, both numerical tables, and both result figures. Its English PDF dated 5 November 2026 was identified (11 pages). The associated bibliography is `references.bib`; no file named `mihajlovic2026validiran.bib` was found. Source-file hashes in `verification/original_hashes.json` confirm that the original manuscript artifacts remain unchanged; transient Word lock files are excluded from the preservation check.

No benchmarks were run, and no raw dataset or existing audit output was changed. All new artifacts are under `paper_jart/`.

## Substantial changes

- Applied the requested title to the manuscript and PDF metadata. Recast the Introduction around heterogeneous AES execution and the requested research question, with three explicit technical/model contributions.
- Expanded Related Work to distinguish Iwai, Tezcan, Gregg–Hazelwood, Lee, Fei, and Yang–Jeong. Acknowledged prior transfer-inclusive AES work and avoided claims of a new transfer-timing concept. Cleaned the bibliography to 12 cited, verified entries; see [reference verification](verification/REFERENCE_VERIFICATION.md).
- Expanded the methods with recorded software environments, AES/counter configurations, validation and pairing, five-session aggregation, exact threading terminology, and allocation/timing asymmetries. Added an estimator equation and a source-checked grayscale vector measurement-boundary diagram.
- Preserved the primary/v1 throughput table and both existing result plots, regenerated from audited CSVs. Kept T4 independent-page results separate, explained the 16 MiB anomaly without attributing a cause, and distinguished throughput ratios from session-paired timing ratios. An additional absolute-time T4 table was not needed to interpret the retained four batch ratios.
- Made normalized resource-time costs a secondary engineering implication. Retained all three audited price thresholds and sensitivity qualifications; removed investment/break-even discussion unsupported by real pricing, utilization, or fixed costs.
- Refocused Discussion and Conclusion on path selection, implementation effects, batching, CTR security limits, multicore limits, and realistic future work. Parquet remains an unbenchmarked motivating application.
- Rewrote the abstract (195 whitespace-delimited words) and keywords. Deleted the entire final SUMMARY; the manuscript ends with References. Used a plain numbered A4 working layout, with no administrative forms or journal acceptance claims.

## Validation and final counts

`verify_evidence.py` independently reconstructed all 15 displayed primary/v1 throughput cells from the five original raw CSVs, checked normalized costs and thresholds against the audit, and reconstructed the four T4 time ratios from the five raw JSONL sessions. All checks passed. Both datasets remain separate. Results and consumed-input hashes are in `verification/numerical_checks.json`.

`verify_document.py` confirmed 12 resolved citation keys, three figures and two tables first referenced in numerical order, four equations, intact external link destinations, no SUMMARY, no empty pages, and all extracted words within page bounds. The final XeLaTeX log has no undefined references, overflow/underflow warnings, or other LaTeX warnings. All pages were visually inspected; the measurement diagram, equations, plots, tables, bibliography wrapping, and final-page placement are readable without clipping. Wrapped URL text retains the complete hyperlink target. Publisher access restrictions are distinguished from malformed links.

Phase 1 PDF: **10 A4 pages; 32,701 characters including spaces; 28,128 characters excluding whitespace.** Counts use PDF-extracted text, collapse whitespace to single spaces, remove page-number footers, and include the title, headings, captions, figure labels, tables, equations as extracted, and references. Current machine-readable details are in `verification/document_checks.json`.

## Rebuild

Requires XeLaTeX and Biber (tested with TeX Live 2025), Python 3.12 and Matplotlib for figure regeneration. Numerical/document checks use the Python standard library and Poppler's `pdftotext`/`pdftohtml` tools. From the repository root:

```powershell
.\paper_jart\build.ps1
python paper_jart/verify_evidence.py
python paper_jart/verify_document.py
```

The build runs figure generation, XeLaTeX, Biber, and two further XeLaTeX passes. The supplied vector figures also permit compilation without regenerating them: run `xelatex main.tex`, `biber main`, then `xelatex main.tex` twice from `paper_jart/`. Verification and regeneration require the existing local evidence tree. `verification/revise_source.py` records how the initial manuscript copy was revised; it is not part of the normal build and should not be rerun after manual manuscript edits.

## Unresolved issues and scope limits

- No numerical inconsistency or unresolved bibliographic metadata mismatch remains. Yang–Jeong's full text was blocked by the publisher; its metadata and publisher-deposited abstract were verified, and the discussion is restricted to that supported scope.
- The cause of the 16 MiB dip, native-thread/core residency, production CUDA performance, energy use, actual resource prices, and application-level Parquet benefit remain unmeasured. The manuscript explicitly limits its claims accordingly.
- Public availability of the complete raw-data archive is not established. Local reproducibility is documented without claiming a released public dataset.
- The author stated that the related manuscripts are not accepted and requested deferral of overlap review. No publication status or invented citation was added. Submission packaging, journal-format compliance, affiliations, declarations, and forms remain outside Phase 1.
