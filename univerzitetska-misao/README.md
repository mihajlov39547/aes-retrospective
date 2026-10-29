# Univerzitetska Misao builds

Run from the repository root in PowerShell:

```powershell
# Both documents, PDF and DOCX
.\univerzitetska-misao\build_univerzitetska_misao.ps1 -Target All

# PDF only (the default)
.\univerzitetska-misao\build_univerzitetska_misao.ps1

# DOCX only
.\univerzitetska-misao\build_univerzitetska_misao_docx.ps1

# Build just the research article or just the separate cover page
.\univerzitetska-misao\build_univerzitetska_misao.ps1 -Target All -Document Article
.\univerzitetska-misao\build_univerzitetska_misao.ps1 -Target All -Document Cover
```

Scripts also work from other working directories when invoked by their full path.

Requirements: XeLaTeX and Biber (TeX Live or MiKTeX) for PDF; Python 3, Pandoc and pdftocairo on PATH
for DOCX, plus `python-docx` (`python -m pip install -r univerzitetska-misao/requirements_docx.txt`).
The script automatically reuses `sjee/.venv-docx` if available. Use `-PythonPath`
to select another interpreter. The sources use `fontspec`, so pdfLaTeX cannot compile them.

Outputs beside the sources:

| Source | Outputs |
| --- | --- |
| `mihajlovic2026validiran.tex` | `mihajlovic2026validiran.pdf`, `mihajlovic2026validiran.docx` |
| `naslovna_mihajlovic2026validiran.tex` | `naslovna_mihajlovic2026validiran.pdf`, `naslovna_mihajlovic2026validiran.docx` |

The cover and anonymous article remain separate. Edit the UTF-8 `.tex` sources
and rebuild; edits made directly to generated files will be overwritten.

The main article contains the complete updated economic manuscript supplied in
`ekonomski_izazovi_aes_v2.tex`, using the established page and typography settings.
Edit `mihajlovic2026validiran.tex` and the standard shared `references.bib` from now on.
The supplied v2 files are retained as the import originals. Both figures are read
from `aes_throughput_comparison.pdf` and `t4_page_batch_ratios.pdf`.

PDF builds run XeLaTeX, Biber, then two XeLaTeX passes and retain auxiliary files in `build/pdf`.
The bibliography uses author-year citations; both output formats read `references.bib`.
Unresolved references or missing glyphs fail the build; layout warnings are
reported for later formatting work.

DOCX builds use Pandoc with `../sjee/SJEE_Template.docx` as the reference styles.
To use Facta or a future journal template, pass `-ReferenceDoc path\template.docx`
to either entry point. Template headers and footers are detached in a generated
copy to avoid displaying another journal's identity. The original SJEE template
is unchanged. `docx_layout.py` adapts its JTitle, JText, JAbstract, JSubtitle,
JReference and JTableText styles to `uputstvo_za_autore.pdf`:

- 17.6 x 25.1 cm pages, 2.5 cm margins, one column, single spacing;
- Times New Roman, 11 pt body, 13 pt centered bold titles, 12 pt uppercase
  section headings, 11 pt bold subheadings, 10 pt abstracts and references;
- separate centered author cover, bilingual title/abstract/keywords, numbered
  references, and an English summary at the end;
- no headers or page numbers; editable tables sized to the 12.6 cm text width,
  numbered captions with italic titles, and author-results source notes;
- 9 pt table contents for the wide data tables (the instructions specify 10 pt
  captions and notes but do not prescribe a table-cell font size).

The abstract word counts are checked against the required 100-200 words.
Table source notes distinguish the measured throughput table from the derived
normalized-cost table. Update that provenance in `docx_layout.py` if tables change.
DOCX builds resolve citations with Pandoc citeproc and embed 300 dpi PNG copies
of the two PDF figures generated only under `build/docx`.
DOCX layout is applied independently of TeX
layout; this does not make the two rendering engines paginate identically.

For visual review, run `render_univerzitetska_misao_docx.ps1 -SofficePath path\soffice.exe`.
It exports the latest validated copies from `build/docx` to preview PDFs in
`build/docx_preview`, leaving the LaTeX PDFs untouched. LibreOffice pagination
may differ slightly from Microsoft Word. Check the journal's 7-14 page limit
and one-page summary after substantial content changes.

Generated intermediate sources, Pandoc ASTs, conversion logs, and validation
counts are in `build/docx`; `build_report.json` describes the most recent DOCX
invocation. Conversion warnings, unconverted LaTeX, or missing tables/equations/
references fail the build. The cover conversion also checks its year, email,
and ORCID. The generated source removes `\fontsize` and `\selectfont` layout
commands because Pandoc otherwise consumes the numeric cover year after font
selection. Word fonts come from the reference template.
