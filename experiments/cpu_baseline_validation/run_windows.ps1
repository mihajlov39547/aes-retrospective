param(
    [Parameter(Mandatory=$true)][string]$OpenSSLRoot,
    [switch]$Study,
    [int]$Workers = 1,
    [string]$Notes = ''
)
# Run from an x64 Native Tools / Developer PowerShell with cl.exe available.
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    function Invoke-Checked([string]$Exe, [string[]]$Arguments) {
        & $Exe @Arguments
        if ($LASTEXITCODE -ne 0) { throw "Command failed: $Exe $Arguments" }
    }
    Invoke-Checked 'python' @('-m', 'venv', '.venv')
    $PythonPath = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
    Invoke-Checked $PythonPath @('-m', 'pip', 'install', '-r', 'requirements.txt')
    Invoke-Checked $PythonPath @('build.py', '--openssl-root', $OpenSSLRoot)
    Invoke-Checked $PythonPath @('-m', 'unittest', 'discover', '-s', '.', '-v')
    Invoke-Checked $PythonPath @('run.py')
    if ($Workers -gt 1) {
        Invoke-Checked $PythonPath @('run.py', '--workers', "$Workers")
    }
    if ($Study) {
        Invoke-Checked $PythonPath @('run.py', '--study', '--workers', "$Workers", "--notes=$Notes")
    }
} finally {
    Pop-Location
}
