"""Build the unchanged Phase 1 EVP wrapper into this experiment's Linux build directory."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import subprocess

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'cpu_baseline_validation/native.c'


def main():
    if platform.system() != 'Linux' or platform.machine().lower() not in ('x86_64', 'amd64'):
        raise SystemExit('Target build requires Linux x86-64. Native Windows local smoke reuses the verified CPU build.')
    out = HERE / 'build'
    out.mkdir(exist_ok=True)
    compiler = os.environ.get('CC', 'cc')
    command = [compiler, '-O3', '-std=c11', '-Wall', '-Wextra', '-Werror', '-fPIC', '-shared',
               str(SOURCE), '-o', str(out / 'libbaseline.so')]
    command += shlex.split(subprocess.check_output(['pkg-config', '--cflags', '--libs', 'libcrypto'], text=True))
    subprocess.run(command, check=True)
    manifest = dict(command=command, compiler=subprocess.check_output([compiler, '--version'], text=True),
        architecture=platform.machine(), platform=platform.platform(), openssl_root=None,
        source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        library_sha256=hashlib.sha256((out / 'libbaseline.so').read_bytes()).hexdigest())
    (out / 'build.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(out / 'libbaseline.so')


if __name__ == '__main__':
    main()
