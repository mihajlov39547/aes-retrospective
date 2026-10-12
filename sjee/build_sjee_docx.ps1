# Primary DOCX build: template copy plus shared manuscript sources. No Pandoc.
[CmdletBinding()]
param([string]$PythonPath = '')
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    if (-not $PythonPath) {
        $PythonPath = Join-Path $PSScriptRoot '.venv-docx/Scripts/python.exe'
        if (-not (Test-Path -LiteralPath $PythonPath)) { $PythonPath = 'python' }
    }
    if (-not (Get-Command $PythonPath -ErrorAction SilentlyContinue)) {
        throw 'Python was not found. See README_sjee_workflow.md for DOCX setup.'
    }
    & $PythonPath -c 'import docx, pylatexenc, bibtexparser, latex2mathml, mathml2omml'
    if ($LASTEXITCODE -ne 0) {
        throw 'Missing DOCX dependencies. Install requirements_docx.txt in .venv-docx.'
    }
    & $PythonPath (Join-Path $PSScriptRoot 'fill_sjee_template_docx.py')
    if ($LASTEXITCODE -ne 0) { throw "DOCX generation failed (exit $LASTEXITCODE)." }
    if (-not (Test-Path -LiteralPath 'main_sjee.docx')) { throw 'No DOCX output was created.' }
    Write-Host "Built $(Join-Path $PSScriptRoot 'main_sjee.docx') from an SJEE template copy."
}
catch {
    Write-Error "SJEE DOCX build failed: $_"
    exit 1
}
finally { Pop-Location }
