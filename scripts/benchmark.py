"""Initial CBC benchmark; scientific interpretation remains TODO."""
import random
from time import perf_counter_ns

from common import (ALGORITHMS, block_size, cipher, key_for, parser, positive,
                    print_plan, save_run, stats)


def main():
    cli = parser(__doc__)
    cli.add_argument("--sizes", nargs="+", type=positive, default=[1024, 1048576, 10485760],
                     help="Exact byte counts, divisible by 16; optional 104857600.")
    cli.add_argument("--repeats", type=positive, default=10)
    cli.add_argument("--warmup", type=positive, default=2)
    cli.add_argument("--aes-backend", choices=("auto", "software"), default="auto")
    args = cli.parse_args()
    if args.repeats < 2 or any(size % 16 for size in args.sizes):
        cli.error("Use at least 2 repeats and sizes divisible by 16.")
    if len(set(args.sizes)) != len(args.sizes):
        cli.error("Sizes must be distinct.")
    method = {"mode": "CBC", "padding": "none", "timer": "perf_counter_ns",
              "timed": "one buffer transform, including output allocation",
              "excluded": "key generation, cipher initialization, IV, validation",
              "throughput_unit": "decimal MB/s = bytes / 1e6 / seconds",
              "aes_backend_request": args.aes_backend, "order": "seeded shuffle per round"}
    if print_plan("benchmark", args, method):
        return
    rng = random.Random(args.seed)
    raw = []
    for size in args.sizes:
        plaintext = rng.randbytes(size)
        keys = {name: key_for(name, rng) for name in ALGORITHMS}
        for repeat in range(-args.warmup, args.repeats):
            names = list(ALGORITHMS)
            rng.shuffle(names)
            for name in names:
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
                        raw.append({"algorithm": name, "mode": "CBC", "bytes": size,
                                    "repeat": repeat, "operation": operation,
                                    "seconds": duration / 1e9,
                                    "throughput_MB_s": size * 1000 / duration})
    summary = []
    for name in ALGORITHMS:
        for size in args.sizes:
            for operation in ("encrypt", "decrypt"):
                selected = [row for row in raw if row["algorithm"] == name
                            and row["bytes"] == size and row["operation"] == operation]
                row = {"algorithm": name, "mode": "CBC", "bytes": size, "operation": operation}
                for metric in ("seconds", "throughput_MB_s"):
                    row.update({f"{metric}_{key}": value
                                for key, value in stats([x[metric] for x in selected]).items()})
                summary.append(row)
    save_run("benchmark", args, method, raw, summary)
    # TODO: Separate setup-cost and AEAD experiments; do not merge modes in one ranking.
    # TODO: Repeat on independently controlled hosts before drawing conclusions.


if __name__ == "__main__":
    main()
