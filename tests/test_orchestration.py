"""Orchestration tests: temporary synthetic artifacts, no CUDA or expensive AES."""
import copy
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from orchestration import artifacts as a, runner as r
from orchestration.registry import REGISTRY, command
from orchestration.configuration import ROOT, resolve, load, safe_output
from orchestration.platform import fingerprint, child_environment
from orchestration.aggregation import summarize_sessions, aggregate


def configuration(**updates):
    value=dict(schema_version=1,experiments={'avalanche':{'options':{'algorithms':['AES-128'],'samples_per_group':2}}})
    value.update(updates)
    return resolve(value)


def environment():
    value=dict(os='Test',packages=dict(pycryptodome='test',psutil='test',matplotlib='test'),cpu_features={'aesni':True,'vaes':None},available_ram_bytes=2**34,gpus=[],cuda={'available':False},git={})
    value['fingerprint']=fingerprint(value)
    return value


def fixture(folder, options=None, passed=True):
    options=options or configuration()['experiments']['avalanche']['options']
    folder.mkdir(parents=True); (folder/'source').mkdir()
    (folder/'source/avalanche_test.py').write_text('# synthetic fixture\n')
    report=dict(passed=passed,tests=[dict(test='fixture',passed=passed)],session_id='fixture-session',purpose='smoke')
    r.write(folder/'validation.json',report)
    raw=[dict(algorithm='AES-128',variant=v+'_bit_flip',sample_id=i,hamming_distance_bits=60+i,seed=2003) for v in options['variants'] for i in range(2)]
    summary=[dict(algorithm='AES-128',variant=v+'_bit_flip',median=60.5,count=2) for v in options['variants']]
    r.write(folder/'metadata.json',dict(experiment='avalanche',seed=2003,purpose='smoke',arguments=options,session_id='fixture-session',validation_sha256=a.digest(folder/'validation.json')))
    r.write(folder/'results.json',dict(raw=raw,summary=summary))
    (folder/'report.md').write_text('Synthetic test only')
    for name,rows in [('raw',raw),('summary',summary)]:
        with (folder/(name+'.csv')).open('w',newline='') as stream:
            w=csv.DictWriter(stream,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    return folder


class ConfigurationTests(unittest.TestCase):
    def test_registry(self):
        self.assertEqual(sum(v['status']=='active' for v in REGISTRY.values()),7)
        self.assertEqual(REGISTRY['legacy_gpu_scaffold']['status'],'disabled')
        for v in REGISTRY.values(): self.assertTrue((ROOT/v['script']).exists())

    def test_all_examples(self):
        for path in (ROOT/'experiments/configs').glob('*.json'): load(path)

    def test_reject_invalid(self):
        for change in ({'schema_version':2},{'seeds':[1,1]},{'execution_profile':'bad'},{'typo':True},{'platform_alias':'../bad'},{'fail_fast':'false'}):
            with self.subTest(change=change),self.assertRaises(ValueError): configuration(**change)

    def test_unsupported_options(self):
        with self.assertRaises(ValueError): configuration(experiments={'avalanche':{'options':{'repeats':2}}})
        with self.assertRaises(ValueError): configuration(experiments={'legacy_gpu_scaffold':{}})

    def test_keyspace_requires_explicit_budget(self):
        with self.assertRaises(ValueError): configuration(execution_profile='study',experiments={'keyspace':{}})
        with self.assertRaises(ValueError): configuration(experiments={'keyspace':{'options':{'reduced_key_bits':20}}})
        c=configuration(repeats=20,experiments={'keyspace':{}})
        self.assertEqual(c['experiments']['keyspace']['options']['repeats'],3)

    def test_seed_order_and_overrides(self):
        c=configuration(seeds=[2003,2004],experiments={'cpu_cbc':{},'avalanche':{'seeds':[9]}})
        self.assertEqual([(n,s) for n,s,_ in r.tasks(c)],[('cpu_cbc',2003),('cpu_cbc',2004),('avalanche',9)])

    def test_argument_translation_all_active(self):
        # Each real script parses the translated command in plan-only mode.
        with tempfile.TemporaryDirectory() as tmp:
            for name,spec in REGISTRY.items():
                if spec['status']!='active': continue
                c=configuration(experiments={name:{}}); options=c['experiments'][name]['options']
                argv=command(name,options,2003,'smoke',Path(tmp)/name,ROOT,run=False)
                p=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,timeout=20)
                self.assertEqual(p.returncode,0,p.stderr)
                plan=json.loads(p.stdout); self.assertEqual(plan['status'],'plan_only')
                self.assertEqual(plan['arguments']['seed'],2003)
                self.assertFalse((Path(tmp)/name).exists())
                if name=='cuda_paired': self.assertEqual(plan['arguments']['profile'],['baseline','optimized'])

    def test_protect_history(self):
        for path in (ROOT,ROOT/'experiments',ROOT/'experiments/results',ROOT/'experiments/results/new'):
            with self.assertRaises(ValueError): safe_output(path)
        self.assertEqual(safe_output(ROOT/'build/test'),ROOT/'build/test')

    def test_gpu_selection(self):
        env=child_environment({'cuda_device':'GPU-example'})
        self.assertEqual(env['CUDA_VISIBLE_DEVICES'],'GPU-example')

    def test_fingerprint_stable(self):
        env=environment(); before=fingerprint(env)
        env.update(available_ram_bytes=1,created_utc='later',git={'commit':'different'})
        self.assertEqual(before,fingerprint(env))
        env['packages']['pycryptodome']='changed'
        self.assertNotEqual(before,fingerprint(env))

    def test_list_types_and_caps(self):
        for options in ({'profile':'baseline'},{'sizes':[0]},{'sizes':[67108864]},{'resident_iterations':0}):
            with self.subTest(options=options),self.assertRaises(ValueError): configuration(experiments={'cuda_paired':{'options':options}})

    def test_preflight_cpu_and_gpu(self):
        c=configuration(); env=environment()
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(r.preflight('avalanche',{},c,env,tmp)['passed'])
            failed=r.preflight('cuda_baseline',{'sizes':[1024]},c,env,tmp)
            self.assertFalse(failed['passed']); self.assertFalse(failed['skip'])
            c['gpu_unavailable']='skip'
            self.assertTrue(r.preflight('cuda_baseline',{'sizes':[1024]},c,env,tmp)['skip'])
            env['cpu_features']['aesni']=False
            self.assertFalse(r.preflight('cpu_gcm',{},c,env,tmp)['passed'])


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.folder=fixture(self.root/'stage/result')
        self.options=configuration()['experiments']['avalanche']['options']

    def verify(self): return a.verify_native(self.folder,'avalanche',self.options,2003,'smoke')

    def test_discovery_and_preservation(self):
        before=a.hashes(self.folder)
        self.assertEqual(a.discover(self.root/'stage'),self.folder)
        self.assertTrue(self.verify()['passed'])
        self.assertEqual(before,a.hashes(self.folder))

    def test_missing_artifact(self):
        (self.folder/'raw.csv').unlink()
        with self.assertRaises(ValueError): self.verify()

    def test_failed_validation(self):
        report=a.read(self.folder/'validation.json'); report['passed']=False
        r.write(self.folder/'validation.json',report)
        with self.assertRaisesRegex(ValueError,'Validation did not pass'): self.verify()

    def test_wrong_seed(self):
        with self.assertRaisesRegex(ValueError,'identity'): a.verify_native(self.folder,'avalanche',self.options,2004,'smoke')

    def test_csv_corruption(self):
        with (self.folder/'raw.csv').open('a') as f: f.write('bogus\n')
        with self.assertRaises(ValueError): self.verify()

    def test_duplicate_discovery(self):
        fixture(self.root/'stage/other')
        with self.assertRaises(ValueError): a.discover(self.root/'stage')

    def test_summary_corruption(self):
        data=a.read(self.folder/'results.json'); data['summary'][0]['median']=2
        r.write(self.folder/'results.json',data)
        with self.assertRaises(ValueError): self.verify()

    def test_nonzero_exit(self):
        attempt=self.root/'attempt'; attempt.mkdir()
        with self.assertRaisesRegex(ValueError,'exited 7'): r.process([sys.executable,'-c','import sys; print("diagnostic"); sys.exit(7)'],attempt,None,10)
        self.assertEqual(a.read(attempt/'execution.json')['exit_code'],7)
        self.assertIn('diagnostic',(attempt/'stdout.log').read_text())

    def test_timeout(self):
        attempt=self.root/'attempt'; attempt.mkdir()
        with self.assertRaises(subprocess.TimeoutExpired): r.process([sys.executable,'-c','import time; time.sleep(30)'],attempt,None,0.1)
        self.assertIn('TimeoutExpired',a.read(attempt/'execution.json')['error'])


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root=Path(self.temp.name)
        self.config=configuration(output_root=str(self.root/'runs')); self.env=environment()
        self.template=fixture(self.root/'template')
        self.script=self.root/'fake.py'
        self.script.write_text('''import json, shutil, sys
from pathlib import Path
stage=Path(sys.argv[1]); target=stage/'result'
shutil.copytree(sys.argv[2],target)
p=target/'metadata.json'; data=json.loads(p.read_text()); data['arguments']['output']=str(stage)
p.write_text(json.dumps(data))
''')
        self.directory=r.create(self.config,self.env)
        self.addCleanup(patch.stopall)
        patch('orchestration.runner.detect',return_value=self.env).start()
        patch('orchestration.runner.command',side_effect=lambda n,o,s,p,stage,root:[sys.executable,str(self.script),str(stage),str(self.template)]).start()

    def test_unique_output_names(self):
        other=r.create(self.config,self.env)
        self.assertNotEqual(other,self.directory)
        self.assertEqual(self.directory.parent.name,self.env['fingerprint'])

    def test_complete_resume_aggregate_preserves(self):
        self.assertTrue(r.execute(self.directory))
        folder=self.directory/'experiments/avalanche/seed-2003/native'; before=a.hashes(folder)
        self.assertTrue(r.execute(self.directory))
        task=a.read(self.directory/'status.json')['tasks']['avalanche/seed-2003']
        self.assertEqual(len(task['attempts']),1)
        self.assertTrue(r.verify_suite(self.directory)['passed'])
        first=aggregate(self.directory); second=aggregate(self.directory)
        self.assertNotEqual(first,second); self.assertEqual(before,a.hashes(folder))

    def test_fail_and_explicit_retry(self):
        with patch('orchestration.runner.command',return_value=[sys.executable,'-c','raise SystemExit(3)']): self.assertFalse(r.execute(self.directory))
        self.assertFalse(r.execute(self.directory))
        self.assertTrue(r.execute(self.directory,retry_failed=True))
        task=a.read(self.directory/'status.json')['tasks']['avalanche/seed-2003']
        self.assertEqual(len(task['attempts']),2)
        self.assertTrue((self.directory/task['attempts'][0]/'failure.json').exists())

    def test_interrupted_recovery(self):
        state=a.read(self.directory/'status.json'); state['tasks']['avalanche/seed-2003']['state']='RUNNING'
        r.write(self.directory/'status.json',state)
        self.assertTrue(r.execute(self.directory))

    def test_crash_after_promotion(self):
        self.assertTrue(r.execute(self.directory))
        state=a.read(self.directory/'status.json'); state['tasks']['avalanche/seed-2003']['state']='VERIFYING'
        r.write(self.directory/'status.json',state)
        self.assertTrue(r.execute(self.directory))
        self.assertEqual(len(a.read(self.directory/'status.json')['tasks']['avalanche/seed-2003']['attempts']),1)

    def test_config_tamper(self):
        c=a.read(self.directory/'config.resolved.json'); c['seeds']=[1]
        r.write(self.directory/'config.resolved.json',c)
        with self.assertRaisesRegex(ValueError,'configuration changed'): r.execute(self.directory)

    def test_source_change_resume(self):
        with patch('orchestration.runner.sources',return_value={}):
            with self.assertRaisesRegex(ValueError,'Source code changed'): r.execute(self.directory)

    def test_completed_tamper_not_overwritten(self):
        self.assertTrue(r.execute(self.directory))
        raw=self.directory/'experiments/avalanche/seed-2003/native/raw.csv'; raw.write_text('corrupt')
        with self.assertRaises(ValueError): r.execute(self.directory,retry_failed=True)
        self.assertEqual(raw.read_text(),'corrupt')

    def test_lock_exclusion(self):
        with r.lock(self.root/'lock'):
            with self.assertRaises(ValueError):
                with r.lock(self.root/'lock'): pass

    def test_zero_exit_without_artifacts_fails(self):
        with patch('orchestration.runner.command',return_value=[sys.executable,'-c','pass']): self.assertFalse(r.execute(self.directory))
        self.assertEqual(a.read(self.directory/'status.json')['tasks']['avalanche/seed-2003']['state'],'FAILED')
        self.assertFalse((self.directory/'experiments/avalanche/seed-2003').exists())

    def test_failed_validation_quarantined(self):
        report=a.read(self.template/'validation.json'); report['passed']=False
        r.write(self.template/'validation.json',report)
        self.assertFalse(r.execute(self.directory))
        self.assertFalse((self.directory/'experiments/avalanche/seed-2003').exists())
        self.assertTrue(list((self.directory/'failed-attempts').rglob('validation.json')))

    def test_environment_change_rejected(self):
        changed=copy.deepcopy(self.env); changed['fingerprint']='different'
        with patch('orchestration.runner.detect',return_value=changed):
            with self.assertRaisesRegex(ValueError,'fingerprint changed'): r.execute(self.directory)

    def test_gpu_skip_lifecycle(self):
        config=configuration(output_root=str(self.root/'gpu-runs'),gpu_unavailable='skip',experiments={'cuda_baseline':{}})
        directory=r.create(config,self.env)
        self.assertTrue(r.execute(directory))
        self.assertEqual(a.read(directory/'status.json')['state'],'COMPLETED_WITH_SKIPS')
        self.assertFalse(list((directory/'experiments').rglob('raw.csv')))

    def test_keyboard_interrupt_recorded(self):
        with patch('orchestration.runner.process',side_effect=KeyboardInterrupt): self.assertFalse(r.execute(self.directory))
        self.assertEqual(a.read(self.directory/'status.json')['state'],'INTERRUPTED')
        self.assertTrue(r.execute(self.directory))

    def test_history_import_is_read_only(self):
        from orchestration.history import index_history
        before=a.hashes(self.template)
        output=index_history(self.template,self.root/'index')
        record=a.read(output)['records'][0]
        self.assertIsNone(record['recorded_git_commit'])
        self.assertIsNone(record['recorded_platform']['gpu'])
        self.assertEqual(before,a.hashes(self.template))


class AggregationTests(unittest.TestCase):
    def test_paired_ratios_not_ratio_of_aggregates(self):
        # Session CPU/GPU medians: (1/1, 100/2, 101/100).
        # Median ratio=1.01, whereas ratio of medians=50.
        records=[]
        for seed,(cpu,gpu) in enumerate([(1,1),(100,2),(101,100)]):
            records.append(dict(experiment='cuda_paired',seed=seed,summary=dict(backend='cuda_baseline',measurement='resident',resident_iterations=1,mode='ECB',bytes=1024,kernel_seconds_median=gpu,speedup_isolated_vs_cpu_aesni=cpu/gpu)))
        rows,_=summarize_sessions(records)
        ratio=next(r for r in rows if r['metric'].startswith('speedup'))
        self.assertEqual(ratio['median_of_sessions'],1.01)
        self.assertEqual(ratio['sessions'],3)

    def test_scopes_not_pooled(self):
        records=[dict(experiment='cuda_paired',seed=2003,summary=dict(backend='cuda_baseline',measurement=m,resident_iterations=n,kernel_seconds_median=v)) for m,n,v in [('resident',1,1),('resident',10,2),('pipeline',None,3)]]
        rows,_=summarize_sessions(records)
        self.assertEqual(len(rows),3)

    def test_duplicate_session_rejected(self):
        record=dict(experiment='cpu_cbc',seed=1,summary=dict(seconds_median=1))
        with self.assertRaises(ValueError): summarize_sessions([record,record])


if __name__=='__main__': unittest.main()
