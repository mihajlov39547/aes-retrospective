[CmdletBinding()]
param(
    [ValidateSet('All', 'Article', 'Cover')][string]$Document = 'All',
    [string]$PythonPath = '',
    [string]$ReferenceDoc = ''
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $PythonPath) {
    $PythonPath = Join-Path $PSScriptRoot '../sjee/.venv-docx/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $PythonPath)) { $PythonPath = 'python' }
}
if ($PythonPath -and (Test-Path -LiteralPath $PythonPath)) {
    $PythonPath = (Resolve-Path -LiteralPath $PythonPath).Path
}
if ($ReferenceDoc) { $ReferenceDoc = (Resolve-Path -LiteralPath $ReferenceDoc).Path }
if (-not (Get-Command $PythonPath -ErrorAction SilentlyContinue)) { throw 'Python 3 is required on PATH, or supply -PythonPath.' }
if (-not (Get-Command pandoc -ErrorAction SilentlyContinue)) { throw 'Pandoc is required on PATH for DOCX conversion.' }
& $PythonPath -c 'import docx'
if ($LASTEXITCODE -ne 0) { throw 'Install DOCX dependencies: python -m pip install -r univerzitetska-misao/requirements_docx.txt' }
$arguments = @((Join-Path $PSScriptRoot 'build_docx.py'), '--document', $Document.ToLowerInvariant())
if ($ReferenceDoc) { $arguments += @('--reference-doc', $ReferenceDoc) }
& $PythonPath @arguments
if ($LASTEXITCODE -ne 0) { throw "DOCX generation failed (exit $LASTEXITCODE). Inspect build/docx." }
