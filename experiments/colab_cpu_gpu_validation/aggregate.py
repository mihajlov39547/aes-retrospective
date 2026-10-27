"""Within-session pairing by identity/boundary; session-level campaign consistency only."""
import argparse
import csv
import json
import math
from pathlib import Path
from statistics import median, mean, stdev, quantiles

from protocol import SCHEMA, SEEDS, SIZES, JOBS, CPU_BACKENDS, GPU_BACKENDS, COMPARISONS


def require(condition, message):
    if not condition:
        raise ValueError(message)


def statistics(values, positive_only=True):
    values = list(values)
    require(bool(values) and all(math.isfinite(v) and (v > 0 or not positive_only) for v in values), 'Invalid measurement')
    q1, _, q3 = quantiles(values, n=4, method='inclusive') if len(values) > 1 else [values[0]]*3
    sd = stdev(values) if len(values) > 1 else None
    return dict(count=len(values), median=median(values), mean=mean(values),
                sample_sd=sd, min=min(values), max=max(values), q1=q1, q3=q3, iqr=q3-q1,
                cv=sd/mean(values) if sd is not None and mean(values) != 0 else None,
                outlier_count=sum(v < q1-1.5*(q3-q1) or v > q3+1.5*(q3-q1) for v in values))


def duration(row, field):
    value = float(row[field])
    require(math.isfinite(value) and value > 0, f'Invalid {field}')
    return value


def summarize(rows, meta):
    require(meta['status'] == 'complete', 'Failed/incomplete session')
    require(meta['schema_version'] == SCHEMA and meta['workers'] == 1, 'Unsupported schema/thread policy')
    expected = {(size, mode, rep, backend, measurement) for size in meta['sizes'] for mode in ('CTR', 'ECB')
                for rep in range(-meta['warmups'], meta['repetitions']) for backend, measurement in JOBS}
    seen, pairs, groups = set(), {}, {}
    for row in rows:
        for field in ('session_id', 'campaign_id', 'runtime_fingerprint'):
            require(row[field] == meta[field], f'Mixed {field}')
        require(int(row['schema_version']) == SCHEMA and int(row['seed']) == meta['seed'], 'Protocol/seed mismatch')
        size, repeat = int(row['bytes']), int(row['repeat'])
        key = (size, row['mode'], repeat, row['backend'], row['measurement'])
        require(key in expected and key not in seen, 'Unexpected/duplicate job')
        seen.add(key)
        require(str(row['validation_passed']).lower() == 'true', 'Unvalidated row')
        require((str(row['warmup']).lower() == 'true') == (repeat < 0), 'Warmup label mismatch')
        require(row['pair_id'] == f'{meta["seed"]}:{size}:{row["mode"]}:{repeat}', 'Wrong pair ID')
        require(len(row['pair_hash']) == 64 and all(c in '0123456789abcdef' for c in row['pair_hash']), 'Invalid pair hash')
        identity = (size, row['mode'], repeat)
        if identity in pairs:
            require(pairs[identity] == row['pair_hash'], 'Independently generated inputs cannot be paired')
        pairs[identity] = row['pair_hash']
        if row['measurement'] == 'cpu':
            fields = ['cpu_transform_ns', 'cpu_operation_ns']
            require(int(row['operation_end_ns']) - int(row['operation_start_ns']) == int(row['cpu_operation_ns']),
                    'CPU operation envelope differs from timestamps')
            require(float(row['transform_ns']) == float(row['cpu_transform_ns']), 'Transform alias mismatch')
        elif row['measurement'] == 'resident':
            fields = ['gpu_resident_ns']
            require(float(row['resident_batch_ns']) == float(row['gpu_resident_ns']), 'Expected one resident launch')
        else:
            fields = ['gpu_pipeline_ns']
            require(int(row['h2d_ns']) + int(row['d2h_ns']) == int(row['transfer_ns']), 'Transfer component mismatch')
            require(float(row['transfer_ns']) <= float(row['gpu_pipeline_ns']), 'Transfers exceed pipeline')
            duration(row, 'gpu_pipeline_kernel_ns')
        for field in fields:
            value = duration(row, field)
            if repeat >= 0:
                groups.setdefault((size, row['mode'], row['backend'], field), {})[repeat] = value
    require(seen == expected, 'Incomplete session/configuration')
    summaries, speedups = [], []
    common = {k: meta[k] for k in ('session_id', 'campaign_id', 'runtime_fingerprint', 'seed')}
    for (size, mode, backend, boundary), samples in sorted(groups.items()):
        summaries.append(dict(**common, bytes=size, mode=mode, backend=backend, boundary=boundary,
            throughput_MB_s_at_median=size*1000/median(samples.values()), **statistics(samples.values())))
    for size in meta['sizes']:
        for mode in ('ECB', 'CTR'):
            for name, (cpu_field, gpu_field) in COMPARISONS.items():
                for cpu in CPU_BACKENDS:
                    for gpu in GPU_BACKENDS:
                        numerator = groups[(size, mode, cpu, cpu_field)]
                        denominator = groups[(size, mode, gpu, gpu_field)]
                        ratios = [numerator[r] / denominator[r] for r in range(meta['repetitions'])]
                        speedups.append(dict(**common, bytes=size, mode=mode, cpu=cpu, gpu=gpu,
                            comparison=name, cpu_boundary=cpu_field, gpu_boundary=gpu_field,
                            primary=name == 'prepared_cpu_transform_over_gpu_pipeline' and gpu == 'cuda_baseline' and cpu == 'openssl_default',
                            ratio_of_medians=median(numerator.values()) / median(denominator.values()),
                            favorable_repetitions=sum(r > 1 for r in ratios), **statistics(ratios)))
    return summaries, speedups


def write_table(output, name, rows):
    for suffix in ('json', 'csv'):
        require(not (output / f'{name}.{suffix}').exists(), 'Output exists; refusing overwrite')
    with (output / f'{name}.json').open('x', encoding='utf-8') as f:
        json.dump(rows, f, indent=2, allow_nan=False)
    with (output / f'{name}.csv').open('x', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load_session(directory):
    meta = json.loads((directory / 'metadata.json').read_text(encoding='utf-8'))
    gate = json.loads((directory / 'validation.json').read_text(encoding='utf-8'))
    require(gate.get('passed') is True, 'Correctness gate not passed')
    with (directory / 'raw.csv').open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    return meta, rows


def component_summary(rows):
    groups = {}
    fields = ('allocation_ns', 'setup_ns', 'cleanup_ns', 'buffer_binding_ns', 'ffi_noop_ns',
              'native_call_ns', 'ffi_residual_ns', 'h2d_ns', 'd2h_ns', 'transfer_ns', 'gpu_pipeline_kernel_ns')
    for row in rows:
        if int(row['repeat']) < 0:
            continue
        values = {field: float(row[field]) for field in fields if row.get(field) not in ('', None)}
        if row['measurement'] == 'cpu':
            accounted = ('allocation_ns', 'setup_ns', 'transform_ns', 'cleanup_ns') if row['backend'] == 'pycryptodome' else (
                'allocation_ns', 'buffer_binding_ns', 'ffi_noop_ns', 'native_call_ns')
            if all(row.get(k) not in ('', None) for k in accounted):
                values['operation_remainder_ns'] = float(row['cpu_operation_ns']) - sum(float(row[k]) for k in accounted)
        for field, value in values.items():
            key = (int(row['bytes']), row['mode'], row['backend'], row['measurement'], field)
            groups.setdefault(key, []).append(value)
    return [dict(bytes=k[0], mode=k[1], backend=k[2], measurement=k[3], component=k[4],
                 **statistics(v, positive_only=False)) for k, v in sorted(groups.items())]


def aggregate_session(directory, output):
    meta, rows = load_session(Path(directory))
    summaries, speedups = summarize(rows, meta)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    write_table(output, 'summary', summaries)
    write_table(output, 'speedups', speedups)
    components = component_summary(rows)
    if components:
        write_table(output, 'components', components)
    return summaries, speedups


def campaign_summary(sessions):
    require(len(sessions) == 5 and sorted(m['seed'] for m, _ in sessions) == SEEDS, 'Exactly five distinct study seeds required')
    require(len({m['session_id'] for m, _ in sessions}) == 5, 'Duplicate session')
    require(len({m['runtime_fingerprint'] for m, _ in sessions}) == 1, 'Different runtime/software/source; cannot combine')
    require(len({m['campaign_id'] for m, _ in sessions}) == 1, 'Different campaign; no cross-campaign pairing')
    throughput, ratios = {}, {}
    for meta, raw in sessions:
        require(meta['purpose'] == 'study' and not meta['local_diagnostic'], 'Study-only target data required')
        require(meta['sizes'] == SIZES and meta['warmups'] == 5 and meta['repetitions'] == 20, 'Unlocked study protocol')
        summary, speedups = summarize(raw, meta)
        for row in summary:
            key = (row['bytes'], row['mode'], row['backend'], row['boundary'])
            throughput.setdefault(key, []).append(row['throughput_MB_s_at_median'])
        for row in speedups:
            for estimator, field in (('median_paired_repetition_ratios', 'median'),
                                     ('ratio_of_session_medians', 'ratio_of_medians')):
                key = (row['bytes'], row['mode'], row['cpu'], row['gpu'], row['comparison'], estimator)
                ratios.setdefault(key, []).append(row[field])
    across_throughput = [dict(bytes=k[0], mode=k[1], backend=k[2], boundary=k[3],
        statistic='distribution of five session throughputs at median time', **statistics(values))
        for k, values in sorted(throughput.items())]
    across_ratios = [dict(bytes=k[0], mode=k[1], cpu=k[2], gpu=k[3], comparison=k[4],
        estimator=k[5], statistic='distribution of five session speedup estimates',
        favorable_sessions=sum(v > 1 for v in values), consistent_gpu_gain=all(v > 1 for v in values),
        **statistics(values)) for k, values in sorted(ratios.items())]
    return across_throughput, across_ratios


def aggregate_campaign(directory, output):
    directory, output = Path(directory), Path(output)
    manifest = json.loads((directory / 'campaign.json').read_text())
    require(manifest['status'] == 'complete' and manifest['purpose'] == 'study', 'Incomplete/non-study campaign')
    sessions = []
    for name in manifest['sessions']:
        session_path = (directory / name).resolve()
        require(session_path.parent == directory.resolve(), 'Session outside campaign')
        meta, raw = load_session(session_path)
        require(meta['campaign_id'] == manifest['campaign_id'] and
                meta['runtime_fingerprint'] == manifest['runtime_fingerprint'], 'Campaign identity mismatch')
        sessions.append((meta, raw))
    throughput, ratios = campaign_summary(sessions)
    output.mkdir(parents=True, exist_ok=False)
    write_table(output, 'session_throughput_distribution', throughput)
    write_table(output, 'session_speedup_distribution', ratios)


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('directory', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--campaign', action='store_true')
    args = p.parse_args()
    if args.campaign:
        aggregate_campaign(args.directory, args.output)
    else:
        aggregate_session(args.directory, args.output)
