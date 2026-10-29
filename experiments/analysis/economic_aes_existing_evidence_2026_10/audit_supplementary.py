"""Read-only inventory and verification of supplementary campaigns; no benchmarks.
Imports only inspected pure statistical/protocol modules, never engines or runners.
"""
import sys
sys.dont_write_bytecode=True
import csv, hashlib, importlib.util, io, json, os, statistics as st, tarfile
from pathlib import Path
from audit_existing import ROOT, OUT, write, close

HASHES={}
def digest(data):return hashlib.sha256(data).hexdigest()
def data(path):
    b=path.read_bytes();HASHES[path.relative_to(ROOT).as_posix()]=digest(b);return b
def load_module(name,path):
    data(path)
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def recursive_equal(a,b):
    if isinstance(a,dict):return set(a)==set(b) and all(recursive_equal(a[k],b[k]) for k in a)
    if isinstance(a,list):return len(a)==len(b) and all(recursive_equal(x,y) for x,y in zip(a,b))
    if isinstance(a,(int,float)) and not isinstance(a,bool):return close(a,b)
    return a==b

def main():
    inventory=[];supp=[];checks=[]
    roots=['experiments/results','experiments/results_orchestrated','experiments/cpu_baseline_validation/results','experiments/colab_cpu_gpu_validation/results','experiments/page_batching_validation/results']
    def inventory_record(m,location,raw=None,validation=None):
        args=m.get('arguments',{});method=m.get('method',{})
        purpose=m.get('purpose',m.get('profile','unknown'))
        types=sorted({r.get('algorithm',r.get('implementation',r.get('layout','unknown'))) for r in raw}) if raw else []
        modes=sorted({r.get('mode','CTR' if 'page_batching' in location else 'unknown') for r in raw}) if raw else []
        scopes=sorted({r.get('measurement',r.get('experiment','unknown')) for r in raw}) if raw else []
        backends=sorted({r.get('backend',r.get('implementation','EVP/CUDA page paths' if 'page_batching' in location else 'unknown')) for r in raw}) if raw else []
        suitability='excluded: '+purpose if purpose!='study' else 'study candidate; independent validation required; not automatically pooled'
        if 'aes_cuda_cpu_gpu-study-20260930' in location:suitability='primary historical study; independently reconstructed'
        inventory.append(dict(location=location,experiment=m.get('experiment','page_batching' if 'page_batching' in location else 'unknown'),
            session_id=m.get('session_id',m.get('run_id','unknown')),sessions_in_record=1,purpose=purpose,seed=m.get('seed'),
            cpu=m.get('cpu_model',m.get('cpu','unknown')),gpu=m.get('gpu',{}).get('gpu_name','none recorded'),
            platform=m.get('machine',m.get('architecture','unknown')),os=m.get('os',m.get('platform','unknown')),
            algorithm_backend=';'.join(types),modes=';'.join(modes),key_bits='128' if ('cuda_cpu_gpu' in location or 'baseline_validation' in location or 'page_batching' in location) else 'see raw algorithm labels',
            backend=';'.join(backends),boundary=';'.join(scopes),workers=m.get('workers',m.get('threads','not specified')),
            warmup=args.get('warmup',m.get('warmups')),repetitions=args.get('repeats',m.get('repetitions',m.get('repeats'))),
            validation_record='present' if validation is not None else 'missing',validation_passed=m.get('validation_passed',validation.get('passed','per-backend; see record') if isinstance(validation,dict) else 'unknown'),
            raw_rows=len(raw) if raw else 0,raw_file=location+'/raw.csv',summary_location=location+'/summary.csv or summary.json',
            source_commit=m.get('git_commit','not recorded'),source_hashes=json.dumps(m.get('source_sha256',m.get('source_hashes',{})),sort_keys=True),publication_suitability=suitability))
    for root in roots:
        for d,dirs,files in os.walk(ROOT/root):
            dirs[:]=sorted(x for x in dirs if not (x.startswith('.venv') or x in ('source','sources','__pycache__','build','attempts','failed-attempts')))
            if 'metadata.json' not in files:continue
            p=Path(d);m=json.loads(data(p/'metadata.json'));raw=list(csv.DictReader(io.StringIO(data(p/'raw.csv').decode('utf-8-sig')))) if 'raw.csv' in files else None
            v=json.loads(data(p/'validation.json')) if 'validation.json' in files else None
            inventory_record(m,p.relative_to(ROOT).as_posix(),raw,v)
    # Independently recheck existing cross-platform audit's full input hashes.
    old=ROOT/'experiments/analysis/cross_platform_2026_10_complete'
    manifest=json.loads(data(old/'reproducibility_manifest.json'))
    for p in sorted(old.iterdir()):
        if p.is_file():data(p)
    for platform,info in manifest['inputs'].items():
        paths=[v for k,v in info.items() if k!='files'];checks.append(dict(campaign=platform,detail=str(paths),status='manifest input identity'))
        archive=manifest['archive_hashes'].get(platform)
        if archive:
            p=Path(archive['path']);assert digest(data(p))==archive['sha256']
            with tarfile.open(p) as tar:
                members={x.name:x for x in tar.getmembers() if x.isfile()}
                for rel,h in info['files'].items():
                    candidates=[name for name in members if name.endswith('/'+rel)]
                    assert len(candidates)==1,(platform,rel,candidates)
                    assert digest(tar.extractfile(members[candidates[0]]).read())==h
                for member in members.values():
                    if member.name.endswith('/native/metadata.json'):
                        m=json.load(tar.extractfile(member));base=member.name.rsplit('/',1)[0]
                        raw=list(csv.DictReader(io.TextIOWrapper(tar.extractfile(members[base+'/raw.csv']),encoding='utf-8')))
                        v=json.load(tar.extractfile(members[base+'/validation.json']))
                        inventory_record(m,p.relative_to(ROOT).as_posix()+'!/'+base,raw,v)
        else:
            run=next(p for p in (ROOT/'experiments/results_orchestrated').rglob('manifest.json') if p.parent.name==info.get('run_id', '') ) if info.get('run_id') else None
            if run is None:
                candidate=[v for v in paths if isinstance(v,str) and Path(v).is_dir()]
                assert candidate,info.keys();base=Path(candidate[0])
            else:base=run.parent
            for rel,h in info['files'].items():assert digest(data(base/rel))==h,(platform,rel)
        checks.append(dict(campaign=platform,status='PASS',detail=f"{len(info['files'])} archived audit input hashes rechecked; prior numerical audit retained, no campaign pooling"))
    # Inspect statistical modules; only call their pure summarizers (never CLI writers).
    cpu=load_module('economic_cpu_statistics',ROOT/'experiments/cpu_baseline_validation/aggregate.py')
    def verify_cpu(m,raw,v,get):
        assert m['status']=='complete' and all(c['passed'] for values in v.values() for c in values)
        for name,h in m['source_sha256'].items():assert digest(get('source/'+name))==h
        result=cpu.summarize(raw,m)
        for r in result:
            if r['mode']=='CTR' and r['bytes_per_worker']==33554432 and r['implementation']=='openssl_default':
                supp.append(dict(campaign='Windows CPU' if m['architecture']=='AMD64' else 'Oracle ARM64',seed=m['seed'],workers=m['workers'],backend='openssl_default',mode='CTR',key_bits=128,bytes_per_worker=33554432,boundary=r['timing_boundary'],worker=r['worker'],throughput_MB_s=r['median_throughput_MB_s'],estimator='bytes / session median time',session=m['session_id']))
        return result
    for p in sorted((ROOT/'experiments/cpu_baseline_validation/results').glob('single-study-*')):
        m=json.loads(data(p/'metadata.json'));raw=list(csv.DictReader(io.StringIO(data(p/'raw.csv').decode())));v=json.loads(data(p/'validation.json'))
        result=verify_cpu(m,raw,v,lambda name:data(p/name))
        assert recursive_equal(result,json.loads(data(p/'summary.json')))
        checks.append(dict(campaign=m['session_id'],status='PASS',detail='source hashes, validation, full sample grid, all saved summary fields'))
    seen={}
    for p in sorted((ROOT/'experiments/results').glob('oracle*.tar.gz')):
        data(p)
        with tarfile.open(p) as tar:
            members={x.name:x for x in tar.getmembers() if x.isfile()}
            for name in sorted(members):
                if not name.endswith('/metadata.json'):continue
                base=name.rsplit('/',1)[0]
                def get(rel):return tar.extractfile(members[base+'/'+rel]).read()
                m=json.loads(get('metadata.json'));rawbytes=get('raw.csv');raw=list(csv.DictReader(io.StringIO(rawbytes.decode())))
                identity=(digest(get('metadata.json')),digest(rawbytes))
                if m['session_id'] in seen:assert seen[m['session_id']]==identity;continue
                seen[m['session_id']]=identity
                v=json.loads(get('validation.json'));inventory_record(m,p.relative_to(ROOT).as_posix()+'!/'+base,raw,v)
                if m['purpose']=='study':
                    verify_cpu(m,raw,v,get);checks.append(dict(campaign=m['session_id'],status='PASS',detail='archive source hashes, validation and complete raw grid; operation envelope reconstructed from timestamps'))
    # Page study is complete despite stale readiness prose.
    protocol=load_module('protocol',ROOT/'experiments/page_batching_validation/protocol.py');sys.modules['protocol']=protocol
    pages=load_module('economic_page_statistics',ROOT/'experiments/page_batching_validation/aggregate.py')
    base=ROOT/'experiments/page_batching_validation/results/t4-phase2-study'
    paths=[base/str(seed) for seed in range(2003,2008)]
    for p in paths:
        m=json.loads(data(p/'metadata.json'));v=json.loads(data(p/'validation.json'))
        assert v['passed'] and all(c['passed'] and c['gpu_checked'] for c in v['cases'])
        for name,h in m['source_hashes'].items():assert digest(data(p/'sources'/name))==h
        rows=[json.loads(x) for x in data(p/'raw.jsonl').decode().splitlines()]
        assert len(rows)==600 and len({r['session_id'] for r in rows})==1
        assert recursive_equal(pages.summarize(rows),json.loads(data(p/'summary.json')))
        checks.append(dict(campaign=m['session_id'],status='PASS',detail='600 rows including warmup, complete schedule/pairs, validation, source hashes, all saved session summary fields'))
    calculated=pages.campaign(paths);assert recursive_equal(calculated,json.loads(data(base/'campaign_summary.json')))
    for r in calculated['speedups']:
        if r['layout']=='pages' and r['comparison']=='prepared_cpu_transform_over_gpu_pipeline':
            supp.append(dict(campaign='T4 independent pages',pages=r['pages'],layout='pages',boundary=r['comparison'],estimator=r['estimator'],median=r['session_distribution']['median'],minimum=r['session_distribution']['min'],maximum=r['session_distribution']['max'],favorable_sessions=r['favorable_sessions']))
    for p in sorted((ROOT/'experiments/configs').glob('*.json')):json.loads(data(p))
    for name in ['experiments/README.md','experiments/ORCHESTRATION.md','experiments/cuda_optimized_cpu_gpu_protocol.md','experiments/aes_acceleration_protocol.md',
                 'scripts/aes_cuda_cpu_gpu.py','scripts/aes_acceleration.py','scripts/aes_cuda_baseline.py','scripts/benchmark.py','scripts/cpu_validation.py',
                 'experiments/aes_cuda_baseline.cu','experiments/aes_cuda_optimized.cu','experiments/cpu_baseline_validation/core.py','experiments/cpu_baseline_validation/native.c','experiments/cpu_baseline_validation/windows_native.py','experiments/cpu_baseline_validation/methodology.md',
                 'experiments/colab_cpu_gpu_validation/readiness.md','experiments/page_batching_validation/READINESS.md']:
        data(ROOT/name)
    write('DATASET_INVENTORY.csv',inventory);write('SUPPLEMENTARY_CHECKS.csv',checks);write('SUPPLEMENTARY_RESULTS.csv',supp)
    (OUT/'supplementary_manifest.json').write_text(json.dumps(dict(input_sha256=HASHES,oracle_unique_sessions=len(seen),checks=checks),indent=2,sort_keys=True)+'\n')
    print('PASS supplementary checks; inventory records:',len(inventory),'Oracle unique sessions:',len(seen))

if __name__=='__main__':main()
