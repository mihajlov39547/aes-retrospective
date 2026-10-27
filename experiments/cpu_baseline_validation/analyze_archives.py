"""Read Oracle tar archives without extraction/mutation; derive boundary-explicit reports."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from statistics import median
import tarfile

from aggregate import job_envelope, operation_duration, summarize, write_summaries


def read_sessions(paths):
    sessions, archives = {}, {}
    for path in paths:
        path = Path(path)
        archives[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        with tarfile.open(path, 'r:gz') as archive:
            for member in archive.getmembers():
                if not member.isfile() or not member.name.endswith('/metadata.json'):
                    continue
                prefix = member.name.rsplit('/', 1)[0]
                metadata_bytes = archive.extractfile(member).read()
                meta = json.loads(metadata_bytes)
                if meta['status'] != 'complete':
                    raise ValueError(f'Incomplete source session: {prefix}')
                raw = archive.extractfile(prefix + '/raw.csv').read()
                raw_hash = hashlib.sha256(raw).hexdigest()
                metadata_hash = hashlib.sha256(metadata_bytes).hexdigest()
                identity = meta['session_id']
                if identity in sessions:
                    prior = sessions[identity]
                    if (raw_hash, metadata_hash) != (prior['raw_sha256'], prior['metadata_sha256']):
                        raise ValueError(f'Conflicting duplicate session: {identity}')
                    prior['archives'].append(str(path))
                    continue
                sessions[identity] = dict(metadata=meta, raw_sha256=raw_hash,
                    metadata_sha256=metadata_hash, archives=[str(path)],
                    rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8')))))
    return sessions, archives


def diagnostics(rows):
    jobs = {}
    for row in rows:
        if int(row['repeat']) >= 0:
            jobs.setdefault((row['bytes'], row['mode'], row['implementation'], row['repeat']), []).append(row)
    result = []
    for (size, mode, implementation, repeat), selected in jobs.items():
        critical = max(selected, key=lambda row: int(row['operation_end_ns']))
        duration = operation_duration(critical)
        envelope = job_envelope(selected)
        start_lag = int(critical['operation_start_ns']) - min(int(r['operation_start_ns']) for r in selected)
        def number(field):
            return int(critical[field]) if critical.get(field) not in ('', None) else 0
        if implementation == 'pycryptodome':
            accounted = sum(number(k) for k in ('allocation_ns', 'setup_ns', 'transform_ns', 'cleanup_ns'))
        else:
            # native_call contains setup/transform/cleanup/FFI residual: don't count them twice.
            accounted = sum(number(k) for k in ('allocation_ns', 'buffer_binding_ns', 'ffi_noop_ns', 'native_call_ns'))
        if envelope != duration + start_lag:
            raise ValueError('Envelope decomposition failed')
        result.append(dict(session_id=critical['session_id'], workers=int(critical['workers']),
            bytes_per_worker=int(size), mode=mode, implementation=implementation, repeat=int(repeat),
            critical_worker=int(critical['worker']), envelope_ns=envelope,
            critical_operation_ns=duration, critical_start_lag_ns=start_lag,
            worker_start_spread_ns=max(int(r['operation_start_ns']) for r in selected) -
                                   min(int(r['operation_start_ns']) for r in selected),
            accounted_nonoverlapping_ns=accounted, uninstrumented_residual_ns=duration-accounted,
            **{k: number(k) for k in ('allocation_ns', 'setup_ns', 'transform_ns', 'cleanup_ns',
                                     'buffer_binding_ns', 'ffi_noop_ns', 'native_call_ns', 'ffi_residual_ns')}))
    return result


def write_csv(path, rows):
    with path.open('x', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for row in rows for k in row)))
        writer.writeheader()
        writer.writerows(rows)


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('archives', nargs='+', type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    sessions, archives = read_sessions(args.archives)
    args.output.mkdir(parents=True, exist_ok=False)
    all_summaries, all_diagnostics, component_medians = [], [], []
    for identity, session in sorted(sessions.items()):
        meta, rows = session['metadata'], session['rows']
        summary = summarize(rows, meta)
        directory = args.output / identity
        directory.mkdir()
        write_summaries(directory, summary)
        diag = diagnostics(rows)
        write_csv(directory / 'envelope_diagnostics.csv', diag)
        all_summaries.extend(summary)
        all_diagnostics.extend(diag)
        configurations = {}
        for row in diag:
            configurations.setdefault((row['bytes_per_worker'], row['mode'], row['implementation']), []).append(row)
        for (size, mode, impl), samples in sorted(configurations.items()):
            component_medians.append(dict(session_id=identity, seed=meta['seed'], workers=meta['workers'],
                bytes_per_worker=size, mode=mode, implementation=impl,
                **{'median_' + k: median(r[k] for r in samples) for k in samples[0] if k.endswith('_ns')}))
    write_csv(args.output / 'all_session_summaries.csv', all_summaries)
    write_csv(args.output / 'component_medians.csv', component_medians)
    provenance = dict(archives=archives, sessions={k: {field: v[field] for field in
        ('raw_sha256', 'metadata_sha256', 'archives')} for k, v in sessions.items()},
        analysis_source_sha256={name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                               for name in ('analyze_archives.py', 'aggregate.py')},
        note='Schema-1 envelopes derived from recorded timestamps. No new timings. No cross-session pairing.')
    (args.output / 'provenance.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
    for path, expected in archives.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Source archive changed during analysis')
    print(f'{len(sessions)} unique sessions analyzed read-only into {args.output}')


if __name__ == '__main__':
    main()
