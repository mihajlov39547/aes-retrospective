"""Read-only, independently recomputed paired AES study analysis CLI."""
import argparse
import json
import platform
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from analysis.core import (SEEDS,SIZES,DIMS,ACTIVE_SOURCES,read,sha,inventory,csvread,csvwrite,
                           require,recompute,session_aggregate,compare_rows,stats,extract_archive,group,RTOL,ATOL)
from orchestration.runner import verify_suite

HINTS={'gtx1650ti':'1472bd2f13cf','t600':'636c48c0ebaf','t4':'9bb918a84386'}
LABELS={'gtx1650ti':'Windows 10 (user label); GTX 1650 Ti',
        't600':'Windows 11 (user label); T600 Laptop','t4':'Google Colab (user label); Tesla T4'}


def dump(path, value):
    Path(path).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')


def discover(roots):
    result=[]
    for root in roots:
        for p in sorted(Path(root).rglob('config.resolved.json')):
            try:
                c=read(p);e=read(p.parent/'environment.json');s=read(p.parent/'status.json')
                result.append(dict(path=p.parent.as_posix(),run_id=p.parent.name,purpose=c['execution_profile'],
                                   seeds=c.get('experiments',{}).get('cuda_paired',{}).get('seeds',[]),
                                   state=s['state'],claimed_completeness=s.get('scientific_completeness'),
                                   gpu=e.get('cuda',{}).get('name'),fingerprint=e.get('fingerprint')))
            except (ValueError,OSError,KeyError) as exc:
                result.append(dict(path=p.parent.as_posix(),discovery_error=str(exc)))
    return result


def audit_run(label,run,checks,discrepancies):
    def note(status,check,detail,seed='all'):
        checks.append(dict(platform=label,run_id=run.name,seed=seed,status=status,check=check,detail=detail))
    def gate(name,fn,seed='all'):
        try: value=fn();note('PASS',name,'Verified',seed);return value
        except (ValueError,OSError,KeyError,TypeError,AssertionError) as exc:
            note('FAIL',name,str(exc),seed);return None
    config=read(run/'config.resolved.json');env=read(run/'environment.json');manifest=read(run/'manifest.json')
    study=dict(platform=label,run_id=manifest['run_id'],root=run,environment=env,manifest=manifest,
               config=config,sessions={},repetitions=[],metadata=[],sources={},eligible=False)
    def contract():
        require(config['execution_profile']=='study','Not a study')
        item=config['experiments']['cuda_paired'];require(item['seeds']==SEEDS,'Wrong seed set/order')
        require(config['seeds']==SEEDS,'Wrong global seeds')
        want=dict(sizes=SIZES,warmup=5,repeats=20,profile=['baseline','optimized'],measurements=['resident','pipeline'],
                  resident_iterations=1,host_memory='pinned',modes=['ECB','CTR'])
        require(item['options']==want,'Study workload does not match required protocol')
        require(sha(run/'config.resolved.json')==manifest['config_sha256'],'Config hash mismatch')
        require(sha(run/'environment.json')==manifest['environment_sha256'],'Environment hash mismatch')
        require(env['fingerprint']==manifest['fingerprint'],'Fingerprint mismatch')
        require(env['cpu_features']['aesni'] is True and env['cuda']['available'] is True,'Missing AES-NI/CUDA availability')
        return True
    gate('Resolved protocol and manifest',contract)
    verification=verify_suite(run)
    note('PASS' if verification['scientific_completeness']=='complete' else 'FAIL','Existing read-only artifact verifier',
         'complete' if verification['scientific_completeness']=='complete' else '; '.join(verification.get('errors',[])))
    study['verification']=verification
    if env.get('git',{}).get('working_tree'):note('WARN','Working tree','Recorded dirty tree: '+env['git']['working_tree']+'; archived active sources are checked separately.')
    note('WARN','Platform interpretation','OS release/kernel are captured facts; Windows marketing edition and Colab provider labels are user supplied, not inferred from NT version.')
    fingerprints=set();ids=set()
    for seed in SEEDS:
        native=run/'experiments/cuda_paired'/f'seed-{seed}'/'native'
        def session():
            side=read(native.parent/'orchestration.json');meta=read(native/'metadata.json');gate_report=read(native/'validation.json')
            require(meta['schema_version']==2,'Unsupported native schema')
            require(meta['session_id'] not in ids,'Duplicate native session ID');ids.add(meta['session_id'])
            require(meta['cpu_dispatch']==gate_report['dispatch'],'Dispatch metadata disagrees with gate')
            for mode in ('ECB','CTR'):
                dispatch=gate_report['dispatch'][mode]
                require(all(dispatch[k] is True for k in ('cpu_aesni','aesni_library_loaded','available','passed')),'AES-NI not confirmed')
                for entry in dispatch['preflight']:
                    counts=entry['native_start_calls'];requested=entry['requested']
                    require(counts[requested]>0 and counts['software' if requested=='aesni' else 'aesni']==0,'Wrong native dispatch')
            for backend,path in gate_report['paths'].items():
                require(path['passed'] is True and len(path['tests'])==18,'Incomplete CUDA/CPU validation '+backend)
            require(meta['validation_passed'] is True,'Failed metadata validation')
            require(meta['gpu']['gpu_name']==env['cuda']['name'],'Native GPU environment mismatch')
            require(meta['library_versions']['pycryptodome']==env['packages']['pycryptodome'],'Library version drift')
            for key in ('runtime_version','driver_version','cupy_version'):
                require(meta['gpu'][key]==env['cuda'][key],'Runtime/driver drift: '+key)
            source_hashes={name:sha(native/'source'/name) for name in ACTIVE_SOURCES}
            for name,h in source_hashes.items():
                require(meta['source_sha256'][name]==h,'Native source hash mismatch: '+name)
                rootname=('experiments/' if name.endswith('.cu') else 'scripts/')+name
                require(manifest['sources'][rootname]==h,'Manifest source differs from snapshot: '+name)
            fingerprints.add(json.dumps(source_hashes,sort_keys=True));study['sources']=source_hashes
            raw=csvread(native/'raw.csv');saved=csvread(native/'summary.csv')
            require(len(saved)==60,'Expected 60 session summary records')
            independent,rep=recompute(raw,seed)
            before=len(discrepancies)
            compare_rows(saved,independent,['backend','measurement','mode','bytes'],f'{label}/seed-{seed}/native/summary.csv',discrepancies)
            compare_rows(read(native/'results.json')['summary'],independent,['backend','measurement','mode','bytes'],f'{label}/seed-{seed}/native/results.json#summary',discrepancies)
            require(len(discrepancies)==before,'Independent session statistic discrepancy')
            study['sessions'][seed]=independent
            study['repetitions'] += [dict(platform=label,run_id=run.name,input_file=f'experiments/cuda_paired/seed-{seed}/native/raw.csv',**r) for r in rep]
            study['metadata'].append(dict(seed=seed,session_id=meta['session_id'],cpu=meta['cpu'],
                  logical_cpus=meta['logical_cpus'],physical_cpus=meta['physical_cpus'],dispatch=meta['cpu_dispatch'],
                  environment_before=meta.get('environment_before'),environment_after=meta.get('environment_after'),
                  source_hashes=source_hashes,raw_rows=len(raw),summary_rows=len(saved),
                  zero_process_time_rows=sum(r['process_cpu_ns']==0 for r in raw if r['backend'].startswith('cpu_')),
                  mixed_clock_component_exceeds_total_rows=sum(r['h2d_ns']+r['kernel_ns']+r['d2h_ns']>r['end_to_end_ns'] for r in raw if r['measurement']=='pipeline')))
            return True
        gate('Raw CSV, 1200 observations / 60 groups, dispatch, sources, all summary statistics',session,seed)
    if len(fingerprints)==1:note('PASS','Within-run source equality','All active Python and CUDA snapshots identical over five sessions' if len(study['sessions'])==5 else 'Available snapshots match; incomplete run remains excluded')
    else:note('FAIL','Within-run source equality','Missing or differing active source snapshots')
    if len(study['sessions'])==5:
        study['aggregates']=session_aggregate(study['sessions'])
        def saved_aggregates():
            folders=sorted((run/'aggregates').glob('*/summary.json'));require(bool(folders),'No saved aggregate export')
            expected=[]
            for r in study['aggregates']:
                expected.append(dict(experiment='cuda_paired',**{k:r[k] for k in DIMS},metric=r['metric'],sessions=5,
                         median_of_sessions=r['median_of_sessions'],expected_sessions=5,observed_sessions=5,complete=True,
                         min_session=r['session_min'],max_session=r['session_max'],session_stdev=r['session_stdev']))
            keys=['experiment','backend','measurement','mode','bytes','metric']
            basefields=['sessions','median_of_sessions','expected_sessions','observed_sessions','complete']
            start=len(discrepancies)
            for path in folders:
                value=read(path);require(value['fingerprint']==manifest['fingerprint'],'Aggregate environment mismatch')
                require(value['execution_profile']=='study','Wrong saved aggregate purpose')
                for filename in ('summary.json','summary.csv','paired_speedups.csv','session_variability.csv'):
                    rows=value['rows'] if filename.endswith('.json') else csvread(path.parent/filename)
                    rows=[r for r in rows if r.get('experiment')=='cuda_paired']
                    wanted=[r for r in expected if filename!='paired_speedups.csv' or r['metric'].startswith('speedup_')]
                    fields=basefields+(['min_session','max_session','session_stdev'] if filename=='session_variability.csv' else [])
                    compare_rows(rows,wanted,keys,f'{label}/{path.parent.relative_to(run).as_posix()}/{filename}',discrepancies,fields)
                    for row in rows:
                        missing=row.get('missing_seeds');missing=json.loads(missing) if isinstance(missing,str) else missing
                        require(missing==[],'Aggregate missing seed flags')
                        if filename=='session_variability.csv':
                            seeds=row['seeds'];seeds=json.loads(seeds) if isinstance(seeds,str) else seeds
                            require(sorted(seeds)==SEEDS,'Saved variability seed set mismatch')
            require(len(discrepancies)==start,'Saved aggregate estimator discrepancies')
            return True
        gate('Independent five-session estimators versus all saved aggregate exports',saved_aggregates)
    study['eligible']=not any(r['status']=='FAIL' and r['platform']==label for r in checks)
    return study


def derived(study):
    rows=[]
    for seed,summaries in study['sessions'].items():
        lookup={group(r):r for r in summaries}
        def emit(backend,scope,mode,size,metric,value):
            rows.append(dict(platform=study['platform'],run_id=study['run_id'],seed=seed,backend=backend,
                             measurement=scope,mode=mode,bytes=size,metric=metric,value=value,
                             input_file=f'experiments/cuda_paired/seed-{seed}/native/raw.csv'))
        for mode in ('ECB','CTR'):
            for size in SIZES:
                cpu=lookup[('cpu_aesni','transform',mode,size)]
                soft=lookup[('cpu_software','transform',mode,size)]
                emit('cpu_aesni','transform',mode,size,'aesni_vs_software_time_speedup',soft['seconds_median']/cpu['seconds_median'])
                for backend in ('cuda_baseline','cuda_optimized_v1'):
                    res=lookup[(backend,'resident',mode,size)];pipe=lookup[(backend,'pipeline',mode,size)]
                    rt=res['kernel_seconds_median'];pt=pipe['end_to_end_seconds_median']
                    emit(backend,'pipeline/resident',mode,size,'pipeline_to_resident_throughput_ratio',pipe['end_to_end_throughput_MB_s_median']/res['kernel_throughput_MB_s_median'])
                    emit(backend,'resident/pipeline',mode,size,'resident_to_pipeline_latency_ratio',rt/pt)
                    emit(backend,'pipeline-resident',mode,size,'approximate_additional_pipeline_seconds',pt-rt)
                    emit(backend,'pipeline-resident',mode,size,'approximate_relative_additional_pipeline_time',(pt-rt)/rt)
                    for scope,metric in [('resident','kernel_seconds_median'),('pipeline','end_to_end_seconds_median')]:
                        baseline=lookup[('cuda_baseline',scope,mode,size)][metric]
                        if backend=='cuda_optimized_v1': emit(backend,scope,mode,size,'v1_vs_baseline_time_speedup',baseline/lookup[(backend,scope,mode,size)][metric])
                for backend in ('cpu_aesni','cpu_software'):
                    if mode=='ECB':
                        ecb=lookup[(backend,'transform','ECB',size)];ctr=lookup[(backend,'transform','CTR',size)]
                        emit(backend,'transform','ECB/CTR',size,'ecb_to_ctr_throughput_ratio',ecb['throughput_MB_s_median']/ctr['throughput_MB_s_median'])
        for backend,scope in [('cpu_software','transform'),('cpu_aesni','transform')]+[(b,s) for b in ('cuda_baseline','cuda_optimized_v1') for s in ('resident','pipeline')]:
            metric='throughput_MB_s_median' if scope=='transform' else 'kernel_throughput_MB_s_median' if scope=='resident' else 'end_to_end_throughput_MB_s_median'
            for mode in ('ECB','CTR'):
                v={size:lookup[(backend,scope,mode,size)][metric] for size in (1048576,16777216,33554432)}
                for other in (1048576,33554432):emit(backend,scope,mode,16777216,'throughput_16MiB_over_'+str(other)+'B',v[16777216]/v[other])
    return rows


def aggregate_derived(rows):
    groups=defaultdict(list)
    keys=['platform','run_id','backend','measurement','mode','bytes','metric']
    for r in rows:groups[tuple(r[k] for k in keys)].append(r)
    result=[]
    for key,group_rows in sorted(groups.items()):
        require(sorted(r['seed'] for r in group_rows)==SEEDS,'Incomplete derived contrast')
        result.append(dict(zip(keys,key),**stats([r['value'] for r in group_rows]),
                           seeds=SEEDS,above_one=sum(r['value']>1 for r in group_rows),below_one=sum(r['value']<1 for r in group_rows)))
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT/'experiments/results_orchestrated')
    parser.add_argument('--run',action='append',default=[],metavar='LABEL=RUN_DIRECTORY')
    parser.add_argument('--archive',action='append',default=[],metavar='LABEL=ZIP_OR_TAR')
    parser.add_argument('--historical-run',action='append',default=[],metavar='LABEL=RUN_DIRECTORY')
    parser.add_argument('--output',type=Path,default=ROOT/'experiments/analysis/cross_platform_2026_10')
    parser.add_argument('--no-figures',action='store_true')
    parser.add_argument('--scratch-root',type=Path,help='Optional short temporary parent, e.g. C:\\aes-tmp; never an input directory')
    args=parser.parse_args(argv);output=args.output.resolve()
    # No overwrite option: each analysis invocation is its own immutable export.
    require(not output.exists(),'Output exists; choose a fresh --output directory')
    require(not output.is_relative_to(args.root.resolve()) and not output.is_relative_to(ROOT/'experiments/results'),'Output cannot be inside input results')
    if args.scratch_root:
        scratch=args.scratch_root.resolve()
        require(not scratch.is_relative_to(args.root.resolve()) and not scratch.is_relative_to(ROOT/'experiments/results'),'Scratch cannot be inside original results')
        scratch.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='aes-offline-',dir=args.scratch_root) as temp:
        discovered=discover([args.root]);selected={};archives={};roles={};receipts={}
        for label,suffix in HINTS.items():
            found=[r for r in discovered if r.get('run_id','').endswith(suffix)]
            require(len(found)<=1,'Ambiguous primary run '+label)
            if found:selected[label]=Path(found[0]['path']).resolve();roles[label]='primary'
        explicit=set()
        for value in args.run+args.historical_run:
            label,path=value.split('=',1);require(label not in explicit,'Duplicate explicit label');explicit.add(label)
            selected[label]=Path(path).resolve();roles[label]='historical' if value in args.historical_run else 'primary'
        for index,value in enumerate(args.archive):
            label,path=value.split('=',1);require(label not in explicit,'Duplicate explicit label');explicit.add(label)
            archive=Path(path).resolve();archive_hash=sha(archive);dest=Path(temp)/str(index)
            receipt=extract_archive(archive,dest)
            candidates=discover([dest]);studies=[r for r in candidates if r.get('purpose')=='study']
            if label in HINTS:studies=[r for r in studies if r['run_id'].endswith(HINTS[label])]
            require(len(studies)==1,'Archive must identify exactly one requested study')
            prior=selected.get(label)
            selected[label]=Path(studies[0]['path']);roles[label]='primary'
            archives[label]=dict(path=archive.as_posix(),sha256=archive_hash)
            receipt['archive']=archives[label]
            if prior and prior.is_dir():
                old=inventory(prior);matches=[]
                for name,h in old.items():
                    full=prior.name+'/'+name
                    originals=[n for n,v in receipt['files'].items() if v['sha256']==h]
                    matches.append(dict(imported_name=full,archive_matches=originals,
                                        truncated_to_100=any(len(n)>100 and n[:100]==full for n in originals)))
                receipt['prior_import']=dict(path=prior.as_posix(),files=len(old),truncated_100_character_matches=sum(m['truncated_to_100'] for m in matches),matches=matches)
            receipts[label]=receipt
        require(len(set(selected.values()))==len(selected),'Same study selected twice')
        for root in selected.values():require(not output.is_relative_to(root),'Output cannot be inside selected input')
        before={label:inventory(root) for label,root in selected.items()}
        checks=[];discrepancies=[];studies=[]
        for label,run in sorted(selected.items()):
            print('Auditing',label,run.name,flush=True)
            study=audit_run(label,run,checks,discrepancies);study['role']=roles[label]
            study['display_path']=archives[label]['path']+'!/'+run.name if label in archives else run.as_posix()
            if label in archives:
                for row in checks:
                    if row['platform']==label:
                        row['detail']=row['detail'].replace(str(run),study['display_path'])
            studies.append(study)
        for label in HINTS:
            if label not in selected: checks.append(dict(platform=label,run_id='',seed='all',status='FAIL',check='Primary selection',detail='Required platform absent; supply --run or --archive'))
        valid=[s for s in studies if s['eligible']]
        primaries=[s for s in valid if s['role']=='primary']
        if len(primaries)>1:
            same=all(s['sources']==primaries[0]['sources'] for s in primaries)
            checks.append(dict(platform='cross-platform',run_id='selected primary runs',seed='all',status='PASS' if same else 'FAIL',check='Active Python/CUDA source identity',detail='Actual archived source SHA-256 equality; Git commit equality is not assumed.'))
            if not same:
                for s in primaries:s['eligible']=False
                valid=[s for s in studies if s['eligible']];primaries=[]
        output.mkdir(parents=True)
        session_rows=[dict(role=s['role'],**r) for s in valid for r in s['repetitions']]
        aggregates=[dict(platform=s['platform'],run_id=s['run_id'],role=s['role'],**r) for s in valid for r in s['aggregates']]
        contrasts=[dict(role=s['role'],**r) for s in valid for r in derived(s)]
        contrast_aggregates=aggregate_derived(contrasts)
        csvwrite(output/'session_level_statistics.csv',session_rows,fields=None if session_rows else ['platform','seed','metric'])
        csvwrite(output/'independent_aggregates.csv',aggregates,fields=None if aggregates else ['platform','metric'])
        csvwrite(output/'session_contrasts.csv',contrasts,fields=None if contrasts else ['platform','seed','metric'])
        csvwrite(output/'derived_comparisons.csv',contrast_aggregates,fields=None if contrast_aggregates else ['platform','metric'])
        csvwrite(output/'estimator_discrepancies.csv',discrepancies,['source','group','field','saved','recomputed','absolute_error'])
        csvwrite(output/'integrity_audit.csv',checks)
        from analysis.reports import reports,figures
        reports(output,studies,discovered,checks,discrepancies,aggregates,contrast_aggregates)
        if receipts:
            from analysis.reports import import_report
            dump(output/'archive_extraction_receipts.json',receipts)
            import_report(output,receipts,len(discrepancies))
        if not args.no_figures:figures(output,[r for r in aggregates if r['role']=='primary'],[r for r in contrasts if r['role']=='primary'])
        unchanged={label:inventory(root)==before[label] for label,root in selected.items()}
        require(all(unchanged.values()),'Input mutation detected during analysis')
        archive_unchanged={label:sha(info['path'])==info['sha256'] for label,info in archives.items()}
        require(all(archive_unchanged.values()),'Original archive changed during analysis')
        versions={}
        from importlib.metadata import version,PackageNotFoundError
        for name in ('matplotlib','numpy'):
            try:versions[name]=version(name)
            except PackageNotFoundError:versions[name]=None
        manifest=dict(schema_version=1,analysis='cross_platform_2026_10',python=platform.python_version(),packages=versions,
                      tolerances=dict(relative=RTOL,absolute=ATOL),quantiles='Linear inclusive (n-1)*p',
                      sources={p.relative_to(ROOT).as_posix():sha(p) for p in sorted((ROOT/'scripts/analysis').glob('*.py'))},
                      verifier_sources={p.relative_to(ROOT).as_posix():sha(p) for p in sorted((ROOT/'scripts/orchestration').glob('*.py'))},
                      inputs={label:dict(run_id=selected[label].name,location=archives.get(label,{}).get('path',str(selected[label])),role=roles[label],files=before[label]) for label in selected},
                      archive_hashes=archives,archives_unchanged=archive_unchanged,inputs_unchanged=unchanged,
                      primary_analysis_complete=all(any(s['platform']==label and s['eligible'] and s['role']=='primary' for s in studies) for label in HINTS),
                      checks=checks,output_hashes=inventory(output))
        dump(output/'reproducibility_manifest.json',manifest)
        print('Output:',output,'; three-platform complete:',manifest['primary_analysis_complete'],flush=True)
        return 0 if manifest['primary_analysis_complete'] and not any(r['status']=='FAIL' for r in checks) else 2


if __name__=='__main__':
    raise SystemExit(main())
