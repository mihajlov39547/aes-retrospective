# Convert the supplied legacy DOC with Word, then apply its written style rules.
[CmdletBinding()]
param([string]$PythonPath = '')
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $PythonPath) {
    $PythonPath = Join-Path $PSScriptRoot '.venv-docx/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $PythonPath)) { $PythonPath = Join-Path $PSScriptRoot '../sjee/.venv-docx/Scripts/python.exe' }
    if (-not (Test-Path -LiteralPath $PythonPath)) { $PythonPath = 'python' }
}
$review = Join-Path $PSScriptRoot 'build/template_review'
New-Item -ItemType Directory -Path $review -Force | Out-Null
$word = $null
$document = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.AutomationSecurity = 3
    $document = $word.Documents.Open((Join-Path $PSScriptRoot 'fu_elecenerg_instructions_for_authors.doc'), $false, $true)
    [string]$converted = [System.IO.Path]::GetFullPath((Join-Path $review 'converted_template.docx'))
    [int]$format = 16
    $document.SaveAs2([ref]$converted, [ref]$format)
} finally {
    if ($null -ne $document) { $document.Close(0); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($document) }
    if ($null -ne $word) { $word.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word) }
}
& $PythonPath (Join-Path $PSScriptRoot 'prepare_facta_template.py')
if ($LASTEXITCODE -ne 0) { throw 'Facta template preparation failed.' }
