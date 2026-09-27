"""Small integration checks; writes only non-study artifacts under build/smoke."""
import csv
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from aes_acceleration import probe, verify_dispatch
from common import modules

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build" / "smoke"


def invoke(script, *arguments, success=True):
    result = subprocess.run([sys.executable, str(ROOT / "experiments" / script),
                             *map(str, arguments)], cwd=ROOT, capture_output=True, text=True)
    if (result.returncode == 0) != success:
        raise RuntimeError(f"{script}: unexpected exit {result.returncode}\n{result.stderr}")
    return result


def run(script, *arguments):
    result = invoke(script, "--run", "--purpose", "smoke", "--output", OUTPUT, *arguments)
    folder = Path(result.stdout.strip().splitlines()[-1])
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["purpose"] == "smoke"
    assert metadata["library_versions"]["pycryptodome"]
    assert metadata["cpu"]
    return folder


def read_csv(folder, name="raw.csv"):
    with (folder / name).open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def main():
    for script in ("benchmark.py", "avalanche_test.py", "brute_force_demo.py", "aes_acceleration.py"):
        plan = json.loads(invoke(script).stdout)
        assert plan["status"] == "plan_only"
    invoke("benchmark.py", "--sizes", 17, success=False)
    invoke("benchmark.py", "--repeats", 1, success=False)
    invoke("avalanche_test.py", "--trials", 0, success=False)
    invoke("brute_force_demo.py", "--bits", 21, success=False)
    invoke("aes_acceleration.py", "--sizes", 17, success=False)
    invoke("aes_acceleration.py", "--repeats", 1, success=False)
    aes, _, _ = modules()
    with patch.object(aes, "_raw_aesni_lib", None):
        try:
            verify_dispatch()
        except RuntimeError:
            pass
        else:
            raise AssertionError("Missing AES-NI library must prevent comparison.")
    if probe()["available"]:
        accelerated = run("aes_acceleration.py", "--sizes", 1024, "--repeats", 2, "--warmup", 1)
        rows = read_csv(accelerated)
        assert len(rows) == 24
        assert {r["backend"] for r in rows} == {"aesni", "software"}
        summary = read_csv(accelerated, "summary.csv")
        assert len(summary) == 12
        for row in summary:
            software = next(r for r in summary if r["backend"] == "software"
                            and r["algorithm"] == row["algorithm"]
                            and r["operation"] == row["operation"])
            ratio = float(software["seconds_median"]) / float(row["seconds_median"])
            assert abs(float(row["speedup_vs_software_median"]) - ratio) < 1e-12
        invoke("export_results.py", accelerated)
        for name in ("aes_acceleration_table.tex", "aes_acceleration.png", "aes_acceleration.pdf"):
            assert (accelerated / name).stat().st_size > 100
    else:
        print("SKIP: AES-NI hardware comparison unavailable on this host.")
    bench = run("benchmark.py", "--sizes", 1024, "--repeats", 2, "--warmup", 1)
    rows = read_csv(bench)
    assert len(rows) == 20
    for row in rows:
        assert float(row["seconds"]) > 0
        assert abs(float(row["throughput_MB_s"]) * float(row["seconds"]) - 0.001024) < 1e-12
    invoke("export_results.py", bench)
    for name in ("benchmark_table.tex", "benchmark.png", "benchmark.pdf"):
        assert (bench / name).stat().st_size > 100
    first = run("avalanche_test.py", "--trials", 8)
    second = run("avalanche_test.py", "--trials", 8)
    rows = read_csv(first)
    assert rows == read_csv(second)
    assert len(rows) == 80
    for row in rows:
        assert 0 <= int(row["hamming_bits"]) <= int(row["block_bits"])
        if row["algorithm"] in ("DES", "3DES") and row["change"] == "key":
            assert int(row["changed_bit"]) % 8 != 0
    brute = run("brute_force_demo.py", "--bits", 6, "--repeats", 2)
    for row in read_csv(brute):
        assert int(row["attempts"]) == int(row["target_index"]) + 1
        assert 1 <= int(row["attempts"]) <= 64
    assert len(read_csv(brute, "summary.csv")) == 10
    print("PASS: plan-only CLI, validation, CBC round-trip, export, avalanche reproducibility, bounded search.")
    print(f"Non-study artifacts: {OUTPUT}")


if __name__ == "__main__":
    main()
