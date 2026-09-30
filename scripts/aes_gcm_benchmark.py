"""AES-GCM payload AEAD benchmark (fresh-object setup excluded).

Only --run measures. Study protocol is not yet locked. Defaults: AES-128/256,
1 KiB/16 KiB/1 MiB/16 MiB/100 MiB, 2 warmups, 10 repeats. No CBC comparison.
Timed: update(AAD) + encrypt_and_digest or decrypt_and_verify, with allocation.
Untimed: new GCM object (including H, key schedules and GHASH setup), inputs,
software reference, validation, output comparison/disposal, file writes.
This is complete authenticated payload processing, NOT setup-inclusive latency.
"""
import hashlib
import json
from pathlib import Path
import random
import shutil
from time import perf_counter_ns, process_time_ns, get_clock_info
from unittest.mock import patch
from uuid import uuid4

from common import key_for, modules, parser, positive, print_plan, save_run, stats
from aes_acceleration import probe, StartObserver
from benchmark import environment_snapshot
from cpu_validation import utc_now

VARIANTS = {"AES-128-GCM": 128, "AES-256-GCM": 256}
AAD = b"AES-GCM-bench-v1"  # Exactly 16 bytes, fixed across every measured message.
NONCE_BYTES, TAG_BYTES = 12, 16
MAX_PAYLOAD = 2**36 - 32  # SP 800-38D: len(P) <= 2**39 - 256 bits.
SOURCE = "https://csrc.nist.gov/CSRC/media/Projects/Cryptographic-Standards-and-Guidelines/documents/examples/AES_GCM.pdf"
# NIST GCM-AES128 and GCM-AES256, Example #5, printed PDF pages 7-9 / 27-29.
# These published KATs intentionally use 20-byte AAD and a 60-byte payload.
VECTORS = [
    dict(algorithm="AES-128-GCM", section="GCM-AES128 Example #5, pp. 7-9",
         key="feffe9928665731c6d6a8f9467308308",
         ciphertext="42831ec2217774244b7221b784d0d49ce3aa212f2c02a4e035c17e2329aca12e"
                    "21d514b25466931c7d8f6a5aac84aa051ba30b396a0aac973d58e091",
         tag="f07c2528eea2fca1211f905e1b6a881b"),
    dict(algorithm="AES-256-GCM", section="GCM-AES256 Example #5, pp. 27-29",
         key="feffe9928665731c6d6a8f9467308308feffe9928665731c6d6a8f9467308308",
         ciphertext="522dc1f099567d07f47f37a32a84427d643a8cdcbfe5c0c97598a2bd2555d1aa"
                    "8cb08e48590dbb3da7b08b1056828838c5f61e6393ba7a0abcc9f662",
         tag="e097195f4532da895fb917a5a55c6aa0"),
]
for _vector in VECTORS:
    _vector.update(source=SOURCE, nonce="cafebabefacedbaddecaf888",
                   aad="3ad77bb40d7a3660a89ecaf32466ef97f5d3d585",
                   plaintext="d9313225f88406e5a55909c5aff5269a86a7a9531534f7da2e4c303d8a318a72"
                             "1c3c0c95956809532fcf0e2449a6b525b16aedf5aa0de657ba637b39")


def gcm_cipher(key, nonce, backend="aesni"):
    if backend not in ("aesni", "software"):
        raise ValueError("Explicit AES backend required; no auto label.")
    if len(nonce) != NONCE_BYTES:
        raise ValueError("This protocol requires 96-bit nonces.")
    aes, _, _ = modules()
    return aes.new(key, aes.MODE_GCM, nonce=nonce, mac_len=TAG_BYTES,
                   use_aesni=backend == "aesni")


def encrypt_message(instance, data, aad):
    instance.update(aad)
    return instance.encrypt_and_digest(data)


def decrypt_message(instance, data, tag, aad):
    instance.update(aad)
    return instance.decrypt_and_verify(data, tag)


def verify_gcm_dispatch():
    evidence = probe()
    if not evidence["available"]:
        raise RuntimeError("GCM requires CPU AES-NI support and its native library; no fallback.")
    aes, _, _ = modules()
    counts, records = {"software": 0, "aesni": 0}, []
    # GCM 3.23.0 initializes AES for H, payload CTR, and tag CTR. Observe the
    # actual GCM factory, not a CBC proxy, including both complete operations.
    with patch.object(aes, "_raw_aes_lib", StartObserver(aes._raw_aes_lib, "AES_start_operation", counts, "software")), \
            patch.object(aes, "_raw_aesni_lib", StartObserver(aes._raw_aesni_lib, "AESNI_start_operation", counts, "aesni")):
        for vector in VECTORS:
            key, nonce, p, aad, c, tag = [bytes.fromhex(vector[k]) for k in
                                        ("key", "nonce", "plaintext", "aad", "ciphertext", "tag")]
            for backend in ("aesni", "software"):
                for operation in ("encrypt", "decrypt"):
                    counts.update(software=0, aesni=0)
                    instance = gcm_cipher(key, nonce, backend)
                    if operation == "encrypt":
                        correct = encrypt_message(instance, p, aad) == (c, tag)
                    else:
                        correct = decrypt_message(instance, c, tag, aad) == p
                    if counts != {b: 3 if b == backend else 0 for b in counts}:
                        raise RuntimeError(f"Unexpected GCM AES dispatch: {counts}")
                    if not correct:
                        raise RuntimeError("GCM dispatch preflight output mismatch")
                    records.append(dict(algorithm=vector["algorithm"], backend=backend,
                                        operation=operation, native_start_calls=dict(counts)))
    from Crypto.Cipher import _mode_gcm
    return {**evidence, "passed": True, "records": records,
            "gcm_module_sha256": hashlib.sha256(Path(_mode_gcm.__file__).read_bytes()).hexdigest(),
            "scope": "AES primitive native backend dispatch verified as AES-NI; complete GCM also includes authentication/GHASH processing.",
            "limit": "Library dispatch observation, not CPU instruction trace; GHASH hardware path not verified"}


def validate_gcm(path, session_id, purpose):
    report = dict(passed=False, session_id=session_id, purpose=purpose, mode="GCM",
                  started_utc=utc_now(), vectors=[])
    try:
        report["dispatch"] = verify_gcm_dispatch()
        for vector in VECTORS:
            key, nonce, p, aad, c, tag = [bytes.fromhex(vector[k]) for k in
                                        ("key", "nonce", "plaintext", "aad", "ciphertext", "tag")]
            for backend in ("aesni", "software"):
                row = {**vector, "backend": backend, "passed": False}
                report["vectors"].append(row)
                actual_c, actual_tag = encrypt_message(gcm_cipher(key, nonce, backend), p, aad)
                row["ciphertext_passed"] = actual_c == c
                row["tag_passed"] = actual_tag == tag
                row["decrypt_verify_passed"] = decrypt_message(gcm_cipher(key, nonce, backend), c, tag, aad) == p
                for label, bad_c, bad_tag, bad_aad in (
                    ("tag", c, bytes([tag[0] ^ 1]) + tag[1:], aad),
                    ("ciphertext", bytes([c[0] ^ 1]) + c[1:], tag, aad),
                    ("aad", c, tag, bytes([aad[0] ^ 1]) + aad[1:])):
                    row[f"modified_{label}_rejected"] = False
                    instance = gcm_cipher(key, nonce, backend)
                    try:
                        decrypt_message(instance, bad_c, bad_tag, bad_aad)
                    except ValueError:
                        row[f"modified_{label}_rejected"] = True
                row["passed"] = all(row[k] for k in ("ciphertext_passed", "tag_passed", "decrypt_verify_passed",
                                                      "modified_tag_rejected", "modified_ciphertext_rejected", "modified_aad_rejected"))
                if not row["passed"]:
                    raise RuntimeError(f"GCM validation failed: {vector['algorithm']}/{backend}")
        report["passed"] = True
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        report["completed_utc"] = utc_now()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as output:
            json.dump(report, output, indent=2)
            output.write("\n")
    return report


def benchmark_key(seed, bits):
    return key_for(f"AES-{bits}", random.Random(f"aes-gcm-v1:key:{seed}:{bits}"))


def benchmark_plaintext(seed, size):
    return random.Random(f"aes-gcm-v1:payload:{seed}:{size}").randbytes(size)


def message_nonce(size, message_index):
    # Globally distinct within a run, even if sizes are reordered or keys collide.
    # Warmup messages also consume indices. Reference/encrypt/decrypt replay the
    # same logical tuple; they never pair this nonce with different plaintext.
    return size.to_bytes(8, "big") + message_index.to_bytes(4, "big")


def main():
    cli = parser(__doc__)
    cli.add_argument("--sizes", nargs="+", type=positive, default=[1024, 16384, 1048576, 16777216, 104857600])
    cli.add_argument("--warmup", type=positive, default=2)
    cli.add_argument("--repeats", type=positive, default=10)
    args = cli.parse_args()
    if len(set(args.sizes)) != len(args.sizes):
        cli.error("Sizes must be distinct; GCM does not require block alignment.")
    if args.repeats < 2 or args.warmup + args.repeats > 2**32:
        cli.error("At least two repeats required; message index must fit 32 bits.")
    if any(size > MAX_PAYLOAD for size in args.sizes):
        cli.error("Payload exceeds the GCM message length limit.")
    method = dict(protocol_version="aes-gcm-v1", study_protocol="not locked; manual pilot first",
                  mode="GCM", backend="aesni", padding="none", nonce_bytes=12, tag_bytes=16,
                  aad_bytes=len(AAD), aad_hex=AAD.hex(), aad_policy="fixed 16-byte ASCII AES-GCM-bench-v1",
                  warmup=args.warmup, repeats=args.repeats,
                  timed="fresh-object AEAD transform: update(AAD), encrypt_and_digest OR decrypt_and_verify, output allocation",
                  excluded="GCM construction incl. H/key schedules/GHASH setup, input generation, reference preparation, validation, comparisons, disposal and exports",
                  timing_scope="setup-excluded authenticated payload processing, not setup-inclusive message latency",
                  decrypt_verification="full PyCryptodome verify included, including its internal random-secret/BLAKE2s comparison",
                  reference="untimed use_aesni=False GCM, separately KAT validated; same key/nonce/plaintext/AAD",
                  nonce_policy="96 bits = size uint64 big-endian || message_index uint32 big-endian; index spans warmup and repeats per size",
                  key_policy="Random('aes-gcm-v1:key:{seed}:{bits}').randbytes(bits/8), synthetic only",
                  plaintext_policy="Random('aes-gcm-v1:payload:{seed}:{size}').randbytes(size), fixed per size",
                  replay_policy="reference and timed operations replay identical logical message; same seed replays same dataset, not production nonce management",
                  order="Random(seed) shuffles variants per round and encrypt/decrypt per variant; sizes follow CLI order",
                  wall_timer="perf_counter_ns", wall_timer_meaning="monotonic wall elapsed time; primary metric",
                  wall_timer_resolution_seconds=get_clock_info("perf_counter").resolution,
                  process_cpu_timer="process_time_ns", process_cpu_timer_resolution_seconds=get_clock_info("process_time").resolution,
                  process_cpu_timer_meaning="current process CPU time, excluding time not executing; not CPU cycles",
                  timer_order="process start, wall start, AEAD operation, wall end, process end",
                  process_to_wall_ratio="diagnostic only; outer process interval includes wall bookkeeping; zero and >1 permitted",
                  throughput_definition="payload bytes / 1e6 / wall seconds; ciphertext length equals plaintext length; excludes AAD/tag from numerator",
                  ghash_policy="PyCryptodome default; hardware GHASH dispatch not measured or verified",
                  environment_policy="before/after context only; no CPU utilization gate or system setting changes")
    if print_plan("aes_gcm", args, method):
        return
    session_id = str(uuid4())
    path = args.output.resolve() / f"gcm-validation-{args.purpose}-{session_id}.json"
    method["session_id"] = session_id
    method["gcm_validation"] = validate_gcm(path, session_id, args.purpose)
    method["validation_file"] = str(path)
    method["validation_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    method["hardware_execution_path"] = method["gcm_validation"]["dispatch"]["scope"]
    method["environment_before"] = environment_snapshot()
    method["measurement_started_utc"] = utc_now()
    rng, raw = random.Random(args.seed), []
    keys = {name: benchmark_key(args.seed, bits) for name, bits in VARIANTS.items()}
    for size in args.sizes:
        plaintext = benchmark_plaintext(args.seed, size)
        for index in range(args.warmup + args.repeats):
            repeat = index - args.warmup
            names = list(VARIANTS)
            rng.shuffle(names)
            for variant_order, name in enumerate(names):
                key, nonce = keys[name], message_nonce(size, index)
                ciphertext, tag = encrypt_message(gcm_cipher(key, nonce, "software"), plaintext, AAD)
                jobs = ["encrypt", "decrypt"]
                rng.shuffle(jobs)
                for job_order, operation in enumerate(jobs):
                    instance = gcm_cipher(key, nonce, "aesni")  # Always fresh, never reused state.
                    transform = encrypt_message if operation == "encrypt" else decrypt_message
                    inputs = (instance, plaintext, AAD) if operation == "encrypt" else (instance, ciphertext, tag, AAD)
                    cpu_start = process_time_ns()
                    wall_start = perf_counter_ns()
                    result = transform(*inputs)
                    wall_ns = perf_counter_ns() - wall_start
                    cpu_ns = process_time_ns() - cpu_start
                    if result != ((ciphertext, tag) if operation == "encrypt" else plaintext):
                        raise RuntimeError(f"GCM output mismatch: {name}/{operation}")
                    if wall_ns <= 0 or cpu_ns < 0:
                        raise RuntimeError("Invalid timer delta.")
                    if repeat >= 0:
                        raw.append(dict(session_id=session_id, algorithm=name, key_bits=VARIANTS[name],
                                        backend="aesni", mode="GCM", bytes=size, repeat=repeat,
                                        message_index=index, operation=operation, nonce_bytes=12, aad_bytes=len(AAD),
                                        tag_bytes=16, wall_elapsed_ns=wall_ns, process_cpu_ns=cpu_ns,
                                        process_to_wall_ratio=cpu_ns / wall_ns, seconds=wall_ns / 1e9,
                                        throughput_MB_s=size * 1000 / wall_ns,
                                        variant_order=variant_order, job_order=job_order))
                    del result, inputs, instance
                del ciphertext, tag
        del plaintext
    method["measurement_finished_utc"] = utc_now()
    method["environment_after"] = environment_snapshot()
    summary = []
    for name in VARIANTS:
        for size in args.sizes:
            for operation in ("encrypt", "decrypt"):
                selected = [r for r in raw if (r["algorithm"], r["bytes"], r["operation"]) == (name, size, operation)]
                row = dict(session_id=session_id, algorithm=name, key_bits=VARIANTS[name], mode="GCM",
                           backend="aesni", bytes=size, operation=operation)
                for metric in ("seconds", "throughput_MB_s", "process_cpu_ns", "process_to_wall_ratio"):
                    row.update({f"{metric}_{k}": v for k, v in stats([r[metric] for r in selected]).items()})
                summary.append(row)
    directory = save_run("aes_gcm", args, method, raw, summary)
    shutil.copyfile(path, directory / "validation.json")
    # Add top-level identity without changing the shared exporter used by prior studies.
    manifest_path = directory / "metadata.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["session_id"] = session_id
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    source = directory / "source"
    source.mkdir()
    for filename in ("aes_gcm_benchmark.py", "aes_gcm_smoke_check.py", "aes_acceleration.py",
                     "common.py", "benchmark.py", "cpu_validation.py"):
        shutil.copyfile(Path(__file__).parent / filename, source / filename)


if __name__ == "__main__":
    main()
