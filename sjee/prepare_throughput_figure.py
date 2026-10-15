"""Reconstruct 32 MiB throughput from original records; write only inside sjee/."""

import csv
import hashlib
import io
import json
import math
import statistics as st
import tarfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "figures"
SIZE = 33554432
PLATFORMS = ("gtx1650ti", "t600", "t4")
SCOPES = {
    "transform": ("cpu_aesni", "seconds", "throughput_MB_s"),
    "resident": ("cuda_baseline", "kernel_seconds", "kernel_throughput_MB_s"),
    "pipeline": ("cuda_baseline", "end_to_end_seconds", "end_to_end_throughput_MB_s"),
}


def main():
    evidence = json.loads((OUT / "focused_evidence.json").read_text(encoding="utf-8"))
    with (OUT / "focused_sessions.csv").open(newline="", encoding="utf-8") as stream:
        audited = {
            (r["platform"], int(r["seed"]), r["mode"], r["scope"]):
            float(r["throughput_MB_s"])
            for r in csv.DictReader(stream) if int(r["bytes"]) == SIZE
        }
    sessions = []
    selected_rows = 0
    for platform in PLATFORMS:
        info = evidence["studies"][platform]
        source = ROOT.parent / info["source"]
        archive = tarfile.open(source, "r:gz") if source.suffix == ".gz" else None
        try:
            for seed in range(2003, 2008):
                rel = f"experiments/cuda_paired/seed-{seed}/native/raw.csv"
                data = (archive.extractfile(info["run_id"] + "/" + rel).read()
                        if archive else (source / rel).read_bytes())
                assert hashlib.sha256(data).hexdigest() == info["raw_files"][rel]
                raw = list(csv.DictReader(io.StringIO(data.decode("utf-8"))))
                for mode in ("ECB", "CTR"):
                    for scope, (backend, time_key, rate_key) in SCOPES.items():
                        rows = [r for r in raw if int(r["bytes"]) == SIZE
                                and r["mode"] == mode and r["backend"] == backend
                                and r["measurement"] == scope]
                        assert len(rows) == 20
                        assert {int(r["repeat"]) for r in rows} == set(range(20))
                        assert all(r["validation_checked"] == "True" for r in rows)
                        assert all(int(r["seed"]) == seed for r in rows)
                        for r in rows:
                            assert math.isclose(float(r[rate_key]),
                                                SIZE / float(r[time_key]) / 1e6,
                                                rel_tol=1e-10)
                        median = st.median(float(r[rate_key]) for r in rows)
                        assert math.isclose(median, audited[platform, seed, mode, scope],
                                            rel_tol=1e-10)
                        sessions.append(dict(platform=platform, seed=seed, mode=mode,
                                             scope=scope, throughput_MB_s=median))
                        selected_rows += len(rows)
        finally:
            if archive:
                archive.close()
    assert selected_rows == 1800 and len(sessions) == 90
    with (OUT / "bulk_throughput_sessions.csv").open(
            "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(sessions[0]))
        writer.writeheader()
        writer.writerows(sessions)

    plt.rcParams.update({"font.size": 12, "pdf.fonttype": 42, "ps.fonttype": 42})
    fig, axes = plt.subplots(2, 1, figsize=(6.8, 6.2), sharey=True)
    positions = np.arange(3)
    styles = [
        ("transform", "CPU AES-NI", "#777777", ""),
        ("resident", "GPU resident", "#0072B2", "//"),
        ("pipeline", "GPU pipeline", "#D55E00", ".."),
    ]
    summaries = []
    for ax, mode in zip(axes, ("ECB", "CTR")):
        for index, (scope, label, color, hatch) in enumerate(styles):
            medians, low, high = [], [], []
            for platform in PLATFORMS:
                rates = [r["throughput_MB_s"] for r in sessions
                         if (r["platform"], r["mode"], r["scope"])
                         == (platform, mode, scope)]
                median = st.median(rates)
                medians.append(median)
                low.append(median - min(rates))
                high.append(max(rates) - median)
                summaries.append(dict(platform=platform, mode=mode, scope=scope,
                                      median_MB_s=median, minimum_MB_s=min(rates),
                                      maximum_MB_s=max(rates)))
            ax.bar(positions + (index - 1) * .25, medians, width=.23,
                   color=color, hatch=hatch, edgecolor="white", linewidth=.7,
                   label=label, yerr=[low, high], capsize=3,
                   error_kw={"elinewidth": 1, "capthick": 1, "ecolor": "#222222"})
        ax.set_title(f"AES-128 {mode} / 32 MiB", loc="left", fontsize=12)
        ax.set_xticks(positions, ["GTX", "T600", "T4"])
        ax.set_ylabel("Throughput (MB/s)")
        ax.set_ylim(0, 11000)
        ax.set_yticks(range(0, 10001, 2000))
        ax.set_axisbelow(True)
        ax.grid(axis="y", alpha=.2)
        ax.spines[["top", "right"]].set_visible(False)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False,
               fontsize=11, bbox_to_anchor=(.54, .995))
    fig.subplots_adjust(left=.16, right=.98, bottom=.07, top=.88, hspace=.38)
    fig.savefig(OUT / "bulk_throughput.pdf",
                metadata={"CreationDate": None, "ModDate": None})
    fig.savefig(OUT / "bulk_throughput.png", dpi=240)
    plt.close(fig)
    report = dict(input_bytes=SIZE, selected_observations=selected_rows,
                  session_count=15, observations_per_group=20,
                  estimator="median of five within-session throughput medians",
                  error_bars="minimum and maximum of five session medians; not confidence intervals",
                  provenance=evidence["studies"], summaries=summaries)
    (OUT / "bulk_throughput_evidence.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Verified 1,800 original observations; wrote throughput figure and provenance.")


if __name__ == "__main__":
    main()
