# SJEE manuscript builds

The PDF and Word builds use the same LaTeX manuscript sources in `content/`,
ordered by `main.tex`, and the same `references.bib`. Edit these sources rather
than the generated Word file. The supplied `SJEE_Template.docx` is never changed.

| Target | Command from `sjee/` | Output |
| --- | --- | --- |
| LaTeX PDF | `./build_sjee.ps1` | `main.pdf` |
| PDF and Word document | `./build_sjee.ps1 -Target All` | `main.pdf` and `main_sjee.docx` |
| Word through the shared entry point | `./build_sjee.ps1 -Target Docx` | `main_sjee.docx` |
| Word document | `./build_sjee_docx.ps1` | `main_sjee.docx` |
| Word and rendered preview | `./build_sjee_docx.ps1 -RenderPreview` | DOCX and `build/docx_preview/main_sjee.pdf` |

From the repository root, run `./sjee/build_sjee.ps1 -Target All` to rebuild both
formats. The default remains PDF-only. `-PythonPath` and `-RenderPreview` are
also supported with `-Target Docx` or `-Target All`; failures stop the combined
build. The separate DOCX entry point remains available.

## Requirements

The PDF build requires TeX Live or MiKTeX. The Word build requires Python, the
packages in `requirements_docx.txt`, and `pdftocairo` from TeX Live or Poppler on
PATH. LibreOffice is needed only for the optional rendered preview.

```powershell
python -m venv .venv-docx
./.venv-docx/Scripts/python.exe -m pip install -r requirements_docx.txt
./build_sjee_docx.ps1
```

The script prefers `.venv-docx/Scripts/python.exe`, then falls back to `python`.
`-PythonPath` accepts another interpreter, including a path relative to the caller.
The build can be invoked from outside `sjee/`. All outputs and preview profiles
stay inside this directory. No Pandoc or Microsoft Word installation is required.

## SJEE formatting

The adapter fills a copy of the supplied template, retaining its paragraph styles,
original numbering definitions, page dimensions, margins, and affiliation footnote.
Sample text, running headers, and unused template illustration/equation objects are
removed. New native list instances restart at one without altering the template's
numbering definitions. The document retains its ordinary draft page-number footer.

- The title uses soft line breaks where needed, with the full author name and
  affiliation from `content/metadata.tex`.
- Abstract and keywords use the template abstract style; keyword entries receive
  initial capitals. Section headings retain their source titles; subheadings use
  sentence case while preserving acronyms and mixed-case identifiers.
- Body paragraphs use `JText`; text immediately following a display equation uses
  `JText-noIndent`. Paragraph spacing and indentation come from the template.
- Both inline and display math are editable native Word equations (OMML), with
  11 pt full-size math. Display equations have a tab on each side and a right-hand
  number. Upright units and textual subscripts remain native math text, and tilde
  accents retain their equation structure. A failed conversion stops the build;
  text placeholders or equation images are not substituted.
- Numbered and unordered lists use `JText-numberedList` and
  `JText-unorderedList`, with native Word numbering rather than typed prefixes.
- Tables are editable Word tables with template borders, repeated header rows,
  non-splitting rows, captions above, and retained notes and bold results. Short
  tables are kept together. In-text table references are bold, and throughput
  column units appear in square brackets.
- Figures are embedded as SVG vectors with high-resolution PNG fallbacks, both
  derived from the original vector PDFs. Their captions appear below the images.
  The plot generators and original vector files remain in `sjee/`. GPU markers
  distinguish systems in monochrome, line styles distinguish execution scopes,
  and the throughput chart retains its hatches.
- References are numbered in first-citation order and include only cited entries,
  unless `main.tex` explicitly requests `\nocite{*}`. Journal-style entries use
  the available source author, title, publication, volume, issue, date, pages,
  chapter, DOI, and URL fields; missing bibliographic information is not invented.
  The References heading follows the numbered main sections.

## Supported source and validation

The bounded LaTeX adapter handles the current manuscript's nested `\input` files,
sections, subsections, paragraphs, emphasis, citations, references, numbered and
unordered lists, inline/display math, PDF figures, and booktabs/tabular/tabularx
Tables with merged headers and notes. Unknown constructs fail explicitly.

`build/docx/manuscript.json` records the expanded content, labels, citation order,
and source hashes, including included tables and figure PDFs.
`build/docx/build_report.json` records the output counts and validation results.
Generation validates a temporary DOCX before replacing the previous successful
output, and checks that sources and the original template did not change during
conversion. It verifies style preservation, original numbering definitions, page
settings, table/figure counts, embedded vectors, native math counts, and removal
of sample headers and legacy equation objects.

Run the adapter regression checks from `sjee/`:

```powershell
./.venv-docx/Scripts/python.exe -m unittest discover -s tests -v
```

The current manuscript exports six tables, two figures, six display equations,
and 23 cited references. Labels and citation numbers are reconstructed from the
sources rather than read from potentially stale PDF auxiliary files.

## Preview and delivery

```powershell
./render_sjee_docx.ps1
# Or specify LibreOffice explicitly:
./render_sjee_docx.ps1 -SofficePath 'C:/path/to/soffice.exe'
```

The preview uses a copy in `build/docx_preview/` and does not overwrite `main.pdf`.
LibreOffice and Microsoft Word can paginate differently. The current export has
been rendered with LibreOffice and checked for title, equation, figure, table,
and reference layout. Final Word pagination may differ. Citation and caption
numbers are generated text, not interactive cross-reference fields.

The build preserves the manuscript's selected sections: an unused acknowledgments
placeholder is not inserted. No journal issue, DOI, funding, or affiliation data
are invented. Rebuilding replaces manual edits to `main_sjee.docx`; keep any
final Word-only delivery edits in a separate copy.

The deprecated Pandoc experiments remain in `experimental/legacy/` and are not
part of either current build.

Original template SHA-256:
`51ab1782847fabe6910f7fa4af264bc25c3bad8585f0db54d31fe963941e578d`.
