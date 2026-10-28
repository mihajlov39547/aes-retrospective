"""Read-only reanalysis of existing records; never imports or runs benchmark code.

Run with Python from any directory. Outputs are written only under build/evidence.
Oracle operation rates are reconstructed from archived wall-clock timestamps,
because the schema-1 single-worker summaries report transform rates instead.
"""
from collections import defaultdict
import csv
from hashlib import sha256
import io
import json
from pathlib import Path
from statistics import median
import tarfile

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / 'build/evidence'
PAYLOAD = 32 * 1024 * 1024


def digest(data):
    return sha256(data).hexdigest()


def summary_rates(name):
    path = ROOT / 'evidence' / name
    groups = defaultdict(list)
    rows = list(csv.DictReader(io.StringIO(path.read_text(encoding='utf-8'))))
    for row in rows:
        if row['mode'] == 'CTR' and int(row['bytes_per_worker']) == PAYLOAD:
            assert int(row['samples']) == 20
            groups[(row['implementation'], row['timing_boundary'])].append(row)
    result = {}
    for (impl, boundary), selected in groups.items():
        assert len(selected) == 5 and {int(r['seed']) for r in selected} == set(range(2003, 2008))
        values = [float(r['median_throughput_MB_s']) for r in selected]
        result[impl + '/' + boundary] = dict(median_MB_s=median(values),
            min_MB_s=min(values), max_MB_s=max(values),
            sessions=[r['session_id'] for r in selected])
    return dict(file=str(path.relative_to(ROOT)), sha256=digest(path.read_bytes()), rates=result)


def oracle_campaign(kind, workers):
    path = ROOT.parent / 'experiments/results' / f'oracle-phase1-{kind}-study.tar.gz'
    sessions = []
    with tarfile.open(path) as archive:
        names = archive.getnames()
        # The multicore archive also contains earlier single and smoke sessions.
        # Select only the named campaign; never count those copies as replication.
        prefixes = sorted(n.rsplit('/', 1)[0] for n in names
            if n.startswith(f'results/{kind}-study-') and n.endswith('/raw.csv'))
        assert len(prefixes) == len(set(prefixes)) == 5
        for prefix in prefixes:
            hashes = {}

            def read(name):
                member = prefix + '/' + name
                data = archive.extractfile(member).read()
                hashes[member] = digest(data)
                return data

            meta = json.loads(read('metadata.json'))
            assert meta['status'] == 'complete' and meta['purpose'] == 'study'
            assert meta['experiment'] == kind and meta['workers'] == workers
            assert meta['repetitions'] == 20 and meta['warmups'] == 5
            assert meta['architecture'] == 'aarch64' and meta['logical_cpus'] == 2
            for filename, expected in meta['source_sha256'].items():
                assert digest(read('source/' + filename)) == expected
            validation = json.loads(read('validation.json'))
            assert len(validation['openssl_default']) == workers
            assert all(v['passed'] for values in validation.values() for v in values)
            wm = meta['worker_metadata']['openssl_default']
            assert len(wm) == workers
            assert all(w['provider'] == 'default' and
                w['environment']['OPENSSL_armcap'] is None and
                '3.0.13' in w['openssl_version'] for w in wm)
            inputs = json.loads(read('inputs.json'))['CTR:33554432']
            assert len(inputs) == workers and all(x['ready'] for x in inputs)
            assert all(len(bytes.fromhex(x['key_hex'])) == 16 for x in inputs)
            assert all(len(bytes.fromhex(x['counter_hex'])) == 16 for x in inputs)
            rows = list(csv.DictReader(io.StringIO(read('raw.csv').decode())))
            groups = defaultdict(list)
            for row in rows:
                if row['mode'] != 'CTR' or row['implementation'] != 'openssl_default' or int(row['bytes']) != PAYLOAD:
                    continue
                assert row['session_id'] == meta['session_id']
                assert int(row['workers']) == workers and row['validation_passed'] == 'True'
                repeat = int(row['repeat'])
                assert (row['warmup'] == 'True') == (repeat < 0)
                if repeat >= 0:
                    groups[repeat].append(row)
            assert set(groups) == set(range(20))
            durations = []
            for repeat, group in sorted(groups.items()):
                assert len(group) == workers and {int(r['worker']) for r in group} == set(range(workers))
                starts = [int(r['operation_start_ns']) for r in group]
                ends = [int(r['operation_end_ns']) for r in group]
                assert all(end > start for start, end in zip(starts, ends))
                elapsed = max(ends) - min(starts)
                if workers > 1:
                    assert all(int(r['aggregate_envelope_ns']) == elapsed for r in group)
                durations.append(elapsed)
            rate = workers * PAYLOAD * 1000 / median(durations)
            if workers > 1:
                original = list(csv.DictReader(io.StringIO(read('summary.csv').decode())))
                selected = [r for r in original if r['mode'] == 'CTR' and
                    r['implementation'] == 'openssl_default' and int(r['bytes_per_worker']) == PAYLOAD]
                assert len(selected) == 1
                assert abs(float(selected[0]['median_throughput_MB_s']) - rate) < 1e-9
            sessions.append(dict(session_id=meta['session_id'], seed=meta['seed'],
                hostname=meta['hostname'], os=meta['os'], python=meta['python'],
                workers=workers, bytes_per_worker=PAYLOAD, bytes_per_timing=workers * PAYLOAD,
                samples=20, median_operation_ns=median(durations), throughput_MB_s=rate,
                operation_durations_ns=durations,
                capability_settings=[w['openssl_cpu_settings'] for w in wm],
                source_sha256=meta['source_sha256'], members_sha256=hashes))
    assert {s['seed'] for s in sessions} == set(range(2003, 2008))
    rates = [s['throughput_MB_s'] for s in sessions]
    return dict(archive=str(path.relative_to(ROOT.parent)), sha256=digest(path.read_bytes()),
        sessions=sessions, median_MB_s=median(rates), min_MB_s=min(rates), max_MB_s=max(rates))


def main():
    windows = summary_rates('windows_phase1_session_summaries.csv')
    arm = summary_rates('oracle_single_session_summaries.csv')
    w = windows['rates']
    o_t = w['openssl_default/transform']['median_MB_s']
    p_t = w['pycryptodome/transform']['median_MB_s']
    o_op = w['openssl_default/operation_envelope']['median_MB_s']
    p_op = w['pycryptodome/operation_envelope']['median_MB_s']
    a = arm['rates']
    oracle_rates = {k.split('/')[0]: v['median_MB_s'] for k, v in a.items()}
    single, multi = oracle_campaign('single', 1), oracle_campaign('multicore', 2)
    all_sessions = single['sessions'] + multi['sessions']
    assert len({s['hostname'] for s in all_sessions}) == 1
    assert len({s['os'] for s in all_sessions}) == 1
    assert len({s['python'] for s in all_sessions}) == 1
    assert len({json.dumps(s['source_sha256'], sort_keys=True) for s in all_sessions}) == 1
    report = dict(windows=windows, arm_transform=arm,
        contrasts=dict(windows_transform_ratio=o_t/p_t, windows_operation_ratio=o_op/p_op,
            openssl_throughput_retention=o_op/o_t, pycryptodome_throughput_retention=p_op/p_t,
            arm_default_over_python=oracle_rates['openssl_default']/oracle_rates['pycryptodome'],
            arm_default_over_masked=oracle_rates['openssl_default']/oracle_rates['openssl_armcap0']),
        oracle_single=single, oracle_multicore=multi,
        oracle_aggregate_rate_ratio=multi['median_MB_s']/single['median_MB_s'],
        definition='Per repetition: N * bytes * 1000 / (latest end - earliest start). '
            'Session summary: N * bytes * 1000 / median elapsed ns. Campaign: median of five session rates. '
            'Single and multicore campaigns are not statistically paired; no transform rates are summed.')
    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / 'audit.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report['contrasts'], indent=2))
    print('Oracle operation MB/s:', single['median_MB_s'], multi['median_MB_s'],
          'aggregate ratio:', report['oracle_aggregate_rate_ratio'])


if __name__ == '__main__':
    main()
