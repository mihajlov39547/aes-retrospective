"""Aggregate ONE complete session at a time; never pair different machines/sessions."""
import argparse
import csv
import json
import math
from pathlib import Path
from statistics import median


def summarize(rows, meta):
    expected = {(n, mode, rep, impl, worker) for n in meta['sizes']
                for mode in ('ECB', 'CTR')
                for rep in range(-meta['warmups'], meta['repetitions'])
                for impl in meta['implementations'] for worker in range(meta['workers'])}
    seen, groups, components = set(), {}, {}
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
        if rep < 0:
            continue
        metric = 'transform_ns' if meta['workers'] == 1 else 'aggregate_envelope_ns'
        duration = float(row[metric])
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError('Nonpositive/nonfinite measured duration')
        g = groups.setdefault((n, row['mode'], row['implementation']), {})
        if rep in g and g[rep] != duration:
            raise ValueError('Inconsistent multicore envelope')
        g[rep] = duration
        component = components.setdefault((n, row['mode'], row['implementation']), {})
        for field in ('allocation_ns', 'setup_ns', 'transform_ns', 'cleanup_ns',
                      'buffer_binding_ns', 'native_call_ns', 'ffi_noop_ns', 'ffi_residual_ns'):
            if row.get(field) not in (None, ''):
                component.setdefault(field, []).append(float(row[field]))
    if seen != expected:
        raise ValueError('Incomplete session')
    summaries = []
    for (n, mode, impl), times in sorted(groups.items()):
        reference = groups[(n, mode, 'pycryptodome')]
        middle = median(times.values())
        default = groups.get((n, mode, 'openssl_default'))
        summaries.append(dict(session_id=meta['session_id'], seed=meta['seed'],
            experiment=meta['experiment'], workers=meta['workers'], bytes_per_worker=n,
            mode=mode, implementation=impl, samples=len(times),
            timing_boundary='python_transform_vs_native_EVP' if meta['workers'] == 1 else 'aggregate_operation_envelope',
            median_ns=middle, min_ns=min(times.values()), max_ns=max(times.values()),
            median_throughput_MB_s=n * meta['workers'] * 1000 / middle,
            ratio_of_session_medians_py_over_impl=median(reference.values()) / middle,
            median_paired_ratio_py_over_impl=median(reference[r] / times[r] for r in times),
            arm_fallback_over_default_ratio_of_medians=(
                middle / median(default.values()) if impl == 'openssl_armcap0' else None),
            **{f'median_worker_{field}': median(values) for field, values in
               components[(n, mode, impl)].items()}))
    return summaries


def aggregate(directory):
    directory = Path(directory)
    meta = json.loads((directory / 'metadata.json').read_text(encoding='utf-8'))
    if meta['status'] != 'complete':
        raise ValueError('Refusing failed/incomplete session')
    with (directory / 'raw.csv').open(newline='', encoding='utf-8') as f:
        summaries = summarize(list(csv.DictReader(f)), meta)
    (directory / 'summary.json').write_text(json.dumps(summaries, indent=2, allow_nan=False), encoding='utf-8')
    with (directory / 'summary.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(dict.fromkeys(
            field for row in summaries for field in row)))
        writer.writeheader()
        writer.writerows(summaries)
    return summaries


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('session', type=Path)
    aggregate(p.parse_args().session)
