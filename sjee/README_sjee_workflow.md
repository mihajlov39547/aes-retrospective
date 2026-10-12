# SJEE manuscript workspace

According to the supplied SJEE instructions, initial submissions may be Word
or PDF. **`main.tex` -> `main.pdf` remains the primary workflow.**
`main_docx.tex` is now only a Pandoc wrapper over the same manuscript.

The author's updated text, equations, six results tables and bibliography
have been preserved. Discussion and Acknowledgments still contain the author's
existing placeholders. No new scientific content was introduced by the refactor.

## Edit shared content once

Both wrappers input these files:

| File | Content |
| --- | --- |
| `content/metadata.tex` | Title, author, affiliation footnote and empty date |
| `content/abstract.tex` | Abstract prose, without label or environment |
| `content/keywords.tex` | Keywords, without label |
| `content/01_introduction.tex` | Introduction heading and text |
| `content/02_related_work.tex` | Related Work and Research Gap |
| `content/03_methodology.tex` | Methodology and throughput equation |
| `content/04_results.tex` | Results, subsections, six tables and captions |
| `content/05_discussion.tex` | Discussion |
| `content/06_conclusion.tex` | Conclusion |
| `content/07_acknowledgments.tex` | Acknowledgments |

Edit these files and `references.bib`, not a second copy of the manuscript
in an export wrapper. Use ordinary LaTeX section, math, table, caption,
label, reference and citation commands. The wrappers contain only output
presentation, include order and bibliography controls.

The PDF wrapper retains the styled abstract, bold labels and the author's
0.2 cm space before Keywords. The DOCX wrapper uses plain `Abstract:` and
`Keywords:` paragraphs, without `sjee.sty` or an abstract environment.
Shared metadata exports the author's affiliation as a Word footnote.

The existing `\FloatBarrier` before Conclusion stays in the PDF wrapper,
with `placeins` loaded to define it. DOCX does not need that layout command.
The author's table specifications and float options are unchanged. There is
currently no figure in the manuscript; the earlier PNG fixture is retained
but is not inserted into either output.

## PDF layout and build

`SJEE_Template.docx` was inspected read-only; the LaTeX layout was written
manually. The original Word template was not converted, edited or moved.
`sjee.sty` remains unchanged: custom 16.5 by 23.5 cm paper, 2.0 cm side
margins, 2.8 cm top margin and 1.7 cm bottom margin. Body text is Times-like
(newtx), 11 pt, justified and single-spaced (13.2 pt baseline), with 0.7 cm
first-line indent and 3 pt paragraph spacing. There is no two-column layout.

The title is centered bold 16 pt; authors are centered bold 12 pt.
Abstract/keywords use 10 pt with 0.5 cm side insets. References are numeric,
9 pt. Figure captions go below figures; table captions go above tables,
with the number on its own line. This is an SJEE-like submission layout,
not an official journal LaTeX class. Publisher production headers are omitted.

Install TeX Live or MiKTeX with pdfLaTeX, BibTeX, `placeins` and the packages
listed in `sjee.sty`. Run:

```powershell
.\build_sjee.ps1
```

The script runs pdfLaTeX, BibTeX when requested, and two more LaTeX passes.
It stops on errors, checks unresolved references, reports final-pass warnings
and keeps logs/auxiliary files. Output is `main.pdf`; Biber is not needed.

Keep figures/tables near first mention, reference them in the text, avoid
complex floating layouts and use proper display equations. Use units in
square brackets where appropriate. These are authoring guidelines; this
refactor did not rewrite the author's captions, units or table references.

## Bibliography during drafting

`references.bib` contains the author's 21 entries and is unchanged byte-for-byte.
The prose currently has typed author-year references, not `\cite{key}` commands.
Those references have been preserved rather than automatically rewritten.

Both wrappers use `\nocite{*}` to include the supplied bibliography before
citation keys are connected. PDF uses `unsrtnat`; DOCX uses the existing
`sjee-numeric.csl`. Numeric bibliography labels do not convert the current
prose references into automatic numeric citations.

Before submission, connect the prose references to the appropriate BibTeX
keys and review SJEE numeric formatting. Remove `\nocite{*}` from both
wrappers when only explicitly cited entries should be included. This
refactor did not infer citation-to-source mappings.

## DOCX export

Install Pandoc. Optional `latexpand` (with Perl if needed) is used only if
direct conversion fails. Run:

```powershell
.\convert_to_docx.ps1
```

The script prefers `main_docx.tex`, otherwise falls back to `main.tex`.
Pandoc reads the shared `\input` files directly. The preferred command is:

```powershell
pandoc main_docx.tex --bibliography=references.bib --citeproc --reference-doc=SJEE_Template.docx --csl=sjee-numeric.csl --number-sections --metadata=reference-section-title:References -o main_sjee.docx
```

On failure, the script runs `latexpand` on the selected input, writes UTF-8
`main_docx_flat.tex` (or `main_flat.tex`), and retries. These are generated
files, not sources to edit. The obsolete unconditional placeholder-image
check was removed because the shared manuscript does not use that image.

The local CSL is a numeric approximation, not an official SJEE citation
style. The reference DOCX supplies page settings and styles but does not
automatically map Pandoc's standard styles onto the custom SJEE styles.

Manual Word review remains necessary:

- Apply SJEE styles; check font sizes, indents, alignment and spacing.
- Inspect the author footnote, equation numbers and cross-references.
- Review all six tables, especially merged headers, widths and borders;
  check caption numbers, alignment, placement and page breaks. A native
  editable table is not proof of visual fidelity.
- Review reference punctuation and connect the author-year prose mentions
  to numeric citations before final submission.
- Remove or correct inherited sample running author/title headers and the
  first-page issue/date/UDC/DOI metadata. Do not invent publication metadata.

If final Word is required, use the untouched `SJEE_Template.docx` as the
visual reference and copy/import its styles as needed. DOCX remains a test
export; PDF remains primary.

## Shared-content validation (2026-10-12)

- The author's abstract, keywords, seven sections, equations, tables, captions,
  Serbian characters and metadata were extracted without rewriting the text.
  `references.bib`, `sjee.sty` and the original Word template are unchanged.
- The pre-refactor source failed at undefined `\FloatBarrier` and had no
  BibTeX citation commands. A temporary comparison build of that same source
  enabled `placeins` and added `\nocite{*}`. All 11 refactored PDF pages are
  pixel-identical to that repaired comparison build. The older two-page
  placeholder PDF was not a valid content baseline.
- `build_sjee.ps1` passed, with no unresolved references. Remaining warnings
  match the comparison build: one 4.55696 pt overfull line in Introduction
  and three underfull lines in the bibliography. They were not reformatted
  because this task preserves the PDF layout.
- `convert_to_docx.ps1` passed without Pandoc warnings. DOCX XML inspection
  confirmed the updated abstract, prose and conclusion, sections 1-7,
  subsections, six native tables, native display math, affiliation footnote
  and 21 numeric bibliography entries, without an extra Abstract heading.
- DOCX checks were structural; the current manuscript still needs final
  visual approval in Word. Earlier placeholder exports showed formatting
  differences during the separate visual experiment.

Original template SHA-256:
`51ab1782847fabe6910f7fa4af264bc25c3bad8585f0db54d31fe963941e578d`.

## Historical Word-filling experiment

`fill_sjee_template_docx.py` and `main_sjee_filled.docx` remain the separate,
frozen placeholder experiment described in [README_docx_experiment.md](README_docx_experiment.md).
They do not contain the author's current manuscript or read `content/`.
Do not use that fixture as the current paper. Its review artifacts refer
to the earlier placeholder documents, not this shared-content manuscript.
