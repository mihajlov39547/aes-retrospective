"""Read-only numerical reconstruction of manuscript values. Never runs encryption."""
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
AUDIT = REPO / 'experiments/analysis/economic_aes_existing_evidence_2026_10'
hashes = {}

def read(path):
    data = path.read_bytes()
    hashes[str(path.relative_to(REPO))] = hashlib.sha256(data).hexdigest()
    return data.decode('utf-8')

def csv_rows(path):
    return list(csv.DictReader(read(path).splitlines()))

def close(a, b):
    assert math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-15), (a, b)

def main():
    expected = {
        ('cpu_aesni','transform'): [1381.7,1446.5,1455.8],
        ('cuda_baseline','resident'): [5017.1,3655.6,4800.6],
        ('cuda_baseline','pipeline'): [1313.1,1103.1,1204.5],
        ('cuda_optimized_v1','resident'): [4853.9,3576.2,4877.7],
        ('cuda_optimized_v1','pipeline'): [1291.0,1074.0,1209.1],
    }
    audit = csv_rows(AUDIT/'RECONSTRUCTED_RESULTS.csv')
    thresholds = csv_rows(AUDIT/'ECONOMIC_THRESHOLDS.csv')
    sessions = sorted((REPO/'experiments/results').glob('aes_cuda_cpu_gpu-study-20260930*/raw.csv'))
    assert len(sessions) == 5
    raw = [csv_rows(p) for p in sessions]
    assert all(len(rs) == 1200 for rs in raw)
    results = []
    for index, size in enumerate([1,16,32]):
        rates, times = {}, {}
        for (backend, scope), values in expected.items():
            session_rates, session_times = [], []
            for rs in raw:
                group = [r for r in rs if r['mode']=='CTR' and int(r['bytes'])==size*1048576
                         and r['backend']==backend and r['measurement']==scope]
                assert len(group)==20 and all(r['validation_checked']=='True' for r in group)
                field = {'transform':'seconds','resident':'kernel_seconds','pipeline':'end_to_end_seconds'}[scope]
                rate_field = {'transform':'throughput_MB_s','resident':'kernel_throughput_MB_s','pipeline':'end_to_end_throughput_MB_s'}[scope]
                session_rates.append(median(float(r[rate_field]) for r in group))
                session_times.append(median(float(r[field]) for r in group))
            rate = median(session_rates)
            assert round(rate,1)==values[index], (backend,scope,size,rate)
            record = next(r for r in audit if r['mode']=='CTR' and int(r['bytes'])==size*1048576 and r['backend']==backend and r['measurement']==scope)
            close(rate, float(record['throughput_MB_s']))
            rates[backend,scope], times[backend,scope] = rate, session_times
            results.append(dict(MiB=size,backend=backend,scope=scope,rate=rate))
        rate_threshold = rates['cuda_baseline','pipeline']/rates['cpu_aesni','transform']
        time_ratios = [c/g for c,g in zip(times['cpu_aesni','transform'],times['cuda_baseline','pipeline'])]
        record = next(r for r in thresholds if int(r['bytes'])==size*1048576 and r['backend']=='cuda_baseline' and r['measurement']=='pipeline')
        close(rate_threshold,float(record['aggregate_rate_price_threshold']))
        close(median(time_ratios),float(record['time_ratio_price_threshold_median']))
        assert round(rate_threshold,4)==[.9503,.7626,.8273][index]
        assert all(v<1 for v in time_ratios)
        for field,key in [('cpu_normalized_cost_per_GB',('cpu_aesni','transform')),('gpu_normalized_cost_per_GB_at_hourly_1',('cuda_baseline','pipeline'))]:
            close(1000/rates[key]/3600,float(record[field]))
        results.append(dict(MiB=size,rate_threshold=rate_threshold,paired_time_median=median(time_ratios),paired_time_min=min(time_ratios),paired_time_max=max(time_ratios)))

    supplementary = csv_rows(AUDIT/'SUPPLEMENTARY_RESULTS.csv')
    page_sessions = []
    for seed in range(2003,2008):
        base = REPO/'experiments/page_batching_validation/results/t4-phase2-study'/str(seed)
        rows = [json.loads(line) for line in read(base/'raw.jsonl').splitlines()]
        assert len(rows)==600 and all(r['validated'] for r in rows)
        page_sessions.append(rows)
    for index, pages in enumerate([1,4,16,32]):
        ratios = []
        for rows in page_sessions:
            group = [r for r in rows if r['layout']=='pages' and r['pages']==pages and not r['warmup']]
            cpu = [r for r in group if r.get('cpu_transform_ns') is not None]
            gpu = [r for r in group if r['measurement']=='pipeline']
            assert len(cpu)==len(gpu)==20
            assert {r['pair_hash'] for r in cpu}=={r['pair_hash'] for r in gpu}
            ratios.append(median(r['cpu_transform_ns'] for r in cpu)/median(r['end_to_end_ns'] for r in gpu))
        record = next(r for r in supplementary if r['campaign']=='T4 independent pages' and r['estimator']=='ratio_of_medians' and r['pages']==str(pages))
        close(median(ratios),float(record['median']))
        assert round(median(ratios),4)==[.5404,.7137,.8240,.9125][index]
        assert all(r<1 for r in ratios)
        results.append(dict(pages=pages,time_ratio_median=median(ratios),time_ratio_min=min(ratios),time_ratio_max=max(ratios)))
    originals=json.loads((ROOT/'verification/original_hashes.json').read_text())
    for path, digest in originals.items():
        if Path(path).name.startswith('~$'):  # Transient Word lock files are not manuscript artifacts.
            continue
        assert hashlib.sha256((REPO/path).read_bytes()).hexdigest()==digest, path
    report=dict(status='PASS',new_benchmarks=False,original_manuscript_files_unchanged=True,
                primary_sessions=5,T4_sessions=5,numerical_results=results,input_sha256=hashes)
    (ROOT/'verification/numerical_checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('PASS: primary and v1 rates, cost thresholds/costs, paired ratios, and T4 ratios reconstructed from retained raw observations; originals unchanged.')

if __name__=='__main__':
    main()
