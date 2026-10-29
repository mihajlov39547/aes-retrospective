[CmdletBinding()]
param([string]$SofficePath = '')
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $SofficePath) {
    $SofficePath = 'soffice.exe'
    if (-not (Get-Command $SofficePath -ErrorAction SilentlyContinue)) {
        $SofficePath = Join-Path $env:TEMP 'um-lo-review/extracted/program/soffice.exe'
        if (-not (Test-Path -LiteralPath $SofficePath)) {
            $SofficePath = Join-Path $env:TEMP 'sjee-lo-review/extracted/program/soffice.exe'
        }
    }
}
$executable = (Get-Command $SofficePath -ErrorAction Stop).Source
$review = Join-Path $PSScriptRoot 'build/docx_preview'
New-Item -ItemType Directory -Path $review -Force | Out-Null
foreach ($stem in @('mihajlovic2026validiran', 'naslovna_mihajlovic2026validiran')) {
    $source = Join-Path $PSScriptRoot "build/docx/$stem.docx"
    $snapshot = Join-Path $review "$stem.docx"
    Copy-Item -LiteralPath $source -Destination $snapshot -Force
    $profile = Join-Path $review ('lo-profile-' + [guid]::NewGuid().ToString('N'))
    $profileUri = ([System.Uri]($profile + '\')).AbsoluteUri.TrimEnd('/')
    $arguments = @(('"-env:UserInstallation=' + $profileUri + '"'), '--headless',
        '--convert-to', 'pdf:writer_pdf_Export', '--outdir', ('"' + $review + '"'), ('"' + $snapshot + '"'))
    $process = Start-Process -FilePath $executable -ArgumentList $arguments -WindowStyle Hidden `
        -PassThru -RedirectStandardOutput (Join-Path $review "$stem-render.log") `
        -RedirectStandardError (Join-Path $review "$stem-render-errors.log")
    $null = $process.Handle
    if (-not $process.WaitForExit(60000)) {
        Stop-Process -Id $process.Id -ErrorAction SilentlyContinue
        throw 'DOCX preview renderer timed out.'
    }
    if ($process.ExitCode -ne 0 -or -not (Test-Path -LiteralPath (Join-Path $review "$stem.pdf"))) {
        throw "DOCX preview failed for $stem; inspect build/docx_preview."
    }
    Write-Host "Rendered $(Join-Path $review "$stem.pdf")"
}
Write-Host 'LibreOffice pagination can differ from Word. LaTeX PDFs were not changed.'
