# Legacy/debug exports only

The primary DOCX build is now `..\..\build_sjee_docx.ps1`, which fills a copy
of the original SJEE Word template with shared manuscript content.

Pandoc DOCX is deprecated because its visual output is poor. For diagnostics
only, run `experimental/legacy/convert_to_docx.ps1` from the workspace. It
always writes `experimental/legacy/main_sjee_pandoc.docx`, never the primary
`main_sjee.docx`. The LaTeX wrapper and numeric CSL here belong to that test.

`main_sjee_filled_placeholder.docx`, `fill_placeholder_template.py`,
`render_old_comparison.ps1`, `requirements_docx_experiment.txt` and
`README_placeholder_experiment.md` archive the earlier placeholder experiment.
The old Python/render scripts are archival source, not supported build entry
points; their historical relative paths are not maintained. The older visual
artifacts in `../../experimental_review/` also describe the placeholder era.

Do not edit scientific content here. Current manuscript sources are exclusively
`../../content/*.tex` and `../../references.bib`.
