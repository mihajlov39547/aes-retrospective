"""Build a small shared library; only Python stdlib needed for the build driver."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import subprocess

ROOT = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--openssl-root', type=Path)
    p.add_argument('--cc', default=os.environ.get('CC', 'cl' if os.name == 'nt' else 'cc'))
    args = p.parse_args()
    dest = ROOT / 'build'
    dest.mkdir(exist_ok=True)
    src = ROOT / 'native.c'
    lib = dest / ('baseline.dll' if os.name == 'nt' else 'libbaseline.so')
    if os.name == 'nt':
        if not args.openssl_root:
            p.error('Windows requires --openssl-root (OpenSSL 3 x64 development installation)')
        root = args.openssl_root.resolve()
        candidates = [root / 'lib/VC/x64/MD/libcrypto.lib', root / 'lib/libcrypto.lib']
        crypto = next((f for f in candidates if f.exists()), None)
        if not crypto:
            p.error('Cannot locate x64 libcrypto.lib under OpenSSL root')
        command = [args.cc, '/nologo', '/O2', '/MD', '/LD', str(src),
                   '/I' + str(root / 'include'), str(crypto), '/link', '/OUT:' + str(lib)]
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
                  openssl_root=str(args.openssl_root) if args.openssl_root else None)
    (dest / 'build.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(lib)


if __name__ == '__main__':
    main()
