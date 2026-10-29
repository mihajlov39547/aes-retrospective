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

Requirements: XeLaTeX (TeX Live or MiKTeX) for PDF; Python 3 and Pandoc on PATH
for DOCX. No Python packages are required. Use `-PythonPath` to select another
interpreter. The sources use `fontspec`, so pdfLaTeX cannot compile them.

Outputs beside the sources:

| Source | Outputs |
| --- | --- |
| `mihajlovic2026validiran.tex` | `mihajlovic2026validiran.pdf`, `mihajlovic2026validiran.docx` |
| `naslovna_mihajlovic2026validiran.tex` | `naslovna_mihajlovic2026validiran.pdf`, `naslovna_mihajlovic2026validiran.docx` |

The cover and anonymous article remain separate. Edit the UTF-8 `.tex` sources
and rebuild; edits made directly to generated files will be overwritten.

PDF builds run XeLaTeX three times and retain auxiliary files in `build/pdf`.
Bibliography entries are handwritten in the article, so BibTeX is not used.
Unresolved references or missing glyphs fail the build; layout warnings are
reported for later formatting work.

DOCX builds use Pandoc with `../sjee/SJEE_Template.docx` as the reference styles.
To use Facta or a future journal template, pass `-ReferenceDoc path\template.docx`
to either entry point. Template headers and footers are detached in a generated
copy to avoid displaying another journal's identity. The original template and
LaTeX sources are unchanged. Tables and Word equations remain editable, and
the manually written reference list is retained. Final journal-specific Word
layout and submission formatting still need review.

Generated intermediate sources, Pandoc ASTs, conversion logs, and validation
counts are in `build/docx`; `build_report.json` describes the most recent DOCX
invocation. Conversion warnings, unconverted LaTeX, or missing tables/equations/
references fail the build. The cover conversion also checks its year, email,
and ORCID. The generated source removes `\fontsize` and `\selectfont` layout
commands because Pandoc otherwise consumes the numeric cover year after font
selection. Word fonts come from the reference template.
