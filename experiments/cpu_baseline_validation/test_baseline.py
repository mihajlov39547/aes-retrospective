"""Run after build.py: python -m unittest discover -s . -v"""
import copy
import ctypes as ct
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import struct
from aggregate import summarize, operation_duration, job_envelope, aggregate, write_summaries
from analyze_archives import diagnostics
from core import Native, check_input, inputs, validate
from run import schedule
from windows_native import require_x64_pe, verify_bindings, sha256


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
                        operation_start_ns=10**18,
                        operation_end_ns=10**18 + 100 + t * (2 if impl == 'openssl_default' else 1),
                        transform_ns=t * (2 if impl == 'openssl_default' else 1)))
        return rows, meta

    def test_negative_outcome_outlier_and_warmup(self):
        rows, meta = self.fixture()
        result = next(r for r in summarize(rows, meta) if r['implementation'] == 'openssl_default' and r['timing_boundary'] == 'transform')
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
        result = next(r for r in summarize(rows, meta) if r['implementation'] == 'openssl_default' and r['timing_boundary'] == 'transform')
        self.assertEqual(result['ratio_of_session_medians_py_over_impl'], 2.5)
        self.assertEqual(result['median_paired_ratio_py_over_impl'], .5)

    def test_multicore_envelope_not_sum(self):
        rows, meta = self.fixture()
        meta.update(experiment='multicore', workers=2)
        out = []
        for row in rows:
            row.update(experiment='multicore', workers=2, aggregate_envelope_ns=100, transform_ns=10)
            out.extend([dict(row, worker=0, operation_start_ns=1000, operation_end_ns=1080),
                        dict(row, worker=1, operation_start_ns=1020, operation_end_ns=1100)])
        result = next(r for r in summarize(out, meta) if r['timing_boundary'] == 'operation_envelope')
        self.assertEqual(result['samples'], 3)
        self.assertEqual(result['median_throughput_MB_s'], 20480)
        transforms = [r for r in summarize(out, meta) if r['timing_boundary'] == 'transform']
        self.assertEqual(len(transforms), 8)
        self.assertTrue(all(r['bytes_per_timing'] == 1024 and r['throughput_scope'] == 'per_worker' for r in transforms))

    def test_envelope_pairing_is_separate_from_transform_pairing(self):
        rows, meta = self.fixture()
        for row in rows:
            row['operation_end_ns'] = row['operation_start_ns'] + (100 if row['implementation'] == 'pycryptodome' else 50)
        output = [r for r in summarize(rows, meta) if r['implementation'] == 'openssl_default']
        for row in output:
            self.assertEqual(row['median_paired_ratio_py_over_impl'],
                             2 if row['timing_boundary'] == 'operation_envelope' else .5)
        # Input order cannot change pairing by repeat, implementation and boundary.
        self.assertEqual(summarize(rows, meta), summarize(list(reversed(rows)), meta))

    def test_single_multicore_comparable_boundary(self):
        rows, meta = self.fixture()
        for row in rows:
            row['operation_end_ns'] = row['operation_start_ns'] + 100
        single = next(r for r in summarize(rows, meta) if r['timing_boundary'] == 'operation_envelope')
        multi_meta = dict(meta, workers=2, experiment='multicore')
        multi_rows = [dict(r, worker=w, workers=2, experiment='multicore', aggregate_envelope_ns=100)
                      for r in rows for w in (0, 1)]
        multi = next(r for r in summarize(multi_rows, multi_meta) if r['timing_boundary'] == 'operation_envelope')
        self.assertEqual(single['median_ns'], multi['median_ns'])
        self.assertEqual(single['operation_boundary'], multi['operation_boundary'])
        self.assertEqual(multi['median_throughput_MB_s'], 2 * single['median_throughput_MB_s'])
        self.assertEqual(multi['samples'], single['samples'])

    def test_timestamp_precision_and_invalid_envelopes(self):
        row = dict(operation_start_ns=10**18, operation_end_ns=10**18+37,
                   operation_envelope_ns=37, aggregate_envelope_ns=37)
        self.assertEqual(operation_duration(row), 37)
        self.assertEqual(job_envelope([row]), 37)
        for bad in (dict(row, operation_envelope_ns=38), dict(row, operation_end_ns=10**18),
                    dict(row, aggregate_envelope_ns=40)):
            with self.assertRaises(ValueError):
                job_envelope([bad])

    def test_diagnostics_no_double_counting(self):
        rows, meta = self.fixture()
        for row in rows:
            row.update(operation_start_ns=1000, operation_end_ns=1200, allocation_ns=30,
                       setup_ns=5, transform_ns=50, cleanup_ns=5, native_call_ns=70,
                       buffer_binding_ns=10, ffi_noop_ns=10, ffi_residual_ns=10)
        diag = next(r for r in diagnostics(rows) if r['implementation'] == 'openssl_default')
        self.assertEqual(diag['accounted_nonoverlapping_ns'], 120)
        self.assertEqual(diag['uninstrumented_residual_ns'], 80)
        self.assertEqual(diag['critical_operation_ns'] + diag['critical_start_lag_ns'], diag['envelope_ns'])

    def test_legacy_export_never_overwrites(self):
        rows, meta = self.fixture()
        meta.update(status='complete', schema_version=1)
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / 'source', Path(tmp) / 'derived'
            source.mkdir()
            (source / 'metadata.json').write_text(json.dumps(meta))
            with (source / 'raw.csv').open('w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            (source / 'summary.json').write_text('historical summary')
            original = {p.name: p.read_bytes() for p in source.iterdir()}
            derived = aggregate(source, output)
            self.assertTrue(any(r['timing_boundary'] == 'operation_envelope' for r in derived))
            self.assertEqual(original, {p.name: p.read_bytes() for p in source.iterdir()})
            with self.assertRaises(FileExistsError):
                aggregate(source)
            with self.assertRaises(FileExistsError):
                aggregate(source, output)


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
                if sys.platform == 'win32':
                    for info in meta['worker_metadata']['openssl_default']:
                        self.assertEqual(set(info['windows_verified_bindings']),
                                         {'OpenSSL_version', 'EVP_EncryptUpdate', 'EVP_CIPHER_fetch'})
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
                                 4 * len(meta['implementations']) * (meta['workers'] + 1))
                for row in rows:
                    self.assertEqual(int(row['operation_envelope_ns']), operation_duration(row))
                    self.assertAlmostEqual(float(row['operation_throughput_MB_s']),
                                           int(row['bytes']) * 1000 / operation_duration(row))


class WindowsLoader(unittest.TestCase):
    def test_pe_architecture_and_resolved_import_checks(self):
        # Synthetic PE memory + mocked Win32 module APIs exercise the IAT parser on every OS.
        # Actual module mapping remains gated by native Windows smoke tests.
        image = bytearray(8192)
        image[:2] = b'MZ'
        struct.pack_into('<I', image, 0x3c, 128)
        image[128:132] = b'PE\0\0'
        struct.pack_into('<H', image, 132, 0x8664)
        optional = 152
        struct.pack_into('<H', image, optional, 0x20b)
        struct.pack_into('<I', image, optional + 56, len(image))
        struct.pack_into('<II', image, optional + 120, 4096, 40)
        struct.pack_into('<IIIII', image, 4096, 4300, 0, 0, 4200, 4400)
        image[4200:4200+len(b'libcrypto-3-x64.dll\0')] = b'libcrypto-3-x64.dll\0'
        names = ['OpenSSL_version', 'EVP_EncryptUpdate', 'EVP_CIPHER_fetch']
        for index, name in enumerate(names):
            address = 4600 + index*100
            struct.pack_into('<Q', image, 4300 + index*8, address)
            struct.pack_into('<Q', image, 4400 + index*8, 123456 + index)
            encoded = name.encode() + b'\0'
            image[address+2:address+2+len(encoded)] = encoded
        mapped = ct.create_string_buffer(bytes(image))
        wrapper = Mock(_handle=ct.addressof(mapped))
        kernel = Mock()
        with tempfile.TemporaryDirectory() as tmp:
            dll = Path(tmp) / 'expected.dll'
            dll.write_bytes(image)
            require_x64_pe(dll)
            wrong = Path(tmp) / 'wrong.dll'
            wrong.write_bytes(image)
            def module(flags, address, out):
                self.assertEqual(flags, 6)
                out._obj.value = 123
                return 1
            resolved_path = str(dll.resolve())
            def module_path(handle, output, size):
                output.value = resolved_path
                return len(resolved_path)
            kernel.GetModuleHandleExW.side_effect = module
            kernel.GetModuleFileNameW.side_effect = module_path
            with patch.object(ct, 'WinDLL', return_value=kernel, create=True):
                evidence = verify_bindings(wrapper, dll, sha256(dll))
                self.assertEqual(set(evidence), set(names))
                resolved_path = str(wrong.resolve())
                with self.assertRaisesRegex(RuntimeError, 'Unintended libcrypto'):
                    verify_bindings(wrapper, dll, sha256(dll))
                with self.assertRaisesRegex(RuntimeError, 'changed since build'):
                    verify_bindings(wrapper, dll, 'incorrect hash')
            image[132:134] = b'\x4c\x01'  # x86, not x64
            wrong.write_bytes(image)
            with self.assertRaisesRegex(RuntimeError, 'x86-64'):
                require_x64_pe(wrong)


if __name__ == '__main__':
    unittest.main()
