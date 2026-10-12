# Experimental filling of the SJEE Word template

This is a separate experiment. **`main.tex` to `main.pdf` remains the primary
submission workflow.** Neither this script nor its Python environment is used
by `build_sjee.ps1` or `convert_to_docx.ps1`. The existing Pandoc export is
retained as a separate option. All manuscript content remains placeholder text.

## Run

An isolated `.venv-docx` environment was created in this folder with
python-docx 1.2.0. To recreate it:

```powershell
python -m venv .venv-docx
.\.venv-docx\Scripts\python.exe -m pip install -r requirements_docx_experiment.txt
```

Generate the experimental Word copy:

```powershell
.\.venv-docx\Scripts\python.exe fill_sjee_template_docx.py
```

This copies `SJEE_Template.docx` to `main_sjee_filled.docx`, fills the copy,
and verifies that the original hash, style definitions, numbering definitions,
headers/footers and section settings have not changed. Running it again
replaces the generated copy, including any manual edits made there. Save
manual production work under another filename.

The script deliberately checks the original template's SHA-256 before using
its paragraph mapping. If the journal supplies another template version,
reinspect it and adapt the mapping; do not simply bypass the check.

## Inspected structure and replacement strategy

Indices below are zero-based direct children of `word/document.xml`'s body,
including tables and bookmarks, not python-docx paragraph-list indices.

| Element | Original body position / style | Experimental handling |
| --- | --- | --- |
| Title | 0, `JTitle` | Replace title text; retain centered bold 16 pt style and spacing. |
| Authors | 1, `JAuthor` | One full name; retain the first real author footnote marker. |
| Affiliation | `word/footnotes.xml`, note 1, `JFootnote` | Replace text with university and ORCID; remove unused author 2 note; no email. |
| Abstract | 2, `JAbstract` | Bold label plus placeholder paragraph; preserve 10 pt and side insets. |
| Keywords | 3, `JAbstract` | Bold label plus placeholder keywords. |
| Sections | 4, 8, 17, 31, 40, 45, 48, 51, `JSubtitle` | Reuse for sections 1–7 and an unnumbered References heading; preserve number/tab layout. |
| Subsections | 10 and 20, `JSubSubTitle` | Reuse one as 3.1 Example equation; omit the extra instructional subsection. |
| Body | Several paragraphs, `JText` / `JText-noIndent` | Replace instructional prose with current placeholder paragraphs. |
| Equations | 13–15, `JEquation`, embedded `Equation.DSMT4` OLE objects | Remove visible sample objects; keep one styled line reading `[Equation placeholder]` with `(1)` and a manual-edit note. |
| Figures | 25–30, `JFigure`, inline drawings and captions | Use one original styled paragraph for `figures/placeholder.png`; keep one caption with a bold label. |
| Table caption | 42, `JFigure` | Keep bold Table 1, line break and italic description. |
| Table | 43, one five-column merged table | Replace text only; preserve five rows, widths, merges, centered positioning, borders and `JTableText` cell paragraphs. |
| References | 52–53, `JReference` | Keep one fictional reference; original inherited list definition supplies `[1]`. |

The script reuses and reorders the template's paragraph/table nodes and drops
unused instructional samples. It preserves paragraph properties rather than
constructing a new document with a new style collection. Local bold/italic
runs are rebuilt where needed for labels/captions. It does not globally
replace text inside arbitrary XML or parse LaTeX.
Document title/author/subject metadata are also updated, so the template's
unrelated historical paper title is not carried into the output properties.

python-docx has no public footnote-editing API; this experiment uses a small,
template-specific XML edit for that single footnote. Legacy media/OLE parts
may remain unused inside the ZIP package even though their sample objects
are removed from the visible document; this is not a production sanitizer.

## Visual review

`render_sjee_comparison.ps1` renders isolated copies of the original template,
filled copy and existing Pandoc output using LibreOffice. It never saves
changes to those DOCX inputs. If LibreOffice is on PATH:

```powershell
.\render_sjee_comparison.ps1
```

Otherwise supply the path to `soffice.exe` with `-SofficePath`. PDF previews
and input snapshots go in `experimental_review`. Rendering is optional and
has no role in generating `main.pdf`.

Microsoft Word automation was attempted here but stalled before producing
its first PDF and was stopped. LibreOffice previews provide a consistent
comparison across the three DOCX files; final Word rendering may differ.

### Observed result, 2026-10-12

The copy-based output is visibly closer to the SJEE template than the current
Pandoc output in this comparison. Both pages of the filled copy were inspected,
along with the original title, table and references pages and both Pandoc pages.
The source template renders as five pages; the shorter filled placeholder
manuscript and Pandoc export each render as two. Equal page counts are not a
fidelity test because the content lengths differ.

| Feature | Filled template copy | Existing Pandoc DOCX in the same renderer |
| --- | --- | --- |
| Title/author | Centered, bold Times-like template appearance; real author footnote. | Title is left-aligned sans serif; affiliation is a body paragraph. |
| Abstract/keywords | Original 10 pt justified inset style, with bold labels only. | Inherited standard styles render the paragraphs centered and bold. |
| Body/headings | Original first-line indents, heading weight, number/tab spacing and paragraph spacing. | Body/heading styles visibly diverge from the template. |
| Figure/caption | One centered inline box image and centered caption near its mention. | Image survives, but caption appearance differs. |
| Table | Clearly legible centered grid, merged headers and original border treatment. | The native table renders poorly, with vertically stacked content and a displaced caption. Structural presence did not establish visual usability. |
| References | Original smaller hanging-indent `[1]` list style. | Numeric content survives but typography differs. |
| Page furniture | Original page dimensions, margins, journal masthead, running headers and page numbers. | Original page settings/headers are also inherited. |

The filled copy has no visible overlap or clipped placeholder text in the
reviewed pages. Results, the figure, its caption and the table appear together
on page 2. The source table's row heights reflow slightly with the replacement
text; preserving geometry does not freeze pagination or guarantee arbitrary
future table content will fit.

The optional renderer used LibreOffice 26.8.1.1 extracted under
`%TEMP%\sjee-lo-review\extracted`, without a system-wide installation. Example
for rerunning this session's renderer while that temporary directory exists:

```powershell
.\render_sjee_comparison.ps1 -SofficePath "$env:TEMP\sjee-lo-review\extracted\program\soffice.exe"
```

The extracted renderer printed `Could not find platform independent libraries
<prefix>` on stderr, but returned success and generated readable PDFs for all
three files. This is a renderer-environment warning; the Python filling script
completed without warnings. Rendering logs are retained in `experimental_review`.

Review artifacts:

- [Original template preview](experimental_review/SJEE_Template.pdf)
- [Filled template preview](experimental_review/main_sjee_filled.pdf)
- [Existing Pandoc preview](experimental_review/main_sjee.pdf)
- [First-page visual comparison](experimental_review/first_page_comparison.png)

The original DOCX, `main.tex`, `sjee.sty`, `build_sjee.ps1` and existing
`main.pdf` were checked by SHA-256 and are unchanged. No PDF rebuild was
needed for this isolated experiment.

## Known limits

- This is a template-specific proof of concept, not a robust manuscript
  conversion system. The placeholders are maintained directly in the Python
  script; changes in the LaTeX sources are not synchronized automatically.
- Actual equations require manual Word/MathType entry. The bracketed note
  is deliberately not mathematical content or a simulated display equation.
- The reference is fictional. Citation text `[1]` is literal, whereas the
  bibliography number comes from the original Word list. There is no BibTeX,
  CSL or automatic cross-reference integration in this experiment.
- The original merged five-column table is intentionally retained rather
  than redesigned into the three-column LaTeX/Pandoc example. All entries are
  placeholders; a real table needs a separate manual design/review pass.
- Headers and footers are deliberately preserved for comparison. They still
  contain sample author/title and 2021 issue/volume/UDC/DOI metadata. These
  must be removed or corrected before submission, not mistaken for assigned
  publication details.
- Long-title wrapping, page breaks, caption placement and keep-with-next
  behavior still require human review when real content is inserted.

Do not adopt this as the primary workflow unless it is separately validated
on a complete manuscript, including Word pagination, real equations, final
figures/tables and references.
