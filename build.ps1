[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
foreach ($tool in @('latexmk', 'xelatex', 'biber', 'pdftotext')) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        throw "Missing tool: $tool. Install TeX Live or MiKTeX (pdftotext is also available in Poppler) and add its tools to PATH."
    }
}

Push-Location -LiteralPath $PSScriptRoot
$previousLocale = $env:LC_ALL
try {
    # Windows Perl does not support the Unix C.UTF-8 locale inherited by some terminals.
    $env:LC_ALL = 'C'
    & latexmk -xelatex -interaction=nonstopmode -halt-on-error -jobname=aes20y -outdir=build main.tex
    if ($LASTEXITCODE -ne 0) {
        throw "PDF build failed (exit $LASTEXITCODE). See build/aes20y.log."
    }
    $pdfPath = Join-Path $PSScriptRoot 'build/aes20y.pdf'
    if (-not (Test-Path -LiteralPath $pdfPath -PathType Leaf)) {
        throw "Build finished without the expected PDF: $pdfPath"
    }
    $txtPath = Join-Path $PSScriptRoot 'build/aes20y.txt'
    # Preserve table columns and captions without exporting image data.
    & pdftotext -layout -enc UTF-8 -nopgbrk $pdfPath $txtPath
    if ($LASTEXITCODE -ne 0) {
        throw "Text export failed (exit $LASTEXITCODE). PDF is available at: $pdfPath"
    }
    if (-not (Test-Path -LiteralPath $txtPath -PathType Leaf) -or
        [string]::IsNullOrWhiteSpace([System.IO.File]::ReadAllText($txtPath, [System.Text.Encoding]::UTF8))) {
        throw "Text export did not produce a nonempty document: $txtPath"
    }
    Write-Host "PDF: $pdfPath"
    Write-Host "TXT: $txtPath"
}
finally {
    $env:LC_ALL = $previousLocale
    Pop-Location
}
