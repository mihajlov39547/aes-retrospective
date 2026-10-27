"""Boundary-explicit summaries. Historical inputs are read-only; export to a NEW directory."""
import argparse
import csv
import json
import math
from pathlib import Path
from statistics import median

COMPONENTS = ('allocation_ns', 'setup_ns', 'transform_ns', 'cleanup_ns',
              'buffer_binding_ns', 'native_call_ns', 'ffi_noop_ns', 'ffi_residual_ns')


def positive(value):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError('Nonpositive/nonfinite measured duration')
    return value


def operation_duration(row):
    # Subtract integers first: large absolute monotonic timestamps must not lose precision.
    duration = int(row['operation_end_ns']) - int(row['operation_start_ns'])
    positive(duration)
    if row.get('operation_envelope_ns') not in (None, '') and int(row['operation_envelope_ns']) != duration:
        raise ValueError('Operation envelope differs from timestamps')
    return duration


def job_envelope(rows):
    for row in rows:
        operation_duration(row)
    duration = max(int(r['operation_end_ns']) for r in rows) - min(int(r['operation_start_ns']) for r in rows)
    for row in rows:
        if row.get('aggregate_envelope_ns') not in (None, '') and int(row['aggregate_envelope_ns']) != duration:
            raise ValueError('Aggregate envelope differs from worker timestamps')
    return duration


def summarize(rows, meta):
    if meta.get('schema_version', 1) not in (1, 2):
        raise ValueError('Unsupported raw schema')
    if meta['experiment'] != ('single' if meta['workers'] == 1 else 'multicore'):
        raise ValueError('Experiment/worker count mismatch')
    expected = {(n, mode, rep, impl, worker) for n in meta['sizes']
                for mode in ('ECB', 'CTR')
                for rep in range(-meta['warmups'], meta['repetitions'])
                for impl in meta['implementations'] for worker in range(meta['workers'])}
    seen, jobs, groups = set(), {}, {}
    for row in rows:
        if row['session_id'] != meta['session_id'] or row['experiment'] != meta['experiment']:
            raise ValueError('Mixed session/experiment rows')
        if int(row['seed']) != meta['seed'] or int(row['workers']) != meta['workers']:
            raise ValueError('Metadata mismatch')
        if str(row['validation_passed']).lower() != 'true':
            raise ValueError('Unvalidated timing')
        n, rep, worker = int(row['bytes']), int(row['repeat']), int(row['worker'])
        key = (n, row['mode'], rep, row['implementation'], worker)
        if key in seen or key not in expected:
            raise ValueError('Duplicate or unexpected sample')
        seen.add(key)
        if (str(row['warmup']).lower() == 'true') != (rep < 0):
            raise ValueError('Warmup label mismatch')
        positive(row['transform_ns'])
        operation_duration(row)
        jobs.setdefault(key[:-1], []).append(row)
    if seen != expected:
        raise ValueError('Incomplete session')

    def add(n, mode, impl, boundary, worker, rep, duration, selected):
        group = groups.setdefault((n, mode, impl, boundary, worker), dict(times={}, components={}))
        group['times'][rep] = duration
        for row in selected:
            for field in COMPONENTS:
                if row.get(field) not in (None, ''):
                    value = float(row[field])
                    if not math.isfinite(value):
                        raise ValueError('Nonfinite component')
                    group['components'].setdefault(field, []).append(value)

    for (n, mode, rep, impl), selected in jobs.items():
        envelope = job_envelope(selected)
        if rep < 0:
            continue
        for row in selected:
            # Multicore transform throughput is PER WORKER; never sum it into an aggregate rate.
            add(n, mode, impl, 'transform', int(row['worker']), rep,
                float(row['transform_ns']), [row])
        add(n, mode, impl, 'operation_envelope', -1, rep, envelope, selected)

    summaries = []
    for (n, mode, impl, boundary, worker), group in sorted(groups.items()):
        times = group['times']
        reference = groups[(n, mode, 'pycryptodome', boundary, worker)]['times']
        middle = median(times.values())
        default = groups.get((n, mode, 'openssl_default', boundary, worker))
        total_bytes = n * meta['workers'] if boundary == 'operation_envelope' else n
        summaries.append(dict(summary_schema_version=2, session_id=meta['session_id'], seed=meta['seed'],
            experiment=meta['experiment'], workers=meta['workers'], bytes_per_worker=n,
            bytes_per_timing=total_bytes, mode=mode, implementation=impl, samples=len(times),
            timing_boundary=boundary, throughput_scope='all_workers' if worker == -1 else 'per_worker',
            worker=None if worker == -1 else worker,
            operation_boundary=meta.get('operation_boundary', 'measure_call_v1'),
            transform_boundary='python_method_with_internal_FFI' if impl == 'pycryptodome' else 'native_EVP_Update_Final',
            median_ns=middle, min_ns=min(times.values()), max_ns=max(times.values()),
            median_throughput_MB_s=total_bytes * 1000 / middle,
            ratio_of_session_medians_py_over_impl=median(reference.values()) / middle,
            median_paired_ratio_py_over_impl=median(reference[r] / times[r] for r in times),
            arm_fallback_over_default_ratio_of_medians=(
                middle / median(default['times'].values()) if impl == 'openssl_armcap0' else None),
            **{f'median_worker_{field}': median(values) for field, values in group['components'].items()}))
    return summaries


def write_summaries(directory, summaries):
    # Exclusive creation prevents accidental overwrite, including historical summaries.
    directory = Path(directory)
    if any((directory / name).exists() for name in ('summary.json', 'summary.csv')):
        raise FileExistsError('Summary already exists; choose a new output directory')
    with (directory / 'summary.json').open('x', encoding='utf-8') as f:
        json.dump(summaries, f, indent=2, allow_nan=False)
    with (directory / 'summary.csv').open('x', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(dict.fromkeys(field for row in summaries for field in row)))
        writer.writeheader()
        writer.writerows(summaries)


def aggregate(directory, output=None):
    directory = Path(directory)
    meta = json.loads((directory / 'metadata.json').read_text(encoding='utf-8'))
    if meta['status'] != 'complete':
        raise ValueError('Refusing failed/incomplete session')
    with (directory / 'raw.csv').open(newline='', encoding='utf-8') as f:
        summaries = summarize(list(csv.DictReader(f)), meta)
    if output is not None:
        output = Path(output)
        output.mkdir(parents=True, exist_ok=False)
    write_summaries(output or directory, summaries)
    return summaries


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('session', type=Path)
    p.add_argument('--output', type=Path, required=True, help='New directory; source session remains untouched')
    args = p.parse_args()
    aggregate(args.session, args.output)
