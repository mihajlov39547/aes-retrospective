"""Build a separate native page-batch wrapper; leaves Phase 1 builds untouched."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import subprocess
import sys

HERE = Path(__file__).resolve().parent
CPU_ROOT = HERE.parent / 'cpu_baseline_validation'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--openssl-root', type=Path)
    args = p.parse_args()
    folder = HERE/'build'/('windows-x86_64' if os.name == 'nt' else 'linux-x86_64')
    folder.mkdir(parents=True, exist_ok=True)
    lib = folder / ('baseline.dll' if os.name == 'nt' else 'libbaseline.so')
    source = HERE/'batch_native.c'
    extra = {}
    if os.name == 'nt':
        if not args.openssl_root:
            p.error('--openssl-root required on Windows; run in x64 Developer PowerShell')
        root = args.openssl_root.resolve()
        imports = next((root/n for n in ('lib/VC/x64/MD/libcrypto.lib', 'lib/libcrypto.lib') if (root/n).exists()), None)
        dlls = list((root/'bin').glob('libcrypto-3*.dll')) + list(root.glob('libcrypto-3*.dll'))
        if imports is None or len(dlls) != 1 or not (root/'include/openssl/evp.h').exists():
            p.error('OpenSSL 3 x64 development headers, import library and exactly one libcrypto DLL required')
        sys.path.append(str(CPU_ROOT))
        from windows_native import require_x64_pe
        require_x64_pe(dlls[0])
        command = ['cl', '/nologo', '/O2', '/MD', '/LD', str(source), '/I'+str(root/'include'),
                   str(imports), '/link', '/MACHINE:X64', '/OUT:'+str(lib)]
        compiler = subprocess.run(['cl'], capture_output=True, text=True)
        version = compiler.stdout + compiler.stderr
        extra = dict(crypto_dll=str(dlls[0].resolve()), crypto_dll_sha256=sha(dlls[0]),
                     import_library=str(imports), import_library_sha256=sha(imports))
    else:
        if platform.machine().lower() != 'x86_64':
            p.error('Phase 2 target is Linux x86-64')
        compiler = os.environ.get('CC', 'cc')
        command = [compiler, '-O3', '-std=c11', '-Wall', '-Wextra', '-Werror', '-fPIC', '-shared',
                   str(source), '-o', str(lib)] + shlex.split(subprocess.check_output(
                       ['pkg-config', '--cflags', '--libs', 'libcrypto'], text=True))
        version = subprocess.check_output([compiler, '--version'], text=True)
    subprocess.run(command, cwd=folder, check=True)
    record = dict(command=command, compiler=version, architecture=platform.machine(), platform=platform.platform(),
        source_sha256=sha(CPU_ROOT/'native.c'), batch_source_sha256=sha(source), library_sha256=sha(lib),
        openssl_root=str(args.openssl_root.resolve()) if args.openssl_root else None, **extra)
    (folder/'build.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    from engines import CPU
    (folder/'native_verification.json').write_text(json.dumps(CPU().metadata(), indent=2), encoding='utf-8')
    print(lib)


if __name__ == '__main__':
    main()
