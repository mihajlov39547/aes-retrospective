"""Isolated AES-GCM unit/integration checks; never pilot/study or large inputs."""
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

import aes_gcm_benchmark as gcm
from common import ROOT, modules


class GCMChecks(unittest.TestCase):
    def invoke(self, *args, success=True):
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "aes_gcm_benchmark.py"),
                                 *map(str, args)], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, success, result.stderr)
        return result

    def test_plan_and_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "no-output"
            plan = json.loads(self.invoke("--output", target).stdout)
            self.assertEqual(plan["status"], "plan_only")
            self.assertEqual(plan["experiment"], "aes_gcm")
            self.assertEqual(plan["arguments"]["sizes"], [1024, 16384, 1048576, 16777216, 104857600])
            self.assertFalse(target.exists())
            self.invoke("--sizes", 17, "--output", target)  # No block-alignment rule.
            for args in (("--sizes", 0), ("--sizes", -1), ("--sizes", 17, 17),
                         ("--warmup", 0), ("--repeats", 1), ("--purpose", "invalid"),
                         ("--sizes", gcm.MAX_PAYLOAD + 1), ("--repeats", 2**32)):
                self.invoke(*args, "--output", target, success=False)
            self.assertFalse(target.exists())

    def test_kat_dispatch_and_authentication(self):
        aes, _, _ = modules()
        handles = aes._raw_aes_lib, aes._raw_aesni_lib
        with tempfile.TemporaryDirectory() as tmp:
            report = gcm.validate_gcm(Path(tmp) / "validation.json", "unit", "smoke")
        self.assertTrue(report["passed"])
        self.assertEqual(len(report["vectors"]), 4)
        self.assertEqual(len(report["dispatch"]["records"]), 8)
        for r in report["vectors"]:
            for field in ("ciphertext_passed", "tag_passed", "decrypt_verify_passed",
                          "modified_tag_rejected", "modified_ciphertext_rejected", "modified_aad_rejected"):
                self.assertTrue(r[field])
        for r in report["dispatch"]["records"]:
            self.assertEqual(r["native_start_calls"], {b: 3 if b == r["backend"] else 0 for b in ("software", "aesni")})
        self.assertIs(aes._raw_aes_lib, handles[0])
        self.assertIs(aes._raw_aesni_lib, handles[1])

    def assert_gate_stops(self, tmp):
        argv = ["aes_gcm_benchmark.py", "--run", "--purpose", "smoke", "--sizes", "1024",
                "--warmup", "1", "--repeats", "2", "--output", tmp]
        with patch.object(sys, "argv", argv), patch.object(gcm, "perf_counter_ns") as wall, \
                patch.object(gcm, "process_time_ns") as cpu, patch.object(gcm, "save_run") as save:
            with self.assertRaises((RuntimeError, ValueError, AttributeError)):
                gcm.main()
            wall.assert_not_called()
            cpu.assert_not_called()
            save.assert_not_called()
        files = list(Path(tmp).iterdir())
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].is_file())
        report = json.loads(files[0].read_text())
        self.assertFalse(report["passed"])
        return report

    def test_capability_and_fallback_guards(self):
        aes, _, _ = modules()
        for field in ("_cpu_features", "_raw_aesni_lib"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp, patch.object(aes, field, None):
                self.assert_gate_stops(tmp)
        factory = gcm.gcm_cipher
        handles = aes._raw_aes_lib, aes._raw_aesni_lib
        with tempfile.TemporaryDirectory() as tmp, patch.object(gcm, "gcm_cipher", side_effect=lambda key, nonce, backend="aesni": factory(key, nonce, "software")):
            self.assertIn("dispatch", self.assert_gate_stops(tmp)["error"])
        self.assertIs(aes._raw_aes_lib, handles[0])
        self.assertIs(aes._raw_aesni_lib, handles[1])

    def test_failed_ciphertext_tag_decrypt_or_authentication_stops(self):
        enc, dec = gcm.encrypt_message, gcm.decrypt_message
        for bits in (128, 256):
            for fault in ("ciphertext", "tag", "plaintext", "accept_corruption"):
                with self.subTest(bits=bits, fault=fault), tempfile.TemporaryDirectory() as tmp:
                    def bad_enc(instance, data, aad):
                        c, t = enc(instance, data, aad)
                        if len(instance._key)*8 == bits:
                            if fault == "ciphertext": c = bytes([c[0] ^ 1]) + c[1:]
                            if fault == "tag": t = bytes([t[0] ^ 1]) + t[1:]
                        return c, t

                    def bad_dec(instance, data, tag, aad):
                        if len(instance._key)*8 == bits and fault == "accept_corruption":
                            instance.update(aad)
                            return instance.decrypt(data)  # Deliberately omit authentication.
                        p = dec(instance, data, tag, aad)
                        return bytes([p[0] ^ 1]) + p[1:] if len(instance._key)*8 == bits and fault == "plaintext" else p

                    with patch.object(gcm, "encrypt_message", side_effect=bad_enc), patch.object(gcm, "decrypt_message", side_effect=bad_dec):
                        report = self.assert_gate_stops(tmp)
                    if fault == "accept_corruption":
                        self.assertTrue(report["dispatch"]["passed"])
                        self.assertFalse(report["vectors"][-1]["modified_tag_rejected"])

    def test_deterministic_inputs_nonce_and_unaligned_messages(self):
        self.assertEqual(len(gcm.AAD), 16)
        for bits in (128, 256):
            key = gcm.benchmark_key(2003, bits)
            self.assertEqual(key, gcm.benchmark_key(2003, bits))
            self.assertNotEqual(key, gcm.benchmark_key(2004, bits))
            seen = set()
            for size in (1, 17, 1024):
                p = gcm.benchmark_plaintext(2003, size)
                self.assertEqual(p, gcm.benchmark_plaintext(2003, size))
                for index in range(3):
                    nonce = gcm.message_nonce(size, index)
                    self.assertEqual(len(nonce), 12)
                    self.assertNotIn(nonce, seen)
                    seen.add(nonce)
                    c, tag = gcm.encrypt_message(gcm.gcm_cipher(key, nonce), p, gcm.AAD)
                    self.assertEqual(len(c), size)
                    self.assertEqual(len(tag), 16)
                    self.assertEqual(gcm.decrypt_message(gcm.gcm_cipher(key, nonce), c, tag, gcm.AAD), p)
            self.assertEqual(sorted(seen), sorted(gcm.message_nonce(size, i) for size in (1024, 17, 1) for i in range(3)))

    def test_timed_scope_order_and_reproducible_jobs(self):
        # Fake clocks make this a unit test, not a performance sample.
        factory = gcm.gcm_cipher

        def run():
            with tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp) / "run"
                folder.mkdir()
                events, jobs, constructions = [], [], []
                active = False
                wall_ticks = itertools.count(0, 100)
                cpu_ticks = itertools.accumulate(itertools.cycle((0, 0, 0, 300)))

                def validated():
                    paths = list(Path(tmp).glob("gcm-validation-*.json"))
                    self.assertEqual(len(paths), 1)
                    self.assertTrue(json.loads(paths[0].read_text())["passed"])

                def wall():
                    validated()
                    events.append("wall")
                    return next(wall_ticks)

                def cpu():
                    nonlocal active
                    validated()
                    events.append("cpu")
                    active = not active
                    return next(cpu_ticks)

                def observed(key, nonce, backend="aesni"):
                    self.assertFalse(active, "GCM construction must be outside timers")
                    obj = factory(key, nonce, backend)
                    after_gate = bool(list(Path(tmp).glob("gcm-validation-*.json")))
                    if after_gate: constructions.append((key, nonce, backend))
                    class Cipher:
                        def update(self, aad):
                            if after_gate:
                                self_aad = aad
                                self.aad = self_aad
                                if backend == "aesni":
                                    self_outer.assertTrue(active, "AAD processing must be timed")
                                    events.append("aad")
                            obj.update(aad)

                        def encrypt_and_digest(self, data):
                            if after_gate:
                                jobs.append((key, nonce, backend, "encrypt", data, self.aad, active))
                                if backend == "aesni": events.append("encrypt_and_digest")
                            return obj.encrypt_and_digest(data)

                        def decrypt_and_verify(self, data, tag):
                            if after_gate:
                                jobs.append((key, nonce, backend, "decrypt", data, self.aad, active))
                                events.append("decrypt_and_verify")
                            return obj.decrypt_and_verify(data, tag)
                    self_outer = self
                    return Cipher()

                def save(name, args, method, raw, summary):
                    (folder / "metadata.json").write_text(json.dumps({"method": method}))
                    self.assertEqual(len(raw), 8)
                    self.assertEqual({r["process_to_wall_ratio"] for r in raw}, {0., 3.})
                    self.assertTrue(all(r["throughput_MB_s"] == 1024 * 1000 / 100 for r in raw))
                    self.assertEqual(len(summary), 4)
                    return folder

                argv = ["aes_gcm_benchmark.py", "--run", "--purpose", "smoke", "--sizes", "1024",
                        "--warmup", "1", "--repeats", "2", "--output", tmp]
                with patch.object(sys, "argv", argv), patch.object(gcm, "gcm_cipher", side_effect=observed), \
                        patch.object(gcm, "environment_snapshot", return_value={"cpu_percent_1s": 99}), \
                        patch.object(gcm, "perf_counter_ns", side_effect=wall), patch.object(gcm, "process_time_ns", side_effect=cpu), \
                        patch.object(gcm, "save_run", side_effect=save):
                    gcm.main()
                self.assertEqual(len(constructions), 18)  # 6 messages: reference + fresh encrypt + fresh decrypt.
                for i in range(0, len(events), 6):
                    self.assertEqual(events[i:i+3], ["cpu", "wall", "aad"])
                    self.assertIn(events[i+3], ("encrypt_and_digest", "decrypt_and_verify"))
                    self.assertEqual(events[i+4:i+6], ["wall", "cpu"])
                self.assertEqual(len(events), 72)
                grouped = {}
                for key, nonce, backend, operation, data, aad, timed in jobs:
                    self.assertEqual(timed, backend == "aesni")
                    self.assertEqual(aad, gcm.AAD)
                    grouped.setdefault((key, nonce), []).append((backend, operation, data))
                self.assertEqual(len(grouped), 6)
                for group in grouped.values():
                    encryptions = [r[2] for r in group if r[1] == "encrypt"]
                    self.assertEqual(len(group), 3)
                    self.assertEqual(encryptions[0], encryptions[1])
                return jobs
        self.assertEqual(run(), run())

    def test_small_smoke_output(self):
        result = self.invoke("--run", "--purpose", "smoke", "--sizes", 1024, "--warmup", 1,
                             "--repeats", 2, "--seed", 2003, "--output", ROOT / "build" / "aes-gcm-smoke")
        folder = Path(result.stdout.strip().splitlines()[-1])
        meta = json.loads((folder / "metadata.json").read_text())
        validation = json.loads((folder / "validation.json").read_text())
        self.assertEqual(meta["experiment"], "aes_gcm")
        self.assertEqual(meta["purpose"], "smoke")
        self.assertTrue(validation["passed"])
        self.assertEqual(meta["session_id"], validation["session_id"])
        self.assertLess(validation["completed_utc"], meta["method"]["measurement_started_utc"])
        self.assertEqual(hashlib.sha256((folder / "validation.json").read_bytes()).hexdigest(), meta["method"]["validation_sha256"])
        for path in (folder / "source").iterdir():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), meta["script_sha256"][path.name])
        for metric in ("wall_timer_resolution_seconds", "process_cpu_timer_resolution_seconds"):
            self.assertGreater(meta["method"][metric], 0)
        with (folder / "raw.csv").open(newline="") as stream: raw = list(csv.DictReader(stream))
        with (folder / "summary.csv").open(newline="") as stream: summary = list(csv.DictReader(stream))
        self.assertEqual(len(raw), 8)
        self.assertEqual(len(summary), 4)
        results = json.loads((folder / "results.json").read_text())
        self.assertEqual(raw, [{k: str(v) for k, v in r.items()} for r in results["raw"]])
        for r in raw:
            self.assertNotIn("key", r)
            self.assertEqual(r["mode"], "GCM")
            self.assertEqual(r["session_id"], meta["session_id"])
            self.assertEqual((r["nonce_bytes"], r["aad_bytes"], r["tag_bytes"]), ("12", "16", "16"))
            self.assertIn(int(r["repeat"]), (0, 1))
            self.assertIn(int(r["variant_order"]), (0, 1))
            self.assertIn(int(r["job_order"]), (0, 1))
            wall, cpu = int(r["wall_elapsed_ns"]), int(r["process_cpu_ns"])
            self.assertGreater(wall, 0)
            self.assertGreaterEqual(cpu, 0)
            self.assertEqual(float(r["seconds"]), wall / 1e9)
            self.assertAlmostEqual(float(r["throughput_MB_s"]), 1024 * 1000 / wall)
            self.assertAlmostEqual(float(r["process_to_wall_ratio"]), cpu / wall)
        for r in summary:
            self.assertFalse(any("speedup" in k for k in r))
            selected = [x for x in raw if all(x[k] == r[k] for k in ("algorithm", "bytes", "operation"))]
            for metric in ("seconds", "throughput_MB_s", "process_cpu_ns", "process_to_wall_ratio"):
                values = [float(x[metric]) for x in selected]
                self.assertEqual(int(r[metric+"_count"]), 2)
                for name, function in (("mean", statistics.mean), ("median", statistics.median),
                                       ("stdev", statistics.stdev), ("min", min), ("max", max)):
                    self.assertAlmostEqual(float(r[metric+"_"+name]), function(values))
        print(f"GCM smoke only: {folder}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
