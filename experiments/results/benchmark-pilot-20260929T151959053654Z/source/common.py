"""Shared infrastructure for educational experiments, not production cryptography."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
ALGORITHMS = ("DES", "3DES", "AES-128", "AES-192", "AES-256")


def positive(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Expected a positive integer.")
    return number


def parser(description: str) -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=description)
    result.add_argument("--run", action="store_true",
                        help="Perform measurements; default only prints the plan.")
    result.add_argument("--seed", type=int, default=2003)
    result.add_argument("--output", type=Path, default=ROOT / "experiments" / "results")
    result.add_argument("--purpose", choices=("pilot", "smoke", "study"), default="pilot")
    result.add_argument("--notes", default="", help="Power mode, load, thermal state, etc.")
    return result


def print_plan(name: str, args: argparse.Namespace, method: dict) -> bool:
    if args.run:
        return False
    print(json.dumps({"experiment": name, "status": "plan_only",
                      "arguments": vars(args), "method": method},
                     indent=2, default=str))
    return True


def modules():
    try:
        from Crypto.Cipher import AES, DES, DES3
    except ImportError as exc:
        raise SystemExit("Install experiments/requirements.txt in the virtual environment.") from exc
    return AES, DES, DES3


def key_for(name: str, rng: random.Random) -> bytes:
    # Deterministic keys are exclusively for reproducible synthetic experiments.
    _, _, des3 = modules()
    size = {"DES": 8, "3DES": 24, "AES-128": 16, "AES-192": 24, "AES-256": 32}[name]
    if name != "3DES":
        return rng.randbytes(size)
    while True:
        try:
            key = des3.adjust_key_parity(rng.randbytes(size))
            # adjust_key_parity rejects single DES, but permits K1 == K3.
            if len({key[:8], key[8:16], key[16:]}) == 3:
                return key
        except ValueError:
            continue


def block_size(name: str) -> int:
    return 8 if name in ("DES", "3DES") else 16


def cipher(name: str, key: bytes, mode: str, iv: bytes | None = None,
           aes_backend: str = "auto"):
    aes, des, des3 = modules()
    module = des if name == "DES" else des3 if name == "3DES" else aes
    options = {"iv": iv} if mode == "CBC" else {}
    if name.startswith("AES") and aes_backend == "software":
        options["use_aesni"] = False
    return module.new(key, getattr(module, "MODE_" + mode), **options)


def stats(values: list[float]) -> dict:
    return {"count": len(values), "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else None,
            "min": min(values), "max": max(values)}


def command_output(arguments: list[str]) -> str | None:
    try:
        return subprocess.check_output(arguments, cwd=ROOT, text=True,
                                       stderr=subprocess.DEVNULL, timeout=5).strip()
    except (OSError, subprocess.SubprocessError):
        return None


def metadata(args: argparse.Namespace, method: dict) -> dict:
    import psutil
    cpu = platform.processor()
    if os.name == "nt":
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                           r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
            cpu = str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
    versions = {name: importlib.metadata.version(name)
                for name in ("pycryptodome", "matplotlib", "psutil")}
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(Path(__file__).parent.glob("*.py"))}
    return {"schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
            "purpose": args.purpose, "seed": args.seed,
            "python": sys.version, "executable": sys.executable,
            "os": platform.platform(), "machine": platform.machine(), "cpu": cpu,
            "logical_cpus": psutil.cpu_count(), "physical_cpus": psutil.cpu_count(logical=False),
            "ram_bytes": psutil.virtual_memory().total, "library_versions": versions,
            "git_commit": command_output(["git", "rev-parse", "HEAD"]),
            "git_status": command_output(["git", "status", "--short"]),
            "script_sha256": hashes, "argv": sys.argv, "arguments": vars(args),
            "method": method,
            "hardware_execution_path": method.get("hardware_execution_path", "not verified"),
            "warning": "Educational synthetic experiment; DES/TDEA are legacy algorithms."}


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("Refusing to export empty measurements.")
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def save_run(name: str, args: argparse.Namespace, method: dict,
             raw: list[dict], summary: list[dict]) -> Path:
    manifest = metadata(args, method)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = args.output.resolve() / f"{name}-{args.purpose}-{stamp}"
    directory.mkdir(parents=True, exist_ok=False)
    manifest["run_id"] = directory.name
    manifest["experiment"] = name
    write_csv(directory / "raw.csv", raw)
    write_csv(directory / "summary.csv", summary)
    for filename, data in (("metadata.json", manifest),
                           ("results.json", {"raw": raw, "summary": summary})):
        (directory / filename).write_text(
            json.dumps(data, indent=2, default=str, allow_nan=False) + "\n", encoding="utf-8")
    frozen = command_output([sys.executable, "-m", "pip", "freeze"])
    if frozen is not None:
        (directory / "requirements-lock.txt").write_text(frozen + "\n", encoding="utf-8")
    print(directory)
    return directory
