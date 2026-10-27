import copy
import ctypes as ct
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from protocol import *
from aggregate import summarize, campaign, load


def synthetic(seed=2003):
    rows=[]
    for j in schedule(seed,1,2):
        r=dict(j,seed=seed,session_id=str(seed),validated=True,pair_hash=j['pair_id'],
               plaintext_sha256=str((j['pages'],j['repeat'])))
        r.update(cpu_transform_ns=100,cpu_operation_ns=400,kernel_ns=50,end_to_end_ns=200,transfer_ns=100)
        rows.append(r)
    return rows


class ProtocolTests(unittest.TestCase):
    def test_unique_nonces(self):
        seen=set()
        for s in SEEDS:
            for p in BATCHES:
                for r in range(-5,20):
                    for l in LAYOUTS:
                        for iv in counters(s,p,r,l):
                            self.assertNotIn(iv[:12],seen); seen.add(iv[:12])
                            self.assertEqual(iv[12:],b'\0\0\0\1')
        self.assertEqual(len(seen),7125)

    def test_inputs_control(self):
        a=material(2003,1,0,'pages'); b=material(2003,1,0,'continuous')
        self.assertEqual(a[:2],b[:2]); self.assertNotEqual(a[2],b[2])

    def test_rejections(self):
        key=bytes(16); iv=bytes(12)+b'\xff'*4
        check(bytes(16),key,[iv],16)
        for data,ivs,size in [(bytes(17),[iv],17),(bytes(32),[iv,iv],16),(bytes(16),[bytes(16)],16)]:
            with self.assertRaises(ValueError): check(data,key,ivs,size)

    def test_schedule(self):
        a=schedule(2003,5,20)
        self.assertEqual(len(a),600); self.assertEqual(sum(j['warmup'] for j in a),120)
        self.assertEqual(a,schedule(2003,5,20)); self.assertNotEqual(a,schedule(2004,5,20))


class AggregationTests(unittest.TestCase):
    def test_boundaries_and_negative_outcomes(self):
        s=summarize(synthetic())
        self.assertEqual(len(s['boundaries']),40)
        r=next(r for r in s['speedups'] if r['comparison'].startswith('prepared'))
        self.assertEqual(r['paired_ratios']['median'],0.5)
        b=next(b for b in s['boundaries'] if b['pages']==1 and b['boundary']=='cpu_transform_ns')
        self.assertEqual(b['throughput_MB_s']['median'],(1<<20)*10)
        self.assertEqual(b['latency_ns']['n'],2)
        self.assertTrue(all(c['paired_ratios']['median']==1 for c in s['page_over_continuous_throughput']))

    def test_pair_failures(self):
        for mutation in ('missing','duplicate','hash','session','control','invalid'):
            rows=synthetic()
            if mutation=='missing': rows.pop()
            if mutation=='duplicate': rows.append(rows[0])
            if mutation=='hash': rows[0]['pair_hash']='wrong'
            if mutation=='session': rows[0]['session_id']='other'
            if mutation=='control':
                for r in rows:
                    if r['layout']=='continuous': r['plaintext_sha256']='different'
            if mutation=='invalid': rows[0]['validated']=False
            with self.subTest(mutation=mutation),self.assertRaises(ValueError): summarize(rows)

    def test_estimators_outlier_preservation(self):
        rows=synthetic()
        for r in rows:
            if r['repeat']==1: r.update(cpu_transform_ns=10000,end_to_end_ns=1000)
        s=summarize(rows)
        r=next(r for r in s['speedups'] if r['comparison'].startswith('prepared'))
        self.assertEqual(r['paired_ratios']['median'],5.25)
        self.assertAlmostEqual(r['ratio_of_medians'],5050/600)

    def test_campaign_rejects_runtime_mixing(self):
        sessions=[(dict(seed=s,session_id=str(s),fingerprint='same',profile='study',warmups=5,repeats=20),
                   summarize(synthetic(s))) for s in SEEDS]
        with patch('aggregate.load',side_effect=sessions):
            result=campaign([Path(str(s)) for s in SEEDS])
            self.assertEqual(result['speedups'][0]['session_distribution']['n'],5)
        sessions[0][0]['fingerprint']='different'
        with patch('aggregate.load',side_effect=sessions),self.assertRaises(ValueError):
            campaign([Path(str(s)) for s in SEEDS])

    def test_load_order_and_completeness(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            rows=synthetic()
            (path/'metadata.json').write_text(json.dumps(dict(status='complete',seed=2003,
                session_id='2003',warmups=1,repeats=2)))
            def save():
                (path/'raw.jsonl').write_text('\n'.join(json.dumps(r) for r in rows))
            save(); load(path)
            rows.pop(); save()
            with self.assertRaises(ValueError): load(path)

    def test_corruption_rejected(self):
        from validation import require_equal
        with self.assertRaises(RuntimeError): require_equal(b'a',b'b')


class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from engines import CPU
        cls.cpu=CPU()

    def test_vectors(self):
        from validation import validate
        report=validate(self.cpu)
        self.assertTrue(report['passed']); self.assertEqual(len(report['cases']),25)

    def test_envelope(self):
        from time import perf_counter_ns
        args=material(2003,1,0,'pages')
        start=perf_counter_ns(); out,m=self.cpu.measure(*args); elapsed=perf_counter_ns()-start
        self.assertGreaterEqual(elapsed,sum(m[k] for k in ('allocation_ns','binding_ns','native_call_ns','output_copy_ns')))
        self.assertGreaterEqual(m['native_call_ns'],m['cpu_transform_ns'])

    def test_c_guard_bypasses_python(self):
        iv=bytes(12)+b'\xff'*4
        for ivs,length,pages in [(iv,17,1),(iv+iv,16,2),(bytes(16),16,1)]:
            out=(ct.c_ubyte*64)(); times=(ct.c_uint64*3)()
            self.assertEqual(self.cpu.call(bytes(16),ivs,bytes(64),out,length,pages,times),0)

    def test_original_aes_source(self):
        from engines import cuda_source,legacy
        self.assertTrue(cuda_source().startswith(legacy.KERNEL.read_text(encoding='utf-8')+'\n'))


if __name__=='__main__': unittest.main()
