[CmdletBinding()]
param(
    [ValidateSet('Pdf', 'Docx', 'All')][string]$Target = 'Pdf',
    [string]$PythonPath = '',
    [switch]$RenderPreview
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Program failed (exit $LASTEXITCODE). Inspect main.log or main.blg."
    }
}

function Build-Pdf {
    foreach ($program in @('pdflatex', 'bibtex')) {
        if (-not (Get-Command $program -ErrorAction SilentlyContinue)) {
            throw "Required executable '$program' was not found on PATH. Install TeX Live or MiKTeX."
        }
    }
    $previousTexInputs = $env:TEXINPUTS
    $sharedStyles = (Join-Path $PSScriptRoot '../sjee').Replace('\', '/')
    $env:TEXINPUTS = '.;' + $sharedStyles + ';' + $env:TEXINPUTS
    try {
        $latexArguments = @('-interaction=nonstopmode', '-halt-on-error', '-file-line-error', 'main.tex')
        Invoke-Checked 'pdflatex' $latexArguments
        $aux = Get-Content -LiteralPath 'main.aux' -Raw
        if ($aux -match '\\bibdata\{') {
            Invoke-Checked 'bibtex' @('main')
        }
        Invoke-Checked 'pdflatex' $latexArguments
        Invoke-Checked 'pdflatex' $latexArguments
        if (-not (Test-Path -LiteralPath 'main.pdf')) {
            throw 'The build did not produce main.pdf.'
        }
        $log = Get-Content -LiteralPath 'main.log' -Raw
        if ($log -match 'There were undefined references|Citation .+ undefined|Rerun to get cross-references right') {
            throw 'The final LaTeX pass still has unresolved references; inspect main.log.'
        }
        $warnings = Select-String -LiteralPath 'main.log' -Pattern '^(LaTeX|Package .+|Class .+|pdfTeX).*warning|^(Overfull|Underfull)'
        if ($warnings) {
            Write-Warning ($warnings.Line -join [Environment]::NewLine)
        }
        Write-Host "Built $(Join-Path $PSScriptRoot 'main.pdf')"
    } finally { $env:TEXINPUTS = $previousTexInputs }
    # Keep auxiliary files and logs for diagnosis; never remove source files.
}

# Resolve relative Python paths in the caller's directory, as the DOCX entry point does.
if ($PythonPath -and (Test-Path -LiteralPath $PythonPath)) {
    $PythonPath = (Resolve-Path -LiteralPath $PythonPath).Path
}
Push-Location -LiteralPath $PSScriptRoot
try {
    if ($RenderPreview -and $Target -eq 'Pdf') {
        throw '-RenderPreview requires -Target Docx or -Target All.'
    }
    if ($Target -in @('Pdf', 'All')) { Build-Pdf }
    if ($Target -in @('Docx', 'All')) {
        & (Join-Path $PSScriptRoot 'build_facta_docx.ps1') -PythonPath $PythonPath -RenderPreview:$RenderPreview
        if ($LASTEXITCODE -ne 0) { throw "DOCX build failed (exit $LASTEXITCODE)." }
    }
}
catch {
    Write-Error "Facta $Target build failed: $_" -ErrorAction Continue
    exit 1
}
finally {
    Pop-Location
}

