# Manuscript figures

Store final figures here. Prefer vector PDF for diagrams in the PDF build,
or high-resolution PNG where raster output is appropriate. Retain editable
originals. Use readable labels and distinguish lines in monochrome as well
as color. For DOCX, supply a PNG or another image format supported by Word;
a PDF figure may need a separate Word-compatible export.

Replace the box in `main.tex` with, for example:

```latex
\includegraphics[width=0.9\linewidth]{figures/example.pdf}
```

The example file is not supplied: the initial template compiles without images.
`placeholder.png` is supplied for `main_docx.tex`: a simple 1200 by 280 pixel
bordered placeholder, embedded inline at 10 cm wide. The primary PDF keeps
its original TeX box, so its layout is unchanged. Replace the PNG and update
the DOCX source when adding a real illustration; no image-generation tool
or Python installation is needed to build or convert the supplied files.

Keep one illustration per simple figure environment, near its first textual
reference. Place captions below figures and reference every figure in the text.
Avoid grouped floating layouts and images of equations or tables.
