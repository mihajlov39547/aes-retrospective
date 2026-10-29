# Formatting review ? 2026-10-29

Completed:
- Reconstructed grayscale figures from the existing audited CSVs using prepare_figures.py; no benchmarks executed or measurements altered.
- Three shades/hatches for GTX throughput; discrete categorical T4 points without interpolation. The caption explicitly separates the campaigns.
- Bold figure numbers, italic titles, and separate author-results source notes in PDF and DOCX.
- Shared references.bib with APA formatting (biblatex-apa for PDF, vendored APA 7 CSL for DOCX), numbered 10-point references; narrative Serbian conjunction and et al. citations.
- Corrected Gregg entry type to conference proceedings. Kept Lee conference DOI 10.1145/1815961.1816021; Crossref metadata confirmed proceedings-article, ISCA proceedings, pp. 451?460.
- Rebuilt anonymous article and separate author cover, including institution, city/country, email and ORCID.

Validation:
- Build checks: 13 cited references, two tables, two figures, three display equations, abstract lengths within 100?200 words, no unresolved references.
- Both embedded PNGs verified pixel-by-pixel as grayscale (2160 x 1110, rasterized at 300 dpi).
- LibreOffice export reviewed visually: equations (1)?(3), both figures/captions, bibliography and author cover.
- Article: 12 pages; separate cover: one page. B5 17.6 x 25.1 cm; 2.5 cm margins. SUMMARY occupies one page.

Limits / not done:
- No original plotting script was found: original authorship of the supplied PDF plots is not established. The replacement script uses documented existing numerical evidence.
- No Microsoft Word application rendering was performed; LibreOffice export is the visual check. Final Word pagination should be checked before submission.
- This is a formatting check, not a fresh review of every bibliographic source or certification of acceptance by the journal.
- No experiments, data edits, installation of dependencies, commit, push or submission.

The separate cover already existed; it was checked and rebuilt, not invented.
APA CSL source: https://github.com/citation-style-language/styles/blob/master/apa.csl
License: CC BY-SA 3.0 (full attribution and license URL in apa.csl header).
CSL SHA-256: 3917def5fc951b104d64216c3373096042368b9704ba269ca83c14ebaba889fc
