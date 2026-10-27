#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ "${1:-}" == '--clean' ]]; then
  find . -type f \( -name '*.aux' -o -name '*.log' -o -name '*.out' -o -name '*.toc' -o -name '*.synctex.gz' \) -delete
fi
command -v pdflatex >/dev/null || { echo 'pdflatex not found (install TeX Live)' >&2; exit 1; }
pdflatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex
echo "Built: $(pwd)/main.pdf"
