"""CPU/numerical tests always run; GPU end-to-end requires an explicit smoke device name."""
import copy
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from protocol import SIZES, SEEDS, schedule, target_check, software_check, aes_capabilities
from aggregate import summarize, campaign_summary, write_table, component_summary
from dependencies import cpu, native, cuda_base
from run import assert_equal


def fixture(seed=2003, study=False):
    sizes, warmups, repeats = (SIZES, 5, 20) if study else ([1024], 1, 3)
    meta = dict(status='complete', schema_version=1, session_id=f'session-{seed}', campaign_id='campaign',
        runtime_fingerprint='runtime', seed=seed, workers=1, sizes=sizes, warmups=warmups,
        repetitions=repeats, purpose='study' if study else 'smoke', local_diagnostic=False)
    rows = []
    for job in schedule(seed, sizes, warmups, repeats):
        row = dict(schema_version=1, **{k: meta[k] for k in ('session_id', 'campaign_id', 'runtime_fingerprint', 'seed')},
                   **job, validation_passed=True, pair_hash='a'*64)
        if job['measurement'] == 'cpu':
            t = 100 if job['backend'] == 'pycryptodome' else 25
            row.update(cpu_transform_ns=t, transform_ns=t, cpu_operation_ns=t+100,
                       operation_start_ns=10**18, operation_end_ns=10**18+t+100)
        elif job['measurement'] == 'pipeline':
            row.update(gpu_pipeline_ns=50, gpu_pipeline_kernel_ns=10, h2d_ns=10, d2h_ns=15, transfer_ns=25)
        else:
            row.update(gpu_resident_ns=10, resident_batch_ns=10)
        rows.append(row)
    return meta, rows


class Numerical(unittest.TestCase):
    def test_separate_boundaries_and_negative_outcomes(self):
        meta, rows = fixture()
        summary, ratios = summarize(rows, meta)
        self.assertEqual(len(summary), 16)
        self.assertEqual(len(ratios), 24)
        selected = {r['comparison']: r for r in ratios if r['mode'] == 'CTR' and
                    r['cpu'] == 'openssl_default' and r['gpu'] == 'cuda_optimized_v1'}
        self.assertEqual(selected['prepared_cpu_transform_over_gpu_pipeline']['median'], .5)
        self.assertEqual(selected['cpu_operation_over_prepared_gpu_pipeline']['median'], 2.5)
        self.assertEqual(selected['isolated_cpu_transform_over_gpu_resident']['median'], 2.5)
        self.assertEqual(selected['prepared_cpu_transform_over_gpu_pipeline']['favorable_repetitions'], 0)
        self.assertEqual(summarize(list(reversed(rows)), meta), (summary, ratios))

    def test_pair_ratios_not_ratios_of_medians(self):
        meta, rows = fixture()
        for row in rows:
            if row['repeat'] < 0:
                continue
            if row['measurement'] == 'cpu':
                row['cpu_transform_ns'] = row['transform_ns'] = [1, 10, 100][row['repeat']]
            elif row['measurement'] == 'pipeline':
                row.update(gpu_pipeline_ns=[2, 100, 4][row['repeat']], h2d_ns=0, d2h_ns=0, transfer_ns=0)
        _, ratios = summarize(rows, meta)
        row = next(r for r in ratios if r['comparison'] == 'prepared_cpu_transform_over_gpu_pipeline')
        self.assertEqual(row['median'], .5)
        self.assertEqual(row['ratio_of_medians'], 2.5)

    def test_wrong_pairs_missing_duplicate_invalid_samples(self):
        meta, rows = fixture()
        for bad in (rows[:-1], rows+[rows[0]]):
            with self.assertRaises(ValueError):
                summarize(bad, meta)
        for field, value in [('pair_hash', 'b'*64), ('session_id', 'other'), ('runtime_fingerprint', 'other'),
                             ('pair_id', 'wrong'), ('validation_passed', False), ('seed', 2007)]:
            bad = copy.deepcopy(rows)
            bad[0][field] = value
            with self.assertRaises(ValueError, msg=field):
                summarize(bad, meta)
        for field, value in [('cpu_operation_ns', 1), ('cpu_transform_ns', float('nan'))]:
            bad = copy.deepcopy(rows)
            next(r for r in bad if r['measurement'] == 'cpu')[field] = value
            with self.assertRaises(ValueError):
                summarize(bad, meta)

    def test_warmup_exclusion_and_outlier_retention(self):
        meta, rows = fixture()
        for row in rows:
            if row['measurement'] == 'resident':
                row['gpu_resident_ns'] = row['resident_batch_ns'] = 999999 if row['warmup'] else [10, 10, 10000][row['repeat']]
        summary, _ = summarize(rows, meta)
        row = next(r for r in summary if r['boundary'] == 'gpu_resident_ns')
        self.assertEqual(row['count'], 3)
        self.assertEqual(row['median'], 10)
        self.assertEqual(row['max'], 10000)

    def test_five_session_consistency_no_cross_runtime_pooling(self):
        sessions = [fixture(seed, True) for seed in SEEDS]
        throughput, ratios = campaign_summary(sessions)
        self.assertEqual(len(throughput), 80)
        self.assertEqual(len(ratios), 240)
        self.assertTrue(all(r['count'] == 5 for r in ratios))
        self.assertTrue(all(r['favorable_sessions'] == 0 for r in ratios
                            if r['cpu'] == 'openssl_default' and r['comparison'] == 'prepared_cpu_transform_over_gpu_pipeline'))
        for field, value in [('runtime_fingerprint', 'another-VM'), ('seed', 2003), ('local_diagnostic', True),
                             ('purpose', 'smoke'), ('repetitions', 10), ('campaign_id', 'other')]:
            bad = copy.deepcopy(sessions)
            bad[-1][0][field] = value
            with self.assertRaises(ValueError, msg=field):
                campaign_summary(bad)

    def test_no_summary_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_table(Path(tmp), 'test', [dict(value=1)])
            with self.assertRaises(ValueError):
                write_table(Path(tmp), 'test', [dict(value=2)])
            self.assertEqual(json.loads((Path(tmp)/'test.json').read_text()), [dict(value=1)])

    def test_components_preserve_residuals_without_double_counting(self):
        meta, rows = fixture()
        for row in rows:
            if row['backend'] == 'openssl_default':
                row.update(allocation_ns=10, setup_ns=5, cleanup_ns=2, buffer_binding_ns=3,
                           ffi_noop_ns=2, native_call_ns=29, ffi_residual_ns=-3)
        summarize(rows, meta)
        components = {r['component']: r for r in component_summary(rows)
                      if r['backend'] == 'openssl_default' and r['mode'] == 'CTR'}
        self.assertEqual(components['ffi_residual_ns']['median'], -3)
        self.assertEqual(components['operation_remainder_ns']['median'], 81)
        self.assertEqual(components['operation_remainder_ns']['count'], 3)


class Correctness(unittest.TestCase):
    def test_native_and_python_vectors_all_sizes(self):
        lib = native()
        for implementation in ('pycryptodome', 'openssl_default'):
            result = cpu.validate(implementation, lib)
            self.assertTrue(result['passed'])
            self.assertEqual(len(result['cases']), 37)

    def test_ciphertext_corruption_is_rejected(self):
        with self.assertRaises(RuntimeError):
            assert_equal(b'bad', b'good')
        class Corrupt:
            def encrypt(self, mode, key, iv, data):
                return bytes(len(data))
        self.assertFalse(cuda_base.validate(Corrupt(), 'test', 'smoke')['passed'])

    def test_input_identity_schedule_and_ctr_guard(self):
        self.assertEqual(cpu.inputs(2003, 1024), cpu.inputs(2003, 1024))
        self.assertNotEqual(cpu.inputs(2003, 1024), cpu.inputs(2004, 1024))
        plan = schedule(2003, SIZES, 5, 20)
        self.assertEqual(len(plan), 1500)
        self.assertEqual(sum(r['warmup'] for r in plan), 300)
        self.assertEqual(plan, schedule(2003, SIZES, 5, 20))
        self.assertNotEqual(plan, schedule(2004, SIZES, 5, 20))
        with self.assertRaises(ValueError):
            cpu.check_input('CTR', bytes(17), bytes(16), b'\xff'*16)

    def test_fail_closed_hardware_and_capabilities(self):
        software_check(12090, '13.6.0', '3.23.0', '2.2.6')
        software_check(13000, '14.0.1', '3.23.0', '2.2.6')
        with self.assertRaises(RuntimeError):
            software_check(13000, '13.6.0', '3.23.0', '2.2.6')
        t4 = dict(compute_capability='75', gpu_name='Tesla T4')
        target_check(t4, 'Linux', 'x86_64', True)
        for gpu, system, arch, study, local in [
            (dict(t4, gpu_name='NVIDIA A100'), 'Linux', 'x86_64', True, None),
            (dict(t4, compute_capability='80'), 'Linux', 'x86_64', False, None),
            (t4, 'Windows', 'AMD64', True, None),
            (t4, 'Linux', 'aarch64', True, None),
            (t4, 'Linux', 'x86_64', True, 'Tesla T4')]:
            with self.assertRaises(RuntimeError):
                target_check(gpu, system, arch, study, local)
        self.assertTrue(aes_capabilities(dict(cpu_aes_available=1,
             openssl_cpu_settings=f'OPENSSL_ia32cap=0x{1<<57:x}:0x0'))['openssl_aes_capability_enabled'])
        self.assertFalse(aes_capabilities(dict(cpu_aes_available=0,
             openssl_cpu_settings='OPENSSL_ia32cap=0x0:0x0'))['openssl_aes_capability_enabled'])


class GPUIntegration(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('AES_GPU_SMOKE_NAME'), 'Set AES_GPU_SMOKE_NAME explicitly for local GPU integration')
    def test_real_gpu_smoke(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('run.py')),
                '--local-smoke-gpu', os.environ['AES_GPU_SMOKE_NAME'], '--output', tmp],
                capture_output=True, text=True, timeout=180)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            campaign_dir = next(Path(tmp).iterdir())
            campaign = json.loads((campaign_dir / 'campaign.json').read_text())
            self.assertEqual(campaign['status'], 'complete')
            session_dir = campaign_dir / campaign['smoke_gate']
            meta = json.loads((session_dir / 'metadata.json').read_text())
            self.assertEqual(meta['status'], 'complete')
            self.assertTrue(meta['local_diagnostic'])
            with (session_dir / 'raw.csv').open() as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 72)
            summary, ratios = summarize(rows, meta)
            self.assertEqual((len(summary), len(ratios)), (32, 48))
            planned = json.loads((session_dir / 'planned_order.json').read_text())
            events = [json.loads(line) for line in (session_dir / 'execution_order.jsonl').read_text().splitlines()]
            self.assertEqual(len(events), 144)
            self.assertTrue(all(e['event'] == 'completed' for e in events[1::2]))
            self.assertEqual([e['execution_index'] for e in events[::2]], [p['execution_index'] for p in planned])
            validation = json.loads((session_dir / 'validation.json').read_text())
            self.assertTrue(validation['passed'])
            self.assertTrue(all(v['wrap_rejected'] for v in validation['gpu'].values()))


if __name__ == '__main__':
    unittest.main()
