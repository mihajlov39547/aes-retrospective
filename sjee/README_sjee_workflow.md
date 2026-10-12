# SJEE manuscript workspace

According to the supplied SJEE submission instructions, initial submissions
may be Microsoft Word or PDF. This workspace makes an SJEE-like single-column
PDF with pdfLaTeX; PDF is the primary initial submission target. It contains
only placeholders, including one explicitly fictional bibliography entry.
No AES manuscript text or results have been inserted.

## Layout and template inspection

The original `SJEE_Template.docx` was inspected read-only as an OOXML ZIP
archive, including its document settings and paragraph styles. It was not
converted to LaTeX, edited, or moved. The LaTeX layout was written manually.

The Word page dimensions are 9356 by 13325 twips (approximately 16.5 by
23.5 cm). Its margins are 1134 twips left/right, 1588 top, and 964 bottom.
`sjee.sty` uses a custom 16.5 by 23.5 cm page with 2.0 cm side margins,
2.8 cm top and 1.7 cm bottom margins, giving a 12.5 cm text width. A4 is
not used. Word defaults specify Times New Roman; LaTeX uses the Times-like
`newtxtext` and `newtxmath` fonts.

The body is justified, 11 pt, single-spaced (13.2 pt baseline), with a
0.7 cm first-line indent and 3 pt between paragraphs. The title is centered,
bold, 16 pt; authors are centered, bold, 12 pt. Abstract and keywords are
10 pt with 0.5 cm side insets. Sections are numbered, bold, 12 pt;
subsections are numbered, bold, 11 pt. References are numeric and 9 pt.
Figure captions are centered below figures as `Fig. 1 − Caption text.`;
table captions are centered above tables with the number on its own line.

This is a submission-oriented approximation, not an official SJEE LaTeX
class. Publisher issue/volume headers, running titles and production
metadata are intentionally omitted. References use an unnumbered heading
after Section 7, and a simple `unsrtnat` bibliography rather than a custom
journal bibliography style. Check final reference punctuation against the
Word examples when replacing the fixture with real sources.

## Build the PDF

Install TeX Live or MiKTeX with pdfLaTeX, BibTeX and the packages named in
`sjee.sty` (including newtx, geometry, graphicx, booktabs, array, caption,
amsmath, natbib, hyperref, titlesec, indentfirst and float).

From this directory in PowerShell:

```powershell
.\build_sjee.ps1
```

The script runs pdfLaTeX, BibTeX when the auxiliary file requests a
bibliography, and two more pdfLaTeX passes. It stops on errors, checks for
unresolved references and reports final-pass warnings. Output is `main.pdf`.
Logs and auxiliary files remain available for diagnosis; sources are never
deleted. Biber is not needed for this BibTeX workspace.

## Editing the skeleton

Use ordinary `\title`, `\author`, `\thanks`, `abstract`, `\section`,
`\subsection`, `equation`, `\caption`, `\label`, `\ref` and `\cite` markup.
The affiliation footnote has no email address. Optional `\\` in the title
provides a soft line break. Keep layout changes in `sjee.sty`.

There is no two-column layout. Insert each figure/table near its first
mention. The simple `[H]` environments keep each item at its source
position, moving it to the next page if necessary. Avoid complex floating
layouts, grouped multi-image objects, landscape pages, scaled tables and
image-based equations. Reference every figure and table in the text; use
units in square brackets. Use proper numbered display equations.
See `figures/README.md` for image guidance.

Replace the fictional `placeholder2026` reference before submission. Add
real entries to `references.bib` and cite them with `\cite{key}`. BibTeX
assigns numbers in citation order.

## Test export to DOCX

Install Pandoc; optional `latexpand` (and its Perl runtime, if required by
the TeX installation) is used only if direct conversion fails.

```powershell
.\convert_to_docx.ps1
```

The script tries the following direct conversion, adding the local numeric
CSL style and section numbering:

```powershell
pandoc main.tex --bibliography=references.bib --citeproc --reference-doc=SJEE_Template.docx --csl=sjee-numeric.csl --number-sections --metadata=reference-section-title:References -o main_sjee.docx
```

On failure it runs `latexpand main.tex`, writes UTF-8 `main_flat.tex`, and
retries Pandoc with that file. Flattening expands inputs, but does not make
arbitrary LaTeX styling portable. `sjee-numeric.csl` is a minimal local
numeric style, not an official SJEE citation style. Without it Pandoc's
default citation style would not match the numeric PDF citations.

The reference DOCX supplies page settings and available Word styles; it
does not automatically map Pandoc's standard styles to SJEE's custom
`JTitle`, `JAuthor`, `JAbstract`, `JText`, `JSubtitle`, `JFigure`, and
`JReference` styles. The LaTeX style package is not a DOCX stylesheet.
Manual cleanup is expected, especially equations and their numbering,
cross-references, tables, captions, references, title and affiliation.
The TeX-only placeholder box may be omitted; replace it with a real image.
A successful conversion only confirms that a test DOCX was generated.

Open `main_sjee.docx` in Word and inspect/fix it before delivery. If the
journal requires final Word, use the untouched `SJEE_Template.docx` as the
final visual reference and copy/import its styles as needed. Never replace
the original template with a generated document.

## Initial validation (2026-10-12)

The PDF was built with pdfLaTeX and BibTeX and both rendered pages were
visually inspected. It has the custom page size, one column, title, author,
affiliation footnote, abstract, keywords, seven sections, one subsection,
one right-numbered display equation, one figure box, one table,
acknowledgments and a numeric reference. The final build has no warnings,
undefined references or overfull/underfull boxes.

Direct Pandoc export succeeded. Pandoc reported that parsing the included
`sjee.sty` failed; this is a limitation of importing LaTeX presentation
commands and does not prevent export of the manuscript body. Inspection
of the generated DOCX XML confirmed numeric citations, section content,
table content and native Word math. It also exposed expected cleanup:
the box is omitted, the equation reference appears as `[eq:example]`,
caption labels need restoration, and the abstract has an extra heading.
The DOCX has not been visually approved in Word. The latexpand fallback
is implemented but was not exercised because direct conversion succeeded.

The original Word template's SHA-256 was verified unchanged:
`51ab1782847fabe6910f7fa4af264bc25c3bad8585f0db54d31fe963941e578d`.
