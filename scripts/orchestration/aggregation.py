"""Explicit within-platform session aggregation; never pools raw observations."""
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from .artifacts import read, check, expected_groups
from .metrics import POLICY_VERSION, is_metric, validate_metrics
from .runner import verify_suite, write, identifier, lock

DIMENSIONS=('algorithm','backend','profile','mode','bytes','operation','measurement','host_memory','resident_iterations','variant','scenario','reduced_key_bits','keyspace_size')


def summarize_sessions(records, config=None, *, require_complete=None):
    """Aggregate exact configured seed sets; retain the old helper API for callers.

    Suite exports always supply the immutable resolved config. The config-free
    helper is descriptive only and infers expectations from the supplied records.
    """
    if require_complete is None:
        require_complete = config is not None and config['execution_profile']=='study'
    seed_sets = {n:set(item['seeds']) for n,item in config['experiments'].items()} if config else {
        n:{r['seed'] for r in records if r['experiment']==n} for n in {r['experiment'] for r in records}}
    if config:
        for name,item in config['experiments'].items():
            check(bool(item['seeds']) and len(seed_sets[name])==len(item['seeds']),'Empty or duplicate configured seeds: '+name)
    groups=defaultdict(list); contracts={}; observed_groups=defaultdict(set); signatures={}
    for record in records:
        row=record['summary']; name=record['experiment']; seed=record['seed']
        check(name in seed_sets and seed in seed_sets[name],'Unexpected experiment or seed in aggregation')
        dimensions={k:row[k] for k in DIMENSIONS if k in row}
        key=json.dumps(dict(experiment=name,**dimensions),sort_keys=True)
        if config:
            fields,expected=expected_groups(name,config['experiments'][name]['options'])
            group=tuple(row[k] for k in fields)
            check(group in expected,'Unexpected metric group: '+name)
            check(group not in observed_groups[(name,seed)],'Duplicate summary observation: '+name+'/'+str(seed))
            observed_groups[(name,seed)].add(group)
            check(signatures.setdefault((name,group),key)==key,'Inconsistent session execution scopes: '+name)
            required,optional=validate_metrics(name,row)
            contracts[key]=(required,optional)
            # Include explicitly optional missing metrics as null, flagged records.
            for field in required | set(optional): groups[(key,field)]
        for field,value in row.items():
            if value is not None and is_metric(field):
                groups[(key,field)].append((seed,float(value)))
    if config:
        for name,item in config['experiments'].items():
            _,expected=expected_groups(name,item['options'])
            for seed in item['seeds']:
                actual=observed_groups.get((name,seed),set())
                # A wholly absent session may be pending/skipped in a partial
                # development suite. A present session must contain every group.
                check(not actual or actual==set(expected),'Incomplete metric groups: '+name+'/'+str(seed))
                if require_complete: check(actual==set(expected),'Missing configured session: '+name+'/'+str(seed))
    output=[]; variability=[]
    for (key,metric),values in sorted(groups.items()):
        check(len({seed for seed,_ in values})==len(values),'Duplicate session seed in aggregation')
        dimensions=json.loads(key); numbers=[n for _,n in values]
        expected=seed_sets[dimensions['experiment']]; observed={s for s,_ in values}; missing=sorted(expected-observed)
        required,optional=contracts.get(key,({metric},{}))
        is_required=metric in required
        if require_complete and is_required: check(not missing,'Incomplete required metric: '+key+'/'+metric)
        row=dict(**dimensions,metric=metric,sessions=len(numbers),median_of_sessions=statistics.median(numbers) if numbers else None,
                 expected_sessions=len(expected),observed_sessions=len(observed),missing_seeds=missing,complete=not missing,
                 required=is_required,optional_reason=optional.get(metric))
        output.append(row)
        variability.append(dict(row,min_session=min(numbers) if numbers else None,max_session=max(numbers) if numbers else None,session_stdev=statistics.stdev(numbers) if len(numbers)>1 else None,seeds=[s for s,_ in values]))
    return output,variability


def csvwrite(path, rows):
    fields=list(dict.fromkeys(k for row in rows for k in row)) or ['experiment','metric','sessions','median_of_sessions']
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def aggregate(directory):
    directory=Path(directory).resolve()
    with lock(directory/'execution.lock'):
        validation=verify_suite(directory)
        status=read(directory/'status.json'); config=read(directory/'config.resolved.json'); records=[]
        check(validation['scientific_completeness']!='invalid','Scientific integrity verification failed: '+str(validation.get('errors',[])))
        if config['execution_profile']=='study':
            check(validation['scientific_completeness']=='complete','Publication-quality study aggregation requires scientific_completeness=complete')
        for key,task in status['tasks'].items():
            if task['state']!='COMPLETED': continue
            name,seed=key.split('/seed-')
            for row in read(directory/'experiments'/name/('seed-'+seed)/'native/results.json')['summary']:
                records.append(dict(experiment=name,seed=int(seed),summary=row))
        check(bool(records),'No successful measurements to aggregate')
        rows,variability=summarize_sessions(records,config)
        target=directory/'aggregates'/identifier(); target.mkdir()
        write(target/'summary.json',dict(schema_version=2,metric_policy_version=POLICY_VERSION,
              scientific_completeness=validation['scientific_completeness'],publication_quality=config['execution_profile']=='study' and validation['scientific_completeness']=='complete',
              publication_quality_definition='Dataset completeness and integrity only; not statistical or scientific publication readiness.',
              expected_seeds={n:item['seeds'] for n,item in config['experiments'].items()},missing_measurements=validation['missing_measurements'],
              policy='Median of session-level medians; speedups are median of within-session timing ratios; no raw pooling. Decimal MB/s.',fingerprint=read(directory/'manifest.json')['fingerprint'],execution_profile=config['execution_profile'],limitations=['No cross-platform pooling or historical import.','No inference of timing reliability from correctness.','Only native medians and native paired ratios are aggregated. Quantiles, means, extrapolation tables and confidence intervals are not combined.','Session stdev is descriptive; null for one session.','Publication quality here means dataset completeness and integrity, not methodological endorsement.'],rows=rows))
        csvwrite(target/'summary.csv',rows)
        csvwrite(target/'paired_speedups.csv',[r for r in rows if r['metric'].startswith('speedup_')])
        csvwrite(target/'session_variability.csv',variability)
        write(target/'validation_summary.json',validation)
        return target
