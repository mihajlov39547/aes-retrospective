[CmdletBinding()]
param([string]$PythonPath = 'python')
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    & $PythonPath prepare_figures.py
    if ($LASTEXITCODE -ne 0) { throw 'Figure generation failed.' }
    & xelatex -interaction=nonstopmode -halt-on-error main.tex *> verification/xelatex-pass1.txt
    if ($LASTEXITCODE -ne 0) { throw 'XeLaTeX pass 1 failed; inspect verification/xelatex-pass1.txt.' }
    & biber main *> verification/biber.txt
    if ($LASTEXITCODE -ne 0) { throw 'Biber failed; inspect verification/biber.txt.' }
    foreach ($pass in 2,3) {
        & xelatex -interaction=nonstopmode -halt-on-error main.tex *> "verification/xelatex-pass$pass.txt"
        if ($LASTEXITCODE -ne 0) { throw "XeLaTeX pass $pass failed." }
    }
    Write-Host 'Built paper_jart/main.pdf with XeLaTeX and Biber.'
}
finally { Pop-Location }
