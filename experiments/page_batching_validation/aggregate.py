"""Explicit boundary summaries, matched-message ratios, and session-level distributions."""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics as st

BOUNDARIES={'cpu':('cpu_transform_ns','cpu_operation_ns'),
            'resident':('kernel_ns',),'pipeline':('end_to_end_ns','transfer_ns')}
COMPARISONS={'prepared_cpu_transform_over_gpu_pipeline':('cpu_transform_ns','end_to_end_ns'),
             'compute_only_cpu_transform_over_gpu_resident':('cpu_transform_ns','kernel_ns'),
             'asymmetric_cpu_operation_over_prepared_gpu_pipeline':('cpu_operation_ns','end_to_end_ns')}


def stats(values):
    values=list(values)
    q1,_,q3=st.quantiles(values,n=4,method='inclusive') if len(values)>1 else [values[0]]*3
    mean=st.mean(values)
    sd=st.stdev(values) if len(values)>1 else 0
    return dict(n=len(values),median=st.median(values),mean=mean,stdev=sd,min=min(values),max=max(values),
        cv=sd/mean if mean else None,q1=q1,q3=q3,
        outliers=sum(v<q1-1.5*(q3-q1) or v>q3+1.5*(q3-q1) for v in values))


def summarize(rows):
    if not rows or len({(r['session_id'],r['seed']) for r in rows})!=1:
        raise ValueError('One session only; never pair independent datasets')
    pairs=defaultdict(dict)
    seen=set()
    for r in rows:
        key=(r['pages'],r['repeat'],r['layout'])
        if (key,r['measurement']) in seen or not r['validated']:
            raise ValueError('Duplicate or invalid observation')
        seen.add((key,r['measurement']))
        if r['bytes']!=r['pages']*(1<<20) or r['warmup']!=(r['repeat']<0):
            raise ValueError('Invalid size/warmup')
        for boundary in BOUNDARIES[r['measurement']]:
            if not math.isfinite(r[boundary]) or r[boundary]<=0:
                raise ValueError('Invalid elapsed time')
        pairs[key][r['measurement']]=r
    times=defaultdict(list); ratios=defaultdict(list); contrasts=defaultdict(list)
    compact={}
    for (pages,repeat,layout), jobs in pairs.items():
        if set(jobs)!={'cpu','resident','pipeline'} or len({j['pair_hash'] for j in jobs.values()})!=1:
            raise ValueError('Incomplete or mismatched ciphertext pair')
        if len({j['plaintext_sha256'] for j in jobs.values()})!=1:
            raise ValueError('Mismatched plaintext')
        if repeat<0:
            continue
        values={b:jobs[m][b] for m,bs in BOUNDARIES.items() for b in bs}
        compact[pages,repeat,layout]=(values,jobs['cpu']['plaintext_sha256'])
        for boundary,value in values.items():
            times[pages,layout,boundary].append(value)
        for label,(num,den) in COMPARISONS.items():
            ratios[pages,layout,label].append(values[num]/values[den])
    for (pages,repeat,layout),(values,datahash) in compact.items():
        if layout!='pages':
            continue
        other=compact.get((pages,repeat,'continuous'))
        if other is None or datahash!=other[1]:
            raise ValueError('Missing equal-data continuous control')
        for b,t in values.items():
            contrasts[pages,b].append(other[0][b]/t)
    summaries=[dict(pages=p,layout=l,boundary=b,latency_ns=stats(v),
        throughput_MB_s=stats(p*(1<<20)*1e3/t for t in v)) for (p,l,b),v in sorted(times.items())]
    comparisons=[]
    for (p,l,label),v in sorted(ratios.items()):
        n,d=COMPARISONS[label]
        comparisons.append(dict(pages=p,layout=l,comparison=label,paired_ratios=stats(v),
            ratio_of_medians=st.median(times[p,l,n])/st.median(times[p,l,d])))
    scaling=[]
    for (p,l,b),v in sorted(times.items()):
        baseline=times.get((1,l,b))
        if baseline:
            scaling.append(dict(pages=p,layout=l,boundary=b,
                throughput_gain_over_one_page=p*st.median(baseline)/st.median(v)))
    return dict(boundaries=summaries,speedups=comparisons,batch_scaling=scaling,
        page_over_continuous_throughput=[dict(pages=p,boundary=b,paired_ratios=stats(v))
                                       for (p,b),v in sorted(contrasts.items())])


def load(path):
    meta=json.loads((path/'metadata.json').read_text())
    if meta['status']!='complete':
        raise ValueError('Incomplete session')
    rows=[json.loads(s) for s in (path/'raw.jsonl').read_text().splitlines()]
    from protocol import schedule
    expected=schedule(meta['seed'],meta['warmups'],meta['repeats'])
    if len(rows)!=len(expected) or any(any(r[k]!=v for k,v in job.items()) for r,job in zip(rows,expected)):
        raise ValueError('Protocol/order/count mismatch')
    if any(r['session_id']!=meta['session_id'] or r['seed']!=meta['seed'] for r in rows):
        raise ValueError('Session metadata mismatch')
    return meta,summarize(rows)


def campaign(paths):
    sessions=[load(Path(p)) for p in paths]
    if sorted(m['seed'] for m,s in sessions)!=list(range(2003,2008)):
        raise ValueError('Exactly five independent study seeds required')
    if len({m['fingerprint'] for m,s in sessions})!=1 or len({m['session_id'] for m,s in sessions})!=5:
        raise ValueError('Runtime/provenance mismatch or repeated session')
    if any(m['profile']!='study' or m['warmups']!=5 or m['repeats']!=20 for m,s in sessions):
        raise ValueError('Full study protocol required')
    groups=defaultdict(list)
    for m,s in sessions:
        for row in s['speedups']:
            for estimator,value in [('median_paired_ratio',row['paired_ratios']['median']),
                                    ('ratio_of_medians',row['ratio_of_medians'])]:
                groups[row['pages'],row['layout'],row['comparison'],estimator].append(value)
    latency=defaultdict(list); throughput=defaultdict(list); controls=defaultdict(list)
    for m,s in sessions:
        for row in s['boundaries']:
            key=(row['pages'],row['layout'],row['boundary'])
            latency[key].append(row['latency_ns']['median'])
            throughput[key].append(row['throughput_MB_s']['median'])
        for row in s['page_over_continuous_throughput']:
            controls[row['pages'],row['boundary']].append(row['paired_ratios']['median'])
    return dict(session_ids=[m['session_id'] for m,s in sessions],
        boundaries=[dict(pages=p,layout=l,boundary=b,session_latency_ns=stats(v),
                        session_throughput_MB_s=stats(throughput[p,l,b])) for (p,l,b),v in sorted(latency.items())],
        page_over_continuous_throughput=[dict(pages=p,boundary=b,session_distribution=stats(v))
                                        for (p,b),v in sorted(controls.items())],speedups=[
        dict(pages=p,layout=l,comparison=c,estimator=e,session_distribution=stats(v),
             favorable_sessions=sum(x>1 for x in v)) for (p,l,c,e),v in sorted(groups.items())])


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('sessions',nargs='+',type=Path)
    args=parser.parse_args()
    print(json.dumps(load(args.sessions[0])[1] if len(args.sessions)==1 else campaign(args.sessions),indent=2))
