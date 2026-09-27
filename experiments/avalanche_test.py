"""Single-block diffusion demonstration; not a cryptographic security test."""
import random

from common import (ALGORITHMS, block_size, cipher, key_for, parser, positive,
                    print_plan, save_run, stats)


def flip(value: bytes, position: int) -> bytes:
    changed = bytearray(value)
    changed[position // 8] ^= 1 << (position % 8)
    return bytes(changed)


def distance(left: bytes, right: bytes) -> int:
    return sum((a ^ b).bit_count() for a, b in zip(left, right))


def main():
    cli = parser(__doc__)
    cli.add_argument("--trials", type=positive, default=1000)
    args = cli.parse_args()
    method = {"mode": "ECB single block, no padding", "bit_numbering": "LSB first per byte",
              "key_change": "one effective bit; excludes DES parity bits",
              "degenerate_tdea": "resample changed bit, record rejected candidates",
              "warning": "Avalanche behavior is not evidence of cryptographic security."}
    if print_plan("avalanche", args, method):
        return
    rng = random.Random(args.seed)
    raw = []
    rejected = 0
    for name in ALGORITHMS:
        width = block_size(name) * 8
        for trial in range(args.trials):
            plaintext = rng.randbytes(block_size(name))
            key = key_for(name, rng)
            baseline = cipher(name, key, "ECB").encrypt(plaintext)
            position = rng.randrange(width)
            changed = cipher(name, key, "ECB").encrypt(flip(plaintext, position))
            samples = [("plaintext", position, distance(baseline, changed))]
            positions = [bit for bit in range(len(key) * 8)
                         if name not in ("DES", "3DES") or bit % 8 != 0]
            while True:
                position = rng.choice(positions)
                changed_key = flip(key, position)
                try:
                    encryptor = cipher(name, changed_key, "ECB")
                    break
                except ValueError:
                    if name != "3DES":
                        raise
                    rejected += 1
            changed = encryptor.encrypt(plaintext)
            samples.append(("key", position, distance(baseline, changed)))
            for kind, position, hamming in samples:
                raw.append({"algorithm": name, "trial": trial, "change": kind,
                            "changed_bit": position, "block_bits": width,
                            "hamming_bits": hamming, "fraction": hamming / width})
    summary = []
    for name in ALGORITHMS:
        for kind in ("plaintext", "key"):
            selected = [r for r in raw if r["algorithm"] == name and r["change"] == kind]
            row = {"algorithm": name, "change": kind}
            for metric in ("hamming_bits", "fraction"):
                row.update({f"{metric}_{key}": value
                            for key, value in stats([r[metric] for r in selected]).items()})
            summary.append(row)
    method["rejected_tdea_changes"] = rejected
    save_run("avalanche", args, method, raw, summary)
    # TODO: Review trial counts and distributions; avoid claiming a proof or a full SAC test.


if __name__ == "__main__":
    main()
