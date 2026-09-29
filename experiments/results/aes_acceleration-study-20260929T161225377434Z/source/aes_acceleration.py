"""Paired AES-NI versus portable native AES benchmark on the same host."""
import hashlib
import json
from pathlib import Path
import random
import shutil
from time import perf_counter_ns, process_time_ns, get_clock_info
from uuid import uuid4

from common import key_for, modules, parser, positive, print_plan, save_run, stats
from cpu_validation import VECTORS, utc_now
from benchmark import environment_snapshot

VARIANTS = ("AES-128", "AES-192", "AES-256")
BACKENDS = ("aesni", "software")


def cbc_cipher(key, iv, backend):
    if backend not in BACKENDS:
        raise ValueError("Explicit software or aesni backend required.")
    aes, _, _ = modules()
    return aes.new(key, aes.MODE_CBC, iv=iv, use_aesni=backend == "aesni")


def probe():
    aes, _, _ = modules()
    features = getattr(aes, "_cpu_features", None)
    supported = bool(features and features.have_aes_ni())
    loaded = getattr(aes, "_raw_aesni_lib", None) is not None
    return {"cpu_aesni": supported, "aesni_library_loaded": loaded,
            "available": supported and loaded,
            "aes_module_sha256": hashlib.sha256(Path(aes.__file__).read_bytes()).hexdigest()}


class StartObserver:
    """Observe native initialization outside the timed region."""
    def __init__(self, library, symbol, counts, label):
        self.library, self.symbol = library, symbol
        self.counts, self.label = counts, label

    def __getattr__(self, name):
        function = getattr(self.library, name)
        if name != self.symbol:
            return function

        def observed(*args):
            self.counts[self.label] += 1
            return function(*args)
        return observed


def verify_dispatch(mode="CBC"):
    if mode not in ("CBC", "ECB", "CTR"):
        raise ValueError("Unsupported dispatch verification mode.")
    evidence = probe()
    if not evidence["available"]:
        raise RuntimeError("AES-NI CPU support and native library are required; no fallback comparison.")
    aes, _, _ = modules()
    portable, accelerated = aes._raw_aes_lib, aes._raw_aesni_lib
    counts = {"software": 0, "aesni": 0}
    records = []
    # Private library handles are restored before timing, even on verification failure.
    try:
        aes._raw_aes_lib = StartObserver(portable, "AES_start_operation", counts, "software")
        aes._raw_aesni_lib = StartObserver(accelerated, "AESNI_start_operation", counts, "aesni")
        for key_bytes in (16, 24, 32):
            ciphertexts = []
            for backend in BACKENDS:
                counts.update(software=0, aesni=0)
                options = {"iv": bytes(16)} if mode == "CBC" else {}
                if mode == "CTR":
                    options = {"nonce": b"", "initial_value": 0}
                # CBC validation must observe the exact factory used by the benchmark.
                if mode == "CBC":
                    enc = cbc_cipher(bytes(key_bytes), bytes(16), backend)
                    dec = cbc_cipher(bytes(key_bytes), bytes(16), backend)
                else:
                    enc = aes.new(bytes(key_bytes), getattr(aes, "MODE_" + mode), **options,
                                  use_aesni=backend == "aesni")
                    dec = aes.new(bytes(key_bytes), getattr(aes, "MODE_" + mode), **options,
                                  use_aesni=backend == "aesni")
                encrypted = enc.encrypt(bytes(32))
                if dec.decrypt(encrypted) != bytes(32):
                    raise RuntimeError("AES preflight round-trip failed.")
                expected = {name: 2 if name == backend else 0 for name in BACKENDS}
                if counts != expected:
                    raise RuntimeError(f"Unexpected AES backend dispatch: {counts}")
                records.append({"key_bits": key_bytes * 8, "requested": backend,
                                "native_start_calls": dict(counts)})
                ciphertexts.append(encrypted)
            if ciphertexts[0] != ciphertexts[1]:
                raise RuntimeError("AES backends produced different ciphertexts.")
    finally:
        aes._raw_aes_lib, aes._raw_aesni_lib = portable, accelerated
    return {**evidence, "passed": True, "mode": mode, "preflight": records,
            "paths": {"software": "_raw_aes", "aesni": "_raw_aesni"},
            "scope": "Native backend initialization observed; not a CPU instruction trace."}


def validate_acceleration(path, session_id, purpose):
    """Persist dispatch and both-backend CBC KAT evidence before either timer."""
    report = {"passed": False, "mode": "CBC", "session_id": session_id,
              "purpose": purpose, "started_utc": utc_now(), "vectors": []}
    try:
        report["dispatch"] = verify_dispatch()
        for name, source, section, key, iv, plaintext, expected in VECTORS:
            if name not in VARIANTS:
                continue
            k, v, p, c = map(bytes.fromhex, (key, iv, plaintext, expected))
            outputs = []
            for backend in BACKENDS:
                row = dict(algorithm=name, backend=backend, source=source, section=section,
                           key=key, iv=iv, plaintext=plaintext, expected_ciphertext=expected,
                           passed=False)
                report["vectors"].append(row)
                encrypted = cbc_cipher(k, v, backend).encrypt(p)
                decrypted = cbc_cipher(k, v, backend).decrypt(c)
                row.update(encrypt_passed=encrypted == c, decrypt_passed=decrypted == p)
                row["passed"] = row["encrypt_passed"] and row["decrypt_passed"]
                if not row["passed"]:
                    raise RuntimeError(f"CBC NIST KAT failed: {name}/{backend}")
                outputs.append((encrypted, decrypted))
            if outputs[0] != outputs[1]:
                raise RuntimeError(f"Backend mismatch: {name}")
        report["backends_equal"] = True
        report["passed"] = True
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        report["completed_utc"] = utc_now()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as output:
            output.write(json.dumps(report, indent=2) + "\n")
    return report


def main():
    cli = parser(__doc__)
    cli.add_argument("--sizes", nargs="+", type=positive, default=[1024, 1048576, 10485760])
    cli.add_argument("--repeats", type=positive, default=10)
    cli.add_argument("--warmup", type=positive, default=2)
    args = cli.parse_args()
    if args.repeats < 2 or any(size % 16 for size in args.sizes):
        cli.error("Use at least 2 repeats and sizes divisible by 16.")
    if len(set(args.sizes)) != len(args.sizes):
        cli.error("Sizes must be distinct.")
    method = {"mode": "CBC", "padding": "none", "timer": "perf_counter_ns",
              "timed": "buffer transform and output allocation",
              "excluded": "preflight, key generation, setup, IV and correctness checks",
              "pairing": "same plaintext, key, IV and ciphertext for both backends",
              "order": "seeded shuffle of variants and backend/operation jobs per round",
              "throughput_unit": "decimal MB/s",
              "speedup": "median software seconds / median backend seconds",
              "protocol_version": "aesni-cbc-v2", "size_order": "CLI order",
              "wall_timer": "perf_counter_ns",
              "wall_timer_resolution_seconds": get_clock_info("perf_counter").resolution,
              "wall_timer_meaning": "monotonic wall elapsed time; primary performance metric",
              "process_cpu_timer": "process_time_ns",
              "process_cpu_timer_resolution_seconds": get_clock_info("process_time").resolution,
              "process_cpu_timer_meaning": "current process CPU time excluding time not executing; not CPU cycles",
              "timer_order": "process start, wall start, transform, wall end, process end",
              "process_cpu_scope": "diagnostic; outer interval includes wall timer bookkeeping",
              "process_to_wall_ratio": "process_cpu_ns / wall_elapsed_ns; not speedup; zero and >1 permitted",
              "allocation": "new output per call; prior output freed outside timers",
              "environment_cpu_policy": "system CPU utilization is context only; no threshold gate",
              "scope": "x86 AES-NI vs portable native library; not Python AES or 2003 hardware"}
    if print_plan("aes_acceleration", args, method):
        return
    session_id = str(uuid4())
    validation_path = args.output.resolve() / f"aesni-validation-{args.purpose}-{session_id}.json"
    method["session_id"] = session_id
    try:
        method["acceleration_validation"] = validate_acceleration(validation_path, session_id, args.purpose)
    except (AttributeError, OSError, RuntimeError) as exc:
        cli.error(str(exc))
    method["backend_verification"] = method["acceleration_validation"]["dispatch"]
    method["validation_file"] = str(validation_path)
    method["validation_sha256"] = hashlib.sha256(validation_path.read_bytes()).hexdigest()
    method["hardware_execution_path"] = "AES-NI/software native dispatch verified in preflight"
    method["environment_before"] = environment_snapshot()
    method["measurement_started_utc"] = utc_now()
    measurement_start = perf_counter_ns()
    rng = random.Random(args.seed)
    raw = []
    for size in args.sizes:
        plaintext = rng.randbytes(size)
        keys = {name: key_for(name, rng) for name in VARIANTS}
        for repeat in range(-args.warmup, args.repeats):
            names = list(VARIANTS)
            rng.shuffle(names)
            for variant_order, name in enumerate(names):
                key, iv = keys[name], rng.randbytes(16)
                expected = cbc_cipher(key, iv, "software").encrypt(plaintext)
                jobs = [(backend, operation) for backend in BACKENDS
                        for operation in ("encrypt", "decrypt")]
                rng.shuffle(jobs)
                for job_order, (backend, operation) in enumerate(jobs):
                    instance = cbc_cipher(key, iv, backend)
                    transform = getattr(instance, operation)
                    data = plaintext if operation == "encrypt" else expected
                    process_start = process_time_ns()
                    start = perf_counter_ns()
                    result = transform(data)
                    duration = perf_counter_ns() - start
                    cpu_ns = process_time_ns() - process_start
                    if result != (expected if operation == "encrypt" else plaintext):
                        raise RuntimeError(f"Backend correctness check failed: {name}/{backend}")
                    if duration <= 0:
                        raise RuntimeError("Timer resolution insufficient.")
                    if repeat >= 0:
                        raw.append({"session_id": session_id,
                                    "pair_id": f"{size}:{repeat}:{name}:{operation}",
                                    "variant_order": variant_order, "job_order": job_order,
                                    "algorithm": name, "backend": backend, "mode": "CBC",
                                    "bytes": size, "repeat": repeat, "operation": operation,
                                    "wall_elapsed_ns": duration, "process_cpu_ns": cpu_ns,
                                    "process_to_wall_ratio": cpu_ns / duration,
                                    "seconds": duration / 1e9,
                                    "throughput_MB_s": size * 1000 / duration})
                    del result
                del expected, data
        del plaintext
    method["measurement_elapsed_seconds"] = (perf_counter_ns() - measurement_start) / 1e9
    method["measurement_finished_utc"] = utc_now()
    method["environment_after"] = environment_snapshot()
    summary = []
    for name in VARIANTS:
        for size in args.sizes:
            for operation in ("encrypt", "decrypt"):
                paired = []
                for backend in BACKENDS:
                    selected = [r for r in raw if r["algorithm"] == name and r["bytes"] == size
                                and r["operation"] == operation and r["backend"] == backend]
                    row = {"session_id": session_id, "algorithm": name, "backend": backend, "mode": "CBC",
                           "bytes": size, "operation": operation}
                    for metric in ("seconds", "throughput_MB_s", "process_cpu_ns", "process_to_wall_ratio"):
                        row.update({f"{metric}_{k}": v for k, v in
                                    stats([r[metric] for r in selected]).items()})
                    paired.append(row)
                software_median = next(r["seconds_median"] for r in paired if r["backend"] == "software")
                for row in paired:
                    row["speedup_vs_software_median"] = software_median / row["seconds_median"]
                summary.extend(paired)
    directory = save_run("aes_acceleration", args, method, raw, summary)
    shutil.copyfile(validation_path, directory / "validation.json")
    source_directory = directory / "source"
    source_directory.mkdir()
    for filename in ("aes_acceleration.py", "common.py", "cpu_validation.py", "benchmark.py",
                     "export_results.py"):
        shutil.copyfile(Path(__file__).parent / filename, source_directory / filename)


if __name__ == "__main__":
    main()
