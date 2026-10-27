"""Setup control-flow tests; no apt/pip installations or benchmarks are launched."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.name == 'posix' and shutil.which('bash'), 'Requires POSIX bash')
class SetupTests(unittest.TestCase):
    def run_setup(self, fail='', cuda='13', fallback=False):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            shutil.copyfile(Path(__file__).with_name('colab_setup.sh'),root/'colab_setup.sh')
            binaries=root/'bin'; binaries.mkdir()
            python=binaries/'python3'
            python.write_text('''#!/usr/bin/env bash
set -eu
echo "$*" >> "$LOG"
if [[ "$*" == '-m venv .venv' ]]; then
  mkdir -p .venv/bin
  ln -sf "$FAKE_PYTHON" .venv/bin/python
  if [[ "$FALLBACK" == 1 ]]; then exit 1; fi
fi
if [[ -n "$FAIL" && "$*" == *"$FAIL"* ]]; then exit 9; fi
''')
            sudo=binaries/'sudo'; sudo.write_text('#!/usr/bin/env bash\necho "sudo $*" >> "$LOG"\n')
            toolkit=root/'cuda'/'bin'; toolkit.mkdir(parents=True)
            nvcc=toolkit/'nvcc'; nvcc.write_text('#!/usr/bin/env bash\necho "release $CUDA_MAJOR.0"\n')
            for p in (python,sudo,nvcc): p.chmod(0o755)
            env=dict(os.environ,PATH=str(binaries)+os.pathsep+os.environ['PATH'],PYTHON=str(python),
                CUDA_PATH=str(toolkit.parent),CUDA_MAJOR=cuda,LOG=str(root/'calls'),
                FAKE_PYTHON=str(python),FAIL=fail,FALLBACK=str(int(fallback)))
            result=subprocess.run(['bash',str(root/'colab_setup.sh')],env=env,text=True,capture_output=True)
            return result,(root/'calls').read_text()

    def test_stdlib_and_cuda_selection(self):
        for major,wheel in [('12','cupy-cuda12x==13.6.0'),('13','cupy-cuda13x==14.0.1')]:
            result,calls=self.run_setup(cuda=major)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn(wheel,calls); self.assertNotIn('virtualenv',calls)
            self.assertNotIn('python3-venv',calls)
            self.assertLess(calls.index('build.py'),calls.index('-m unittest'))
            self.assertIn('Setup complete:',result.stdout)

    def test_ensurepip_fallback(self):
        result,calls=self.run_setup(fallback=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('virtualenv==20.35.4',calls)
        self.assertIn('-m virtualenv --python',calls)

    def test_fail_closed(self):
        for fail in ('pip install -r','pip install cupy','pip check','build.py','-m unittest'):
            with self.subTest(fail=fail):
                result,calls=self.run_setup(fail=fail)
                self.assertNotEqual(result.returncode,0)
                self.assertNotIn('Setup complete:',result.stdout)
                if fail!='-m unittest': self.assertNotIn('-m unittest',calls)

    def test_fallback_install_failure(self):
        result,calls=self.run_setup(fail='pip install --target',fallback=True)
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn('build.py',calls)

    def test_unsupported_cuda(self):
        result,calls=self.run_setup(cuda='11')
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn('sudo',calls)


if __name__=='__main__': unittest.main()
