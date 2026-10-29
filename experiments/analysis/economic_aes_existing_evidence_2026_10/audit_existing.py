"""Deterministic offline audit. Reads evidence; writes only beside this script.
No benchmark modules are imported or executed. Standard library only.
"""
import sys
sys.dont_write_bytecode = True
import csv
import hashlib
import json
import math
import statistics as st
from collections import defaultdict
from pathlib import Path
from economic_model import seconds_per_gb, cost_per_gb, decision, HOURLY_RATIOS

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
INPUTS = {}
SIZES = (1024,16384,1048576,16777216,33554432)
VARIANTS = (('cpu_software','transform'),('cpu_aesni','transform'),
            ('cuda_baseline','resident'),('cuda_baseline','pipeline'),
            ('cuda_optimized_v1','resident'),('cuda_optimized_v1','pipeline'))
REFERENCE = {1048576:(1381.7,5017.1,1313.1),16777216:(1446.5,3655.6,1103.1),33554432:(1455.8,4800.6,1204.5)}

def read(path):
    data=path.read_bytes(); INPUTS[path.relative_to(ROOT).as_posix()]=hashlib.sha256(data).hexdigest()
    return data.decode('utf-8-sig')

def js(path): return json.loads(read(path))
def csvread(path): return list(csv.DictReader(read(path).splitlines()))
def write(name,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with (OUT/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def close(a,b): return math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-15)
def fields(backend,scope):
    return ('seconds','throughput_MB_s') if backend.startswith('cpu') else (
        ('kernel_seconds','kernel_throughput_MB_s') if scope=='resident' else
        ('end_to_end_seconds','end_to_end_throughput_MB_s'))

def main():
    records=[]; sessions=[]; differences=[]
    paths=sorted((ROOT/'experiments/results').glob('aes_cuda_cpu_gpu-study-*'))
    assert len(paths)==5
    for p in paths:
        m,v=js(p/'metadata.json'),js(p/'validation.json')
        assert m['purpose']=='study' and m['validation_passed'] and v['passed'] and v['all_backends_equal']
        assert v['session_id']==m['session_id'] and v['purpose']=='study'
        assert INPUTS[(p/'validation.json').relative_to(ROOT).as_posix()]==m['validation_sha256']
        assert all(x['passed'] and x['wrap_rejected'] and len(x['tests'])==18 and all(t['passed'] for t in x['tests']) for x in v['paths'].values())
        assert all(x['passed'] for x in v['dispatch'].values())
        for mode in ('ECB','CTR'):
            for check in v['dispatch'][mode]['preflight']:
                assert check['native_start_calls']=={k:2 if k==check['requested'] else 0 for k in ('software','aesni')}
        for name,h in m['source_sha256'].items():
            read(p/'source'/name)
            assert INPUTS[(p/'source'/name).relative_to(ROOT).as_posix()]==h
        a=m['arguments']
        for k,value in dict(profile=['baseline','optimized'],measurements=['resident','pipeline'],host_memory='pinned',modes=['ECB','CTR'],sizes=list(SIZES),warmup=5,repeats=20,resident_iterations=1).items():
            assert a[k]==value,(p,k)
        raw,summary=csvread(p/'raw.csv'),csvread(p/'summary.csv')
        result=js(p/'results.json')
        # CSV/JSON serialization is checked fieldwise where lists are available.
        for key,table in [('raw',raw),('summary',summary)]:
            if key in result:
                assert len(result[key])==len(table)
                for x,y in zip(table,result[key]):
                    for k,val in y.items():
                        assert (x[k]=='' if val is None else close(x[k],val) if isinstance(val,(int,float)) and not isinstance(val,bool) else x[k]==str(val)),(p,key,k)
        assert len(raw)==1200 and len(summary)==60
        groups=defaultdict(list);pairs=defaultdict(list)
        for r in raw:
            assert r['session_id']==m['session_id'] and int(r['seed'])==m['seed']
            assert r['validation_checked']=='True' and r['algorithm']=='AES-128' and r['operation']=='encrypt'
            if r['backend'].startswith('cuda'):
                assert r['host_memory']=='pinned'
                if r['measurement']=='resident': assert r['resident_iterations']=='1'
            groups[r['backend'],r['measurement'],r['mode'],int(r['bytes'])].append(r)
            pairs[r['pair_id']].append(r)
        assert set(groups)=={(b,z,mode,n) for b,z in VARIANTS for mode in ('ECB','CTR') for n in SIZES}
        for pair in pairs.values():
            assert len(pair)==6 and len({r['pair_sha256'] for r in pair})==1
            assert {(r['backend'],r['measurement']) for r in pair}==set(VARIANTS)
        for (b,z,mode,n),g in sorted(groups.items()):
            assert sorted(int(x['repeat']) for x in g)==list(range(20))
            clock,rate=fields(b,z)
            times=[float(x[clock]) for x in g];rates=[float(x[rate]) for x in g]
            assert all(math.isfinite(t) and t>0 for t in times)
            assert all(close(r,n/1e6/t) for r,t in zip(rates,times))
            saved=next(x for x in summary if (x['backend'],x['measurement'],x['mode'],int(x['bytes']))==(b,z,mode,n))
            t,r=st.median(times),st.median(rates)
            for field,value in [(clock,t),(rate,r)]:
                assert int(saved[field+'_count'])==20
                if not close(value,saved[field+'_median']):differences.append(dict(file=str(p/'summary.csv'),field=field,calculated=value,saved=saved[field+'_median']))
            cpu=groups['cpu_aesni','transform',mode,n]
            ratio=st.median(float(x['seconds']) for x in cpu)/t
            if b.startswith('cuda'):
                assert close(ratio,saved['speedup_'+('isolated' if z=='resident' else 'pipeline')+'_vs_cpu_aesni'])
            pipeline_kernel=st.median(float(x['kernel_seconds']) for x in g) if z=='pipeline' else None
            records.append(dict(run_id=p.name,session_id=m['session_id'],seed=m['seed'],mode=mode,bytes=n,backend=b,measurement=z,
                samples=20,time_seconds=t,throughput_MB_s=r,throughput_from_median_time_MB_s=n/1e6/t,
                paired_time_speedup_vs_aesni=ratio if b.startswith('cuda') else None,
                pipeline_kernel_seconds=pipeline_kernel,
                derived_pipeline_nonkernel_fraction=(t-pipeline_kernel)/t if pipeline_kernel else None,
                median_sample_nonkernel_fraction=st.median((float(x['end_to_end_seconds'])-float(x['kernel_seconds']))/float(x['end_to_end_seconds']) for x in g) if z=='pipeline' else None,
                raw_file=(p/'raw.csv').relative_to(ROOT).as_posix()))
        sessions.append(dict(run_id=p.name,session_id=m['session_id'],seed=m['seed'],cpu=m['cpu'],gpu=m['gpu'],os=m['os'],git_commit=m['git_commit'],git_status=m['git_status'],source_sha256=m['source_sha256'],arguments=a,validation='PASS',raw_rows=len(raw)))
    assert sorted(s['seed'] for s in sessions)==list(range(2003,2008))
    assert len({s['session_id'] for s in sessions})==5
    assert all(s['source_sha256']==sessions[0]['source_sha256'] and s['gpu']==sessions[0]['gpu'] for s in sessions)
    original=csvread(ROOT/'experiments/results/aes_cuda_cpu_gpu-final-aggregate/aggregate.csv')
    aggregates=[]
    for mode in ('ECB','CTR'):
        for n in SIZES:
            for b,z in VARIANTS:
                g=[r for r in records if (r['mode'],r['bytes'],r['backend'],r['measurement'])==(mode,n,b,z)]
                rate=st.median(x['throughput_MB_s'] for x in g); t=st.median(x['time_seconds'] for x in g)
                saved=next(x for x in original if (x['mode'],int(x['bytes']),x['backend'],x['measurement'])==(mode,n,b,z))
                assert close(rate,saved['throughput_MB_s']) and close(t*1000,saved['time_ms'])
                speed=st.median(x['paired_time_speedup_vs_aesni'] for x in g) if b.startswith('cuda') else None
                if speed is not None: assert close(speed,saved['speedup_vs_cpu_aesni'])
                ref=None
                if mode=='CTR' and n in REFERENCE and (b,z) in VARIANTS[1:4]: ref=REFERENCE[n][VARIANTS[1:4].index((b,z))]
                if ref is not None and round(rate,1)!=ref: differences.append(dict(file='manuscript',field=f'{n}/{b}/{z}',calculated=rate,saved=ref))
                aggregates.append(dict(mode=mode,bytes=n,input_MiB=n/2**20,backend=b,measurement=z,sessions=5,
                    throughput_MB_s=rate,time_seconds=t,throughput_from_aggregate_median_time_MB_s=n/1e6/t,
                    median_paired_time_speedup=speed,manuscript_MB_s=ref,
                    unrounded_minus_manuscript=rate-ref if ref is not None else None,
                    manuscript_matches_one_decimal=round(rate,1)==ref if ref is not None else None,
                    saved_aggregate_matches=True,session_rate_min=min(x['throughput_MB_s'] for x in g),session_rate_max=max(x['throughput_MB_s'] for x in g)))
    assert not differences,differences
    write('RECONSTRUCTED_RESULTS.csv',aggregates)
    write('RECONSTRUCTED_SESSION_RESULTS.csv',records)
    indicators=[];thresholds=[];scenarios=[]
    ctr=[r for r in records if r['mode']=='CTR']
    for r in ctr:
        cpu=next(x for x in ctr if x['seed']==r['seed'] and x['bytes']==r['bytes'] and x['backend']=='cpu_aesni')
        indicators.append(dict(**r,seconds_per_decimal_GB=seconds_per_gb(r['throughput_MB_s']),
            normalized_cost_per_GB_at_hourly_1=cost_per_gb(r['throughput_MB_s'],1),
            throughput_ratio_vs_cpu=r['throughput_MB_s']/cpu['throughput_MB_s'],
            time_ratio_price_threshold=cpu['time_seconds']/r['time_seconds'],
            relative_time_difference_percent=(r['time_seconds']/cpu['time_seconds']-1)*100))
    for r in [x for x in aggregates if x['mode']=='CTR' and x['backend'].startswith('cuda')]:
        cpu=next(x for x in aggregates if x['mode']=='CTR' and x['bytes']==r['bytes'] and x['backend']=='cpu_aesni')
        g=[x for x in indicators if (x['bytes'],x['backend'],x['measurement'])==(r['bytes'],r['backend'],r['measurement'])]
        threshold=r['throughput_MB_s']/cpu['throughput_MB_s']
        row=dict(bytes=r['bytes'],input_MiB=r['input_MiB'],backend=r['backend'],measurement=r['measurement'],
            cpu_MB_s=cpu['throughput_MB_s'],gpu_MB_s=r['throughput_MB_s'],
            cpu_seconds_per_GB=seconds_per_gb(cpu['throughput_MB_s']),gpu_seconds_per_GB=seconds_per_gb(r['throughput_MB_s']),
            cpu_normalized_cost_per_GB=cost_per_gb(cpu['throughput_MB_s'],1),gpu_normalized_cost_per_GB_at_hourly_1=cost_per_gb(r['throughput_MB_s'],1),
            aggregate_rate_price_threshold=threshold,aggregate_time_price_threshold=cpu['time_seconds']/r['time_seconds'])
        for metric in ['time_ratio_price_threshold','throughput_ratio_vs_cpu','relative_time_difference_percent','derived_pipeline_nonkernel_fraction','median_sample_nonkernel_fraction','seconds_per_decimal_GB']:
            values=[x[metric] for x in g if x[metric] is not None]
            for suffix,fn in [('median',st.median),('min',min),('max',max),('sample_sd',st.stdev)]:row[metric+'_'+suffix]=fn(values) if values else None
        thresholds.append(row)
        for h in HOURLY_RATIOS:
            cc,cg=cost_per_gb(cpu['throughput_MB_s'],1),cost_per_gb(r['throughput_MB_s'],h)
            costs=[cost_per_gb(x['throughput_MB_s'],h) for x in g]
            scenarios.append(dict(bytes=r['bytes'],input_MiB=r['input_MiB'],backend=r['backend'],measurement=r['measurement'],cpu_hourly_normalized=1,gpu_hourly_normalized=h,
                cpu_cost_per_GB=cc,gpu_cost_per_GB=cg,lower_modeled_variable_cost=decision(cc,cg),
                gpu_session_cost_min=min(costs),gpu_session_cost_max=max(costs),
                sessions_gpu_cheaper=sum(h<x['throughput_ratio_vs_cpu'] for x in g),
                interpretation='prepared host-memory pipeline' if r['measurement']=='pipeline' else 'resident compute only; data placement costs excluded'))
    write('SESSION_ECONOMIC_INDICATORS.csv',indicators);write('ECONOMIC_THRESHOLDS.csv',thresholds);write('SENSITIVITY_ANALYSIS.csv',scenarios)
    (OUT/'reconstruction_manifest.json').write_text(json.dumps(dict(selected_sessions=sessions,input_sha256=INPUTS,discrepancies=differences,checks='PASS; 6000 raw rows; 300 session groups; 60 aggregates; nine manuscript cells',tolerance=dict(relative=1e-10,absolute=1e-15)),indent=2,sort_keys=True)+'\n')
    # Standalone SVG: no plotting dependency or external fonts; decision is based on unrounded rates.
    selected=[r for r in thresholds if r['backend']=='cuda_baseline' and r['measurement']=='pipeline']
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="960" height="460" viewBox="0 0 960 460">','<rect width="960" height="460" fill="white"/>','<g font-family="sans-serif" fill="#20252b">',
         '<text x="30" y="30" font-size="20">Conditional cost decision: baseline CUDA prepared pipeline</text>',
         '<text x="30" y="55" font-size="13">September 2026 GTX 1650 Ti / i5-10300H, AES-128-CTR; h_CPU = 1 normalized unit/hour</text>']
    x0,width,maxh=170,710,2
    for i,r in enumerate(selected):
        y=95+i*48;t=r['aggregate_rate_price_threshold'];xx=x0+width*t/maxh
        svg.extend([f'<text x="30" y="{y+22}" font-size="14">{r["input_MiB"]:g} MiB</text>',f'<rect x="{x0}" y="{y}" width="{width}" height="32" fill="#f2c7bf"/>',f'<rect x="{x0}" y="{y}" width="{width*min(t,maxh)/maxh}" height="32" fill="#b6dece"/>',f'<line x1="{xx}" x2="{xx}" y1="{y}" y2="{y+32}" stroke="#17232d"/>',f'<text x="{xx+5}" y="{y+21}" font-size="12">{t:.4f}</text>'])
    for h in (0,.5,.75,1,1.25,1.5,2):
        x=x0+width*h/maxh;svg.append(f'<text x="{x}" y="355" text-anchor="middle" font-size="12">{h:g}</text>')
    svg.extend(['<text x="400" y="382" font-size="14">GPU / CPU attributable hourly cost ratio</text>','<text x="30" y="410" font-size="13">Green: GPU lower variable cost. Red: CPU lower variable cost. Boundary: equal.</text>','<text x="30" y="435" font-size="12">Threshold = ratio of unrounded aggregate throughput medians; session variation in CSV. No market or energy costs.</text>','</g></svg>'])
    (OUT/'sensitivity_decision.svg').write_text('\n'.join(svg),encoding='utf-8')
    print('PASS: 5 historical sessions, 6000 rows, 60 aggregates, nine manuscript cells; outputs only in',OUT)

if __name__=='__main__': main()
