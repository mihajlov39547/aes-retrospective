# SJEE DOCX validation — 27 October 2026

The regenerated, validated output is `main_sjee_ready.docx`. Word has the existing
`main_sjee.docx` open and prevents its replacement. After saving and closing it,
run `./build_sjee_docx.ps1` to regenerate the standard filename. The build report
currently identifies the ready copy; the original open document was not modified.

- Twelve converter regression tests passed.
- Six numbered display equations and 34 inline expressions export as 40 editable
  OMML objects. Full-size math is 11 pt. Tests check membership, multiplication,
  transfer-component subscripts, fractions, median delimiters, tildes and ellipsis.
- Output validation compares every expression's complete OMML structure with its
  source conversion; checks sequential display numbers, two tabs per display,
  center/right template tab stops, and absence of equation-layout tables.
- Original template styles, list definitions and page settings are preserved.
  Body/equation paragraphs explicitly use single spacing; body style remains 11 pt.
- Four editable tables, two inline SVG figures with PNG fallbacks and 24 cited
  references pass validation. All manuscript blocks, math expressions, label
  mappings and citation numbers match the previous generated source snapshot.
- All 31 bibliography entries are retained. Personal names use consistent
  surname/given-name BibTeX notation; DOCX initials are generated after decoding
  accents. Corporate authors, technical capitalization and citation order remain
  intact. DOI fields use bare DOI syntax; duplicate DOI URLs are suppressed in
  DOCX. Bibliography paragraphs retain the template style with left alignment to
  avoid stretched spacing around long URLs.
- `SJEE.eqp` is unchanged, with Full = 11 pt. SHA-256:
  `fbdd5e9e8809183e807afc4824f253bb26d98a6b95943734dbee21553171d702`.
- No MathType OLE conversion has been performed. The generated DOCX deliberately
  contains zero OLE equations. Follow `MATHTYPE_FINALIZATION.md` on a submission
  copy and verify all 40 resulting objects in MathType 7.

The tests emit deprecation notices from bibtexparser's pyparsing dependency;
these are not document-validation failures. Actual rendering in Word/MathType
after manual conversion remains a required final check.
