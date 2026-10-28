# Facta Word template review

The supplied `fu_elecenerg_instructions_for_authors.doc` was opened and converted with Microsoft Word. Its page geometry, header/footer structure and styles were inspected directly. The original DOC is unchanged; its SHA-256 and the normalized template hash are recorded in `facta_template_manifest.json`.

## Formatting decisions

Written instructions take precedence where the stored legacy styles disagree. `Facta_Template.docx` is the reusable normalized template.

| Element | Applied formatting |
| --- | --- |
| Page | Original A4 dimensions and margins retained |
| Title / Heading 1 | Times New Roman 12 pt, bold, all caps, centered; 30/0 pt spacing |
| Author / Heading 2 | 10 pt bold, centered; 0/12 pt spacing |
| Affiliation | 10 pt centered; 0/18 pt spacing |
| ORCID | Aligned author/identifier block with clickable ORCID URL |
| Abstract | 9 pt italic, justified, 0.75 cm left/right inset; bold upright label |
| Keywords | Six keywords, bold upright label |
| Body | 10 pt, justified, single spaced; 0.5 cm first-line indent; no paragraph spacing |
| Main heading / Heading 3 | 10 pt small caps, centered; 24/6 pt spacing |
| Subheading / Heading 4 | 10 pt bold, left; 5 pt left indent; 12/6 pt spacing |
| Lower subheading / Heading 5 | 10 pt italic, left; 5 pt left indent; 12/6 pt spacing |
| Equations | Editable native Word equations, 10 pt base size; centered tab at 6.25 cm, right equation-number tab at 12.7 cm; 6/6 pt spacing |
| Figures | Centered, 12.7 cm wide; 300 dpi maximum-quality JPEG with companion TIFF; captions below |
| Tables | Numbered captions above, horizontal rules, 9 pt table text, repeated header rows |
| References | Numbered in citation order, 8 pt hanging layout from the supplied template |

The legacy file stored title spacing of 18/18 pt, author size 12 pt, affiliation spacing after 12 pt, and subheading indentation about 14 pt. These were corrected to the written rules. The abstract's written “0.75 pt” indentation conflicts with the actual 425-twip inset; the latter corresponds to 0.75 cm and is retained.

Word equations use native OMML with automatic script sizing rather than obsolete Equation Editor OLE objects. The legacy screenshot's exact equation-editor controls are not reproduced. The rendered PDF confirms Times New Roman for prose, with Cambria Math fallback in native mathematical expressions; this is a remaining difference from the template's Times New Roman/Symbol-only instruction. Figures are immutable raster images; their underlying verified plots are unchanged. No acknowledgement was invented.

## Author details

The manuscript identifies Marko Mihajlović, Singidunum University, Belgrade, Serbia. The author name, affiliation and corresponding email are read from `content/metadata.tex`. ORCID `0009-0006-7979-0341` is recorded in `content/author_details.json`, sourced from `sjee/content/metadata.tex`, and checksum-validated. The first page includes the affiliation, linked ORCID and corresponding-author footnote.

## Validation and remaining publication fields

The generated DOCX was rendered with Microsoft Word and visually reviewed: 13 pages, three figures, three tables, two display equations and ten references. Structural checks verify template styles and geometry, retained headers/footers, author details, native equation structures and embedded JPEG figures. The Word preview is `build/docx_preview/main_facta.pdf`; `main.pdf` remains the separate LaTeX proof.

Publication volume, issue, date, page range, DOI, running headings and copyright year are editable placeholders in the template headers/footers. The received date remains a placeholder in the first-page footnote. These fields are intentionally left for the author/editor. Changing those fields may alter pagination, so render again after completing them.
