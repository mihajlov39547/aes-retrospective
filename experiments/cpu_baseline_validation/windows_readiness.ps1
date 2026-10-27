param([string]$OpenSSLRoot = '')
# Read-only inventory. No installation, compilation or benchmark is performed.
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Run this check in native Windows PowerShell.' }
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$vs = @()
$cpp = @()
if (Test-Path -LiteralPath $vswhere) {
    $vs = & $vswhere -all -products '*' -format json | ConvertFrom-Json
    $cpp = & $vswhere -all -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -format json | ConvertFrom-Json
    if (-not $vs) { $vs = @() }
    if (-not $cpp) { $cpp = @() }
}
$compiler = Get-Command cl.exe -ErrorAction SilentlyContinue
$compilerPaths = @($cpp | ForEach-Object {
    Get-ChildItem -LiteralPath (Join-Path $_.installationPath 'VC/Tools/MSVC') -Filter cl.exe -Recurse -ErrorAction SilentlyContinue |
        Where-Object FullName -Match 'Hostx64[\\/]x64[\\/]cl.exe$' | ForEach-Object FullName
})
$roots = @($OpenSSLRoot, $env:OPENSSL_ROOT_DIR, 'C:/OpenSSL-Win64', 'C:/Program Files/OpenSSL-Win64')
$roots += @(Get-ItemProperty 'HKLM:/SOFTWARE/Microsoft/Windows/CurrentVersion/Uninstall/*',
    'HKLM:/SOFTWARE/WOW6432Node/Microsoft/Windows/CurrentVersion/Uninstall/*' -ErrorAction SilentlyContinue |
    Where-Object DisplayName -Match 'OpenSSL' | ForEach-Object InstallLocation)
$openssl = @($roots | Where-Object { $_ } | Select-Object -Unique | ForEach-Object {
    $root = $_
    $libs = @('lib/VC/x64/MD/libcrypto.lib', 'lib/libcrypto.lib') | ForEach-Object { Join-Path $root $_ } |
        Where-Object { Test-Path -LiteralPath $_ }
    $dlls = @(Get-ChildItem -Path (Join-Path $root 'bin/libcrypto-3*.dll'),
        (Join-Path $root 'libcrypto-3*.dll') -ErrorAction SilentlyContinue | ForEach-Object FullName)
    [PSCustomObject]@{root=$root; headers=(Test-Path -LiteralPath (Join-Path $root 'include/openssl/evp.h'));
        import_libraries=@($libs); dlls=$dlls; complete=((Test-Path -LiteralPath (Join-Path $root 'include/openssl/evp.h')) -and @($libs).Count -gt 0 -and $dlls.Count -eq 1)}
})
$sdkRoot = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits/10'
$sdkLibraries = @(Get-ChildItem -Path (Join-Path $sdkRoot 'Lib/*/um/x64/kernel32.lib') -ErrorAction SilentlyContinue | ForEach-Object FullName)
$sdkHeaders = @(Get-ChildItem -Path (Join-Path $sdkRoot 'Include/*/um/Windows.h') -ErrorAction SilentlyContinue | ForEach-Object FullName)
$pythonInfo = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonInfo = (& python -c "import sys,struct,platform,importlib.metadata,importlib.util,json; print(json.dumps(dict(executable=sys.executable,version=platform.python_version(),bits=struct.calcsize('P')*8,pycryptodome=importlib.metadata.version('pycryptodome') if importlib.util.find_spec('Crypto') else None)))" | ConvertFrom-Json)
}
$missing = @()
if (-not $compiler -and $compilerPaths.Count -eq 0) { $missing += 'MSVC x64 C++ toolset' }
if ($sdkLibraries.Count -eq 0 -or $sdkHeaders.Count -eq 0) { $missing += 'Windows SDK headers and x64 libraries' }
if (@($openssl | Where-Object complete).Count -eq 0) { $missing += 'OpenSSL 3 x64 development headers, import library and DLL' }
if (-not $pythonInfo -or $pythonInfo.bits -ne 64) { $missing += '64-bit Python with PyCryptodome' }
elseif (-not $pythonInfo.pycryptodome) { $missing += 'PyCryptodome' }
$runtime = Test-Path -LiteralPath (Join-Path $env:SystemRoot 'System32/vcruntime140.dll')
if (-not $runtime) { $missing += 'MSVC x64 runtime' }
[PSCustomObject]@{
    native_windows=$true; cpu=@(Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors);
    visual_studio=@($vs | Select-Object displayName,installationPath);
    cpp_installations=@($cpp | Select-Object installationPath); compiler_on_path=$compiler.Source;
    compiler_paths=$compilerPaths; sdk_headers=$sdkHeaders; sdk_libraries=$sdkLibraries;
    openssl_candidates=$openssl; python=$pythonInfo; msvc_runtime_present=$runtime;
    missing=$missing; ready_to_attempt_build=($missing.Count -eq 0);
    note='Inventory is not a build/ABI/DLL verification. build.py and Native enforce x64 PE, paths, hashes and actual EVP imports.'
} | ConvertTo-Json -Depth 8
