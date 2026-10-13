"""Explicit within-platform session aggregation; never pools raw observations."""
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from .artifacts import read, check
from .runner import verify_suite, write, identifier, lock

DIMENSIONS=('algorithm','backend','profile','mode','bytes','operation','measurement','host_memory','resident_iterations','variant','scenario','reduced_key_bits','keyspace_size')


def summarize_sessions(records):
    groups=defaultdict(list)
    for record in records:
        row=record['summary']
        dimensions={k:row[k] for k in DIMENSIONS if k in row}
        key=json.dumps(dict(experiment=record['experiment'],**dimensions),sort_keys=True)
        for field,value in row.items():
            if value is not None and (field.endswith('_median') or field.startswith('speedup_') or field in ('median','median_normalized')):
                groups[(key,field)].append((record['seed'],float(value)))
    output=[]; variability=[]
    for (key,metric),values in sorted(groups.items()):
        check(len({seed for seed,_ in values})==len(values),'Duplicate session seed in aggregation')
        dimensions=json.loads(key); numbers=[n for _,n in values]
        row=dict(**dimensions,metric=metric,sessions=len(numbers),median_of_sessions=statistics.median(numbers))
        output.append(row)
        variability.append(dict(row,min_session=min(numbers),max_session=max(numbers),session_stdev=statistics.stdev(numbers) if len(numbers)>1 else None,seeds=[s for s,_ in values]))
    return output,variability


def csvwrite(path, rows):
    fields=list(dict.fromkeys(k for row in rows for k in row)) or ['experiment','metric','sessions','median_of_sessions']
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def aggregate(directory):
    directory=Path(directory).resolve()
    with lock(directory/'execution.lock'):
        validation=verify_suite(directory)
        check(validation['passed'],'Suite incomplete; aggregation requires completed or explicitly skipped tasks')
        status=read(directory/'status.json'); config=read(directory/'config.resolved.json'); records=[]
        for key,task in status['tasks'].items():
            if task['state']!='COMPLETED': continue
            name,seed=key.split('/seed-')
            for row in read(directory/'experiments'/name/('seed-'+seed)/'native/results.json')['summary']:
                records.append(dict(experiment=name,seed=int(seed),summary=row))
        check(bool(records),'No successful measurements to aggregate')
        rows,variability=summarize_sessions(records)
        target=directory/'aggregates'/identifier(); target.mkdir()
        write(target/'summary.json',dict(policy='Median of session-level medians; speedups are median of within-session timing ratios; no raw pooling. Decimal MB/s.',fingerprint=read(directory/'manifest.json')['fingerprint'],execution_profile=config['execution_profile'],limitations=['No cross-platform pooling or historical import.','No inference of timing reliability from correctness.','Only native medians and native paired ratios are aggregated. Quantiles, means, extrapolation tables and confidence intervals are not combined.','Session stdev is descriptive; null for one session.'],rows=rows))
        csvwrite(target/'summary.csv',rows)
        csvwrite(target/'paired_speedups.csv',[r for r in rows if r['metric'].startswith('speedup_')])
        csvwrite(target/'session_variability.csv',variability)
        write(target/'validation_summary.json',validation)
        return target
