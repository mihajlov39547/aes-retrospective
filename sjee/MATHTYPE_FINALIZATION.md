# SJEE MathType 7 finalization

LaTeX (`main.tex`, `content/*.tex`, `references.bib`) remains the source of truth.
`build_sjee_docx.ps1` generates `main_sjee.docx` from the unchanged SJEE template,
using LaTeX → MathML → editable OMML. It does **not** generate MathType OLE objects.
The current manuscript has **40 expressions: six numbered equations and 34 inline
expressions**, including mathematical content in tables. Figures remain vector
objects with PNG fallbacks; tables remain editable Word tables.

## Finalize a copy in Word for Windows

1. Rebuild with `./build_sjee_docx.ps1` and close the generated document before
   rebuilding again. Save a copy as `main_sjee_mathtype.docx` inside `sjee/`.
   Use desktop Word with the installed MathType **7 desktop** ribbon integration.
2. In the copy, open **MathType → Convert Equations**. Enable **Word 2007 and
   later (OMML) equations**, select **Whole document**, and convert to **MathType
   equations (OLE objects)**. Record the reported conversion count: expect 40.
   This option depends on the Word/MathType version. If it is unavailable or
   conversion fails, retain the OMML original and resolve the installation/version
   issue before submission; do not substitute equation images or rename objects.
3. Open **MathType → Equation Preferences → Load from MathType Preference File**
   and select `C:\Projects\aes\sjee\SJEE.eqp`. Use the document's preferences.
   Preview the settings: the supplied file specifies **Full = 11 pt**, Times New
   Roman text/variables and Symbol/MT Extra symbols. Do not modify this file.
4. Run **MathType → Format Equations**, choose the current document's preferences
   (or select `SJEE.eqp` directly), and apply to the whole document. Loading
   preferences alone sets defaults; formatting applies them to existing objects.
   Format Equations does not format remaining native OMML, so conversion comes first.
5. Save, close and reopen the copy. Double-click a display equation and an inline
   expression: both must open as editable mathematics in MathType 7. Check all
   equations against `main.pdf`, especially tildes, subscripts, superscripts,
   fractions, parentheses, membership, multiplication and ellipsis symbols.

Keep the existing `JEquation` paragraphs: TAB, equation, TAB, `(1)` through `(6)`.
The template uses a centered tab at 3544 twips and a right tab at 7088 twips.
Do not use MathType's numbered-equation insertion command on these paragraphs:
the numbers already exist. Keep equation objects inline with text, not floating.
Main text stays 11 pt and single-spaced. `SJEE.eqp`'s internal equation line-spacing
setting is separate from Word paragraph spacing.

## Verify the saved submission copy

- Confirm six `JEquation` paragraphs, with numbers `(1)`–`(6)` exactly once and
  centered equations/right-aligned numbers. Confirm 24 bibliography entries,
  unchanged citation numbering, four editable tables, two vector figures, captions
  and all section/table/figure references. Numbers and references are generated
  literals, not Word fields; updating fields will not regenerate them.
- Inspect a ZIP copy of the DOCX (do not edit the archive). In `word/document.xml`,
  count Office `o:OLEObject` elements with MathType's `ProgID="Equation.DSMT4"`:
  expect 40 after complete conversion. There should be no remaining `m:oMath`
  expressions. For every object's `r:id`, find an `oleObject` relationship in
  `word/_rels/document.xml.rels`, and verify that its embedded target exists under
  `word/embeddings/`. Preview images alone, or arbitrary `.bin` files, do not prove
  that the equations are editable MathType objects. An unexpected ProgID requires
  checking the installed version and opening the object in MathType.
- Reopen and inspect every equation, including inline expressions in table cells.
  Structural counts do not establish visual correctness or prove that preferences
  were applied. Check MathType's size/style settings and the final rendered pages.
- Keep `main_sjee.docx` as the generated OMML baseline. Any content correction must
  be made in LaTeX, rebuilt, and manually finalized again in a fresh copy. The
  converter's validator deliberately rejects OLE objects in its generated output;
  do not run that validator against the finalized MathType copy.

No automatic MathType conversion has been performed or tested by this project.
The manual steps follow [Wiris's MathType 7 Office integration documentation](https://docs.wiris.com/using-mathtype-other-applications-and-websites/mathtype-7-with-microsoft-office-2016-or-later).
The generated build report is `build/docx/build_report.json`.
