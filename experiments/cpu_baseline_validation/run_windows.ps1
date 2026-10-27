param(
    [string]$OpenSSLRoot = '',
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
    $readiness = & (Join-Path $PSScriptRoot 'windows_readiness.ps1') -OpenSSLRoot $OpenSSLRoot | ConvertFrom-Json
    if (-not $readiness.ready_to_attempt_build) {
        throw ('Missing components: ' + ($readiness.missing -join '; ') + '. See WINDOWS_READINESS.md.')
    }
    if (-not $OpenSSLRoot) {
        $OpenSSLRoot = ($readiness.openssl_candidates | Where-Object complete | Select-Object -First 1).root
    }
    if ($readiness.cpp_installations.Count -gt 0) {
        $vsPath = $readiness.cpp_installations[0].installationPath
        Import-Module (Join-Path $vsPath 'Common7/Tools/Microsoft.VisualStudio.DevShell.dll')
        Enter-VsDevShell -VsInstallPath $vsPath -SkipAutomaticLocation -DevCmdArguments '-arch=x64 -host_arch=x64'
    }
    Invoke-Checked 'python' @('-m', 'venv', '.venv-windows')
    $PythonPath = Join-Path $PSScriptRoot '.venv-windows/Scripts/python.exe'
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
