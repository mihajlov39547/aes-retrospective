"""Build a small shared library; only Python stdlib needed for the build driver."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import subprocess
import ctypes

ROOT = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--openssl-root', type=Path)
    p.add_argument('--cc', default=os.environ.get('CC', 'cl' if os.name == 'nt' else 'cc'))
    args = p.parse_args()
    dest = ROOT / 'build' / 'windows-x86_64' if os.name == 'nt' else ROOT / 'build'
    dest.mkdir(parents=True, exist_ok=True)
    src = ROOT / 'native.c'
    lib = dest / ('baseline.dll' if os.name == 'nt' else 'libbaseline.so')
    if os.name == 'nt':
        if not args.openssl_root:
            p.error('Windows requires --openssl-root (OpenSSL 3 x64 development installation)')
        root = args.openssl_root.resolve()
        if ctypes.sizeof(ctypes.c_void_p) != 8 or platform.machine().lower() not in ('amd64', 'x86_64'):
            p.error('Use native Windows x86-64 Python')
        if not (root / 'include/openssl/evp.h').is_file():
            p.error('Missing OpenSSL development headers')
        candidates = [root / 'lib/VC/x64/MD/libcrypto.lib', root / 'lib/libcrypto.lib']
        crypto = next((f for f in candidates if f.exists()), None)
        if not crypto:
            p.error('Cannot locate x64 libcrypto.lib under OpenSSL root')
        dlls = list((root / 'bin').glob('libcrypto-3*.dll')) + list(root.glob('libcrypto-3*.dll'))
        if len(dlls) != 1:
            p.error('Expected exactly one libcrypto-3*.dll in OpenSSL root or bin')
        crypto_dll = dlls[0].resolve()
        from windows_native import require_x64_pe
        require_x64_pe(crypto_dll)
        command = [args.cc, '/nologo', '/O2', '/MD', '/LD', str(src),
                   '/I' + str(root / 'include'), str(crypto), '/link', '/MACHINE:X64', '/OUT:' + str(lib)]
        compiler = subprocess.run([args.cc], capture_output=True, text=True)
    else:
        flags = shlex.split(subprocess.check_output(
            ['pkg-config', '--cflags', '--libs', 'libcrypto'], text=True))
        command = [args.cc, '-O3', '-std=c11', '-Wall', '-Wextra', '-Werror', '-fPIC',
                   '-shared', str(src), '-o', str(lib)] + flags
        compiler = subprocess.run([args.cc, '--version'], capture_output=True, text=True)
    subprocess.run(command, cwd=dest, check=True)
    record = dict(command=command, compiler=compiler.stdout + compiler.stderr,
                  architecture=platform.machine(), platform=platform.platform(),
                  source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
                  library_sha256=hashlib.sha256(lib.read_bytes()).hexdigest(),
                  openssl_root=str(args.openssl_root.resolve()) if args.openssl_root else None)
    if os.name == 'nt':
        from windows_native import sha256
        require_x64_pe(lib)
        record.update(crypto_dll=str(crypto_dll), crypto_dll_sha256=sha256(crypto_dll),
                      import_library=str(crypto), import_library_sha256=sha256(crypto))
    (dest / 'build.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    if os.name == 'nt':
        from core import Native
        verified = Native().metadata()
        (dest / 'native_verification.json').write_text(json.dumps(verified, indent=2), encoding='utf-8')
    print(lib)


if __name__ == '__main__':
    main()
