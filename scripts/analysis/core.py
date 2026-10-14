"""Independent CSV estimators and strict paired-study contracts (standard library)."""
import csv
import hashlib
import itertools
import json
import math
import statistics as st
import tarfile
import zipfile
from collections import defaultdict
from pathlib import Path, PurePosixPath

SEEDS = list(range(2003, 2008))
SIZES = [1024, 16384, 1048576, 16777216, 33554432]
BACKENDS = ['cpu_software', 'cpu_aesni', 'cuda_baseline', 'cuda_optimized_v1']
METRICS = ['kernel_throughput_MB_s', 'end_to_end_throughput_MB_s', 'kernel_seconds',
           'end_to_end_seconds', 'h2d_ns', 'kernel_ns', 'd2h_ns', 'transfer_ns',
           'end_to_end_ns', 'wall_elapsed_ns', 'seconds', 'throughput_MB_s',
           'process_cpu_ns', 'process_to_wall_ratio', 'resident_batch_ns']
DIMS = ['algorithm','backend','profile','mode','bytes','measurement','host_memory','resident_iterations']
RTOL, ATOL = 1e-10, 1e-15
ACTIVE_SOURCES = ['aes_cuda_cpu_gpu.py','aes_cuda_baseline.py','aes_acceleration.py',
                  'common.py','benchmark.py','cpu_validation.py','aes_cuda_baseline.cu',
                  'aes_cuda_optimized.cu','aes_cuda_ttable.cu']


def require(ok, message):
    if not ok: raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''): h.update(block)
    return h.hexdigest()


def inventory(root):
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(Path(root).rglob('*')) if p.is_file()}


def cell(value):
    if value == '': return None
    if value in ('True','False'): return value == 'True'
    try: return int(value)
    except ValueError:
        try: return float(value)
        except ValueError: return value


def csvread(path):
    with Path(path).open(encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames and len(set(reader.fieldnames)) == len(reader.fieldnames), 'Duplicate/empty CSV columns')
        rows = []
        for row in reader:
            require(None not in row and all(v is not None for v in row.values()), 'Malformed CSV row')
            rows.append({k:cell(v) for k,v in row.items()})
        return rows


def csvwrite(path, rows, fields=None):
    fields = fields or list(dict.fromkeys(k for row in rows for k in row))
    with Path(path).open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for row in rows:
            writer.writerow({k:json.dumps(v,sort_keys=True) if isinstance(v,(dict,list)) else v for k,v in row.items()})


def quantile(values, p):
    v = sorted(values); pos = (len(v)-1)*p; lo = int(pos); hi = min(lo+1,len(v)-1)
    return v[lo] + (v[hi]-v[lo])*(pos-lo)


def stats(values):
    keys = ['count','mean','median','stdev','min','max','q1','q3','iqr','coefficient_of_variation','outlier_count','outlier_flag']
    if not values: return dict.fromkeys(keys)
    require(all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in values), 'Nonfinite/nonnumeric observations')
    mean = st.mean(values); sd = st.stdev(values) if len(values)>1 else None
    q1,q3 = quantile(values,.25),quantile(values,.75); iqr = q3-q1
    out = sum(v<q1-1.5*iqr or v>q3+1.5*iqr for v in values)
    return dict(count=len(values),mean=mean,median=st.median(values),stdev=sd,min=min(values),max=max(values),
                q1=q1,q3=q3,iqr=iqr,coefficient_of_variation=sd/mean if sd is not None and mean else None,
                outlier_count=out,outlier_flag=bool(out))


def close(a,b):
    if a is None or b is None: return a is b
    if isinstance(a,bool) or isinstance(b,bool): return type(a)==type(b) and a==b
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):
        return math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,rel_tol=RTOL,abs_tol=ATOL)
    return a==b


def group(row):
    return tuple(row[k] for k in ('backend','measurement','mode','bytes'))


def expected_groups(sizes=SIZES, modes=('ECB','CTR')):
    jobs=[('cpu_software','transform'),('cpu_aesni','transform')]+list(itertools.product(BACKENDS[2:],['resident','pipeline']))
    return {(b,m,mode,size) for (b,m),mode,size in itertools.product(jobs,modes,sizes)}


def recompute(raw, seed, sizes=SIZES, repeats=20, modes=('ECB','CTR')):
    """All estimates originate from CSV rows, independently of saved summaries."""
    groups=defaultdict(list); pairs=defaultdict(list); sessions=set()
    require(len(raw)==len(expected_groups(sizes,modes))*repeats,'Wrong raw row count')
    for r in raw:
        require(r['seed']==seed and r['algorithm']=='AES-128' and r['operation']=='encrypt','Wrong raw identity')
        require(r['validation_checked'] is True,'Unchecked measurement')
        require(all(k in r for k in METRICS),'Missing raw metric column')
        sessions.add(r['session_id']); groups[group(r)].append(r); pairs[r['pair_id']].append(r)
        require(r['pair_id']==f"{r['bytes']}:{r['mode']}:{r['repeat']}",'Wrong pair ID')
        cpu=r['backend'].startswith('cpu_'); resident=r['measurement']=='resident'
        require(r['host_memory']==('bytes' if cpu else 'pinned'),'Wrong memory scope')
        require(r['resident_iterations']==(1 if resident else None),'Wrong resident iteration scope')
        require(r['profile']==dict(cpu_software='software',cpu_aesni='aesni',cuda_baseline='baseline',cuda_optimized_v1='optimized').get(r['backend']),'Wrong kernel profile')
        active = {'wall_elapsed_ns','seconds','throughput_MB_s','process_cpu_ns','process_to_wall_ratio'} if cpu else {'kernel_ns','kernel_seconds','kernel_throughput_MB_s'}
        active |= {'resident_batch_ns'} if resident else set() if cpu else {'h2d_ns','d2h_ns','transfer_ns','end_to_end_ns','end_to_end_seconds','end_to_end_throughput_MB_s'}
        require(all((r[k] is not None)==(k in active) for k in METRICS),'Null/scope contamination')
        for k in active: require(math.isfinite(r[k]) and r[k]>=0,'Invalid raw metric '+k)
        ns=r['wall_elapsed_ns'] if cpu else r['kernel_ns']
        require(ns>0,'Nonpositive primary timer')
        formulas={'seconds':ns/1e9,'throughput_MB_s':r['bytes']*1e3/ns,'process_to_wall_ratio':r['process_cpu_ns']/ns} if cpu else {'kernel_seconds':ns/1e9,'kernel_throughput_MB_s':r['bytes']*1e3/ns}
        if resident: formulas['resident_batch_ns']=ns
        elif not cpu:
            require(r['end_to_end_ns']>0,'Nonpositive pipeline timer')
            formulas.update(end_to_end_seconds=r['end_to_end_ns']/1e9,end_to_end_throughput_MB_s=r['bytes']*1e3/r['end_to_end_ns'],transfer_ns=r['h2d_ns']+r['d2h_ns'])
        for k,v in formulas.items(): require(close(r[k],v),'Raw units/formula mismatch: '+k)
    require(len(sessions)==1,'Mixed native sessions')
    require(set(groups)==expected_groups(sizes,modes),'Missing/unexpected raw groups')
    require([r['global_order'] for r in raw]==list(range(len(raw))),'Duplicate/out-of-order global observations')
    for observations in pairs.values():
        require(len(observations)==6 and len({r['pair_sha256'] for r in observations})==1,'Broken paired input identity')
        require({r['job_order'] for r in observations}==set(range(6)),'Duplicate job order')
    summaries=[]; repetitions=[]
    for key,observations in sorted(groups.items()):
        require(len(observations)==repeats and {r['repeat'] for r in observations}==set(range(repeats)),'Duplicate/missing repeat')
        row={k:observations[0][k] for k in ['session_id','seed',*DIMS]}
        for metric in METRICS:
            s=stats([r[metric] for r in observations if r[metric] is not None])
            row.update({metric+'_'+k:v for k,v in s.items()})
            if s['count']: repetitions.append(dict(**{k:row[k] for k in ['seed','session_id',*DIMS]},metric=metric,**s))
        summaries.append(row)
    bykey={group(r):r for r in summaries}
    for row in summaries:
        for cpu in BACKENDS[:2]:
            for scope in ('isolated','pipeline'): row['speedup_'+scope+'_vs_'+cpu]=None
            if row['backend'].startswith('cuda_'):
                resident=row['measurement']=='resident';scope='isolated' if resident else 'pipeline'
                row['speedup_'+scope+'_vs_'+cpu]=bykey[(cpu,'transform',row['mode'],row['bytes'])]['seconds_median']/row['kernel_seconds_median' if resident else 'end_to_end_seconds_median']
    return summaries,repetitions


def session_aggregate(sessions):
    require(set(sessions)==set(SEEDS),'Expected exactly five configured seeds')
    groups=defaultdict(list)
    for seed,rows in sessions.items():
        require(len(rows)==len({group(r) for r in rows}),'Duplicate summary group')
        for r in rows:
            for metric,value in r.items():
                if (metric.endswith('_median') or metric.startswith('speedup_')) and value is not None:
                    groups[(group(r),metric)].append((seed,value,r))
    result=[]
    for (key,metric),values in sorted(groups.items()):
        require(sorted(s for s,_,_ in values)==SEEDS,'Missing session-level metric')
        s=stats([v for _,v,_ in values]);r=values[0][2]
        result.append(dict(**{k:r[k] for k in DIMS},metric=metric,expected_sessions=5,observed_sessions=5,
                           missing_seeds=[],complete=True,seeds=SEEDS,median_of_sessions=s['median'],
                           **{'session_'+k:v for k,v in s.items()}))
    return result


def compare_rows(saved, expected, keys, source, discrepancies, fields=None):
    key=lambda r:tuple(r.get(k) for k in keys)
    actual={key(r):r for r in saved}; wanted={key(r):r for r in expected}
    require(len(actual)==len(saved),'Duplicate saved records: '+source)
    require(set(actual)==set(wanted),'Missing/unexpected saved records: '+source)
    for ident,row in wanted.items():
        for field in fields or row.keys():
            v=row[field];got=actual[ident].get(field)
            if field not in actual[ident] or not close(got,v):
                discrepancies.append(dict(source=source,group=str(ident),field=field,saved=got,recomputed=v,
                                          absolute_error=abs(got-v) if isinstance(got,(int,float)) and isinstance(v,(int,float)) else None))


def extract_archive(archive, target, max_bytes=4*1024**3):
    """Preserve PAX/GNU long names; return a byte-verified extraction receipt."""
    target=Path(target); target.mkdir(parents=True,exist_ok=True); seen=set(); total=0; files={}; pax_paths=0
    def destination(name,size):
        nonlocal total
        path=PurePosixPath(name.replace('\\','/'))
        require(not path.is_absolute() and '..' not in path.parts and not any(':' in p for p in path.parts),'Unsafe archive path')
        key=str(path).casefold();require(key not in seen,'Duplicate archive path');seen.add(key)
        total+=size;require(total<=max_bytes,'Archive size limit exceeded')
        dest=target.joinpath(*path.parts);require(dest.resolve().is_relative_to(target.resolve()),'Archive traversal')
        dest.parent.mkdir(parents=True,exist_ok=True);return dest
    def copy_verified(src,dest,name,size):
        h=hashlib.sha256(); written=0
        with dest.open('xb') as out:
            for block in iter(lambda:src.read(1024*1024),b''):
                out.write(block);h.update(block);written+=len(block)
        require(written==size and sha(dest)==h.hexdigest(),'Extracted bytes differ from archive member')
        files[name]=dict(bytes=size,sha256=h.hexdigest())
    if zipfile.is_zipfile(archive):
        archive_format='zip'
        with zipfile.ZipFile(archive) as z:
            for item in z.infolist():
                if item.is_dir(): continue
                require((item.external_attr>>16)&0o170000 != 0o120000,'Archive symlink rejected')
                dest=destination(item.filename,item.file_size)
                with z.open(item) as src:copy_verified(src,dest,item.filename,item.file_size)
    else:
        archive_format='tar'
        with tarfile.open(archive) as t:
            for item in t:
                if item.isdir(): continue
                require(item.isfile(),'Nonregular tar entry rejected');dest=destination(item.name,item.size)
                pax_paths+=int('path' in item.pax_headers)
                with t.extractfile(item) as src:copy_verified(src,dest,item.name,item.size)
    return dict(format=archive_format,regular_files=len(files),raw_csv_files=sum(n.endswith('/raw.csv') for n in files),
                source_snapshots=sum('/source/' in n for n in files),pax_path_records=pax_paths,
                maximum_member_path_characters=max((len(n) for n in files),default=0),files=files)
