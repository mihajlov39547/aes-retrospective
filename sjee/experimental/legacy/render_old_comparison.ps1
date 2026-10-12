# Optional visual review of DOCX files. Requires LibreOffice, not the PDF build.
[CmdletBinding()]
param([string]$SofficePath = 'soffice.exe')
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$executable = (Get-Command $SofficePath -ErrorAction Stop).Source
$review = Join-Path $PSScriptRoot 'experimental_review'
$inputs = Join-Path $review 'inputs'
New-Item -ItemType Directory -Path $inputs -Force | Out-Null
$profile = Join-Path $env:TEMP ('sjee-lo-profile-' + [guid]::NewGuid().ToString('N'))
$profileUri = ([System.Uri]($profile + '\')).AbsoluteUri.TrimEnd('/')
foreach ($name in @('SJEE_Template.docx', 'main_sjee_filled.docx', 'main_sjee.docx')) {
    $source = Join-Path $PSScriptRoot $name
    $snapshot = Join-Path $inputs $name
    [System.IO.File]::WriteAllBytes($snapshot, [System.IO.File]::ReadAllBytes($source))
    $stem = [System.IO.Path]::GetFileNameWithoutExtension($name)
    $stdout = Join-Path $review ($stem + '_render.log')
    $stderr = Join-Path $review ($stem + '_render_errors.log')
    $arguments = @(('"-env:UserInstallation=' + $profileUri + '"'), '--headless',
        '--convert-to', 'pdf:writer_pdf_Export', '--outdir', ('"' + $review + '"'),
        ('"' + $snapshot + '"'))
    $process = Start-Process -FilePath $executable -ArgumentList $arguments -WindowStyle Hidden `
        -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
    # Keep a process handle so Windows PowerShell retains the exit code.
    $null = $process.Handle
    if (-not $process.WaitForExit(60000)) {
        Stop-Process -Id $process.Id -ErrorAction SilentlyContinue
        throw "LibreOffice timed out rendering $name. Check $stderr."
    }
    if ($process.ExitCode -ne 0 -or -not (Test-Path -LiteralPath (Join-Path $review ($stem + '.pdf')))) {
        throw "Rendering failed for $name. Check $stderr."
    }
    Write-Host "Rendered $name -> experimental_review/$stem.pdf"
}
Write-Host 'LibreOffice previews compare layout; final Microsoft Word pagination may differ.'
