# Optional visual review only. No effect on the primary main.pdf build.
[CmdletBinding()]
param([string]$SofficePath = '')
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if (-not $SofficePath) {
    $SofficePath = 'soffice.exe'
    if (-not (Get-Command $SofficePath -ErrorAction SilentlyContinue)) {
        $SofficePath = Join-Path $env:TEMP 'sjee-lo-review/extracted/program/soffice.exe'
    }
}
$executable = (Get-Command $SofficePath -ErrorAction Stop).Source
$review = Join-Path $PSScriptRoot 'build/docx_preview'
New-Item -ItemType Directory -Path $review -Force | Out-Null
$source = Join-Path $PSScriptRoot 'main_sjee.docx'
$snapshot = Join-Path $review 'main_sjee.docx'
[System.IO.File]::WriteAllBytes($snapshot, [System.IO.File]::ReadAllBytes($source))
$profile = Join-Path $env:TEMP ('sjee-lo-profile-' + [guid]::NewGuid().ToString('N'))
$profileUri = ([System.Uri]($profile + '\')).AbsoluteUri.TrimEnd('/')
$arguments = @(('"-env:UserInstallation=' + $profileUri + '"'), '--headless',
    '--convert-to', 'pdf:writer_pdf_Export', '--outdir', ('"' + $review + '"'),
    ('"' + $snapshot + '"'))
$process = Start-Process -FilePath $executable -ArgumentList $arguments -WindowStyle Hidden `
    -PassThru -RedirectStandardOutput (Join-Path $review 'render.log') `
    -RedirectStandardError (Join-Path $review 'render_errors.log')
$null = $process.Handle
if (-not $process.WaitForExit(60000)) {
    Stop-Process -Id $process.Id -ErrorAction SilentlyContinue
    throw 'DOCX preview renderer timed out.'
}
if ($process.ExitCode -ne 0 -or -not (Test-Path -LiteralPath (Join-Path $review 'main_sjee.pdf'))) {
    throw 'DOCX preview failed; inspect build/docx_preview/render_errors.log.'
}
Write-Host "Rendered Word preview: $(Join-Path $review 'main_sjee.pdf')"
Write-Host 'LibreOffice pagination can differ from Word. main.pdf was not changed.'
