# Manuscript figures

Store final figures here. Prefer vector PDF for diagrams in the PDF build,
or high-resolution PNG where raster output is appropriate. Retain editable
originals. Use readable labels and distinguish lines in monochrome as well
as color. For DOCX, supply a PNG or another image format supported by Word;
a PDF figure may need a separate Word-compatible export.

When adding a figure to the shared manuscript under `content/`, use, for example:

```latex
\includegraphics[width=0.9\linewidth]{figures/example.pdf}
```

The example file is not supplied. The current shared manuscript has no figures
and builds without image inputs. `placeholder.png` is a retained 1200 by 280
pixel bordered fixture used by the separate historical Word-filling experiment.
It is no longer inserted automatically by either manuscript wrapper. Keep
new figure content in the shared files, not in `main_docx.tex`.

Keep one illustration per simple figure environment, near its first textual
reference. Place captions below figures and reference every figure in the text.
Avoid grouped floating layouts and images of equations or tables.
