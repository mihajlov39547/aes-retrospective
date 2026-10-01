"""Small isolated avalanche checks; no pilot/study workload."""
import csv
import hashlib
import json
import math
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import avalanche_test as demo


def main():
    with tempfile.TemporaryDirectory(prefix='avalanche-smoke-') as temporary:
        root=Path(temporary)
        command=[sys.executable,str(Path(demo.__file__))]
        result=subprocess.run(command+['--output',str(root)],capture_output=True,text=True)
        assert result.returncode==0 and json.loads(result.stdout)['status']=='plan_only' and not list(root.iterdir())
        for options in (['--samples-per-group','0'],['--samples-per-group','21'],['--profile','pilot','--samples-per-group','501'],['--purpose','study'],['--algorithms','DES','DES'],['--variants','key','key']):
            assert subprocess.run(command+options,capture_output=True).returncode!=0
        validation=demo.validate();assert validation['passed'],validation
        with patch.object(demo,'distance',return_value=999):
            assert not demo.validate()['passed']
        args=demo.arguments(['--run','--samples-per-group','8','--output',str(root)])
        with patch.object(demo,'collect',side_effect=AssertionError('Sampling after failed gate')):
            try:
                demo.run(args,validator=lambda:dict(passed=False))
            except RuntimeError:
                pass
            else:
                raise AssertionError('Failed gate accepted')
        assert not list(root.rglob('raw.csv')) and not list(root.rglob('summary.csv'))
        def valid_gate():
            return validation
        real_collect=demo.collect
        def guarded_collect(a):
            assert any(json.loads(p.read_text())['passed'] for p in root.glob('avalanche-validation-*/validation.json'))
            return real_collect(a)
        with patch.object(demo,'collect',side_effect=guarded_collect):
            directory=demo.run(args,validator=valid_gate)
        def read(name):
            with (directory/name).open(newline='') as f:return list(csv.DictReader(f))
        raw=read('raw.csv');summary=read('summary.csv')
        assert len(raw)==80 and len(summary)==10
        for row in summary:
            selected=[r for r in raw if (r['algorithm'],r['variant'])==(row['algorithm'],row['variant'])]
            values=[int(r['hamming_distance_bits']) for r in selected]
            normalized=[float(r['normalized_distance']) for r in selected]
            for name,expected in [('count',8),('mean',statistics.mean(values)),('median',statistics.median(values)),('stdev',statistics.stdev(values)),('min',min(values)),('max',max(values)),('mean_normalized',statistics.mean(normalized)),('median_normalized',statistics.median(normalized)),('stdev_normalized',statistics.stdev(normalized))]:
                assert math.isclose(float(row[name]),expected)
            percentiles=statistics.quantiles(values,n=100,method='inclusive')
            for q in (5,25,75,95):assert math.isclose(float(row['q'+str(q).zfill(2)]),percentiles[q-1])
        meta=json.loads((directory/'metadata.json').read_text())
        assert meta['validation_passed']
        assert meta['validation_sha256']==hashlib.sha256((directory/'validation.json').read_bytes()).hexdigest()
        for name,digest in meta['source_sha256'].items():assert hashlib.sha256((directory/'source'/name).read_bytes()).hexdigest()==digest
        assert (directory/'report.md').exists()
        # Force initial rejection and a changed key collapsing K1 into K2.
        k1=bytes.fromhex('0123456789abcdef');k2=demo.flip(k1,1);k3=bytes.fromhex('456789abcdef0123')
        key=demo.parity(k1+k2+k3)
        audit=demo.new_audit();rng=Mock();rng.randbytes.side_effect=[bytes(24),key]
        assert demo.new_key('TDEA',rng,audit,0)==key
        rng.choice.side_effect=[1,2]
        changed,bit=demo.changed_key('TDEA',key,rng,audit,0)
        assert bit==2 and demo.distance(demo.effective(key),demo.effective(changed))==1
        assert audit['generated']==4 and audit['rejected']==2 and audit['accepted']==2
        assert [r['stage'] for r in audit['rejections']]==['initial','key_flip']
        # Force rejection during actual exported collection and inspect persisted audit.
        original=demo.new_key
        def injected(name,rng,audit,sample):
            if name=='TDEA':demo.audit_record(audit,'initial',bytes(24),sample)
            return original(name,rng,audit,sample)
        with patch.object(demo,'new_key',side_effect=injected):
            rejected_dir=demo.run(demo.arguments(['--algorithms','TDEA','--samples-per-group','5','--output',str(root)]),validator=valid_gate)
        audit=json.loads((rejected_dir/'metadata.json').read_text())['method']['tdea_candidates']
        assert audit['rejected']==5 and len(audit['rejections'])==5
        print(f'PASS: {len(validation["tests"])} validation checks; 80 rows / 10 groups; CLI, gate failure/order, distribution statistics, source hashes and injected TDEA rejection export.')


if __name__=='__main__':main()
