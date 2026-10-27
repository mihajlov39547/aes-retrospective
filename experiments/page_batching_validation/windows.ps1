param(
    [string]$Python = "$PSScriptRoot/../../.venv/Scripts/python.exe",
    [string]$OpenSSLRoot = 'C:/OpenSSL-Win64',
    [string]$Output = "$PSScriptRoot/results/windows-smoke-$([guid]::NewGuid())"
)
$ErrorActionPreference = 'Stop'
$vswhere = "${env:ProgramFiles(x86)}/Microsoft Visual Studio/Installer/vswhere.exe"
if (!(Test-Path $vswhere)) { throw 'Missing MSVC: install Visual Studio Build Tools, Desktop development with C++, x64 tools and Windows SDK.' }
$vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (!$vs) { throw 'Missing MSVC x64 C++ tools/Windows SDK. Add Desktop development with C++ in Visual Studio Installer.' }
Import-Module "$vs/Common7/Tools/Microsoft.VisualStudio.DevShell.dll"
Enter-VsDevShell -VsInstallPath $vs -SkipAutomaticLocation -DevCmdArguments '-arch=x64 -host_arch=x64'
if (!(Test-Path "$OpenSSLRoot/include/openssl/evp.h")) { throw 'Missing OpenSSL 3 x64 development installation: supply headers, MD import library and libcrypto DLL via -OpenSSLRoot.' }
if (!(Test-Path $Python)) { throw 'Supply -Python with Python 3.10-3.12 x64 and the documented dependencies.' }
& $Python "$PSScriptRoot/build.py" --openssl-root $OpenSSLRoot
if ($LASTEXITCODE) { throw 'Native build failed' }
& $Python -m unittest discover -s $PSScriptRoot -p test_phase2.py -v
if ($LASTEXITCODE) { throw 'Tests failed' }
& $Python "$PSScriptRoot/run.py" --local-gpu 'NVIDIA GeForce GTX 1650 Ti' --output $Output
if ($LASTEXITCODE) { throw 'GPU smoke failed' }
