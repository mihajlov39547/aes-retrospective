"""Isolated Experiment 2 checks; only 1 KiB purpose=smoke measurements."""
import contextlib
import csv
import hashlib
import io
import itertools
import json
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import aes_acceleration as experiment
from common import ROOT, modules
from export_results import verify_acceleration_export, verify_acceleration_summary


class AESAccelerationChecks(unittest.TestCase):
    def test_probe_dispatch_and_kat(self):
        evidence = experiment.probe()
        self.assertTrue(evidence["cpu_aesni"], "CPU AES-NI is required; no fallback or skip")
        self.assertTrue(evidence["aesni_library_loaded"])
        self.assertTrue(evidence["available"])
        with tempfile.TemporaryDirectory() as tmp:
            report = experiment.validate_acceleration(Path(tmp) / "validation.json", "test", "smoke")
        self.assertTrue(report["passed"])
        self.assertTrue(report["backends_equal"])
        self.assertEqual(len(report["vectors"]), 6)
        for row in report["vectors"]:
            self.assertTrue(row["encrypt_passed"] and row["decrypt_passed"])
        for row in report["dispatch"]["preflight"]:
            self.assertEqual(row["native_start_calls"],
                             {b: 2 if b == row["requested"] else 0 for b in experiment.BACKENDS})

    def assert_stops_before_timing(self, tmp):
        argv = ["aes_acceleration.py", "--run", "--purpose", "smoke", "--output", tmp,
                "--sizes", "1024", "--warmup", "1", "--repeats", "2"]
        with patch.object(sys, "argv", argv), contextlib.redirect_stderr(io.StringIO()), \
                patch.object(experiment, "perf_counter_ns") as wall, \
                patch.object(experiment, "process_time_ns") as cpu, \
                patch.object(experiment, "save_run") as save:
            with self.assertRaises(SystemExit):
                experiment.main()
            wall.assert_not_called()
            cpu.assert_not_called()
            save.assert_not_called()
        files = list(Path(tmp).glob("*.json"))
        self.assertEqual(len(files), 1)
        report = json.loads(files[0].read_text())
        self.assertFalse(report["passed"])
        return report

    def test_missing_capability_library_and_fallback_stop(self):
        aes, _, _ = modules()
        for field, value in (("_cpu_features", None), ("_raw_aesni_lib", None)):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp, patch.object(aes, field, value):
                self.assertFalse(experiment.probe()["available"])
                self.assert_stops_before_timing(tmp)
        factory = experiment.cbc_cipher
        original_handles = (aes._raw_aes_lib, aes._raw_aesni_lib)
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(experiment, "cbc_cipher", side_effect=lambda key, iv, backend: factory(key, iv, "software")):
            report = self.assert_stops_before_timing(tmp)
            self.assertIn("dispatch", report["error"])
        self.assertIs(aes._raw_aes_lib, original_handles[0])
        self.assertIs(aes._raw_aesni_lib, original_handles[1])

    def test_each_failed_kat_stops_before_timers(self):
        factory = experiment.cbc_cipher
        for size in (16, 24, 32):
            for backend in experiment.BACKENDS:
                for operation in ("encrypt", "decrypt"):
                    with self.subTest(size=size, backend=backend, operation=operation), tempfile.TemporaryDirectory() as tmp:
                        def broken(key, iv, requested):
                            obj = factory(key, iv, requested)
                            # Dispatch preflight uses zero keys; corrupt the NIST KAT only.
                            if len(key) == size and any(key) and requested == backend:
                                setattr(obj, operation, lambda data: bytes(len(data)))
                            return obj
                        with patch.object(experiment, "cbc_cipher", side_effect=broken):
                            report = self.assert_stops_before_timing(tmp)
                        self.assertTrue(report["dispatch"]["passed"])
                        self.assertIn("KAT failed", report["error"])

    def test_pairing_order_and_timer_diagnostics(self):
        factory = experiment.cbc_cipher

        def run():
            with tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp) / "run"
                folder.mkdir()
                records, events = [], []
                active = False
                wall_ticks = itertools.count(0, 100)
                cpu_ticks = itertools.accumulate(itertools.cycle((0, 0, 0, 300)))

                def check_validation():
                    files = list(Path(tmp).glob("aesni-validation-*.json"))
                    self.assertEqual(len(files), 1)
                    self.assertTrue(json.loads(files[0].read_text())["passed"])

                def wall():
                    check_validation()
                    events.append("wall")
                    return next(wall_ticks)

                def cpu():
                    nonlocal active
                    check_validation()
                    events.append("process")
                    active = not active
                    return next(cpu_ticks)

                def observed(key, iv, backend):
                    obj = factory(key, iv, backend)
                    class Cipher:
                        def encrypt(self, data):
                            if active:
                                records.append((key, iv, backend, "encrypt", data))
                            return obj.encrypt(data)

                        def decrypt(self, data):
                            if active:
                                records.append((key, iv, backend, "decrypt", data))
                            return obj.decrypt(data)
                    return Cipher()

                argv = ["aes_acceleration.py", "--run", "--purpose", "smoke", "--output", tmp,
                        "--sizes", "1024", "--warmup", "1", "--repeats", "2", "--seed", "2003"]
                with patch.object(sys, "argv", argv), patch.object(experiment, "cbc_cipher", side_effect=observed), \
                        patch.object(experiment, "environment_snapshot", return_value={"cpu_percent_1s": 99}), \
                        patch.object(experiment, "perf_counter_ns", side_effect=wall), \
                        patch.object(experiment, "process_time_ns", side_effect=cpu), \
                        patch.object(experiment, "save_run", return_value=folder) as save:
                    experiment.main()
                raw = save.call_args.args[3]
                self.assertEqual({r["process_to_wall_ratio"] for r in raw}, {0., 3.})
                self.assertTrue(all(r["throughput_MB_s"] == 1024 * 1000 / 100 for r in raw))
                self.assertEqual(events, ["wall"] + ["process", "wall", "wall", "process"] * 36 + ["wall"])
                self.assertEqual(len(records), 36)
                for start in range(0, len(records), 4):
                    group = records[start:start+4]
                    self.assertEqual(len({(r[0], r[1]) for r in group}), 1)
                    for op in ("encrypt", "decrypt"):
                        pair = [r for r in group if r[3] == op]
                        self.assertEqual({r[2] for r in pair}, set(experiment.BACKENDS))
                        self.assertEqual(pair[0][4], pair[1][4])
                self.assertGreater(len({tuple((r[2], r[3]) for r in records[i:i+4])
                                        for i in range(0, 36, 4)}), 1)
                return records
        self.assertEqual(run(), run())

    def test_smoke_run_statistics_and_export(self):
        def invoke(script, *args, success=True):
            result = subprocess.run([sys.executable, str(ROOT / "scripts" / script), *map(str, args)],
                                    cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode == 0, success, result.stderr)
            return result
        plan = json.loads(invoke("aes_acceleration.py").stdout)
        self.assertEqual(plan["status"], "plan_only")
        for args in (("--sizes", 17), ("--sizes", 1024, 1024), ("--repeats", 1)):
            invoke("aes_acceleration.py", *args, success=False)
        result = invoke("aes_acceleration.py", "--run", "--purpose", "smoke", "--sizes", 1024,
                        "--warmup", 1, "--repeats", 2, "--seed", 2003,
                        "--output", ROOT / "build" / "aes-acceleration-smoke")
        folder = Path(result.stdout.strip().splitlines()[-1])
        metadata = json.loads((folder / "metadata.json").read_text())
        self.assertEqual(metadata["purpose"], "smoke")
        verify_acceleration_export(folder, metadata)
        for f in (folder / "source").iterdir():
            self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest(), metadata["script_sha256"][f.name])
        for field in ("wall_timer_resolution_seconds", "process_cpu_timer_resolution_seconds"):
            self.assertGreater(metadata["method"][field], 0)
        with (folder / "raw.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        with (folder / "summary.csv").open(newline="") as stream:
            summary = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 24)
        self.assertEqual(len(summary), 12)
        pairs = {}
        for r in rows:
            self.assertEqual(r["session_id"], metadata["method"]["session_id"])
            self.assertGreater(int(r["wall_elapsed_ns"]), 0)
            self.assertGreaterEqual(int(r["process_cpu_ns"]), 0)
            self.assertEqual(float(r["seconds"]), int(r["wall_elapsed_ns"]) / 1e9)
            self.assertAlmostEqual(float(r["throughput_MB_s"]), int(r["bytes"]) * 1000 / int(r["wall_elapsed_ns"]))
            self.assertAlmostEqual(float(r["process_to_wall_ratio"]), int(r["process_cpu_ns"]) / int(r["wall_elapsed_ns"]))
            pairs.setdefault(r["pair_id"], []).append(r)
        self.assertEqual(len(pairs), 12)
        for pair in pairs.values():
            self.assertEqual({r["backend"] for r in pair}, set(experiment.BACKENDS))
            self.assertEqual(len(pair), 2)
        for r in summary:
            selected = [x for x in rows if all(x[k] == r[k] for k in ("algorithm", "backend", "operation", "bytes"))]
            for metric in ("seconds", "throughput_MB_s", "process_cpu_ns", "process_to_wall_ratio"):
                values = [float(x[metric]) for x in selected]
                self.assertEqual(int(r[metric+"_count"]), 2)
                for name, function in (("mean", statistics.mean), ("median", statistics.median),
                                       ("stdev", statistics.stdev), ("min", min), ("max", max)):
                    self.assertAlmostEqual(float(r[metric+"_"+name]), function(values))
            software = next(x for x in summary if x["backend"] == "software"
                            and all(x[k] == r[k] for k in ("algorithm", "operation", "bytes")))
            self.assertEqual(float(r["speedup_vs_software_median"]),
                             float(software["seconds_median"]) / float(r["seconds_median"]))
        verify_acceleration_summary(summary, metadata)
        invoke("export_results.py", folder)
        for name in ("aes_acceleration_table.tex", "aes_acceleration.png", "aes_acceleration.pdf",
                     "aes_acceleration_speedup.png", "aes_acceleration_speedup.pdf"):
            self.assertGreater((folder / name).stat().st_size, 100)
        table = (folder / "aes_acceleration_table.tex").read_text()
        self.assertIn("purpose: smoke", table)
        self.assertIn("software", table)
        self.assertIn("aesni", table)
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp)
            (bad / "metadata.json").write_text(json.dumps(metadata))
            invoke("export_results.py", bad, success=False)
            (bad / "validation.json").write_text('{}')
            invoke("export_results.py", bad, success=False)
            self.assertFalse(list(bad.glob("*.png")))
        for mutation in ("failed", "incomplete", "late", "dispatch"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                bad = Path(tmp)
                altered = json.loads(json.dumps(metadata))
                report = altered["method"]["acceleration_validation"]
                if mutation == "failed": report["passed"] = False
                if mutation == "incomplete": report["vectors"].pop()
                if mutation == "late": report["completed_utc"] = "9999"
                if mutation == "dispatch": report["dispatch"]["preflight"][0]["native_start_calls"] = {}
                data = json.dumps(report).encode()
                (bad / "validation.json").write_bytes(data)
                altered["method"]["validation_sha256"] = hashlib.sha256(data).hexdigest()
                with self.assertRaises(ValueError):
                    verify_acceleration_export(bad, altered)
        broken = [dict(r) for r in summary]
        broken[0]["speedup_vs_software_median"] = "99999"
        with self.assertRaises(ValueError): verify_acceleration_summary(broken, metadata)
        with self.assertRaises(ValueError): verify_acceleration_summary(summary[:-1], metadata)
        print(f"Experiment 2 smoke artifacts: {folder}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
