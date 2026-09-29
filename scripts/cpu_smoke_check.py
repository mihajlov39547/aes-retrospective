"""Experiment 1 checks only; no acceleration, CUDA, search or avalanche imports."""
import csv
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import benchmark
import cpu_validation
from common import ROOT, cipher, key_for, stats


class CPUChecks(unittest.TestCase):
    def test_known_answers_and_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = cpu_validation.validate_cpu(Path(tmp) / "validation.json")
        self.assertTrue(report["passed"])
        self.assertEqual(len(report["vectors"]), 5)
        self.assertEqual(report["dispatch"]["native_start_calls"],
                         {name: 2 for name in ("AES-128", "AES-192", "AES-256")})

    def test_each_bad_operation_stops_before_timing(self):
        for target, *_ in cpu_validation.VECTORS:
            for operation in ("encrypt", "decrypt"):
                with self.subTest(algorithm=target, operation=operation), tempfile.TemporaryDirectory() as tmp:
                    def broken(name, *args, **kwargs):
                        obj = cipher(name, *args, **kwargs)
                        if name == target:
                            setattr(obj, operation, lambda data: bytes(len(data)))
                        return obj
                    argv = ["benchmark.py", "--run", "--purpose", "smoke", "--output", tmp]
                    with patch.object(sys, "argv", argv), patch.object(cpu_validation, "cipher", broken), \
                            patch.object(benchmark, "perf_counter_ns") as timer, \
                            patch.object(benchmark, "save_run") as save:
                        with self.assertRaises(RuntimeError):
                            benchmark.main()
                        timer.assert_not_called()
                        save.assert_not_called()
                    files = list(Path(tmp).glob("*.json"))
                    self.assertEqual(len(files), 1)
                    self.assertFalse(json.loads(files[0].read_text())["passed"])

    def test_tdea_rejects_two_key_case(self):
        k1 = bytes.fromhex("0123456789abcdef")
        k2 = bytes.fromhex("23456789abcdef01")
        k3 = bytes.fromhex("456789abcdef0123")
        rng = random.Random(1)
        with patch.object(rng, "randbytes", side_effect=[k1+k2+k1, k1+k2+k3]):
            self.assertEqual(key_for("3DES", rng), k1+k2+k3)
        for _ in range(20):
            key = key_for("3DES", rng)
            self.assertEqual(len({key[:8], key[8:16], key[16:]}), 3)
            self.assertTrue(all(byte.bit_count() % 2 == 1 for byte in key))

    def test_des_parity_ignored(self):
        _, _, _, k, iv, p, c = cpu_validation.VECTORS[0]
        key = bytes(x ^ 1 for x in bytes.fromhex(k))
        self.assertEqual(cipher("DES", key, "CBC", bytes.fromhex(iv)).encrypt(bytes.fromhex(p)),
                         bytes.fromhex(c))

    def test_sample_statistics(self):
        self.assertEqual(stats([1., 2., 3.]),
                         dict(count=3, mean=2., median=2., stdev=1., min=1., max=3.))
        self.assertIsNone(stats([1.])["stdev"])

    def test_cli_and_export(self):
        def invoke(script, *args, success=True):
            result = subprocess.run([sys.executable, str(ROOT / "scripts" / script), *map(str, args)],
                                    capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(result.returncode == 0, success, result.stderr)
            return result
        for args in (("--sizes", 17), ("--repeats", 1), ("--sizes", 16, 16),
                     ("--purpose", "study", "--aes-backend", "auto")):
            invoke("benchmark.py", *args, success=False)
        result = invoke("benchmark.py", "--run", "--purpose", "smoke", "--output",
                        ROOT / "build" / "cpu-smoke", "--sizes", 1024, "--warmup", 1, "--repeats", 2)
        folder = Path(result.stdout.strip().splitlines()[-1])
        meta = json.loads((folder / "metadata.json").read_text())
        self.assertLess(meta["method"]["cpu_validation"]["completed_utc"],
                        meta["method"]["measurement_started_utc"])
        with (folder / "raw.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 20)
        for row in rows:
            self.assertGreater(float(row["seconds"]), 0)
            self.assertAlmostEqual(float(row["seconds"]) * float(row["throughput_MB_s"]), .001024)
        invoke("export_results.py", folder)
        for suffix in ("png", "pdf", "tex"):
            name = "benchmark_table.tex" if suffix == "tex" else f"benchmark.{suffix}"
            self.assertGreater((folder / name).stat().st_size, 100)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "metadata.json").write_text(json.dumps(dict(experiment="benchmark", method={})))
            invoke("export_results.py", tmp, success=False)


if __name__ == "__main__":
    unittest.main(verbosity=2)
