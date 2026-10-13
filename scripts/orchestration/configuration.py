import json
import re
from pathlib import Path
from .registry import REGISTRY, defaults

ROOT = Path(__file__).resolve().parents[2]


def safe_output(path):
    path = Path(path).resolve()
    historical = (ROOT/'experiments/results').resolve()
    if path == historical or historical in path.parents or path in historical.parents:
        raise ValueError('Output must not overlap historical results')
    return path


def positive(value, name):
    if type(value) is not int or value < 1: raise ValueError(name+' must be a positive integer')


def resolve(data):
    allowed = {'schema_version','suite_id','execution_profile','seeds','warmup','repeats','output_root','platform_alias','fail_fast','experiments','limits','cuda_device','gpu_unavailable','cloud','required_cpu_features','min_compute_capability'}
    if set(data)-allowed: raise ValueError('Unknown configuration keys: '+str(set(data)-allowed))
    if data.get('schema_version') != 1: raise ValueError('schema_version must be 1')
    c = dict(schema_version=1,suite_id='aes-retrospective-v1',execution_profile='smoke',seeds=[2003],output_root='experiments/results_orchestrated',platform_alias=None,fail_fast=True,limits={},cuda_device=None,gpu_unavailable='fail',cloud=None,required_cpu_features=[],min_compute_capability=None)
    c.update(data)
    if c['execution_profile'] not in ('smoke','pilot','study'): raise ValueError('Invalid execution_profile')
    if not isinstance(c['suite_id'],str) or not re.fullmatch(r'[A-Za-z0-9_-]+',c['suite_id']): raise ValueError('Invalid suite_id')
    if c['platform_alias'] is not None and not re.fullmatch(r'[A-Za-z0-9_-]+',c['platform_alias']): raise ValueError('Invalid platform alias')
    if type(c['fail_fast']) is not bool: raise ValueError('fail_fast must be boolean')
    if c['gpu_unavailable'] not in ('fail','skip'): raise ValueError('gpu_unavailable must be fail or skip')
    if c['cuda_device'] is not None and not re.fullmatch(r'(\d+|GPU-[A-Za-z0-9-]+)',str(c['cuda_device'])): raise ValueError('cuda_device must be one index or GPU UUID')
    if c['cloud'] is not None and (not isinstance(c['cloud'],dict) or set(c['cloud'])-{'provider','instance_type','region'}): raise ValueError('cloud accepts provider, instance_type, region only')
    if not isinstance(c['required_cpu_features'],list) or set(c['required_cpu_features'])-{'aesni','vaes'}: raise ValueError('Unknown required CPU features')
    if c['min_compute_capability'] is not None and not re.fullmatch(r'\d+\.\d+',str(c['min_compute_capability'])): raise ValueError('Use major.minor compute capability')
    c['output_root']=str(safe_output(ROOT/c['output_root']))
    limits=dict(max_workload_bytes=104857600,min_free_ram_bytes=268435456,min_free_disk_bytes=104857600,max_key_bits=12,max_key_candidates=1000000,timeout_seconds=600)
    if set(c['limits'])-set(limits): raise ValueError('Unknown resource limit')
    limits.update(c['limits'])
    for k,v in limits.items():
        if k=='timeout_seconds' and v is None: continue
        positive(v,k)
    c['limits']=limits
    if not isinstance(c['seeds'],list) or not c['seeds'] or any(type(s) is not int for s in c['seeds']) or len(set(c['seeds']))!=len(c['seeds']): raise ValueError('Global seeds must be unique integers')
    for k in ('warmup','repeats'):
        if k in c: positive(c[k],k)
    specs=data.get('experiments',{'cpu_cbc':{'enabled':True},'avalanche':{'enabled':True},'keyspace':{'enabled':True}})
    if not isinstance(specs,dict): raise ValueError('experiments must be an object')
    resolved={}
    for name,item in specs.items():
        if name not in REGISTRY: raise ValueError('Unknown experiment '+name)
        if not isinstance(item,dict) or type(item.get('enabled',True)) is not bool: raise ValueError('Invalid experiment configuration')
        if set(item)-{'enabled','seeds','options'}: raise ValueError('Use experiment options object for CLI overrides')
        if not item.get('enabled',True): continue
        if REGISTRY[name]['status']!='active': raise ValueError('Disabled/non-benchmark experiment '+name)
        seeds=item.get('seeds',c['seeds'])
        if not isinstance(seeds,list) or not seeds or any(type(s) is not int for s in seeds) or len(set(seeds))!=len(seeds): raise ValueError('Seeds must be unique integers')
        opts=defaults(name,c['execution_profile'])
        for k in ('warmup','repeats'):
            if k in opts and k in c and name!='keyspace': opts[k]=c[k]
        overrides=item.get('options',{})
        if not isinstance(overrides,dict): raise ValueError('options must be an object')
        if set(overrides)-set(opts): raise ValueError('Unsupported options for '+name+': '+str(set(overrides)-set(opts)))
        for k,v in overrides.items():
            if type(v) is not type(opts[k]): raise ValueError('Wrong option type: '+k)
        opts.update(overrides)
        if name=='keyspace' and c['execution_profile']!='smoke' and not {'reduced_key_bits','repeats'} <= set(overrides): raise ValueError('Keyspace pilot/study requires explicit bits and repeats')
        for k,v in opts.items():
            if isinstance(v,list):
                if not v or len(set(v))!=len(v): raise ValueError('Empty/duplicate '+k)
            if k in ('repeats','samples_per_group','reduced_key_bits','resident_iterations'): positive(v,k)
        if 'warmup' in opts and (type(opts['warmup']) is not int or opts['warmup'] < (0 if name.startswith('cuda') else 1)): raise ValueError('Invalid warmup')
        if name not in ('keyspace','avalanche','cuda_baseline') and opts['repeats']<2: raise ValueError('At least two repeats required')
        if 'sizes' in opts:
            for size in opts['sizes']: positive(size,'size')
            if max(opts['sizes'])>limits['max_workload_bytes']: raise ValueError('Workload size limit exceeded')
            if (name in ('cpu_cbc','cpu_aesni') or 'ECB' in opts.get('modes',[])) and any(s%16 for s in opts['sizes']): raise ValueError('Block alignment required')
        choices=dict(aes_backend=['software','auto'],modes=['ECB','CTR'],measurements=['resident','pipeline'],measurement=['resident','pipeline','transfer-only'],host_memory=['pinned','pageable'],variants=['plaintext','key'],algorithms=['DES','TDEA','AES-128','AES-192','AES-256'],target_position=['start','middle','end','random'],algorithm=['AES-128'],mode=['ECB'])
        choices['profile']=['baseline','optimized','ttable'] if name=='cuda_paired' else ['baseline','diagnostic'] if name=='cuda_baseline' else [c['execution_profile']]
        for k,values in choices.items():
            if k in opts and any(v not in values for v in (opts[k] if isinstance(opts[k],list) else [opts[k]])): raise ValueError('Invalid '+k)
        if name=='cpu_cbc' and c['execution_profile']=='study' and opts['aes_backend']!='software': raise ValueError('CBC study requires software')
        if name=='cpu_gcm' and (opts['warmup']+opts['repeats']>=2**32 or max(opts['sizes'])>2**36-32): raise ValueError('GCM nonce/payload limit exceeded')
        if name=='cuda_paired' and (max(opts['sizes'])>33554432 or opts['host_memory']!='pinned' or ('resident' not in opts['measurements'] and opts['resident_iterations']!=1)): raise ValueError('Invalid paired CUDA scope')
        if name=='cuda_baseline':
            if opts['profile']=='baseline' and (opts['measurement']!='pipeline' or opts['host_memory']!='pinned' or max(opts['sizes'])>33554432 or opts['resident_iterations']!=10): raise ValueError('Invalid baseline scope')
            if opts['profile']=='diagnostic' and c['execution_profile']=='study': raise ValueError('Diagnostic study prohibited')
        if name=='avalanche' and opts['samples_per_group']>{'smoke':20,'pilot':500,'study':10000}[c['execution_profile']]: raise ValueError('Sample cap exceeded')
        if name=='keyspace':
            cap=min(limits['max_key_bits'],{'smoke':12,'pilot':22,'study':28}[c['execution_profile']])
            if opts['reduced_key_bits']>cap or (2**opts['reduced_key_bits'])*opts['repeats']*len(opts['target_position'])>limits['max_key_candidates']: raise ValueError('Keyspace budget exceeded')
        resolved[name]=dict(enabled=True,seeds=seeds,options=opts)
    if not resolved: raise ValueError('No active experiments selected')
    c['experiments']=resolved
    return c


def load(path):
    return resolve(json.loads(Path(path).read_text(encoding='utf-8-sig')))
