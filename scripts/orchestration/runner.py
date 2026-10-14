"""Sequential, recoverable execution with isolated attempts and immutable results."""
import json
import os
import shutil
import subprocess
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from .configuration import ROOT, safe_output
from .registry import REGISTRY, command
from .platform import detect, child_environment
from .artifacts import read, digest, hashes, discover, verify_native, check


def utc(): return datetime.now(timezone.utc).isoformat()


def identifier(): return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid.uuid4().hex[:12]


def write(path, value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temporary.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    os.replace(temporary,path)


def sources():
    paths=list((ROOT/'scripts').rglob('*.py'))+list((ROOT/'experiments').glob('*.cu'))+list((ROOT/'experiments').glob('*protocol.md'))
    return {p.relative_to(ROOT).as_posix():digest(p) for p in sorted(paths)}


@contextmanager
def lock(path):
    """OS-released lock: safe across crashes; no stale PID guessing."""
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a+b') as stream:
        stream.seek(0,2)
        if stream.tell()==0: stream.write(b'0'); stream.flush()
        stream.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as exc: raise ValueError('Another orchestrator holds '+str(path)) from exc
        try: yield
        finally:
            stream.seek(0)
            if os.name=='nt': msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else: fcntl.flock(stream,fcntl.LOCK_UN)


def preflight(name, options, config, environment, disk_path):
    reasons=[]; spec=REGISTRY[name]; lim=config['limits']
    for dep in spec['required_packages']:
        if not environment['packages'].get(dep): reasons.append('Missing '+dep)
        elif environment.get('package_imports',{}).get(dep) is False: reasons.append('Cannot import mandatory dependency '+dep)
    for feature in set(config['required_cpu_features']) | ({'aesni'} if 'aesni' in spec['required_capabilities'] else set()):
        if environment['cpu_features'].get(feature) is not True: reasons.append('Required CPU feature unavailable: '+feature)
    size=max(options.get('sizes',[32]))
    if size>lim['max_workload_bytes']: reasons.append('Workload exceeds byte cap')
    available=environment.get('available_ram_bytes')
    if available is None or available < 8*size+lim['min_free_ram_bytes']: reasons.append('Insufficient or unknown available host RAM')
    parent=Path(disk_path)
    while not parent.exists(): parent=parent.parent
    if shutil.disk_usage(parent).free<lim['min_free_disk_bytes']: reasons.append('Insufficient disk space')
    cuda_missing=False
    if spec['classification']=='CUDA':
        cuda=environment.get('cuda',{})
        cuda_missing=not cuda.get('available')
        if cuda_missing: reasons.append('CUDA discovery unavailable; no synthetic measurements')
        else:
            if cuda.get('vram_bytes',0)<4*size+67108864: reasons.append('Insufficient GPU VRAM capacity')
            # nvidia-smi free memory is advisory when unavailable; allocation failures remain fatal.
            free=[float(g['memory.free'])*1048576 for g in environment['gpus'] if g.get('memory.free') and g.get('name')==cuda.get('name')]
            if free and min(free)<4*size+67108864: reasons.append('Insufficient free GPU VRAM')
            required=config.get('min_compute_capability')
            if required:
                cc=str(cuda.get('compute_capability',''))
                actual=(int(cc[:-1]),int(cc[-1])) if cc.isdigit() and len(cc)>1 else None
                if actual is None or actual<tuple(map(int,required.split('.'))): reasons.append('Required compute capability unavailable')
    return dict(passed=not reasons,reasons=reasons,skip=cuda_missing and config['gpu_unavailable']=='skip' and len(reasons)==1,
                required_packages=spec['required_packages'],optional_telemetry_errors=environment.get('telemetry_errors',[]),
                cuda_discovered=environment.get('cuda',{}).get('available',False),kernel_compiled=None,cryptographic_validation=None)


def tasks(config):
    return [(name,seed,item['options']) for name,item in config['experiments'].items() for seed in item['seeds']]


def create(config, environment):
    base=safe_output(config['output_root'])
    directory=base/(config['platform_alias'] or environment['os'].lower())/environment['fingerprint']/(config['suite_id']+'-'+identifier())
    directory.mkdir(parents=True,exist_ok=False)
    for part in ('logs','validation','experiments','attempts','failed-attempts','aggregates','reports'): (directory/part).mkdir()
    write(directory/'config.resolved.json',config); write(directory/'environment.json',environment)
    write(directory/'manifest.json',dict(schema_version=1,run_id=directory.name,created_utc=utc(),fingerprint=environment['fingerprint'],
          config_sha256=digest(directory/'config.resolved.json'),environment_sha256=digest(directory/'environment.json'),sources=sources(),
          ordering=[dict(experiment=n,seed=s) for n,s,_ in tasks(config)],global_seeds=config['seeds'],git=environment['git']))
    write(directory/'status.json',dict(state='PENDING',scientific_completeness='partial',events=[],tasks={n+'/seed-'+str(s):dict(state='PENDING',attempts=[],events=[dict(state='PENDING',utc=utc())]) for n,s,_ in tasks(config)}))
    return directory


def verify_completed(directory, key, task, config):
    name,seed_text=key.split('/seed-'); seed=int(seed_text)
    folder=directory/'experiments'/name/('seed-'+str(seed))
    side=read(folder/'orchestration.json')
    check(side.get('fingerprint')==read(directory/'manifest.json')['fingerprint'],'Result platform fingerprint mismatch: '+key)
    native=folder/'native'
    check(hashes(native)==side['artifact_hashes'],'Completed artifacts changed: '+key)
    return verify_native(native,name,config['experiments'][name]['options'],seed,config['execution_profile'])


def failed_integrity(directory, task):
    """Inspect the most recent failed attempt; successful retries supersede it."""
    if task['state']!='FAILED': return False
    events=task.get('events',[])
    if len(events)>1 and events[-2]['state']=='VERIFYING': return True
    for attempt in task.get('attempts',[])[-1:]:
        folder=directory/attempt
        if (folder/'failure.json').exists():
            failure=read(folder/'failure.json')
            if failure.get('scientific_integrity_failed'): return True
            if any(v.get('passed') is False for v in failure.get('validation_records',[])): return True
        for path in folder.rglob('*validation*.json'):
            if 'source' not in path.relative_to(folder).parts and read(path).get('passed') is False: return True
    return False


def verify_suite(directory, *, strict=False):
    """Read-only schema-2 report, including for schema-1 suite manifests.

    strict preserves resume's refusal to touch corrupted accepted artifacts.
    CLI verification returns a structured invalid report instead of losing the
    classification in an exception. Failed attempts remain explicitly retryable.
    """
    try:
        return _verify_suite(Path(directory).resolve(),strict=strict)
    except (ValueError,KeyError,TypeError,OSError,ArithmeticError) as exc:
        if strict: raise
        return dict(schema_version=2,passed=False,scientific_completeness='invalid',tasks={},
                    missing_measurements=[],errors=[str(exc)])


def _verify_suite(directory, *, strict):
    directory=Path(directory).resolve(); manifest=read(directory/'manifest.json')
    check(digest(directory/'config.resolved.json')==manifest['config_sha256'],'Resolved configuration changed')
    check(digest(directory/'environment.json')==manifest['environment_sha256'],'Environment manifest changed')
    config=read(directory/'config.resolved.json'); status=read(directory/'status.json'); results={}
    expected={n+'/seed-'+str(s) for n,s,_ in tasks(config)}
    check(bool(expected) and len(expected)==len(tasks(config)),'Empty or duplicate configured sessions')
    check(set(status['tasks'])==expected,'Task inventory mismatch')
    records=[]; errors=[]; identities=set(); missing=[]; invalid=False
    for key,task in status['tasks'].items():
        check(task['state'] in ('PENDING','PREFLIGHT','VALIDATING','RUNNING','VERIFYING','COMPLETED','FAILED','SKIPPED','INTERRUPTED'),'Unknown task state: '+key)
        name,seed=key.split('/seed-'); seed=int(seed)
        if task['state']=='COMPLETED':
            try:
                results[key]=verify_completed(directory,key,task,config)
                identity=(name,results[key]['session_id'])
                check(identity not in identities,'Duplicate native session identity: '+key)
                identities.add(identity)
                for row in read(directory/'experiments'/name/('seed-'+str(seed))/'native/results.json')['summary']:
                    records.append(dict(experiment=name,seed=seed,summary=row))
            except (ValueError,KeyError,TypeError,OSError,ArithmeticError) as exc:
                if strict: raise
                invalid=True; errors.append(key+': '+str(exc))
                results[key]=dict(passed=False,state='COMPLETED',error=str(exc))
        else:
            invalid_attempt=failed_integrity(directory,task)
            invalid=invalid or invalid_attempt
            results[key]=dict(passed=False,state=task['state'],scientific_completeness='invalid' if invalid_attempt else 'partial')
            missing.append(dict(experiment=name,seed=seed,state=task['state'],reason=task.get('events',[])[-1] if task.get('events') else None))
    if records and not invalid:
        from .aggregation import summarize_sessions
        try: summarize_sessions(records,config,require_complete=False)
        except (ValueError,KeyError,TypeError) as exc:
            if strict: raise
            invalid=True; errors.append(str(exc))
    completeness='invalid' if invalid else 'partial' if missing else 'complete'
    sessions={}
    for name,item in config['experiments'].items():
        observed=[s for s in item['seeds'] if results[name+'/seed-'+str(s)].get('passed')]
        absent=[s for s in item['seeds'] if s not in observed]
        sessions[name]=dict(expected_sessions=len(item['seeds']),observed_sessions=len(observed),missing_seeds=absent,complete=not absent)
    return dict(schema_version=2,passed=not invalid and all(r.get('passed') or r.get('state')=='SKIPPED' for r in results.values()),
                scientific_completeness=completeness,tasks=results,sessions=sessions,missing_measurements=missing,errors=errors)


def process(argv, attempt, env, timeout):
    start=time.monotonic(); p=None; outcome=dict(command=argv,cwd=str(ROOT),started_utc=utc(),exit_code=None)
    write(attempt/'command.json',outcome)
    try:
        with (attempt/'stdout.log').open('wb') as stdout, (attempt/'stderr.log').open('wb') as stderr:
            p=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=stdout,stderr=stderr)
            outcome['pid']=p.pid
            try:
                import psutil
                outcome['process_created']=psutil.Process(p.pid).create_time()
            except (ImportError,OSError): outcome['process_created']=None
            write(attempt/'command.json',outcome)
            try: outcome['exit_code']=p.wait(timeout=timeout)
            except (KeyboardInterrupt,subprocess.TimeoutExpired):
                p.terminate()
                try: p.wait(timeout=5)
                except subprocess.TimeoutExpired: p.kill(); p.wait()
                outcome['exit_code']=p.returncode
                raise
        check(outcome['exit_code']==0,'Subprocess exited '+str(outcome['exit_code']))
    except BaseException as exc:
        outcome['error']=type(exc).__name__+': '+str(exc)
        raise
    finally:
        outcome.update(finished_utc=utc(),duration_seconds=time.monotonic()-start)
        write(attempt/'execution.json',outcome)
    return outcome


def execute(directory, retry_failed=False, retry_skipped=False):
    directory=safe_output(directory)
    # One performance suite per checkout; file locks release on hard termination.
    with lock(ROOT/'build/orchestration-machine.lock'), lock(directory/'execution.lock'):
        initial_verification=verify_suite(directory,strict=True)
        config=read(directory/'config.resolved.json'); manifest=read(directory/'manifest.json')
        check(sources()==manifest['sources'],'Source code changed; create a fresh suite instead of resuming')
        environment=detect(config)
        check(environment['fingerprint']==manifest['fingerprint'],'Hardware/software fingerprint changed; create a fresh suite')
        status=read(directory/'status.json')
        status['state']='RUNNING'; status['scientific_completeness']=initial_verification['scientific_completeness']; status['events'].append(dict(state='RUNNING',utc=utc()))
        write(directory/'status.json',status)
        for name,seed,options in tasks(config):
            key=name+'/seed-'+str(seed); task=status['tasks'][key]
            if task['state']=='COMPLETED': continue
            if task['state']=='FAILED' and not retry_failed: continue
            if task['state']=='SKIPPED' and not retry_skipped: continue
            def transition(state, **details):
                task['state']=state; task['events'].append(dict(state=state,utc=utc(),**details)); write(directory/'status.json',status)
            final=directory/'experiments'/name/('seed-'+str(seed))
            # Crash after atomic promotion but before status update: verify and adopt, never rerun.
            if final.exists():
                verify_completed(directory,key,task,config); transition('COMPLETED',recovered_promotion=True); continue
            for old in task['attempts']:
                old_path=directory/old
                if old_path.exists() and old_path.parent.name=='attempts':
                    if (old_path/'command.json').exists() and not (old_path/'execution.json').exists():
                        orphan=read(old_path/'command.json')
                        if orphan.get('pid'):
                            import psutil
                            try:
                                proc=psutil.Process(orphan['pid'])
                                check(orphan.get('process_created') is not None and proc.create_time()!=orphan['process_created'],'Prior benchmark process is still alive; wait for it to exit before resuming')
                            except psutil.NoSuchProcess: pass
                            except psutil.AccessDenied as exc:
                                raise ValueError('Cannot establish prior benchmark process identity; refusing to resume') from exc
                    old_path.rename(directory/'failed-attempts'/old_path.name)
                    task['attempts'][task['attempts'].index(old)]='failed-attempts/'+old_path.name
            attempt=directory/'attempts'/(name+'-seed-'+str(seed)+'-'+identifier()); attempt.mkdir()
            task['attempts'].append(attempt.relative_to(directory).as_posix())
            print(key+': PREFLIGHT',flush=True)
            try:
                transition('PREFLIGHT')
                # Refresh available RAM, disk and GPU telemetry before each sequential job.
                live=detect(config)
                check(live['fingerprint']==manifest['fingerprint'],'Environment changed during suite')
                evidence=preflight(name,options,config,live,directory)
                write(attempt/'preflight.json',evidence)
                if evidence['skip']:
                    transition('SKIPPED',reason=evidence['reasons']); continue
                check(evidence['passed'],'; '.join(evidence['reasons']))
                staging=attempt/'staging'; staging.mkdir()
                transition('VALIDATING',gate='Legacy internal gate precedes warmups and timers; result pending')
                argv=command(name,options,seed,config['execution_profile'],staging,ROOT)
                transition('RUNNING',note='Subprocess includes internal validation; this state does not assert gate success')
                execution=process(argv,attempt,child_environment(config),config['limits']['timeout_seconds'])
                transition('VERIFYING')
                native=discover(staging)
                outcome=verify_native(native,name,options,seed,config['execution_profile'],staging)
                check(sources()==manifest['sources'],'Source code changed during execution; result quarantined')
                write(attempt/'verification.json',outcome)
                # Prepare a complete bundle on the same filesystem, then rename once.
                bundle=attempt/'promotion'; bundle.mkdir()
                artifact_hashes=hashes(native); native.rename(bundle/'native')
                write(bundle/'orchestration.json',dict(experiment=name,seed=seed,options=options,execution=execution,validation=outcome,artifact_hashes=artifact_hashes,original_output=str(native),attempt=attempt.relative_to(directory).as_posix(),fingerprint=manifest['fingerprint']))
                check(hashes(bundle/'native')==artifact_hashes,'Promotion integrity failure')
                final.parent.mkdir(parents=True,exist_ok=True)
                check(not final.exists(),'Refusing to overwrite completed output')
                bundle.rename(final)
                transition('COMPLETED')
                print(key+': COMPLETED',flush=True)
            except (Exception,KeyboardInterrupt) as exc:
                state='INTERRUPTED' if isinstance(exc,KeyboardInterrupt) else 'FAILED'
                gates=[]
                for path in attempt.rglob('*validation*.json'):
                    try: gates.append(dict(path=path.relative_to(attempt).as_posix(),passed=read(path).get('passed')))
                    except (ValueError,OSError): gates.append(dict(path=path.relative_to(attempt).as_posix(),passed=None))
                write(attempt/'failure.json',dict(state=state,error=type(exc).__name__+': '+str(exc),utc=utc(),validation_records=gates,
                      scientific_integrity_failed=task['state']=='VERIFYING' or any(g['passed'] is False for g in gates),
                      note='Missing evidence means unknown, never passed. Compilation is established only by persisted CUDA validation; exit zero alone establishes no scientific condition.'))
                dest=directory/'failed-attempts'/attempt.name; attempt.rename(dest)
                task['attempts'][-1]=dest.relative_to(directory).as_posix()
                transition(state,error=str(exc)); print(key+': '+state+' '+str(exc),flush=True)
                if state=='INTERRUPTED' or config['fail_fast']: break
        states={t['state'] for t in status['tasks'].values()}
        status['state']='COMPLETED' if states=={'COMPLETED'} else 'COMPLETED_WITH_SKIPS' if states<={'COMPLETED','SKIPPED'} else 'INTERRUPTED' if 'INTERRUPTED' in states else 'INCOMPLETE'
        status['events'].append(dict(state=status['state'],utc=utc())); write(directory/'status.json',status)
        verification=verify_suite(directory)
        status['scientific_completeness']=verification['scientific_completeness']
        status['missing_measurements']=verification['missing_measurements']
        write(directory/'status.json',status)
        print('Suite state: '+status['state']+'; scientific_completeness: '+status['scientific_completeness'],flush=True)
        return status['state'] in ('COMPLETED','COMPLETED_WITH_SKIPS') and verification['scientific_completeness']!='invalid'
