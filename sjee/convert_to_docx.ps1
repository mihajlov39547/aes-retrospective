[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Push-Location -LiteralPath $PSScriptRoot
try {
    if (-not (Get-Command pandoc -ErrorAction SilentlyContinue)) {
        throw 'Pandoc was not found on PATH.'
    }
    foreach ($source in @('main.tex', 'references.bib', 'SJEE_Template.docx', 'sjee-numeric.csl')) {
        if (-not (Test-Path -LiteralPath $source)) { throw "Missing input: $source" }
    }
    # The requested direct conversion, with numeric citations and section numbers.
    $options = @('--bibliography=references.bib', '--citeproc',
        '--reference-doc=SJEE_Template.docx', '--csl=sjee-numeric.csl',
        '--number-sections', '--metadata=reference-section-title:References',
        '-o', 'main_sjee.docx')
    & pandoc 'main.tex' @options
    if ($LASTEXITCODE -ne 0) {
        Write-Warning 'Direct conversion failed; trying a flattened LaTeX input.'
        if (-not (Get-Command latexpand -ErrorAction SilentlyContinue)) {
            throw 'Direct conversion failed and latexpand was not found on PATH.'
        }
        # Avoid Windows PowerShell > redirection, which writes UTF-16 by default.
        $flatLines = & latexpand 'main.tex'
        if ($LASTEXITCODE -ne 0) { throw "latexpand failed (exit $LASTEXITCODE)." }
        $utf8 = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllLines((Join-Path $PSScriptRoot 'main_flat.tex'), [string[]]$flatLines, $utf8)
        & pandoc 'main_flat.tex' @options
        if ($LASTEXITCODE -ne 0) { throw "Flattened conversion failed (exit $LASTEXITCODE)." }
    }
    if (-not (Test-Path -LiteralPath 'main_sjee.docx')) { throw 'No DOCX output was produced.' }
    Write-Host "Created $(Join-Path $PSScriptRoot 'main_sjee.docx')"
    Write-Warning 'Test export only. Inspect title/affiliation, styles, equations, cross-references, figures, table captions and bibliography in Word. TeX-only boxes may be omitted.'
}
catch {
    Write-Error "SJEE DOCX conversion failed: $_"
    exit 1
}
finally {
    Pop-Location
}
