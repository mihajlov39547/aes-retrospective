# DEPRECATED: visual-debug Pandoc export only. Never writes the primary DOCX.
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$workspace = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Push-Location -LiteralPath $workspace
try {
    Write-Warning 'LEGACY Pandoc test only. Use .\build_sjee_docx.ps1 for the primary DOCX.'
    if (-not (Get-Command pandoc -ErrorAction SilentlyContinue)) {
        throw 'Pandoc was not found on PATH.'
    }
    $inputFile = 'experimental/legacy/main_docx.tex'
    $outputFile = 'experimental/legacy/main_sjee_pandoc.docx'
    foreach ($source in @($inputFile, 'references.bib', 'SJEE_Template.docx', 'experimental/legacy/sjee-numeric.csl')) {
        if (-not (Test-Path -LiteralPath $source)) { throw "Missing input: $source" }
    }
    Write-Host "Exporting $inputFile"
    # The requested direct conversion, with numeric citations and section numbers.
    $options = @('--bibliography=references.bib', '--citeproc',
        '--reference-doc=SJEE_Template.docx', '--csl=experimental/legacy/sjee-numeric.csl',
        '--number-sections', '--metadata=reference-section-title:References',
        '-o', $outputFile)
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
        $flatFile = 'experimental/legacy/main_docx_flat.tex'
        [System.IO.File]::WriteAllLines((Join-Path $workspace $flatFile), [string[]]$flatLines, $utf8)
        & pandoc $flatFile @options
        if ($LASTEXITCODE -ne 0) { throw "Flattened conversion failed (exit $LASTEXITCODE)." }
    }
    if (-not (Test-Path -LiteralPath $outputFile)) { throw 'No legacy DOCX output was produced.' }
    Write-Host "Created legacy/debug output: $(Join-Path $workspace $outputFile)"
    Write-Host 'Review in Word: apply SJEE styles; check author footnote, equation numbering, tables, captions, references and pagination. See README_sjee_workflow.md.'
}
catch {
    Write-Error "SJEE DOCX conversion failed: $_"
    exit 1
}
finally {
    Pop-Location
}
