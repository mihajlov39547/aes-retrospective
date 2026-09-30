"""Isolated tiny CUDA integration checks. Never invokes pilot/study."""
import contextlib
import csv
import io
import json
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
from unittest.mock import patch

import aes_cuda_baseline as b


def main():
    with tempfile.TemporaryDirectory(prefix='aes-cuda-smoke-') as temporary:
        root = Path(temporary)
        proc = subprocess.run([sys.executable, str(Path(b.__file__)), '--output', str(root)],
                              capture_output=True, text=True)
        assert proc.returncode == 0 and json.loads(proc.stdout)['status']=='plan_only'
        defaults = json.loads(proc.stdout)['arguments']
        assert defaults['sizes']==[1024,16384,1048576,16777216,33554432]
        assert (defaults['profile'],defaults['measurement'],defaults['host_memory'])==('baseline','pipeline','pinned')
        b.arguments(['--profile','baseline','--measurement','pipeline','--host-memory','pinned','--sizes','33554432'])
        # CLI-only checks: never allocate or measure these large buffers in smoke.
        for size in (67108864,104857600):
            for measurement in ('pipeline','resident','transfer-only'):
                for memory in ('pageable','pinned'):
                    b.arguments(['--profile','diagnostic','--measurement',measurement,
                                 '--host-memory',memory,'--sizes',str(size)])
        assert not list(root.iterdir())
        for options in (['--sizes','0'], ['--sizes','16','16'], ['--warmup','-1'],
                        ['--repeats','0'], ['--modes','ECB','ECB'], ['--sizes','1025'],
                        ['--sizes','104857600'], ['--sizes','67108864'], ['--host-memory','pageable'],
                        ['--measurement','resident'], ['--profile','diagnostic','--purpose','study'],
                        ['--profile','diagnostic','--resident-iterations','0']):
            with contextlib.redirect_stderr(io.StringIO()):
                try:
                    b.arguments(options)
                except SystemExit as exc:
                    assert exc.code == 2
                else:
                    raise AssertionError(options)
        for size in (1000,1025,16385):
            b.arguments(['--modes','CTR','--sizes',str(size)])
        try:
            b.check_input('CTR', b.KEY, (2**128-1).to_bytes(16,'big'),17)
        except ValueError:
            pass
        else:
            raise AssertionError('CTR wrap accepted')
        b.check_input('CTR', b.KEY, (2**128-1).to_bytes(16,'big'),16)
        args = b.arguments(['--run','--purpose','smoke','--output',str(root),
                            '--sizes','1024','--warmup','1','--repeats','2'])
        class ForbiddenGPU:
            def measure(self, job):
                raise AssertionError('Timer entered after failed validation')
            def prepare(self, *args):
                raise AssertionError('Performance preparation after failed validation')
        try:
            b.run(args, ForbiddenGPU(), lambda *a: {'passed':False})
        except RuntimeError as exc:
            assert 'validation failed' in str(exc)
        else:
            raise AssertionError('Failed gate accepted')
        assert not list(root.rglob('raw.csv')) and not list(root.rglob('summary.csv'))
        print('PASS: plan-only, CLI validation, counter-wrap rejection, failed-validation gate')
        gpu = b.GPU()  # A missing runtime/device is a smoke failure, never a simulated PASS.
        print('GPU:', json.dumps(gpu.info))
        with patch.object(gpu, 'measure', side_effect=AssertionError('Validation must not time')):
            report = b.validate(gpu, 'smoke-validation', 'smoke')
        assert report['passed'], report
        assert len(report['tests']) == 18
        print('PASS: 18 real GPU KAT/differential tests (ECB, CTR, carry, partial blocks)')
        original_encrypt = gpu.encrypt
        def corrupt(*a):
            output = original_encrypt(*a)
            return bytes([output[0]^1]) + output[1:]
        with patch.object(gpu, 'encrypt', side_effect=corrupt), patch.object(
                gpu, 'measure', side_effect=AssertionError('Timer after corrupt validation')):
            try:
                b.run(args, gpu)
            except RuntimeError as exc:
                assert 'validation failed' in str(exc)
            else:
                raise AssertionError('Corrupted CUDA output accepted')
        assert not list(root.rglob('raw.csv')) and not list(root.rglob('summary.csv'))
        print('PASS: deliberately corrupted GPU output rejected before timing/export')
        original_measure = gpu.measure
        def audited_measure(job):
            assert gpu.host_memory=='pinned'
            assert isinstance(job[1].base.obj, gpu.cp.cuda.PinnedMemoryPointer)
            assert isinstance(job[2].base.obj, gpu.cp.cuda.PinnedMemoryPointer)
            reports = [json.loads(p.read_text()) for p in root.glob('aes_cuda_baseline-validation-*/validation.json')]
            assert any(r.get('passed') is True and r.get('purpose')=='smoke' for r in reports)
            return original_measure(job)
        for modes, sizes, expected_rows in [(['ECB','CTR'],['1024','16384'],8), (['CTR'],['1025'],2)]:
            args = b.arguments(['--run','--purpose','smoke','--output',str(root), '--modes',*modes,
                                '--sizes',*sizes,'--warmup','1','--repeats','2','--seed','2003'])
            with patch.object(gpu, 'measure', side_effect=audited_measure):
                directory = b.run(args, gpu)
            data = json.loads((directory/'results.json').read_text())
            raw, summary = data['raw'], data['summary']
            assert len(raw)==expected_rows and len(summary)==expected_rows//2
            for filename, count in [('raw.csv',expected_rows),('summary.csv',expected_rows//2)]:
                with (directory/filename).open(newline='',encoding='utf-8') as handle:
                    assert len(list(csv.DictReader(handle)))==count
            for row in raw:
                assert (row['profile'],row['measurement'],row['host_memory'])==('baseline','pipeline','pinned')
                assert row['validation_checked'] and row['kernel_ns']>0 and row['end_to_end_ns']>0
                assert row['kernel_seconds']==row['kernel_ns']/1e9
                assert row['end_to_end_seconds']==row['end_to_end_ns']/1e9
                assert row['transfer_ns']==row['h2d_ns']+row['d2h_ns']
                for scope in ('kernel','end_to_end'):
                    assert abs(row[scope+'_throughput_MB_s'] - row['bytes']/1e6/row[scope+'_seconds'])<1e-8
            for row in summary:
                group = [r for r in raw if (r['mode'],r['bytes'])==(row['mode'],row['bytes'])]
                for metric in b.METRICS:
                    values=[r[metric] for r in group]
                    expected=dict(count=2,mean=statistics.mean(values),median=statistics.median(values),
                                  stdev=statistics.stdev(values),min=min(values),max=max(values))
                    for key,value in expected.items():
                        assert row[metric+'_'+key]==value
            meta=json.loads((directory/'metadata.json').read_text())
            assert meta['validation_sha256']==b.digest(directory/'validation.json')
            for name, sha in meta['source_sha256'].items():
                assert b.digest(directory/'source'/name)==sha
            assert meta['kernel_sha256']==b.digest(b.KERNEL)
        print('PASS: validation-before-timing, raw/summary counts, formulas, sample statistics, source hashes')
        example = b.extended_stats([1,2,3,4,100])
        assert example['iqr']==2 and example['outlier_count']==1 and example['outlier_flag']
        assert example['coefficient_of_variation']==statistics.stdev([1,2,3,4,100])/22
        assert b.extended_stats([5])['coefficient_of_variation'] is None
        for memory in ('pageable','pinned'):
            for measurement in ('pipeline','resident','transfer-only'):
                args = b.arguments(['--run','--purpose','smoke','--output',str(root),
                                    '--profile','diagnostic','--measurement',measurement,
                                    '--host-memory',memory,'--resident-iterations','3',
                                    '--sizes','1024','--warmup','1','--repeats','2'])
                directory = b.run(args,gpu)
                assert directory.name.startswith('aes_cuda_baseline_diagnostic-smoke-')
                data = json.loads((directory/'results.json').read_text())
                assert len(data['raw'])==4 and len(data['summary'])==2
                for row in data['raw']:
                    assert row['profile']=='diagnostic' and row['host_memory']==memory
                    if measurement=='resident':
                        assert row['kernel_ns']==row['resident_batch_ns']/3
                        assert row['end_to_end_ns'] is None and row['transfer_ns'] is None
                    elif measurement=='transfer-only':
                        assert row['kernel_ns'] is None and row['end_to_end_ns'] is None
                        assert row['transfer_ns']==row['h2d_ns']+row['d2h_ns']
                        assert row['operation']=='copy'
                meta=json.loads((directory/'metadata.json').read_text())
                assert 'environment_before' in meta and 'environment_after' in meta
                # Directly assert transfer-only never launches AES in its timed path.
                job=gpu.prepare('CTR',b.KEY,b.COUNTER,b.PLAIN[:17])
                if memory=='pinned':
                    assert isinstance(job[1].base.obj, gpu.cp.cuda.PinnedMemoryPointer)
                    assert isinstance(job[2].base.obj, gpu.cp.cuda.PinnedMemoryPointer)
                if measurement=='transfer-only':
                    with patch.object(gpu,'launch',side_effect=AssertionError('AES in copy-only')):
                        gpu.measure_diagnostic(job,measurement,3)
                    assert job[2].tobytes()==b.PLAIN[:17]
        print('PASS: diagnostic isolation, pinned/pageable paths, resident batches, transfer-only, IQR/CV/outliers')
    print('PASS: isolated CUDA baseline smoke (temporary artifacts only; no pilot/study)')


if __name__=='__main__':
    main()
