"""Small isolated integration tests; never pilot/study or old-result modification."""
import contextlib
import csv
import io
import json
import math
import random
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import aes_cuda_cpu_gpu as c


def main():
    baseline_hash=c.base.digest(c.base.KERNEL)
    v1_hash=c.base.digest(c.OPTIMIZED)
    with tempfile.TemporaryDirectory(prefix='cuda-paired-smoke-') as tmp:
        root=Path(tmp)
        plan=subprocess.run([sys.executable,c.__file__,'--output',str(root)],capture_output=True,text=True)
        assert plan.returncode==0 and json.loads(plan.stdout)['status']=='plan_only'
        assert not list(root.iterdir())
        assert c.arguments([]).sizes==[1024,16384,1048576,16777216,33554432]
        assert c.arguments([]).profile==list(c.PROFILES)
        assert c.arguments(['--profile','optimized']).profile==['optimized']
        for opts in (['--sizes','0'],['--sizes','67108864'],['--sizes','104857600'],
                     ['--sizes','1025'],['--profile','baseline','baseline'],['--warmup','-1'],
                     ['--repeats','1'],['--host-memory','pageable'],['--resident-iterations','0'],
                     ['--measurements','pipeline','--resident-iterations','2']):
            with contextlib.redirect_stderr(io.StringIO()):
                try: c.arguments(opts)
                except SystemExit as exc: assert exc.code==2
                else: raise AssertionError(opts)
        assert c.material(random.Random(2003),1025)==c.material(random.Random(2003),1025)
        assert c.material(random.Random(2003),1025)!=c.material(random.Random(2004),1025)
        gpus={p:c.GPU(p) for p in c.PROFILES}
        with patch.object(c,'cpu_measure',side_effect=AssertionError('CPU timed during validation')), \
             patch.object(c.base.GPU,'measure',side_effect=AssertionError('GPU timed during validation')):
            report=c.validate(gpus,'smoke','smoke')
        assert report['passed'],report
        assert report['all_backends_equal'] and len(report['paths'])==5
        assert all(len(p['tests'])==18 and p['wrap_rejected'] for p in report['paths'].values())
        print('PASS: dispatch ECB/CTR; five paths x18 KAT/differential checks; carry/tails/wrap/equality')
        args=c.arguments(['--run','--purpose','smoke','--output',str(root),'--sizes','1024',
                          '--warmup','1','--repeats','2'])
        def corrupt(*a): return bytes(len(a[-1]))
        for profile in ('optimized','ttable'):
            with patch.object(gpus[profile],'encrypt',side_effect=corrupt), \
                 patch.object(c,'cpu_measure',side_effect=AssertionError('Timing after failure')), \
                 patch.object(c.base.GPU,'measure_diagnostic',side_effect=AssertionError('Timing after failure')):
                try: c.run(args,gpus)
                except RuntimeError as exc: assert 'Validation failed' in str(exc)
                else: raise AssertionError('Corruption accepted: '+profile)
        assert not list(root.rglob('raw.csv'))
        with patch.object(c,'verify_dispatch',side_effect=RuntimeError('Capability unavailable')):
            try: c.run(args,gpus)
            except RuntimeError as exc: assert 'Validation failed' in str(exc)
            else: raise AssertionError('Missing dispatch accepted')
        assert not list(root.rglob('summary.csv'))
        original_cpu=c.cpu_measure
        original_gpu=c.base.GPU.measure_diagnostic
        active_report=None
        def audited_validator(*a):
            nonlocal active_report
            active_report=c.validate(*a)
            return active_report
        def assert_gate():
            assert active_report is not None and active_report['passed']
            path=root/('aes_cuda_cpu_gpu-validation-'+active_report['session_id'])/'validation.json'
            assert json.loads(path.read_text())==active_report
        def audited_cpu(*a):
            assert_gate()
            return original_cpu(*a)
        def audited_gpu(self,*a):
            assert_gate()
            return original_gpu(self,*a)
        for modes,sizes,iterations,rows in [(['ECB','CTR'],['1024','16384'],1,64),(['CTR'],['1025'],3,16)]:
            args=c.arguments(['--run','--purpose','smoke','--output',str(root),'--modes',*modes,
                              '--sizes',*sizes,'--warmup','1','--repeats','2','--resident-iterations',str(iterations)])
            with patch.object(c,'cpu_measure',side_effect=audited_cpu), \
                 patch.object(c.base.GPU,'measure_diagnostic',new=audited_gpu):
                directory=c.run(args,gpus,validator=audited_validator)
            results=json.loads((directory/'results.json').read_text())
            raw,summary=results['raw'],results['summary']
            assert len(raw)==rows and len(summary)==rows//2
            for pair in {r['pair_id'] for r in raw}:
                paired=[r for r in raw if r['pair_id']==pair]
                assert len(paired)==8 and len({r['pair_sha256'] for r in paired})==1
                assert sorted(r['job_order'] for r in paired)==list(range(8))
                assert {r['backend'] for r in paired}=={'cpu_software','cpu_aesni',*c.BACKENDS.values()}
            for row in raw:
                if row['backend'].startswith('cpu'):
                    assert row['wall_elapsed_ns']>0 and row['process_cpu_ns']>=0
                    assert row['seconds']==row['wall_elapsed_ns']/1e9
                    assert math.isclose(row['throughput_MB_s'],row['bytes']/1e6/row['seconds'])
                else:
                    assert row['host_memory']=='pinned' and row['kernel_ns']>0
                    assert math.isclose(row['kernel_throughput_MB_s'],row['bytes']/1e6/row['kernel_seconds'])
                    if row['measurement']=='resident':
                        assert row['end_to_end_ns'] is None
                        assert row['resident_batch_ns']/iterations==row['kernel_ns']
                    else:
                        assert math.isclose(row['end_to_end_throughput_MB_s'],row['bytes']/1e6/row['end_to_end_seconds'])
            for row in summary:
                group=[r for r in raw if all(r[k]==row[k] for k in ('backend','mode','bytes','measurement'))]
                for metric in c.METRICS:
                    expected=c.base.extended_stats([r[metric] for r in group if r[metric] is not None])
                    assert all(row[metric+'_'+k]==v for k,v in expected.items())
                if row['backend'].startswith('cuda'):
                    scope='isolated' if row['measurement']=='resident' else 'pipeline'
                    denom=row['kernel_seconds_median'] if scope=='isolated' else row['end_to_end_seconds_median']
                    for cpu in ('cpu_aesni','cpu_software'):
                        numerator=next(r['seconds_median'] for r in summary if r['backend']==cpu and
                                       (r['mode'],r['bytes'])==(row['mode'],row['bytes']))
                        assert row['speedup_'+scope+'_vs_'+cpu]==numerator/denom
            meta=json.loads((directory/'metadata.json').read_text())
            assert set(meta['kernel_sha256'])==set(c.PROFILES)
            assert meta['kernel_sha256']['ttable']==c.base.digest(c.TTABLE)
            assert meta['validation_sha256']==c.base.digest(directory/'validation.json')
            for name,sha in meta['source_sha256'].items(): assert sha==c.base.digest(directory/'source'/name)
            for name,n in [('raw.csv',rows),('summary.csv',rows//2)]:
                with (directory/name).open() as h: assert len(list(csv.DictReader(h)))==n
        assert c.base.digest(c.base.KERNEL)==baseline_hash
        assert c.base.digest(c.OPTIMIZED)==v1_hash
    print('PASS: plan/CLI, fail-closed validation, pairing, timers, statistics/speedups, snapshots, baseline unchanged')
    print('PASS: tiny smoke only; no pilot/study')


if __name__=='__main__': main()
