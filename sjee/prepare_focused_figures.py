"""Read-only reconstruction of the manuscript's AES-NI/single-CUDA evidence.

Run from any directory with Python and matplotlib. All outputs stay in sjee/.
Original study files, including the authoritative T4 archive, are never changed.
"""
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

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
ANALYSIS = REPO / "experiments/analysis/cross_platform_2026_10_complete"
OUT = ROOT / "figures"
PLATFORMS = ("gtx1650ti", "t600", "t4")
NAMES = dict(gtx1650ti="GTX", t600="T600", t4="T4")
SEEDS = list(range(2003, 2008))
SIZES = [1024, 16384, 1048576, 16777216, 33554432]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def close(a, b):
    assert math.isclose(float(a), float(b), rel_tol=1e-10, abs_tol=1e-15), (a, b)


def write_csv(name, rows):
    with (OUT / name).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUT.mkdir(exist_ok=True)
    manifest = json.loads((ANALYSIS / "reproducibility_manifest.json").read_text())
    with (ANALYSIS / "independent_aggregates.csv").open(newline="") as stream:
        audited = {(r["platform"], r["backend"], r["measurement"], r["mode"],
                    int(r["bytes"]), r["metric"]): r for r in csv.DictReader(stream)}
    sessions, provenance = [], {}
    for platform in PLATFORMS:
        info = manifest["inputs"][platform]
        location = info["location"].replace("\\", "/")
        source = REPO / location[location.index("experiments/"):]
        archive = tarfile.open(source) if source.suffix == ".gz" else None

        def read(rel):
            if archive:
                return archive.extractfile(info["run_id"] + "/" + rel).read()
            return (source / rel).read_bytes()

        try:
            for rel, expected in info["files"].items():
                assert digest(read(rel)) == expected, (platform, rel)
            provenance[platform] = dict(run_id=info["run_id"],
                source=source.relative_to(REPO).as_posix(), raw_files={})
            for seed in SEEDS:
                rel = f"experiments/cuda_paired/seed-{seed}/native/raw.csv"
                data = read(rel)
                provenance[platform]["raw_files"][rel] = digest(data)
                raw = list(csv.DictReader(io.StringIO(data.decode("utf-8"))))
                assert len(raw) == 1200
                assert {int(r["seed"]) for r in raw} == {seed}
                assert len({r["session_id"] for r in raw}) == 1
                assert all(r["validation_checked"] == "True" for r in raw)
                assert [int(r["global_order"]) for r in raw] == list(range(1200))
                chosen = [r for r in raw if r["backend"] in ("cpu_aesni", "cuda_baseline")]
                assert len(chosen) == 600
                for mode in ("ECB", "CTR"):
                    for size in SIZES:
                        subset = [r for r in chosen if r["mode"] == mode and int(r["bytes"]) == size]
                        for repeat in range(20):
                            pair = [r for r in subset if int(r["repeat"]) == repeat]
                            assert len(pair) == 3 and len({r["pair_sha256"] for r in pair}) == 1
                        for backend, scope in (("cpu_aesni", "transform"),
                                               ("cuda_baseline", "resident"),
                                               ("cuda_baseline", "pipeline")):
                            group = [r for r in subset if r["backend"] == backend and r["measurement"] == scope]
                            assert len(group) == 20 and {int(r["repeat"]) for r in group} == set(range(20))
                            time_key, rate_key = {
                                "transform": ("seconds", "throughput_MB_s"),
                                "resident": ("kernel_seconds", "kernel_throughput_MB_s"),
                                "pipeline": ("end_to_end_seconds", "end_to_end_throughput_MB_s"),
                            }[scope]
                            for r in group:
                                assert r["host_memory"] == ("bytes" if scope == "transform" else "pinned")
                                if scope == "resident":
                                    assert int(r["resident_iterations"]) == 1
                                close(r[rate_key], size / float(r[time_key]) / 1e6)
                            sessions.append(dict(platform=platform, run_id=info["run_id"], seed=seed,
                                mode=mode, bytes=size, backend=backend, scope=scope,
                                seconds=st.median(float(r[time_key]) for r in group),
                                throughput_MB_s=st.median(float(r[rate_key]) for r in group),
                                raw_file=rel))
        finally:
            if archive:
                archive.close()

    values = {(r["platform"], r["seed"], r["mode"], r["bytes"], r["scope"]): r for r in sessions}
    aggregates, pairs = [], []
    for platform in PLATFORMS:
        for mode in ("ECB", "CTR"):
            for size in SIZES:
                for scope in ("transform", "resident", "pipeline"):
                    entries = [values[platform, s, mode, size, scope] for s in SEEDS]
                    time_metric, rate_metric = {
                        "transform": ("seconds_median", "throughput_MB_s_median"),
                        "resident": ("kernel_seconds_median", "kernel_throughput_MB_s_median"),
                        "pipeline": ("end_to_end_seconds_median", "end_to_end_throughput_MB_s_median"),
                    }[scope]
                    backend = entries[0]["backend"]
                    for field, metric in (("seconds", time_metric), ("throughput_MB_s", rate_metric)):
                        close(st.median(r[field] for r in entries),
                              audited[platform, backend, scope, mode, size, metric]["median_of_sessions"])
                    if scope == "transform":
                        continue
                    ratios = []
                    for seed, r in zip(SEEDS, entries):
                        ratio = values[platform, seed, mode, size, "transform"]["seconds"] / r["seconds"]
                        ratios.append(ratio)
                        pairs.append(dict(platform=platform, run_id=r["run_id"], seed=seed,
                            mode=mode, bytes=size, scope=scope, speedup=ratio,
                            raw_file=r["raw_file"]))
                    metric = "speedup_" + ("isolated" if scope == "resident" else "pipeline") + "_vs_cpu_aesni"
                    record = dict(platform=platform, mode=mode, bytes=size, scope=scope,
                        median=st.median(ratios), minimum=min(ratios), maximum=max(ratios),
                        iqr=sorted(ratios)[3]-sorted(ratios)[1],
                        cv=st.stdev(ratios)/st.mean(ratios), wins=sum(v > 1 for v in ratios),
                        sessions=5, throughput_MB_s=st.median(r["throughput_MB_s"] for r in entries))
                    saved = audited[platform, backend, scope, mode, size, metric]
                    for field, other in (("median", "median_of_sessions"), ("minimum", "session_min"),
                                         ("maximum", "session_max"), ("iqr", "session_iqr"),
                                         ("cv", "session_coefficient_of_variation")):
                        close(record[field], saved[other])
                    aggregates.append(record)
    write_csv("focused_sessions.csv", sessions)
    write_csv("focused_paired_speedups.csv", pairs)
    write_csv("focused_aggregates.csv", aggregates)

    # Check the rounded quantities and directional statements retained in the prose.
    bykey = {(r["platform"], r["mode"], r["bytes"], r["scope"]): r for r in aggregates}
    checks = []

    def reported(name, computed, displayed, decimals):
        assert f"{computed:.{decimals}f}" == displayed, (name, computed, displayed)
        checks.append(dict(claim=name, computed=computed, displayed=displayed))

    for platform, rate, resident in (("gtx1650ti", "1188.9", "4585.6"),
                                     ("t600", "2049.4", "4328.9"),
                                     ("t4", "3713.9", "9166.8")):
        for scope, shown in (("pipeline", rate), ("resident", resident)):
            reported(f"{platform} CTR 32MiB {scope} MB/s",
                     bykey[platform, "CTR", 33554432, scope]["throughput_MB_s"], shown, 1)
    for platform, mode, shown, wins in (("gtx1650ti", "CTR", "0.935", 1),
                                       ("t600", "CTR", "1.354", 5),
                                       ("t4", "CTR", "4.761", 5),
                                       ("t4", "ECB", "0.893", 0)):
        r = bykey[platform, mode, 33554432, "pipeline"]
        reported(f"{platform} {mode} 32MiB pipeline speedup", r["median"], shown, 3)
        assert r["wins"] == wins
    r = bykey["t600", "CTR", 33554432, "pipeline"]
    reported("T600 paired latency reduction percent", 100*(1-1/r["median"]), "26.14", 2)
    reported("T600 paired speedup IQR", r["iqr"], "0.030896", 6)
    reported("T600 paired speedup CV percent", 100*r["cv"], "8.18", 2)
    assert bykey["t600", "CTR", 1048576, "pipeline"]["wins"] == 5
    assert 0 < bykey["t600", "CTR", 16777216, "pipeline"]["wins"] < 5
    assert bykey["t600", "ECB", 33554432, "pipeline"]["wins"] == 3
    assert not any(r["wins"] == 5 for r in aggregates
                   if r["platform"] == "gtx1650ti" and r["scope"] == "pipeline")
    for platform in PLATFORMS:
        mode_ratios = [values[platform, s, "ECB", 33554432, "transform"]["throughput_MB_s"] /
                       values[platform, s, "CTR", 33554432, "transform"]["throughput_MB_s"]
                       for s in SEEDS]
        reported(f"{platform} CPU ECB/CTR throughput ratio", st.median(mode_ratios),
                 "5.378" if platform == "t4" else "1.26", 3 if platform == "t4" else 2)
        if platform == "t4":
            reported("T4 CPU mode ratio minimum", min(mode_ratios), "5.250", 3)
            reported("T4 CPU mode ratio maximum", max(mode_ratios), "5.795", 3)
        for mode in ("ECB", "CTR"):
            assert bykey[platform, mode, 33554432, "resident"]["wins"] == 5
            for scope in ("resident", "pipeline"):
                dips = sum(values[platform, s, mode, 16777216, scope]["throughput_MB_s"] <
                           min(values[platform, s, mode, n, scope]["throughput_MB_s"]
                               for n in (1048576, 33554432)) for s in SEEDS)
                if platform in ("gtx1650ti", "t4"):
                    assert dips == (5 if platform == "gtx1650ti" else 4 if scope == "resident" else 0)
                checks.append(dict(claim=f"{platform} {mode} {scope} local-dip sessions",
                                   computed=dips, displayed=str(dips)))

    # Two mode panels: platform colors and execution-scope line styles.
    plt.rcParams.update({"font.size": 12, "pdf.fonttype": 42, "svg.fonttype": "none"})
    fig, axes = plt.subplots(2, 1, figsize=(6.8, 7.0), sharex=True, sharey=True)
    colors = {"gtx1650ti": "#0072B2", "t600": "#D55E00", "t4": "#009E73"}
    markers = {"gtx1650ti": "o", "t600": "s", "t4": "^"}
    for ax, mode in zip(axes, ("ECB", "CTR")):
        for platform in PLATFORMS:
            for scope, style in (("resident", "-"), ("pipeline", "--")):
                data = [next(r for r in aggregates
                             if (r["platform"], r["mode"], r["bytes"], r["scope"])
                             == (platform, mode, size, scope)) for size in SIZES]
                ax.plot(SIZES, [r["median"] for r in data], color=colors[platform],
                        marker=markers[platform], linestyle=style, linewidth=1.6, markersize=4,
                        label=f"{NAMES[platform]} {scope}")
                ax.fill_between(SIZES, [r["minimum"] for r in data],
                                [r["maximum"] for r in data],
                                color=colors[platform], alpha=.09, linewidth=0)
        ax.axhline(1, color=".35", linestyle=":", linewidth=1)
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_ylim(.01, 20)
        ax.set_title(f"AES-128 {mode}", loc="left", fontsize=12)
        ax.grid(alpha=.15)
        ax.set_ylabel("AES-NI / GPU time")
        ax.set_xticks(SIZES, ["1 KiB", "16 KiB", "1 MiB", "16 MiB", "32 MiB"],
                      rotation=35, ha="right", fontsize=10)
        ax.tick_params(axis="x", labelbottom=True)
        ax.spines[["top", "right"]].set_visible(False)
    axes[-1].set_xlabel("Input size")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=3, frameon=False,
               fontsize=10, bbox_to_anchor=(.55, .995), columnspacing=1.2)
    fig.subplots_adjust(left=.14, right=.98, bottom=.12, top=.85, hspace=.48)
    fig.savefig(OUT / "aesni_gpu_scopes.pdf", metadata={"CreationDate": None, "ModDate": None})
    fig.savefig(OUT / "aesni_gpu_scopes.png", dpi=240)
    plt.close(fig)

    lines = [r"\begin{table}[htbp]", r"  \centering", r"  \small",
        r"  \setlength{\tabcolsep}{4pt}",
        r"  \caption{Paired speedup over AES-NI at 32~MiB. R: resident; P: pipeline.",
        r"  Brackets show the five-session pipeline range; the last column counts P gains.}",
        r"  \label{tab:gpu-speedups}", r"  \begin{tabular}{llrrlc}",
        r"    \toprule", "    System & Mode & R & P & P range & $P>1$ " + chr(92)*2,
        r"    \midrule"]
    for platform in PLATFORMS:
        for mode in ("ECB", "CTR"):
            r, p = [next(x for x in aggregates if (x["platform"], x["mode"], x["bytes"], x["scope"])
                         == (platform, mode, 33554432, scope)) for scope in ("resident", "pipeline")]
            median, wins = f"{p['median']:.3f}", f"{p['wins']}/5"
            if p['wins'] == 5:
                median, wins = [r"\textbf{" + v + "}" for v in (median, wins)]
            lines.append(f"    {NAMES[platform]} & {mode} & {r['median']:.3f} & {median} & "
                         f"[{p['minimum']:.3f}, {p['maximum']:.3f}] & {wins} " + r"\\")
    lines += [r"    \bottomrule", r"  \end{tabular}", r"  \par\smallskip",
        r"  \parbox{\linewidth}{\footnotesize Bold pipeline medians and counts indicate",
        r"  acceleration in all five sessions. Resident execution is faster in all five sessions",
        r"  for every row.}", r"\end{table}"]
    (ROOT / "content/focused_results_table.tex").write_bytes(("\n".join(lines)+"\n").encode())
    provenance = dict(selection="cpu_aesni transform + cuda_baseline resident/pipeline; AES-128 ECB/CTR",
        original_campaign_rows=18000, selected_rows=9000, seeds=SEEDS, repeats=20, warmup=5,
        source_audit="experiments/analysis/cross_platform_2026_10_complete/reproducibility_manifest.json",
        estimator="median of five paired session median-time ratios; no raw pooling",
        tolerance=dict(relative=1e-10, absolute=1e-15), numerical_discrepancies=0,
        prose_checks=checks, studies=provenance)
    (OUT / "focused_evidence.json").write_bytes((json.dumps(provenance, indent=2)+"\n").encode())
    print("Verified 15 sessions, 9000 selected raw rows, all retained estimators; zero discrepancies.")


if __name__ == "__main__":
    main()
