[CmdletBinding()]
param(
    [ValidateSet('Pdf', 'Docx', 'All')][string]$Target = 'Pdf',
    [ValidateSet('All', 'Article', 'Cover')][string]$Document = 'All',
    [string]$PythonPath = '',
    [string]$ReferenceDoc = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program failed (exit $LASTEXITCODE). See build/pdf for LaTeX logs." }
}

# Resolve overrides before changing the caller's working directory.
if ($PythonPath -and (Test-Path -LiteralPath $PythonPath)) {
    $PythonPath = (Resolve-Path -LiteralPath $PythonPath).Path
}
if ($ReferenceDoc) { $ReferenceDoc = (Resolve-Path -LiteralPath $ReferenceDoc).Path }
Push-Location -LiteralPath $PSScriptRoot
try {
    if ($Document -in @('All', 'Article')) {
        $figurePython = Join-Path $PSScriptRoot '../.venv/Scripts/python.exe'
        if (-not (Test-Path -LiteralPath $figurePython)) { $figurePython = 'python' }
        Invoke-Checked $figurePython @((Join-Path $PSScriptRoot 'prepare_figures.py'))
    }
    if ($Target -in @('Pdf', 'All')) {
        if (-not (Get-Command xelatex -ErrorAction SilentlyContinue)) {
            throw 'XeLaTeX is required (the sources use fontspec). Install TeX Live or MiKTeX and add it to PATH.'
        }
        $build = Join-Path $PSScriptRoot 'build/pdf'
        New-Item -ItemType Directory -Force -Path $build | Out-Null
        $stems = @()
        if ($Document -in @('All', 'Article')) { $stems += 'mihajlovic2026validiran' }
        if ($Document -in @('All', 'Cover')) { $stems += 'naslovna_mihajlovic2026validiran' }
        foreach ($stem in $stems) {
            $latexArguments = @('-interaction=nonstopmode', '-halt-on-error', '-file-line-error', "-output-directory=$build", "$stem.tex")
            Invoke-Checked 'xelatex' $latexArguments
            if ((Get-Content -LiteralPath "$stem.tex" -Raw) -match '\\addbibresource') {
                if (-not (Get-Command biber -ErrorAction SilentlyContinue)) { throw 'Biber is required for references.bib.' }
                $previousLocale = $env:LC_ALL
                try {
                    $env:LC_ALL = 'C'
                    Invoke-Checked 'biber' @("--input-directory=$build", "--output-directory=$build", $stem)
                }
                finally { $env:LC_ALL = $previousLocale }
            }
            1..2 | ForEach-Object { Invoke-Checked 'xelatex' $latexArguments }
            $logPath = Join-Path $build "$stem.log"
            $log = Get-Content -LiteralPath $logPath -Raw
            if ($log -match 'There were undefined references|Citation .+ undefined|Rerun to get cross-references right|Missing character:') {
                throw "Unresolved references or missing glyphs: inspect $logPath."
            }
            $warnings = Select-String -LiteralPath $logPath -Pattern '^(LaTeX|Package .+|Class .+).*Warning|^(Overfull|Underfull)'
            if ($warnings) { Write-Warning ($warnings.Line -join [Environment]::NewLine) }
            Copy-Item -LiteralPath (Join-Path $build "$stem.pdf") -Destination (Join-Path $PSScriptRoot "$stem.pdf") -Force
            Write-Host "Built $(Join-Path $PSScriptRoot "$stem.pdf")"
        }
    }
    if ($Target -in @('Docx', 'All')) {
        & (Join-Path $PSScriptRoot 'build_univerzitetska_misao_docx.ps1') -Document $Document -PythonPath $PythonPath -ReferenceDoc $ReferenceDoc
    }
}
catch {
    Write-Error "Univerzitetska Misao $Target build failed: $_" -ErrorAction Continue
    exit 1
}
finally { Pop-Location }
