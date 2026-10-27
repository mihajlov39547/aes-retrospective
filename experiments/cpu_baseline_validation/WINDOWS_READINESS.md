# Native Windows x86-64 readiness — i5-10300H

Local inspection on 2026-10-27 found:

| Component | Status |
|---|---|
| CPU | Intel Core i5-10300H, 4 cores / 8 logical processors |
| Native Python | `C:/Projects/aes/.venv/Scripts/python.exe`, 3.12.10, 64 bit |
| PyCryptodome | 3.23.0, present; all 37 correctness cases pass natively |
| Visual Studio | Community 2026 installed at `C:/Program Files/Microsoft Visual Studio/18/Community` |
| MSVC C++ x64 toolset | Missing: no `cl.exe` on PATH, no installed x86/x64 tools component in vswhere, no compiler found under VS roots |
| Windows SDK development files | Missing: no Windows.h / x64 kernel32.lib under Windows Kits/10 |
| OpenSSL 3 development installation | Missing: no headers/import library in configured/default/registered locations; broader Program Files/Downloads searches found no libcrypto.lib |
| MSVC runtime | Present (`System32/vcruntime140.dll`) |

The Windows launcher was executed in smoke mode and correctly stopped at this
dependency gate. **Native EVP compilation, EVP NIST validation, DLL binding proof,
and Windows benchmark smoke runs remain blocked by missing build dependencies.**
The Windows PyCryptodome checks, numerical regressions and mocked PE/loader tests
passed; these do not substitute for the native EVP gate. No WSL timing is labelled
as a Windows result, and no full campaign was launched.

## Install only the missing components

1. Modify the existing Visual Studio Community installation using **Visual Studio
   Installer → Modify → Desktop development with C++**. Include the MSVC x64/x86
   build tools and a Windows SDK. There is no need to install another IDE, Python,
   PyCryptodome or runtime. Microsoft's [C++ workload instructions](https://learn.microsoft.com/cpp/build/vscpp-step-0-installation)
   describe adding this workload to an existing installation.
2. Install an **OpenSSL 3.x Win64 full development package**, e.g. the non-Light
   Win64 3.x package from the [Shining Light distribution](https://slproweb.com/products/Win32OpenSSL.html),
   into `C:/OpenSSL-Win64` for the commands below. Select the package's own `bin`
   directory for DLL placement. This experiment requires 3.x, not 4.x, and the
   full development files, not just the Light runtime. A source-built OpenSSL 3
   x64 installation with the same layout is also supported.

Required OpenSSL layout: `include/openssl/evp.h`, one `libcrypto-3*.dll` in `bin`
or the installation root, and `lib/VC/x64/MD/libcrypto.lib` or `lib/libcrypto.lib`.
The build records the actual version, compiler flags and hashes. Git's bundled
OpenSSL DLL is not a substitute for the missing development package.

## Exact PowerShell commands

Start a fresh **native Windows PowerShell**, then run the read-only check:

```powershell
Set-Location C:/Projects/aes
& ./experiments/cpu_baseline_validation/windows_readiness.ps1 -OpenSSLRoot C:/OpenSSL-Win64
```

After `ready_to_attempt_build` becomes true, compile, verify DLL bindings, run all
tests and run single-thread smoke (no full study):

```powershell
& ./experiments/cpu_baseline_validation/run_windows.ps1 -OpenSSLRoot C:/OpenSSL-Win64
```

The launcher discovers the C++ installation and initializes the x64 MSVC
Developer PowerShell environment. It creates `.venv-windows/` separately from
the existing Linux `.venv/`; native artifacts live in `build/windows-x86_64/`.
Unit tests include separate single-thread and two-worker smoke sessions; the
retained default smoke output is single-thread. All child commands must succeed.

**Only after reviewing the native smoke outputs**, the exact single-thread study
command is (provided for later execution; not run during this task):

```powershell
Set-Location C:/Projects/aes
& ./experiments/cpu_baseline_validation/run_windows.ps1 `
  -OpenSSLRoot C:/OpenSSL-Win64 `
  -Study -Workers 1 `
  -Notes 'Native Windows i5-10300H; AC power; record power plan and competing load'
```

This repeats build/tests/smoke first, then runs seeds 2003–2007 with five warmups
and twenty repetitions. Each session gets a new UUID; Oracle outputs are untouched.
Change `-OpenSSLRoot` if a different installation directory is used. No PATH-based
`openssl.exe` selection is used for the primary comparison.

## Native library provenance gate

`build.py` requires an x64 Windows PE libcrypto and links the wrapper with
`/MACHINE:X64`. The manifest pins absolute paths and SHA-256 hashes of the wrapper,
OpenSSL DLL and import library. `Native` explicitly preloads that DLL, then walks
the loaded wrapper's import address table. It resolves the module owning the
actual addresses for `OpenSSL_version`, `EVP_EncryptUpdate` and `EVP_CIPHER_fetch`
using the Windows [address-based module API](https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-getmodulehandleexw).
Each must map to the configured file and hash, or the run fails. This also catches
a conflicting preloaded DLL with the same basename; checking just the algorithm
name, version string or `openssl.exe` on PATH would not do so.

Successful evidence goes to `build/windows-x86_64/native_verification.json` and
each session's worker metadata. The build and each fresh worker enforce the check
before accepting timings. WSL ELF binaries fail the Windows PE check. The current
machine cannot produce this evidence until its missing dependencies are installed.
