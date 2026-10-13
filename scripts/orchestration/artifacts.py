"""Verify native artifacts without rewriting their schema or contents."""
import csv
import hashlib
import itertools
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from .registry import REGISTRY


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def hashes(folder):
    return {p.relative_to(folder).as_posix():digest(p) for p in sorted(folder.rglob('*')) if p.is_file()}


def discover(staging):
    candidates=[p.parent for p in staging.rglob('metadata.json') if 'source' not in p.relative_to(staging).parts]
    if len(candidates)!=1: raise ValueError('Expected exactly one native result directory, found '+str(len(candidates)))
    return candidates[0]


def check(condition, message):
    if not condition: raise ValueError(message)


def validation(report, experiment):
    check(report.get('passed') is True,'Validation did not pass')
    def walk(value):
        if isinstance(value,dict):
            for k,v in value.items():
                if k=='passed' or k.endswith('_passed') or k.endswith('_rejected'):
                    check(v is True,'Failed validation field '+k)
                walk(v)
        elif isinstance(value,list):
            for v in value: walk(v)
    walk(report)
    counts={'cpu_cbc':5,'cpu_aesni':6,'cpu_gcm':4}
    if experiment in counts: check(len(report.get('vectors',[]))==counts[experiment],'Incomplete KAT records')
    if experiment=='cpu_cbc':
        check({v.get('algorithm') for v in report['vectors']}=={'DES','3DES','AES-128','AES-192','AES-256'},'Missing CBC KAT algorithm')
        if report.get('aes_backend')=='software': check(report.get('dispatch',{}).get('passed') is True,'Missing software dispatch evidence')
    if experiment in ('cpu_aesni','cpu_gcm'):
        algorithms=['AES-128','AES-192','AES-256'] if experiment=='cpu_aesni' else ['AES-128-GCM','AES-256-GCM']
        check({(v.get('algorithm'),v.get('backend')) for v in report['vectors']}==set(itertools.product(algorithms,['software','aesni'])),'Missing backend KAT')
        check(report.get('dispatch',{}).get('passed') is True,'Missing accelerated dispatch evidence')
        if experiment=='cpu_aesni': check(report.get('backends_equal') is True,'Missing paired equality evidence')
    if experiment=='cuda_baseline': check(len(report.get('tests',[]))==18,'Incomplete CUDA KAT records')
    if experiment=='cuda_paired':
        check(set(report.get('paths',{}))=={'cpu_software','cpu_aesni','cuda_baseline','cuda_optimized_v1','cuda_ttable'},'Missing validated backend')
        check(report.get('all_backends_equal') is True,'Cross-backend equality missing')
        check(set(report.get('dispatch',{}))=={'ECB','CTR'},'Missing CPU dispatch modes')
        for path in report['paths'].values():
            check(len(path.get('tests',[]))==18 and path.get('wrap_rejected') is True,'Incomplete backend validation')
    if experiment in ('avalanche','keyspace'): check(bool(report.get('tests')),'Missing functional tests')


def expected_groups(experiment, o):
    if experiment=='cpu_cbc': return ('algorithm','mode','bytes','operation'),list(itertools.product(['DES','3DES','AES-128','AES-192','AES-256'],['CBC'],o['sizes'],['encrypt','decrypt']))
    if experiment=='cpu_aesni': return ('algorithm','backend','mode','bytes','operation'),list(itertools.product(['AES-128','AES-192','AES-256'],['software','aesni'],['CBC'],o['sizes'],['encrypt','decrypt']))
    if experiment=='cpu_gcm': return ('algorithm','bytes','operation'),list(itertools.product(['AES-128-GCM','AES-256-GCM'],o['sizes'],['encrypt','decrypt']))
    if experiment=='avalanche': return ('algorithm','variant'),list(itertools.product(o['algorithms'],[v+'_bit_flip' for v in o['variants']]))
    if experiment=='keyspace': return ('scenario',),[(v,) for v in o['target_position']]
    if experiment=='cuda_baseline': return ('mode','bytes'),list(itertools.product(o['modes'],o['sizes']))
    jobs=[('cpu_software','transform'),('cpu_aesni','transform')]+[(dict(baseline='cuda_baseline',optimized='cuda_optimized_v1',ttable='cuda_ttable')[p],m) for p in o['profile'] for m in o['measurements']]
    return ('backend','measurement','mode','bytes'),[(b,m,mode,size) for b,m in jobs for mode in o['modes'] for size in o['sizes']]


def verify_native(folder, experiment, options, seed, purpose, staging=None):
    spec=REGISTRY[experiment]
    for name in spec['expected_artifacts']: check((folder/name).exists(),'Missing artifact: '+name)
    check(any((folder/'source').iterdir()),'Empty source archive')
    meta=read(folder/'metadata.json'); report=read(folder/'validation.json'); data=read(folder/'results.json')
    native=spec['native_name']+('_diagnostic' if experiment=='cuda_baseline' and options['profile']=='diagnostic' else '')
    check(meta.get('experiment')==native and meta.get('seed')==seed and meta.get('purpose')==purpose,'Invocation identity mismatch')
    for k,v in options.items(): check(meta['arguments'].get(k)==v,'Recorded argument differs: '+k)
    if staging is not None: check(Path(meta['arguments']['output']).resolve()==staging.resolve(),'Output provenance mismatch')
    validation(report,experiment)
    method=meta.get('method',{})
    check(report.get('purpose')==purpose and report.get('session_id')==meta.get('session_id',method.get('session_id')),'Validation session mismatch')
    check(digest(folder/'validation.json')==meta.get('validation_sha256',method.get('validation_sha256')),'Validation hash mismatch')
    if 'measurement_started_utc' in method: check(report['completed_utc']<method['measurement_started_utc'],'Validation must precede measurements')
    for name,sha in meta.get('source_sha256',{}).items(): check(digest(folder/'source'/name)==sha,'Source snapshot mismatch')
    for p in (folder/'source').glob('*.py'):
        if p.name in meta.get('script_sha256',{}): check(digest(p)==meta['script_sha256'][p.name],'Script snapshot mismatch')
    for kind in ('raw','summary'):
        check(bool(data.get(kind)),'Empty '+kind)
        with (folder/(kind+'.csv')).open(encoding='utf-8',newline='') as f: rows=list(csv.DictReader(f))
        check(len(rows)==len(data[kind]),'CSV/JSON row count mismatch')
        for csvrow,row in zip(rows,data[kind]):
            check(csvrow=={k:'' if v is None else str(v) for k,v in row.items()},'CSV/JSON values differ')
    fields,expected=expected_groups(experiment,options)
    group=lambda r:tuple(r[k] for k in fields)
    raw=defaultdict(list)
    for row in data['raw']:
        raw[group(row)].append(row)
        if 'session_id' in row: check(row['session_id']==report['session_id'],'Raw session mismatch')
        if 'seed' in row: check(row['seed']==seed,'Raw seed mismatch')
        if 'validation_checked' in row: check(row['validation_checked'] is True,'Unchecked raw observation')
        for k,v in row.items():
            if isinstance(v,float): check(math.isfinite(v),'Nonfinite measurement')
            if v is not None and (k in ('seconds','wall_elapsed_ns','elapsed_seconds','kernel_ns','end_to_end_ns','candidates_per_second') or k.endswith('throughput_MB_s')):
                check(v>0,'Nonpositive timing/rate: '+k)
        if experiment.startswith('cuda'):
            check(row.get('measurement') in options.get('measurements',[options.get('measurement')]) or row.get('backend','').startswith('cpu_'),'Unexpected execution scope')
            if row.get('measurement')=='resident':
                check(row['resident_iterations']==options['resident_iterations'] and row.get('end_to_end_ns') is None and row.get('transfer_ns') is None,'Resident scope contamination')
            if row.get('backend','').startswith('cuda'): check(row.get('host_memory')==options['host_memory'],'Host memory policy mismatch')
    count=options.get('samples_per_group',options.get('repeats'))
    check(set(raw)==set(expected) and all(len(v)==count for v in raw.values()),'Incomplete or unexpected raw groups')
    summaries={group(r):r for r in data['summary']}
    check(len(summaries)==len(data['summary']) and set(summaries)==set(expected),'Incomplete or duplicate summary groups')
    for key,observations in raw.items():
        index='sample_id' if experiment=='avalanche' else 'repeat'
        check({r[index] for r in observations}==set(range(count)),'Missing/duplicate sample indices')
        for field,value in summaries[key].items():
            metric=field[:-7] if field.endswith('_median') else None
            if metric and metric in observations[0]:
                values=[r[metric] for r in observations if r[metric] is not None]
                check((value is None and not values) or (values and math.isclose(value,statistics.median(values),rel_tol=1e-10,abs_tol=1e-15)),'Summary median differs from raw: '+field)
        if experiment=='avalanche': check(summaries[key]['median']==statistics.median(r['hamming_distance_bits'] for r in observations),'Invalid avalanche median')
    if experiment=='cuda_paired':
        pairs=defaultdict(list)
        for r in data['raw']: pairs[r['pair_id']].append(r)
        n=2+len(options['profile'])*len(options['measurements'])
        check(all(len(p)==n and len({r['pair_sha256'] for r in p})==1 for p in pairs.values()),'Pair input identity mismatch')
        for row in data['summary']:
            if not row['backend'].startswith('cuda_'): continue
            scope='isolated' if row['measurement']=='resident' else 'pipeline'
            denominator=row['kernel_seconds_median'] if scope=='isolated' else row['end_to_end_seconds_median']
            for cpu in ('cpu_aesni','cpu_software'):
                numerator=summaries[(cpu,'transform',row['mode'],row['bytes'])]['seconds_median']
                check(denominator>0 and math.isclose(row['speedup_'+scope+'_vs_'+cpu],numerator/denominator,rel_tol=1e-10),'Invalid paired timing ratio')
    if experiment=='cpu_aesni':
        for row in data['summary']:
            key=(row['algorithm'],'software',row['mode'],row['bytes'],row['operation'])
            check(math.isclose(row['speedup_vs_software_median'],summaries[key]['seconds_median']/row['seconds_median'],rel_tol=1e-10),'Invalid AES-NI paired ratio')
    return dict(passed=True,raw_rows=len(data['raw']),summary_rows=len(data['summary']),session_id=report['session_id'],source_hashes=hashes(folder/'source'),
                cuda_conditions=dict(discovery=True,compilation=True,known_answer=True,cpu_differential=True,cross_backend=True if experiment=='cuda_paired' else None,performance=True,export=True) if experiment.startswith('cuda') else None)
