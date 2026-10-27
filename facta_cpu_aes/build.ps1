param([switch]$Clean)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if ($Clean) {
  Get-ChildItem -File -Include '*.aux','*.log','*.out','*.toc','*.synctex.gz' -Recurse | Remove-Item -Force
}
$engine = Get-Command pdflatex -ErrorAction SilentlyContinue
if (-not $engine) { throw 'pdflatex not found. Install MiKTeX or TeX Live and ensure pdflatex is on PATH.' }
foreach ($pass in 1..2) {
  & pdflatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex
  if ($LASTEXITCODE -ne 0) { throw "LaTeX pass $pass failed" }
}
Write-Host "Built: $PSScriptRoot/main.pdf"
