[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Push-Location -LiteralPath $PSScriptRoot
try {
    if (-not (Get-Command pandoc -ErrorAction SilentlyContinue)) {
        throw 'Pandoc was not found on PATH.'
    }
    $inputFile = if (Test-Path -LiteralPath 'main_docx.tex') { 'main_docx.tex' } else { 'main.tex' }
    foreach ($source in @($inputFile, 'references.bib', 'SJEE_Template.docx', 'sjee-numeric.csl')) {
        if (-not (Test-Path -LiteralPath $source)) { throw "Missing input: $source" }
    }
    if ($inputFile -eq 'main_docx.tex' -and -not (Test-Path -LiteralPath 'figures/placeholder.png')) {
        throw 'Missing DOCX placeholder image: figures/placeholder.png'
    }
    Write-Host "Exporting $inputFile"
    # The requested direct conversion, with numeric citations and section numbers.
    $options = @('--bibliography=references.bib', '--citeproc',
        '--reference-doc=SJEE_Template.docx', '--csl=sjee-numeric.csl',
        '--number-sections', '--metadata=reference-section-title:References',
        '-o', 'main_sjee.docx')
    & pandoc $inputFile @options
    if ($LASTEXITCODE -ne 0) {
        Write-Warning 'Direct conversion failed; trying a flattened LaTeX input.'
        if (-not (Get-Command latexpand -ErrorAction SilentlyContinue)) {
            throw 'Direct conversion failed and latexpand was not found on PATH.'
        }
        # Avoid Windows PowerShell > redirection, which writes UTF-16 by default.
        $flatLines = & latexpand $inputFile
        if ($LASTEXITCODE -ne 0) { throw "latexpand failed (exit $LASTEXITCODE)." }
        $utf8 = New-Object System.Text.UTF8Encoding($false)
        $flatFile = [System.IO.Path]::GetFileNameWithoutExtension($inputFile) + '_flat.tex'
        [System.IO.File]::WriteAllLines((Join-Path $PSScriptRoot $flatFile), [string[]]$flatLines, $utf8)
        & pandoc $flatFile @options
        if ($LASTEXITCODE -ne 0) { throw "Flattened conversion failed (exit $LASTEXITCODE)." }
    }
    if (-not (Test-Path -LiteralPath 'main_sjee.docx')) { throw 'No DOCX output was produced.' }
    Write-Host "Created $(Join-Path $PSScriptRoot 'main_sjee.docx')"
    Write-Host 'Review in Word: apply SJEE styles, move affiliation to a footnote, add equation numbering, and check captions, references and pagination. See README_sjee_workflow.md.'
}
catch {
    Write-Error "SJEE DOCX conversion failed: $_"
    exit 1
}
finally {
    Pop-Location
}
