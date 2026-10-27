"""Read-only historical/Phase-1 inventory; never import these observations as new pairs."""
import csv
import hashlib
import io
import json
from pathlib import Path
from statistics import median
import tarfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def review():
    archive = next((REPO / 'experiments/results_orchestrated/t4-colab').glob('*.tar.gz'))
    t4 = []
    with tarfile.open(archive) as tar:
        names = [n for n in tar.getnames() if '/cuda_paired/' in n and n.endswith('/metadata.json')]
        for name, backend in ((n, b) for n in names for b in ('cuda_baseline', 'cuda_optimized_v1')):
            meta = json.load(tar.extractfile(name))
            raw_bytes = tar.extractfile(name.replace('metadata.json', 'raw.csv')).read()
            rows = list(csv.DictReader(io.StringIO(raw_bytes.decode())))
            pairs = {}
            for row in rows:
                if row['bytes'] == '33554432' and row['mode'] == 'CTR':
                    if row['backend'] == 'cpu_aesni' or (row['backend'] == backend and row['measurement'] == 'pipeline'):
                        pairs.setdefault(int(row['repeat']), {})[row['backend']] = row
            ratios, cpu_times, gpu_times = [], [], []
            for pair in pairs.values():
                c, g = pair['cpu_aesni'], pair[backend]
                if c['pair_sha256'] != g['pair_sha256']:
                    raise ValueError('Historical pairing mismatch')
                ct, gt = float(c['wall_elapsed_ns']), float(g['end_to_end_ns'])
                ratios.append(ct/gt)
                cpu_times.append(ct)
                gpu_times.append(gt)
            t4.append(dict(seed=meta['seed'], backend=backend, metadata_member=name, raw_sha256=sha(raw_bytes),
                gpu=meta['gpu'], python=meta['python'], libraries=meta['library_versions'],
                cpu_recorded=meta['cpu'], cpu_timing=meta['method']['cpu_timing'],
                gpu_excluded=meta['method']['gpu_excluded'], repetitions=len(ratios),
                median_paired_ratio=median(ratios), ratio_of_medians=median(cpu_times)/median(gpu_times),
                kernel_hashes={n: sha(tar.extractfile(name.replace('metadata.json', 'source/'+n)).read())
                               for n in ('aes_cuda_baseline.cu', 'aes_cuda_optimized.cu')}))
    windows = []
    for directory in sorted((REPO / 'experiments/cpu_baseline_validation/results').glob('single-study-*')):
        meta_bytes = (directory / 'metadata.json').read_bytes()
        meta = json.loads(meta_bytes)
        if meta['os'].startswith('Windows'):
            windows.append(dict(session_id=meta['session_id'], seed=meta['seed'], status=meta['status'],
                schema_version=meta['schema_version'], os=meta['os'], cpu=meta['cpu'],
                native=meta['worker_metadata']['openssl_default'][0],
                metadata_sha256=sha(meta_bytes), raw_sha256=sha((directory / 'raw.csv').read_bytes())))
    oracle = {}
    for path in sorted((REPO / 'experiments/results').glob('oracle-phase1-*-study.tar.gz')):
        sessions = []
        with tarfile.open(path) as tar:
            for name in tar.getnames():
                if name.endswith('/metadata.json'):
                    meta = json.load(tar.extractfile(name))
                    if meta['purpose'] == 'study':
                        sessions.append(dict(session_id=meta['session_id'], seed=meta['seed'],
                            workers=meta['workers'], architecture=meta['architecture'],
                            hostname=meta['hostname'], status=meta['status']))
        oracle[path.name] = dict(sha256=sha(path.read_bytes()), sessions=sessions)
    return dict(t4_archive=str(archive), t4_archive_sha256=sha(archive.read_bytes()),
        t4_sessions=sorted(t4, key=lambda m:m['seed']),
        t4_ctr32_estimators={b:dict(
            median_of_session_paired_ratios=median(r['median_paired_ratio'] for r in t4 if r['backend']==b),
            median_of_session_ratio_of_medians=median(r['ratio_of_medians'] for r in t4 if r['backend']==b))
            for b in ('cuda_baseline', 'cuda_optimized_v1')},
        current_kernel_hashes={n:sha((REPO/'experiments'/n).read_bytes())
                              for n in ('aes_cuda_baseline.cu', 'aes_cuda_optimized.cu')},
        windows=windows, oracle=oracle,
        note='Read-only inventory. Windows, Oracle and historical T4 sessions are not paired with new Colab observations.')


if __name__ == '__main__':
    print(json.dumps(review(), indent=2))
