"""Experiment 1: validated CBC CPU comparison on a contemporary platform."""
import hashlib
import os
from pathlib import Path
import random
import shutil
from time import perf_counter_ns, get_clock_info
from uuid import uuid4

from common import (ALGORITHMS, block_size, cipher, key_for, parser, positive,
                    print_plan, save_run, stats)
from cpu_validation import validate_cpu, utc_now


def environment_snapshot():
    import psutil
    from common import command_output
    battery = psutil.sensors_battery()
    return {"utc": utc_now(), "cpu_percent_1s": psutil.cpu_percent(interval=1),
            "available_ram_bytes": psutil.virtual_memory().available,
            "process_rss_bytes": psutil.Process().memory_info().rss,
            "cpu_affinity": psutil.Process().cpu_affinity(),
            "power_plugged": battery.power_plugged if battery else None,
            "power_scheme": command_output(["powercfg", "/getactivescheme"]) if os.name == "nt" else None,
            "temperature": None, "temperature_note": "Not monitored",
            "clock_note": "Dynamic CPU clocks not controlled or sampled"}


def main():
    cli = parser(__doc__)
    cli.add_argument("--sizes", nargs="+", type=positive, default=[1024, 1048576, 10485760],
                     help="Exact byte counts, divisible by 16; optional 104857600.")
    cli.add_argument("--repeats", type=positive, default=10)
    cli.add_argument("--warmup", type=positive, default=2)
    cli.add_argument("--aes-backend", choices=("auto", "software"), default="software")
    args = cli.parse_args()
    if args.repeats < 2 or any(size % 16 for size in args.sizes):
        cli.error("Use at least 2 repeats and sizes divisible by 16.")
    if len(set(args.sizes)) != len(args.sizes):
        cli.error("Sizes must be distinct.")
    if args.purpose == "study" and args.aes_backend != "software":
        cli.error("Experiment 1 study protocol requires --aes-backend software.")
    method = {"mode": "CBC", "padding": "none", "timer": "perf_counter_ns",
              "timed": "one buffer transform, including output allocation",
              "excluded": "key generation, cipher initialization, IV, validation",
              "throughput_unit": "decimal MB/s = bytes / 1e6 / seconds",
              "aes_backend_request": args.aes_backend, "order": "seeded shuffle per round",
              "operation_order": "encrypt then decrypt; warm-cache sequential pair",
              "size_order": "CLI order", "protocol_version": "cpu-cbc-v2",
              "key_policy": "DES parity ignored; TDEA odd parity, three distinct effective keys",
              "allocation": "new output each call; previous outputs freed outside timing",
              "timer_resolution_seconds": get_clock_info("perf_counter").resolution}
    if print_plan("benchmark", args, method):
        return
    session_id = str(uuid4())
    validation_path = args.output.resolve() / f"cpu-validation-{args.purpose}-{session_id}.json"
    method["session_id"] = session_id
    method["cpu_validation"] = validate_cpu(validation_path, args.aes_backend, session_id, args.purpose)
    method["validation_file"] = str(validation_path)
    method["validation_sha256"] = hashlib.sha256(validation_path.read_bytes()).hexdigest()
    method["hardware_execution_path"] = ("verified PyCryptodome _raw_aes software dispatch"
                                         if args.aes_backend == "software" else "auto; not verified")
    method["environment_before"] = environment_snapshot()
    method["measurement_started_utc"] = utc_now()
    measurement_start = perf_counter_ns()
    rng = random.Random(args.seed)
    raw = []
    for size in args.sizes:
        plaintext = rng.randbytes(size)
        keys = {name: key_for(name, rng) for name in ALGORITHMS}
        for repeat in range(-args.warmup, args.repeats):
            names = list(ALGORITHMS)
            rng.shuffle(names)
            for order_index, name in enumerate(names):
                iv = rng.randbytes(block_size(name))
                encryptor = cipher(name, keys[name], "CBC", iv, args.aes_backend)
                decryptor = cipher(name, keys[name], "CBC", iv, args.aes_backend)
                start = perf_counter_ns()
                ciphertext = encryptor.encrypt(plaintext)
                enc_ns = perf_counter_ns() - start
                start = perf_counter_ns()
                recovered = decryptor.decrypt(ciphertext)
                dec_ns = perf_counter_ns() - start
                if recovered != plaintext:
                    raise RuntimeError(f"Round-trip failed: {name}")
                if repeat >= 0:
                    for operation, duration in (("encrypt", enc_ns), ("decrypt", dec_ns)):
                        if duration <= 0:
                            raise RuntimeError("Timer resolution insufficient.")
                        raw.append({"session_id": session_id, "algorithm": name,
                                    "mode": "CBC", "bytes": size, "order_index": order_index,
                                    "repeat": repeat, "operation": operation,
                                    "elapsed_ns": duration,
                                    "seconds": duration / 1e9,
                                    "throughput_MB_s": size * 1000 / duration})
                # Avoid freeing the preceding large bytes object inside the next timer.
                del ciphertext, recovered
        del plaintext
    method["measurement_elapsed_seconds"] = (perf_counter_ns() - measurement_start) / 1e9
    method["measurement_finished_utc"] = utc_now()
    method["environment_after"] = environment_snapshot()
    summary = []
    for name in ALGORITHMS:
        for size in args.sizes:
            for operation in ("encrypt", "decrypt"):
                selected = [row for row in raw if row["algorithm"] == name
                            and row["bytes"] == size and row["operation"] == operation]
                row = {"session_id": session_id, "algorithm": name, "mode": "CBC",
                       "bytes": size, "operation": operation}
                for metric in ("seconds", "throughput_MB_s"):
                    row.update({f"{metric}_{key}": value
                                for key, value in stats([x[metric] for x in selected]).items()})
                summary.append(row)
    directory = save_run("benchmark", args, method, raw, summary)
    shutil.copyfile(validation_path, directory / "validation.json")
    source_directory = directory / "source"
    source_directory.mkdir()
    for filename in ("benchmark.py", "common.py", "cpu_validation.py", "export_results.py"):
        shutil.copyfile(Path(__file__).parent / filename, source_directory / filename)
    # TODO: Separate setup-cost and AEAD experiments; do not merge modes in one ranking.
    # TODO: Repeat on independently controlled hosts before drawing conclusions.


if __name__ == "__main__":
    main()
