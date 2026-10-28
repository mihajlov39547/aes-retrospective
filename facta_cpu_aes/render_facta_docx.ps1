# Render the generated DOCX with Microsoft Word; never overwrite the LaTeX PDF.
[CmdletBinding()]
param()
# Word exposes optional COM arguments through late binding.
Set-StrictMode -Off
$ErrorActionPreference = 'Stop'
$review = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'build/docx_preview'))
New-Item -ItemType Directory -Path $review -Force | Out-Null
$snapshot = Join-Path $review ('review-' + [guid]::NewGuid().ToString('N') + '.docx')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'main_facta.docx') -Destination $snapshot -Force
$word = $null
$document = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.AutomationSecurity = 3
    Write-Host 'Opening DOCX in Word for visual verification...'
    $document = $word.Documents.Open($snapshot, $false, $true)
    Write-Host 'Exporting Word layout to PDF...'
    [string]$pdf = Join-Path $review ('review-' + [guid]::NewGuid().ToString('N') + '.pdf')
    [int]$pdfFormat = 17
    $document.SaveAs2([ref]$pdf, [ref]$pdfFormat)
} finally {
    if ($null -ne $document) { $document.Close(0); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($document) }
    if ($null -ne $word) { $word.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word) }
}

$finalPdf = Join-Path $review 'main_facta.pdf'
Move-Item -LiteralPath $pdf -Destination $finalPdf -Force
$info = & pdfinfo $finalPdf
if ($LASTEXITCODE -ne 0) { throw 'PDF preview inspection failed.' }
$pages = [int](($info | Select-String '^Pages:').Line -replace '^Pages:\s*', '')
@{ renderer = 'Microsoft Word'; pages = $pages; pdf = $finalPdf; source = $snapshot } |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $review 'render_report.json') -Encoding utf8
Write-Host "Rendered $pages pages: $finalPdf"
