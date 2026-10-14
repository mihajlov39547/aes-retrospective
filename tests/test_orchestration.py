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
from orchestration.metrics import metric_policy


def configuration(**updates):
    value=dict(schema_version=1,experiments={'avalanche':{'options':{'algorithms':['AES-128'],'samples_per_group':2}}})
    value.update(updates)
    return resolve(value)


def environment():
    value=dict(os='Test',packages=dict(pycryptodome='test',psutil='test',matplotlib='test',numpy='test'),cpu_features={'aesni':True,'vaes':None},available_ram_bytes=2**34,gpus=[],cuda={'available':False},git={})
    value['fingerprint']=fingerprint(value)
    return value


def fixture(folder, options=None, passed=True, seed=2003, purpose='smoke'):
    options=options or configuration()['experiments']['avalanche']['options']
    folder.mkdir(parents=True); (folder/'source').mkdir()
    (folder/'source/avalanche_test.py').write_text('# synthetic fixture\n')
    report=dict(passed=passed,tests=[dict(test='fixture',passed=passed)],session_id='fixture-session-'+str(seed),purpose=purpose)
    r.write(folder/'validation.json',report)
    raw=[dict(algorithm='AES-128',variant=v+'_bit_flip',sample_id=i,hamming_distance_bits=60+i,normalized_distance=(60+i)/128,seed=seed) for v in options['variants'] for i in range(2)]
    summary=[dict(algorithm='AES-128',variant=v+'_bit_flip',median=60.5,median_normalized=60.5/128,count=2) for v in options['variants']]
    r.write(folder/'metadata.json',dict(experiment='avalanche',seed=seed,purpose=purpose,arguments=options,session_id=report['session_id'],validation_sha256=a.digest(folder/'validation.json')))
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

    def orphan_attempt(self, created):
        attempt=self.directory/'attempts/orphan'; attempt.mkdir()
        r.write(attempt/'command.json',dict(pid=12345,process_created=created))
        state=a.read(self.directory/'status.json')
        state['tasks']['avalanche/seed-2003'].update(state='RUNNING',attempts=['attempts/orphan'])
        r.write(self.directory/'status.json',state)
        return attempt

    def test_resume_original_pid_still_running(self):
        attempt=self.orphan_attempt(100.0)
        with patch('psutil.Process') as process, patch('orchestration.runner.process') as launch:
            process.return_value.create_time.return_value=100.0
            with self.assertRaisesRegex(ValueError,'still alive'): r.execute(self.directory)
            launch.assert_not_called()
        self.assertTrue(attempt.exists())
        self.assertEqual(len(a.read(self.directory/'status.json')['tasks']['avalanche/seed-2003']['attempts']),1)

    def test_resume_reused_pid_runs_once(self):
        attempt=self.orphan_attempt(100.0)
        with patch('psutil.Process') as process, patch('orchestration.runner.process',wraps=r.process) as launch:
            process.return_value.create_time.return_value=200.0
            self.assertTrue(r.execute(self.directory))
            self.assertTrue(r.execute(self.directory))
            self.assertEqual(launch.call_count,1)
            process.return_value.terminate.assert_not_called()
            process.return_value.kill.assert_not_called()
        self.assertFalse(attempt.exists())
        self.assertTrue((self.directory/'failed-attempts/orphan/command.json').exists())

    def test_resume_missing_creation_timestamp_blocks(self):
        self.orphan_attempt(None)
        with patch('psutil.Process'), patch('orchestration.runner.process') as launch:
            with self.assertRaisesRegex(ValueError,'still alive'): r.execute(self.directory)
            launch.assert_not_called()

    def test_resume_unreadable_creation_timestamp_blocks(self):
        import psutil
        self.orphan_attempt(100.0)
        with patch('psutil.Process') as process, patch('orchestration.runner.process') as launch:
            process.return_value.create_time.side_effect=psutil.AccessDenied(12345)
            with self.assertRaisesRegex(ValueError,'Cannot establish'): r.execute(self.directory)
            launch.assert_not_called()

    def test_resume_missing_timestamp_exited_pid_safe(self):
        import psutil
        self.orphan_attempt(None)
        original=psutil.Process
        with patch('psutil.Process',side_effect=lambda pid: (_ for _ in ()).throw(psutil.NoSuchProcess(pid)) if pid==12345 else original(pid)):
            self.assertTrue(r.execute(self.directory))

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


def study_records(names=('cuda_paired',)):
    config=configuration(execution_profile='study',seeds=list(range(2003,2008)),experiments={name:{} for name in names})
    records=[]
    for name,item in config['experiments'].items():
        fields,groups=a.expected_groups(name,item['options'])
        for seed in item['seeds']:
            for group in groups:
                row=dict(zip(fields,group))
                if name=='cuda_baseline': row.update(backend='cuda',profile='baseline',measurement='pipeline',host_memory='pinned',resident_iterations=None)
                required,optional=metric_policy(name,row)
                row.update({metric:float(seed-2000) for metric in required|set(optional)})
                records.append(dict(experiment=name,seed=seed,summary=row))
    return config,records


class ScientificAggregationTests(unittest.TestCase):
    def test_complete_five_sessions(self):
        config,records=study_records()
        rows,variability=summarize_sessions(records,config)
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(row['expected_sessions'],5)
            self.assertEqual(row['observed_sessions'],5)
            self.assertEqual(row['missing_seeds'],[])
            self.assertTrue(row['complete'])
            self.assertEqual(row['median_of_sessions'],5.0)
        self.assertTrue(all(v['session_stdev']>0 for v in variability))

    def test_missing_session(self):
        config,records=study_records()
        records=[r for r in records if r['seed']!=2005]
        with self.assertRaisesRegex(ValueError,'Missing configured session'): summarize_sessions(records,config)

    def test_missing_metric_group_one_session(self):
        config,records=study_records()
        records.pop(0)
        with self.assertRaisesRegex(ValueError,'Incomplete metric groups'): summarize_sessions(records,config)

    def test_missing_required_metric_one_session(self):
        config,records=study_records()
        del records[0]['summary']['seconds_median']
        with self.assertRaisesRegex(ValueError,'Missing required metric'): summarize_sessions(records,config)

    def test_required_metric_missing_everywhere(self):
        config,records=study_records(('cpu_cbc',))
        for row in records: row['summary'].pop('throughput_MB_s_median')
        with self.assertRaisesRegex(ValueError,'Missing required metric'): summarize_sessions(records,config)

    def test_duplicate_observation(self):
        config,records=study_records()
        records.append(copy.deepcopy(records[0]))
        with self.assertRaisesRegex(ValueError,'Duplicate summary observation'): summarize_sessions(records,config)

    def test_duplicate_configured_seed(self):
        config,records=study_records()
        config['experiments']['cuda_paired']['seeds'].append(2003)
        with self.assertRaisesRegex(ValueError,'duplicate configured seeds'): summarize_sessions(records,config)

    def test_unexpected_seed(self):
        config,records=study_records()
        records[0]['seed']=9999
        with self.assertRaisesRegex(ValueError,'Unexpected experiment or seed'): summarize_sessions(records,config)

    def test_optional_diagnostics_are_flagged(self):
        config,records=study_records(('cpu_cbc',))
        records[0]['summary'].pop('process_cpu_ns_median')
        rows,_=summarize_sessions(records,config)
        partial=[r for r in rows if not r['complete']]
        self.assertEqual(len(partial),1)
        row=partial[0]
        self.assertFalse(row['required']); self.assertTrue(row['optional_reason'])
        self.assertEqual(row['missing_seeds'],[2003]); self.assertEqual(row['observed_sessions'],4)
        self.assertEqual(row['median_of_sessions'],5.5)

    def test_optional_metric_absent_entirely_is_explicit(self):
        config,records=study_records(('cpu_gcm',))
        for record in records: record['summary'].pop('process_cpu_ns_median')
        rows,_=summarize_sessions(records,config)
        missing=[r for r in rows if r['metric']=='process_cpu_ns_median']
        self.assertTrue(missing)
        self.assertTrue(all(not r['complete'] and r['observed_sessions']==0 and r['median_of_sessions'] is None for r in missing))

    def test_partial_development_is_labelled(self):
        config,records=study_records()
        config['execution_profile']='smoke'
        rows,_=summarize_sessions([r for r in records if r['seed']!=2007],config)
        self.assertTrue(all(r['missing_seeds']==[2007] and not r['complete'] for r in rows))

    def test_standalone_and_paired_independent(self):
        config,records=study_records(('cuda_baseline','cuda_paired'))
        for record in records:
            if record['experiment']=='cuda_baseline': record['summary']['kernel_seconds_median']=1000
        rows,_=summarize_sessions(records,config)
        standalone=[r for r in rows if r['experiment']=='cuda_baseline' and r['metric']=='kernel_seconds_median']
        paired=[r for r in rows if r['experiment']=='cuda_paired' and r['metric']=='kernel_seconds_median']
        self.assertTrue(standalone and paired)
        self.assertTrue(all(r['median_of_sessions']==1000 for r in standalone))
        self.assertTrue(all(r['median_of_sessions']==5 for r in paired))

    def test_scientific_paired_estimator_unchanged(self):
        config,records=study_records()
        numerators=[1,100,101,102,103]; denominators=[1,2,100,1,100]
        for record in records:
            row=record['summary']; i=record['seed']-2003
            for field in list(row):
                if field.startswith('speedup_'): row[field]=numerators[i]/denominators[i]
        rows,_=summarize_sessions(records,config)
        ratios=[r for r in rows if r['metric'].startswith('speedup_')]
        self.assertTrue(all(r['median_of_sessions']==1.03 for r in ratios))
        self.assertNotEqual(1.03,101/2) # Ratio of aggregate timing medians would be 50.5.

    def test_scope_drift_rejected(self):
        config,records=study_records()
        records[0]['summary']['host_memory']='pageable'
        with self.assertRaisesRegex(ValueError,'Inconsistent session execution scopes'): summarize_sessions(records,config)


class ScientificSuiteTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.env=environment()

    def make_suite(self, profile='study', seeds=(2003,2004,2005,2006,2007), skipped_gpu=False):
        experiments={'avalanche':{'options':{'algorithms':['AES-128'],'samples_per_group':2}}}
        if skipped_gpu: experiments['cuda_baseline']={}
        config=configuration(output_root=str(self.root/'runs'),execution_profile=profile,seeds=list(seeds),experiments=experiments)
        directory=r.create(config,self.env); status=a.read(directory/'status.json')
        for seed in seeds:
            key='avalanche/seed-'+str(seed); folder=directory/'experiments'/key
            fixture(folder/'native',config['experiments']['avalanche']['options'],seed=seed,purpose=profile)
            r.write(folder/'orchestration.json',dict(artifact_hashes=a.hashes(folder/'native'),fingerprint=self.env['fingerprint']))
            status['tasks'][key]['state']='COMPLETED'
            if skipped_gpu: status['tasks']['cuda_baseline/seed-'+str(seed)]['state']='SKIPPED'
        status['state']='COMPLETED_WITH_SKIPS' if skipped_gpu else 'COMPLETED'
        r.write(directory/'status.json',status)
        return directory,config

    def test_complete_study_export(self):
        directory,_=self.make_suite()
        self.assertEqual(r.verify_suite(directory)['scientific_completeness'],'complete')
        before=a.hashes(directory/'experiments')
        output=aggregate(directory); report=a.read(output/'summary.json')
        self.assertEqual(report['schema_version'],2)
        self.assertTrue(report['publication_quality'])
        self.assertEqual(report['publication_quality_definition'],
                         'Dataset completeness and integrity only; not statistical or scientific publication readiness.')
        self.assertTrue(all(r['expected_sessions']==5 and r['complete'] for r in report['rows']))
        self.assertEqual(before,a.hashes(directory/'experiments'))

    def test_skipped_cuda_partial_study_refused(self):
        directory,_=self.make_suite(skipped_gpu=True)
        report=r.verify_suite(directory)
        self.assertTrue(report['passed']) # Backward-compatible technical status.
        self.assertEqual(report['scientific_completeness'],'partial')
        self.assertEqual(len(report['missing_measurements']),5)
        self.assertEqual(report['sessions']['cuda_baseline']['missing_seeds'],list(range(2003,2008)))
        with self.assertRaisesRegex(ValueError,'requires scientific_completeness=complete'): aggregate(directory)
        self.assertFalse(list((directory/'aggregates').iterdir()))

    def test_partial_smoke_export_explicit(self):
        directory,_=self.make_suite(profile='smoke',seeds=(2003,),skipped_gpu=True)
        output=aggregate(directory); report=a.read(output/'summary.json')
        self.assertEqual(report['scientific_completeness'],'partial')
        self.assertFalse(report['publication_quality'])
        self.assertEqual(report['missing_measurements'][0]['experiment'],'cuda_baseline')
        self.assertTrue(all(r['experiment']=='avalanche' for r in report['rows']))

    def test_pending_is_partial(self):
        directory,_=self.make_suite()
        status=a.read(directory/'status.json'); status['tasks']['avalanche/seed-2007']['state']='PENDING'
        r.write(directory/'status.json',status)
        report=r.verify_suite(directory)
        self.assertEqual(report['scientific_completeness'],'partial'); self.assertFalse(report['passed'])
        with self.assertRaises(ValueError): aggregate(directory)

    def test_corruption_is_invalid_and_resume_rejects(self):
        directory,_=self.make_suite()
        (directory/'experiments/avalanche/seed-2003/native/raw.csv').write_text('corruption')
        report=r.verify_suite(directory)
        self.assertEqual(report['scientific_completeness'],'invalid'); self.assertFalse(report['passed'])
        with self.assertRaises(ValueError): aggregate(directory)
        with self.assertRaises(ValueError): r.execute(directory)

    def test_failed_gate_is_invalid(self):
        directory,_=self.make_suite()
        status=a.read(directory/'status.json'); task=status['tasks']['avalanche/seed-2003']
        task['state']='FAILED'; task['attempts']=['failed-attempts/gate']
        r.write(directory/'failed-attempts/gate/staging/validation.json',{'passed':False})
        r.write(directory/'status.json',status)
        self.assertEqual(r.verify_suite(directory)['scientific_completeness'],'invalid')
        with self.assertRaises(ValueError): aggregate(directory)

    def test_corrupted_config_is_structured_invalid(self):
        directory,_=self.make_suite()
        (directory/'config.resolved.json').write_text('{}')
        self.assertEqual(r.verify_suite(directory)['scientific_completeness'],'invalid')

    def test_required_metric_missing_from_accepted_result(self):
        directory,_=self.make_suite(); folder=directory/'experiments/avalanche/seed-2003'
        data=a.read(folder/'native/results.json')
        for row in data['summary']: row.pop('median_normalized')
        r.write(folder/'native/results.json',data)
        with (folder/'native/summary.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(data['summary'][0])); writer.writeheader(); writer.writerows(data['summary'])
        side=a.read(folder/'orchestration.json'); side['artifact_hashes']=a.hashes(folder/'native')
        r.write(folder/'orchestration.json',side)
        report=r.verify_suite(directory)
        self.assertEqual(report['scientific_completeness'],'invalid')
        self.assertIn('Missing required metric',' '.join(report['errors']))

    def test_skipped_study_cli_verify_preserves_exit_code(self):
        directory,_=self.make_suite(skipped_gpu=True)
        process=subprocess.run([sys.executable,str(ROOT/'scripts/run_all_experiments.py'),'verify','--run-dir',str(directory)],capture_output=True,text=True)
        self.assertEqual(process.returncode,0)
        self.assertEqual(json.loads(process.stdout)['scientific_completeness'],'partial')


class DependencyTests(unittest.TestCase):
    def test_no_matplotlib_required_for_any_benchmark(self):
        config=configuration(); env=environment(); env['packages'].pop('matplotlib')
        env['cuda']=dict(available=True,vram_bytes=2**32)
        for name,spec in REGISTRY.items():
            if spec['status']!='active': continue
            self.assertNotIn('matplotlib',spec['required_packages'])
            self.assertTrue(r.preflight(name,{},config,env,ROOT)['passed'],name)

    def test_missing_mandatory_dependency_fails(self):
        env=environment(); env['packages'].pop('pycryptodome')
        self.assertFalse(r.preflight('avalanche',{},configuration(),env,ROOT)['passed'])
        env=environment(); env['package_imports']={'pycryptodome':False}
        self.assertFalse(r.preflight('avalanche',{},configuration(),env,ROOT)['passed'])

    def test_missing_optional_telemetry_does_not_fail(self):
        env=environment(); env['telemetry_errors']=['nvidia-smi unavailable']; env['cuda']=dict(available=True,vram_bytes=2**32)
        result=r.preflight('cuda_baseline',{},configuration(),env,ROOT)
        self.assertTrue(result['passed']); self.assertTrue(result['optional_telemetry_errors'])

    def test_common_metadata_without_matplotlib(self):
        # No cipher or timing execution. Proves native export no longer fails
        # merely because optional plotting distribution metadata is absent.
        try:
            import common, psutil
        except ImportError: self.skipTest('psutil unavailable; minimal integration checked separately')
        import argparse, importlib.metadata
        def version(name):
            if name=='matplotlib': raise importlib.metadata.PackageNotFoundError(name)
            return 'fixture'
        with patch('common.importlib.metadata.version',side_effect=version),patch('common.command_output',return_value=None):
            meta=common.metadata(argparse.Namespace(purpose='smoke',seed=2003),{})
        self.assertIsNone(meta['library_versions']['matplotlib'])


class HistoricalCompatibilityTests(unittest.TestCase):
    def test_saved_five_session_paired_study_exact_values(self):
        path=ROOT/'experiments/results/aes_cuda_cpu_gpu-final-aggregate/aggregate.json'
        if not path.exists(): self.skipTest('Archived final study is not available in this checkout')
        old=a.read(path); records=[]; seeds=[]; options=None
        for session in old['selected_sessions']:
            native=path.parent.parent/session['run_id']
            if not (native/'results.json').exists(): self.skipTest('Archived native data is not available')
            meta=a.read(native/'metadata.json'); options=meta['arguments']; seeds.append(meta['seed'])
            for row in a.read(native/'results.json')['summary']:
                records.append(dict(experiment='cuda_paired',seed=meta['seed'],summary=row))
        config=dict(execution_profile='study',experiments={'cuda_paired':dict(seeds=seeds,options=options)})
        rows,_=summarize_sessions(records,config)
        lookup={(row['backend'],row['mode'],row['bytes'],row['measurement'],row['metric']):row['median_of_sessions'] for row in rows}
        for row in old['rows']:
            backend=row['backend']; scope=row['measurement']; prefix=(backend,row['mode'],row['bytes'],scope)
            timing='seconds' if backend.startswith('cpu') else 'kernel_seconds' if scope=='resident' else 'end_to_end_seconds'
            throughput='throughput_MB_s' if backend.startswith('cpu') else 'kernel_throughput_MB_s' if scope=='resident' else 'end_to_end_throughput_MB_s'
            self.assertEqual(lookup[(*prefix,timing+'_median')]*1000,row['time_ms'])
            self.assertEqual(lookup[(*prefix,throughput+'_median')],row['throughput_MB_s'])
            if backend.startswith('cuda'):
                for cpu in ('cpu_aesni','cpu_software'):
                    metric='speedup_'+('isolated' if scope=='resident' else 'pipeline')+'_vs_'+cpu
                    self.assertEqual(lookup[(*prefix,metric)],row['speedup_vs_'+cpu])


if __name__=='__main__': unittest.main()
