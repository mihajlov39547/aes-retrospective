"""GPU-free synthetic regression tests for independent scientific estimators."""
import copy
import csv
import json
import sys
import tempfile
import tarfile
import io
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from analysis import core as c
from analysis.cross_platform import aggregate_derived


def raw_fixture(seed=2003,repeats=4):
    rows=[]
    for mode in ('ECB','CTR'):
        for repeat in range(repeats):
            jobs=[('cpu_software','transform'),('cpu_aesni','transform'),('cuda_baseline','resident'),('cuda_baseline','pipeline'),('cuda_optimized_v1','resident'),('cuda_optimized_v1','pipeline')]
            for order,(backend,scope) in enumerate(jobs):
                cpu=backend.startswith('cpu');ns=(repeat+1)*1000
                row=dict(session_id='fixture-'+str(seed),seed=seed,algorithm='AES-128',operation='encrypt',
                         backend=backend,profile={'cpu_software':'software','cpu_aesni':'aesni','cuda_baseline':'baseline','cuda_optimized_v1':'optimized'}[backend],
                         measurement=scope,host_memory='bytes' if cpu else 'pinned',mode=mode,bytes=1024,
                         repeat=repeat,pair_id=f'1024:{mode}:{repeat}',pair_sha256='same-input',job_order=order,
                         global_order=len(rows),validation_checked=True,resident_iterations=1 if scope=='resident' else None,
                         **dict.fromkeys(c.METRICS))
                if cpu:row.update(wall_elapsed_ns=ns,seconds=ns/1e9,throughput_MB_s=1024*1e3/ns,process_cpu_ns=0,process_to_wall_ratio=0)
                else:
                    row.update(kernel_ns=ns,kernel_seconds=ns/1e9,kernel_throughput_MB_s=1024*1e3/ns)
                    if scope=='resident':row['resident_batch_ns']=ns
                    else:row.update(h2d_ns=ns,d2h_ns=ns,transfer_ns=2*ns,end_to_end_ns=4*ns,end_to_end_seconds=4*ns/1e9,end_to_end_throughput_MB_s=1024*1e3/(4*ns))
                rows.append(row)
    return rows


class IndependentAnalysisTests(unittest.TestCase):
    def compute(self,raw=None):return c.recompute(raw if raw is not None else raw_fixture(),2003,[1024],4)

    def test_csv_is_primary_and_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'raw.csv';c.csvwrite(path,raw_fixture());before=c.sha(path)
            rows,reps=self.compute(c.csvread(path))
            self.assertEqual(len(rows),12);self.assertTrue(reps);self.assertEqual(c.sha(path),before)

    def test_independent_extended_statistics(self):
        s=c.stats([1,2,3,4]);self.assertEqual(s['median'],2.5)
        self.assertEqual(s['q1'],1.75);self.assertEqual(s['q3'],3.25);self.assertEqual(s['iqr'],1.5)
        self.assertAlmostEqual(s['stdev'],(5/3)**.5)
        self.assertIsNone(c.stats([0,0])['coefficient_of_variation'])

    def test_throughput_median_not_reciprocal_latency(self):
        rows,_=self.compute();row=rows[0]
        self.assertNotEqual(row['throughput_MB_s_median'],1024/1e6/row['seconds_median'])

    def test_duplicate_repeat_rejected(self):
        raw=raw_fixture();raw[6]['repeat']=0;raw[6]['pair_id']='1024:ECB:0'
        with self.assertRaises(ValueError):self.compute(raw)

    def test_missing_observation_rejected(self):
        with self.assertRaises(ValueError):self.compute(raw_fixture()[:-1])

    def test_wrong_formula_rejected(self):
        raw=raw_fixture();raw[0]['throughput_MB_s']*=1.1
        with self.assertRaisesRegex(ValueError,'formula'):self.compute(raw)

    def test_incompatible_scope_rejected(self):
        raw=raw_fixture();raw[2]['h2d_ns']=100
        with self.assertRaisesRegex(ValueError,'scope'):self.compute(raw)

    def test_unvalidated_observation_rejected(self):
        raw=raw_fixture();raw[0]['validation_checked']=False
        with self.assertRaises(ValueError):self.compute(raw)

    def test_pair_identity_rejected(self):
        raw=raw_fixture();raw[1]['pair_sha256']='other-input'
        with self.assertRaisesRegex(ValueError,'identity'):self.compute(raw)

    def test_nonfinite_rejected(self):
        raw=raw_fixture();raw[0]['seconds']=float('nan')
        with self.assertRaises(ValueError):self.compute(raw)

    def test_five_session_ratio_estimator(self):
        sessions={};cpu=[1,100,101,102,103];gpu=[1,2,100,1,100]
        for i,seed in enumerate(c.SEEDS):
            rows,_=c.recompute(raw_fixture(seed),seed,[1024],4)
            for row in rows:
                if row['backend']=='cuda_baseline' and row['measurement']=='resident':
                    row['speedup_isolated_vs_cpu_aesni']=cpu[i]/gpu[i]
            sessions[seed]=rows
        out=c.session_aggregate(sessions)
        row=next(r for r in out if r['backend']=='cuda_baseline' and r['measurement']=='resident' and r['metric']=='speedup_isolated_vs_cpu_aesni')
        self.assertEqual(row['median_of_sessions'],1.03)
        self.assertNotEqual(row['median_of_sessions'],101/2)

    def test_missing_seed_rejected(self):
        rows,_=self.compute()
        with self.assertRaises(ValueError):c.session_aggregate({2003:rows})

    def test_missing_metric_session_rejected(self):
        sessions={s:copy.deepcopy(self.compute()[0]) for s in c.SEEDS}
        sessions[2004][0]['seconds_median']=None
        with self.assertRaises(ValueError):c.session_aggregate(sessions)

    def test_tolerance_and_discrepancy(self):
        diffs=[]
        c.compare_rows([dict(key='a',value=1+1e-12)],[dict(key='a',value=1.)],['key'],'fixture',diffs)
        self.assertEqual(diffs,[])
        c.compare_rows([dict(key='a',value=2.)],[dict(key='a',value=1.)],['key'],'fixture',diffs)
        self.assertEqual(len(diffs),1)

    def test_duplicate_saved_record_rejected(self):
        with self.assertRaises(ValueError):c.compare_rows([dict(key=1),dict(key=1)],[dict(key=1)],['key'],'fixture',[])

    def test_archive_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'bad.zip'
            with zipfile.ZipFile(p,'w') as z:z.writestr('../outside','data')
            with self.assertRaisesRegex(ValueError,'Unsafe'):c.extract_archive(p,Path(tmp)/'extract')
            self.assertFalse((Path(tmp)/'outside').exists())

    def test_archive_input_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'good.zip'
            with zipfile.ZipFile(p,'w') as z:z.writestr('run/raw.csv','hello')
            before=c.sha(p);c.extract_archive(p,Path(tmp)/'extract')
            self.assertEqual(c.sha(p),before);self.assertEqual((Path(tmp)/'extract/run/raw.csv').read_text(),'hello')

    def test_tar_long_names_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'long.tar.gz';name='run-'+('x'*75)+'/experiments/cuda_paired/seed-2003/native/raw.csv'
            with tarfile.open(p,'w:gz',format=tarfile.PAX_FORMAT) as t:
                item=tarfile.TarInfo(name);item.size=5;t.addfile(item,io.BytesIO(b'hello'))
            c.extract_archive(p,Path(tmp)/'extract')
            self.assertEqual((Path(tmp)/'extract'/name).read_bytes(),b'hello')

    def test_archive_case_collision_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'collision.zip'
            with zipfile.ZipFile(p,'w') as z:
                z.writestr('run/raw.csv','a');z.writestr('run/RAW.csv','b')
            with self.assertRaisesRegex(ValueError,'Duplicate'):c.extract_archive(p,Path(tmp)/'extract')

    def test_pax_names_sharing_legacy_100_byte_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'pax.tar.gz';prefix='run/'+('x'*95)+'/'
            names=[prefix+'raw.csv',prefix+'results.json']
            self.assertEqual(names[0][:100],names[1][:100])
            with tarfile.open(p,'w:gz',format=tarfile.PAX_FORMAT) as t:
                for name,data in zip(names,[b'csv data',b'json data']):
                    item=tarfile.TarInfo(name);item.size=len(data);t.addfile(item,io.BytesIO(data))
            before=c.sha(p);receipt=c.extract_archive(p,Path(tmp)/'extract')
            self.assertEqual(receipt['regular_files'],2);self.assertEqual(receipt['pax_path_records'],2)
            for name,data in zip(names,[b'csv data',b'json data']):
                dest=Path(tmp)/'extract'/name
                self.assertEqual(dest.read_bytes(),data)
                self.assertEqual(c.sha(dest),receipt['files'][name]['sha256'])
            self.assertEqual(c.sha(p),before)

    def test_archive_refuses_existing_member(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'input.zip';target=Path(tmp)/'extract';target.mkdir()
            (target/'raw.csv').write_text('existing')
            with zipfile.ZipFile(p,'w') as z:z.writestr('raw.csv','new')
            with self.assertRaises(FileExistsError):c.extract_archive(p,target)
            self.assertEqual((target/'raw.csv').read_text(),'existing')

    def test_archive_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'link.tar'
            with tarfile.open(p,'w') as t:
                item=tarfile.TarInfo('link');item.type=tarfile.SYMTYPE;item.linkname='../outside';t.addfile(item)
            with self.assertRaisesRegex(ValueError,'Nonregular'):c.extract_archive(p,Path(tmp)/'extract')

    def test_platforms_never_pooled(self):
        rows=[dict(platform=p,run_id=p,backend='cpu_aesni',measurement='transform',mode='ECB',bytes=1024,
                   metric='contrast',seed=s,value=value) for p,value in [('a',1),('b',10)] for s in c.SEEDS]
        result=aggregate_derived(rows);self.assertEqual([r['median'] for r in result],[1,10])


if __name__=='__main__':unittest.main()
