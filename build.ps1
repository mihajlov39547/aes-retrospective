[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
foreach ($tool in @('latexmk', 'xelatex', 'biber')) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        throw "Missing tool: $tool. Install TeX Live or MiKTeX and add its tools to PATH."
    }
}

Push-Location -LiteralPath $PSScriptRoot
try {
    & latexmk -xelatex -interaction=nonstopmode -halt-on-error -jobname=aes20y -outdir=build main.tex
    if ($LASTEXITCODE -ne 0) {
        throw "PDF build failed (exit $LASTEXITCODE). See build/aes20y.log."
    }
    $pdfPath = Join-Path $PSScriptRoot 'build/aes20y.pdf'
    if (-not (Test-Path -LiteralPath $pdfPath -PathType Leaf)) {
        throw "Build finished without the expected PDF: $pdfPath"
    }
    Write-Host "PDF: $pdfPath"
}
finally {
    Pop-Location
}
