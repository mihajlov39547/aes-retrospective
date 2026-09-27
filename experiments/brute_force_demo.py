"""Bounded AES-128 key search with explicitly illustrative extrapolation."""
import math
import random
from time import perf_counter_ns

from common import cipher, parser, positive, print_plan, save_run, stats


def reduced_key(number: int) -> bytes:
    return number.to_bytes(16, "big")


def main():
    cli = parser(__doc__)
    cli.add_argument("--bits", type=positive, default=12, help="Variable key bits, 1..20.")
    cli.add_argument("--repeats", type=positive, default=3)
    args = cli.parse_args()
    if args.bits > 20:
        cli.error("Educational search is capped at 20 variable bits.")
    method = {"primitive": "AES-128", "mode": "ECB two known blocks",
              "variable_bits": args.bits, "fixed_key_bits": 128 - args.bits,
              "search": "sequential; stops at the known target",
              "timed": "key construction, cipher setup, encrypt and compare",
              "extrapolation": "same measured AES/Python rate for all abstract spaces",
              "year_seconds": 365.25 * 24 * 3600,
              "warning": "Not DES/TDEA attack estimates; hardware, parallelism and MITM differ."}
    if print_plan("brute_force", args, method):
        return
    rng = random.Random(args.seed)
    raw = []
    for repeat in range(args.repeats):
        target = rng.randrange(1 << args.bits)
        plaintext = rng.randbytes(32)
        expected = cipher("AES-128", reduced_key(target), "ECB").encrypt(plaintext)
        start = perf_counter_ns()
        found = None
        for candidate in range(1 << args.bits):
            encrypted = cipher("AES-128", reduced_key(candidate), "ECB").encrypt(plaintext)
            if encrypted == expected:
                found = candidate
                break
        seconds = (perf_counter_ns() - start) / 1e9
        if found != target or seconds <= 0:
            raise RuntimeError("Reduced-space search failed.")
        attempts = found + 1
        raw.append({"repeat": repeat, "variable_bits": args.bits, "target_index": target,
                    "attempts": attempts, "seconds": seconds, "attempts_s": attempts / seconds})
    rate = sum(row["attempts"] for row in raw) / sum(row["seconds"] for row in raw)
    method["observed_rate_stats"] = stats([row["attempts_s"] for row in raw])
    method["pooled_attempts_s"] = rate
    summary = []
    for bits in (56, 112, 128, 192, 256):
        for extent, attempts in (("full", 2 ** bits), ("expected", (2 ** bits + 1) / 2)):
            seconds = attempts / rate
            years = seconds / method["year_seconds"]
            summary.append({"keyspace_bits": bits, "extent": extent,
                            "illustrative_seconds": f"{seconds:.6e}",
                            "illustrative_years": f"{years:.6e}",
                            "log10_seconds": math.log10(seconds),
                            "log10_years": math.log10(years)})
    save_run("brute_force", args, method, raw, summary)
    # TODO: Optional universe-age scale only after verifying its reference.
    # TODO: Discuss TDEA attack models separately; 2^112 here is an abstract search space.


if __name__ == "__main__":
    main()
