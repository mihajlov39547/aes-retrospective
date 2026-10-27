"""Run after build.py: python -m unittest discover -s . -v"""
import copy
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from aggregate import summarize
from core import Native, check_input, inputs, validate
from run import schedule


class Correctness(unittest.TestCase):
    def test_vectors_and_all_sizes(self):
        native = Native()
        for impl in ('pycryptodome', 'openssl_default'):
            result = validate(impl, native)
            self.assertTrue(result['passed'])
            self.assertEqual(len(result['cases']), 37)

    def test_guardrails(self):
        for mode, data, key, iv in (
            ('ECB', b'x', bytes(16), bytes(16)),
            ('CTR', bytes(17), bytes(16), b'\xff' * 16),
            ('CTR', bytes(16), bytes(24), bytes(16)),
            ('CBC', bytes(16), bytes(16), bytes(16))):
            with self.assertRaises(ValueError):
                check_input(mode, data, key, iv)
        check_input('CTR', bytes(16), bytes(16), b'\xff' * 16)

    def test_data_and_order(self):
        self.assertEqual(inputs(2003, 1024), inputs(2003, 1024))
        self.assertNotEqual(inputs(2003, 1024), inputs(2004, 1024))
        a = schedule(2003, [1024, 16384], ['pycryptodome', 'openssl_default'], 5, 20)
        self.assertEqual(a, schedule(2003, [1024, 16384], ['pycryptodome', 'openssl_default'], 5, 20))
        self.assertEqual(len(a), 200)
        self.assertEqual(sum(j['warmup'] for j in a), 40)
        self.assertNotEqual(a, schedule(2004, [1024, 16384], ['pycryptodome', 'openssl_default'], 5, 20))


class Numerical(unittest.TestCase):
    def fixture(self):
        meta = dict(session_id='one', seed=2003, experiment='single', workers=1,
                    sizes=[1024], warmups=1, repetitions=3,
                    implementations=['pycryptodome', 'openssl_default'])
        rows = []
        for mode in ('ECB', 'CTR'):
            for impl in meta['implementations']:
                for repeat, t in zip(range(-1, 3), [999999, 10, 20, 10000]):
                    rows.append(dict(session_id='one', seed=2003, experiment='single', workers=1,
                        worker=0, bytes=1024, mode=mode, implementation=impl, repeat=repeat,
                        warmup=repeat < 0, validation_passed=True,
                        transform_ns=t * (2 if impl == 'openssl_default' else 1)))
        return rows, meta

    def test_negative_outcome_outlier_and_warmup(self):
        rows, meta = self.fixture()
        result = next(r for r in summarize(rows, meta) if r['implementation'] == 'openssl_default')
        self.assertEqual(result['median_ns'], 40)
        self.assertEqual(result['max_ns'], 20000)
        self.assertEqual(result['ratio_of_session_medians_py_over_impl'], .5)
        self.assertEqual(result['median_paired_ratio_py_over_impl'], .5)
        self.assertEqual(result['median_throughput_MB_s'], 1024 * 1000 / 40)

    def test_reject_incomplete_mixed_duplicate_invalid(self):
        rows, meta = self.fixture()
        for bad in (rows[:-1], rows + [rows[0]]):
            with self.assertRaises(ValueError):
                summarize(bad, meta)
        for field, value in [('session_id', 'other-host'), ('validation_passed', False),
                             ('transform_ns', float('nan')), ('transform_ns', 0)]:
            bad = copy.deepcopy(rows)
            bad[1][field] = value
            with self.assertRaises(ValueError):
                summarize(bad, meta)

    def test_paired_ratio_differs_from_ratio_of_medians(self):
        rows, meta = self.fixture()
        for row in rows:
            if row['repeat'] >= 0:
                row['transform_ns'] = ([1, 10, 100] if row['implementation'] == 'pycryptodome'
                                       else [2, 100, 4])[row['repeat']]
        result = next(r for r in summarize(rows, meta) if r['implementation'] == 'openssl_default')
        self.assertEqual(result['ratio_of_session_medians_py_over_impl'], 2.5)
        self.assertEqual(result['median_paired_ratio_py_over_impl'], .5)

    def test_multicore_envelope_not_sum(self):
        rows, meta = self.fixture()
        meta.update(experiment='multicore', workers=2)
        out = []
        for row in rows:
            row.update(experiment='multicore', workers=2, aggregate_envelope_ns=100)
            out.extend([dict(row, worker=0), dict(row, worker=1)])
        result = summarize(out, meta)[0]
        self.assertEqual(result['samples'], 3)
        self.assertEqual(result['median_throughput_MB_s'], 20480)


class Smoke(unittest.TestCase):
    def test_single_and_multicore_pipeline(self):
        root = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory() as tmp:
            for workers in (1, 2):
                subprocess.run([sys.executable, str(root / 'run.py'), '--workers', str(workers),
                                '--output', tmp], check=True, capture_output=True, text=True,
                               timeout=180)
            directories = list(Path(tmp).iterdir())
            self.assertEqual(len(directories), 2)
            for directory in directories:
                meta = json.loads((directory / 'metadata.json').read_text())
                self.assertEqual(meta['status'], 'complete')
                self.assertEqual(meta['purpose'], 'smoke')
                with (directory / 'raw.csv').open() as f:
                    rows = list(csv.DictReader(f))
                expected_jobs = 2 * 2 * 3 * len(meta['implementations'])
                self.assertEqual(len(rows), expected_jobs * meta['workers'])
                events = [json.loads(line) for line in
                          (directory / 'execution_order.jsonl').read_text().splitlines()]
                self.assertEqual(len(events), expected_jobs * 2)
                self.assertTrue(all(e['event'] == 'completed' for e in events[1::2]))
                self.assertEqual([int(row['execution_index']) for row in rows[::meta['workers']]],
                                 list(range(expected_jobs)))
                self.assertEqual(len(json.loads((directory / 'summary.json').read_text())),
                                 4 * len(meta['implementations']))


if __name__ == '__main__':
    unittest.main()
