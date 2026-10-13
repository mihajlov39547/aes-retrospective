# SJEE manuscript workflow

Initial submission may be Word or PDF under the supplied SJEE instructions.
The primary submission target remains the LaTeX PDF. There are two normal builds:

| Target | Command | Output |
| --- | --- | --- |
| PDF | `.\build_sjee.ps1` | `main.pdf` |
| DOCX | `.\build_sjee_docx.ps1` | `main_sjee.docx` |

The DOCX build copies `SJEE_Template.docx` and fills that copy using the
original SJEE paragraph styles, numbering, page settings, table borders and
affiliation footnote formatting. It never calls Pandoc. The supplied template
is never edited or moved. This preserves SJEE formatting better than the old
Pandoc export, although final review in Microsoft Word is still necessary.

## One source of manuscript content

Edit `content/metadata.tex`, `content/abstract.tex`, `content/keywords.tex`,
`content/01_introduction.tex` through `content/07_acknowledgments.tex`, and
`references.bib`. Both builds read these sources. Your abstract, introduction,
conclusion, other prose, equation, six tables and bibliography are preserved;
no scientific content was added or rewritten. Acknowledgments still contains its existing placeholder.

`main.tex` remains the primary PDF entry point and specifies source order.
The DOCX generator reads its shared inputs and creates a generated intermediate
at `build/docx/manuscript.json`, plus `build/docx/build_report.json` containing
source hashes, counts and warnings. These JSON files are audit artifacts,
not additional sources to edit. Rebuilding replaces manual edits to the DOCX;
keep any final Word-only corrections in a separately named delivery copy and
record them before rebuilding.

## PDF build

Install TeX Live or MiKTeX with pdfLaTeX, BibTeX, `placeins` and the packages
listed in `sjee.sty`, then run:

```powershell
.\build_sjee.ps1
```

The script runs pdfLaTeX and BibTeX as needed, resolves references, reports
warnings and stops on errors. The existing PDF layout is unchanged: custom
16.5 by 23.5 cm paper, 2 cm side margins, 2.8 cm top and 1.7 cm bottom margins,
single-column Times-like 11 pt body text, justified paragraphs and 0.7 cm
first-line indents. Abstract and keywords use 10 pt; references use 9 pt.
The template was reproduced manually in LaTeX, not converted from Word.

Keep figures and tables near their first textual reference. Use simple
layouts, proper display equations and units in square brackets where relevant.
Avoid two-column text, grouped floating objects and images of equations/tables.
There are currently no figures in the manuscript; the historical PNG fixture
is retained but is not inserted automatically.

## Primary DOCX build

Python dependencies are isolated in `.venv-docx`. To set up a new machine:

```powershell
python -m venv .venv-docx
.\.venv-docx\Scripts\python.exe -m pip install -r requirements_docx.txt
.\build_sjee_docx.ps1
```

The build script prefers that environment; `-PythonPath` can select another
Python installation with the dependencies installed.
`fill_sjee_template_docx.py` creates `main_sjee.docx` from a template copy.
It preserves the template's style and numbering definitions, title/author,
abstract/keywords, section/body, reference and affiliation-footnote styles.
Tables are editable Word tables with template borders and merged headers;
math is converted to editable native Word equations. Sample running headers
and issue/volume/date/UDC/DOI metadata are removed. Ordinary draft page-number
fields in footers are retained; no publication metadata is invented.

This is a bounded LaTeX adapter, not a general LaTeX converter. It handles the
current manuscript's sections/subsections/subsubsections, numbered lists,
paragraphs, emphasis, inline math, display equations, numeric citations,
label references and simple booktabs/tabular tables including multicolumn headers. Unsupported commands/environments stop the build before replacing
the previous DOCX. New figures and LaTeX constructs outside this supported subset need explicit
adapter support before use in the DOCX path. The original figure
caption style is preserved, but no figure insertion has been exercised in the
current manuscript. Math conversion failures produce visible editable
`[MATH CLEANUP: ...]` text and a build warning instead of losing the expression.

The generator verifies the original template hash and checks preserved styles,
numbering, page settings and cleared headers. If the journal supplies a new
template, inspect its structure and update the adapter deliberately.

## Bibliography and remaining Word cleanup

The current manuscript has 32 BibTeX entries and uses numeric `\cite{key}`
citations. PDF uses `unsrtnat` and `\nocite{*}`. DOCX orders references by first
citation, then includes uncited entries in source order, matching this PDF
configuration. Basic `\ref` and `\eqref` resolve from source labels. DOCX
numbers are regenerated text, not interactive Word citation or reference fields.

Before submission:

- Review numeric citation placement and journal bibliography punctuation.
  The DOCX formatter is deliberately simple; long
  URLs can leave large justified spaces and need Word cleanup.
- Review equation typography and numbering. Caption, heading and equation
  numbers are generated text, not automatic Word cross-reference fields.
- Review all table widths, merged headings, caption placement and pagination
  in Microsoft Word; keep tables near their first mention.
- Finish the existing Acknowledgments placeholder.
- Check final title, affiliation, page breaks and references against the
  untouched `SJEE_Template.docx`. If needed, import its styles into the final
  delivery copy. Do not add unassigned journal issue/DOI/UDC/date metadata.

## Optional visual preview

With LibreOffice installed:

```powershell
.\render_sjee_docx.ps1
# Or: .\render_sjee_docx.ps1 -SofficePath 'C:\path\to\soffice.exe'
```

This renders a copied DOCX to `build/docx_preview/main_sjee.pdf`, never to
`main.pdf`. It can also use the temporary extracted LibreOffice installation
from this session if that installation still exists. LibreOffice preview is
useful for inspection but does not guarantee identical Microsoft Word
pagination. No Word installation is required to generate the primary DOCX.

## Legacy Pandoc export

Pandoc DOCX is deprecated because its visual output did not match the SJEE
custom styles well. It is excluded from both normal build commands.
The former `main_docx.tex` wrapper, `sjee-numeric.csl`, conversion script and
placeholder experiments are clearly archived under `experimental/legacy/`.
The wrapper still reads shared content; it is not an independent manuscript.
For deliberate debugging only, run:

```powershell
.\experimental\legacy\convert_to_docx.ps1
```

It writes only `experimental/legacy/main_sjee_pandoc.docx` and cannot overwrite
`main_sjee.docx`. Older placeholder experiments and `experimental_review/`
are historical artifacts, not current manuscript outputs.

## Validation (2026-10-12)

- PDF build passes: 11 pages, single column. Existing warnings remain: one
  4.55696 pt overfull Introduction line and three underfull bibliography
  lines. The layout has not been reformatted to suppress them.
- Primary DOCX build passes without conversion warnings: current shared prose,
  seven numbered sections, four subsections, six editable tables, one display
  equation, affiliation footnote and 21 numeric references. No extra Abstract
  heading or sample running headers remain.
- All ten pages of the LibreOffice DOCX preview were visually inspected.
  Table borders and merged headers are readable and the equation renders as
  a fraction with a right-hand number. Reference URL spacing and final Word
  pagination still need review. LibreOffice emitted a Python-prefix diagnostic
  but returned success and produced the complete preview.
- Scientific source files, `references.bib`, `sjee.sty` and the original Word
  template are unchanged. The only PDF-wrapper edit describes the DOCX command.
- All 11 PDF pages match the pre-change PDF pixel-for-pixel at 1200 px preview
  resolution. Source-to-DOCX checks verified every body paragraph and all 288
  table cells, including merged headers; unsupported LaTeX rejection was checked.

Original template SHA-256:
`51ab1782847fabe6910f7fa4af264bc25c3bad8585f0db54d31fe963941e578d`.

## Rebuild validation (2026-10-13)

Both current outputs build successfully: 39-page PDF and 39-page LibreOffice
DOCX preview. The updated manuscript includes six tables, 12 display equations,
32 references, seven sections, 26 subsections and two subsubsections.
All 32 reference numbers and all 50 labels match the PDF auxiliary data.

Build fixes preserve the scientific text: escaped `sm\_80` in a bibliography
note; enabled 2 em emergency line-breaking stretch in `main.tex` to avoid
prose overflow; extended the DOCX adapter for citations, references, numbered
lists and third-level headings; repaired the math converter's wide-tilde XML
and mapped tilde accents to native Word accents. The PDF has no overfull lines
or unresolved citations/references; ten underfull-line warnings remain (loose
spacing, including long bibliography URLs). DOCX conversion has no warnings.
Selected title, equation, table and bibliography pages were visually checked
in both outputs. Native Microsoft Word pagination still needs final review.
The original SJEE template remains unchanged. No scientific review was performed.
