[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Program failed (exit $LASTEXITCODE). Inspect main.log or main.blg."
    }
}

Push-Location -LiteralPath $PSScriptRoot
try {
    foreach ($program in @('pdflatex', 'bibtex')) {
        if (-not (Get-Command $program -ErrorAction SilentlyContinue)) {
            throw "Required executable '$program' was not found on PATH. Install TeX Live or MiKTeX."
        }
    }
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
    # Keep auxiliary files and logs for diagnosis; never remove source files.
}
catch {
    Write-Error "SJEE PDF build failed: $_"
    exit 1
}
finally {
    Pop-Location
}
