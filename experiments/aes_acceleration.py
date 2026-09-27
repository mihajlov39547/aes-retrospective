"""Paired AES-NI versus portable native AES benchmark on the same host."""
import hashlib
from pathlib import Path
import random
from time import perf_counter_ns

from common import key_for, modules, parser, positive, print_plan, save_run, stats

VARIANTS = ("AES-128", "AES-192", "AES-256")
BACKENDS = ("aesni", "software")


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


def verify_dispatch():
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
                enc = aes.new(bytes(key_bytes), aes.MODE_CBC, iv=bytes(16),
                              use_aesni=backend == "aesni")
                dec = aes.new(bytes(key_bytes), aes.MODE_CBC, iv=bytes(16),
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
    return {**evidence, "preflight": records,
            "scope": "Native backend initialization observed; not a CPU instruction trace."}


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
              "scope": "x86 AES-NI vs portable native library; not Python AES or 2003 hardware"}
    if print_plan("aes_acceleration", args, method):
        return
    try:
        method["backend_verification"] = verify_dispatch()
    except (AttributeError, OSError, RuntimeError) as exc:
        cli.error(str(exc))
    method["hardware_execution_path"] = "AES-NI/software native dispatch verified in preflight"
    aes, _, _ = modules()
    rng = random.Random(args.seed)
    raw = []
    for size in args.sizes:
        plaintext = rng.randbytes(size)
        keys = {name: key_for(name, rng) for name in VARIANTS}
        for repeat in range(-args.warmup, args.repeats):
            names = list(VARIANTS)
            rng.shuffle(names)
            for name in names:
                key, iv = keys[name], rng.randbytes(16)
                expected = aes.new(key, aes.MODE_CBC, iv=iv, use_aesni=False).encrypt(plaintext)
                jobs = [(backend, operation) for backend in BACKENDS
                        for operation in ("encrypt", "decrypt")]
                rng.shuffle(jobs)
                for backend, operation in jobs:
                    instance = aes.new(key, aes.MODE_CBC, iv=iv, use_aesni=backend == "aesni")
                    transform = getattr(instance, operation)
                    data = plaintext if operation == "encrypt" else expected
                    start = perf_counter_ns()
                    result = transform(data)
                    duration = perf_counter_ns() - start
                    if result != (expected if operation == "encrypt" else plaintext):
                        raise RuntimeError(f"Backend correctness check failed: {name}/{backend}")
                    if duration <= 0:
                        raise RuntimeError("Timer resolution insufficient.")
                    if repeat >= 0:
                        raw.append({"algorithm": name, "backend": backend, "mode": "CBC",
                                    "bytes": size, "repeat": repeat, "operation": operation,
                                    "seconds": duration / 1e9,
                                    "throughput_MB_s": size * 1000 / duration})
    summary = []
    for name in VARIANTS:
        for size in args.sizes:
            for operation in ("encrypt", "decrypt"):
                paired = []
                for backend in BACKENDS:
                    selected = [r for r in raw if r["algorithm"] == name and r["bytes"] == size
                                and r["operation"] == operation and r["backend"] == backend]
                    row = {"algorithm": name, "backend": backend, "mode": "CBC",
                           "bytes": size, "operation": operation}
                    for metric in ("seconds", "throughput_MB_s"):
                        row.update({f"{metric}_{k}": v for k, v in
                                    stats([r[metric] for r in selected]).items()})
                    paired.append(row)
                software_median = paired[1]["seconds_median"]
                for row in paired:
                    row["speedup_vs_software_median"] = software_median / row["seconds_median"]
                summary.extend(paired)
    save_run("aes_acceleration", args, method, raw, summary)


if __name__ == "__main__":
    main()
