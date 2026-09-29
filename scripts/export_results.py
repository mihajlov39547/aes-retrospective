"""Export a verified benchmark run to a LaTeX table and PNG/PDF figure."""
import argparse
import csv
import json
from pathlib import Path
import math


def export_cpu_gpu(folder, metadata):
    """No output is created without a validated run and complete comparison groups."""
    if metadata.get("method", {}).get("gpu_validation", {}).get("passed") is not True:
        raise ValueError("CPU/GPU export requires recorded GPU validation.")
    with (folder / "summary.csv").open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    groups = {}
    for row in rows:
        if row["backend"] not in ("cpu_software", "cpu_aesni", "gpu_cuda") or row["mode"] not in ("ECB", "CTR"):
            raise ValueError("Unexpected CPU/GPU mode or backend.")
        if row["algorithm"] != "AES-128" or int(row["key_bits"]) != 128:
            raise ValueError("Initial GPU exporter supports AES-128 only.")
        key = (row["mode"], int(row["input_bytes"]))
        if row["backend"] in groups.setdefault(key, {}):
            raise ValueError("Duplicate backend in CPU/GPU summary.")
        groups[key][row["backend"]] = row
        metrics = ["end_to_end_ms_median", "throughput_mib_s_median", "end_to_end_ms_mean"]
        if row["backend"] == "gpu_cuda":
            metrics += ["kernel_ms_median", "kernel_ms_mean", "transfer_ms_mean",
                        "kernel_throughput_mib_s_median"]
        for metric in metrics:
            if not math.isfinite(float(row[metric])) or float(row[metric]) <= 0:
                raise ValueError(f"Invalid timing or throughput: {metric}")
        if int(row["end_to_end_ms_count"]) < 2:
            raise ValueError("At least two measured iterations are required.")
    if not groups or any(set(g) != {"cpu_software", "cpu_aesni", "gpu_cuda"} for g in groups.values()):
        raise ValueError("Incomplete CPU/GPU comparison; no graphs generated.")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for mode in sorted({key[0] for key in groups}):
        sizes = sorted(size for m, size in groups if m == mode)
        selected = [groups[mode, size] for size in sizes]
        target = folder / mode
        target.mkdir(exist_ok=True)
        title = f'{mode} / AES-128 / {metadata["purpose"]}\n{metadata["run_id"]}'

        def series(backend, field):
            return [float(g[backend][field]) for g in selected]

        def save(figure, name):
            figure.suptitle(title, fontsize=8)
            figure.tight_layout()
            for extension in ("pdf", "png"):
                figure.savefig(target / f"{name}.{extension}", dpi=180)
            plt.close(figure)

        fig, ax = plt.subplots(figsize=(8, 5))
        for backend, field, label in (
            ("cpu_software", "throughput_mib_s_median", "CPU software (end-to-end)"),
            ("cpu_aesni", "throughput_mib_s_median", "CPU AES-NI (end-to-end)"),
            ("gpu_cuda", "kernel_throughput_mib_s_median", "GPU kernel-only"),
            ("gpu_cuda", "throughput_mib_s_median", "GPU end-to-end")):
            ax.plot(sizes, series(backend, field), marker="o", label=label)
        ax.set(xscale="log", xlabel="Input bytes", ylabel="Median throughput (MiB/s)")
        ax.legend()
        ax.grid(alpha=.2)
        save(fig, "throughput_vs_size")

        fig, ax = plt.subplots(figsize=(8, 5))
        for backend in ("cpu_software", "cpu_aesni", "gpu_cuda"):
            ax.plot(sizes, series(backend, "end_to_end_ms_median"), marker="o", label=backend)
        ax.set(xscale="log", yscale="log", xlabel="Input bytes", ylabel="Median end-to-end latency (ms)")
        ax.legend()
        ax.grid(alpha=.2)
        save(fig, "latency_vs_size")

        transfer = series("gpu_cuda", "transfer_ms_mean")
        kernel = series("gpu_cuda", "kernel_ms_mean")
        total = series("gpu_cuda", "end_to_end_ms_mean")
        residual = [t - h - k for t, h, k in zip(total, transfer, kernel)]
        fig, ax = plt.subplots(figsize=(9, 5))
        positions = list(range(len(sizes)))
        ax.bar(positions, [100*h/t for h, t in zip(transfer, total)], label="Transfer")
        ax.bar(positions, [100*k/t for k, t in zip(kernel, total)],
               bottom=[100*h/t for h, t in zip(transfer, total)], label="Kernel")
        ax.bar(positions, [100*r/t for r, t in zip(residual, total)],
               bottom=[100*(h+k)/t if r >= 0 else 0
                       for h, k, r, t in zip(transfer, kernel, residual, total)], label="Other residual")
        if any(r < 0 for r in residual):
            ax.text(.02, .98, "Negative residual: timing uncertainty; not physical negative overhead.",
                    transform=ax.transAxes, va="top", fontsize=8)
        ax.set_xticks(positions, [f"{n / 1024:g} KiB" for n in sizes], rotation=30)
        ax.set_ylabel("Share of mean end-to-end time (%)")
        ax.legend()
        save(fig, "gpu_overhead_breakdown")

        fig, ax = plt.subplots(figsize=(8, 5))
        cpu = series("cpu_aesni", "end_to_end_ms_median")
        for field, label in (("kernel_ms_median", "GPU kernel-only / CPU AES-NI"),
                             ("end_to_end_ms_median", "GPU end-to-end / CPU AES-NI")):
            ax.plot(sizes, [c/g for c, g in zip(cpu, series("gpu_cuda", field))], marker="o", label=label)
        ax.axhline(1, color="black", linewidth=.7)
        ax.set(xscale="log", xlabel="Input bytes", ylabel="Speedup = CPU time / GPU time")
        ax.legend()
        ax.grid(alpha=.2)
        save(fig, "speedup_vs_size")

        table = [f"% {mode}; median times in ms; end-to-end CPU/GPU speedup.",
                 r"\begin{tabular}{rrrrrr}", r"\toprule",
                 r"Bajtovi & CPU soft. & CPU AES-NI & GPU kernel & GPU ukupno & Faktor \\",
                 r"\midrule"]
        for size, g in zip(sizes, selected):
            sw = float(g["cpu_software"]["end_to_end_ms_median"])
            hw = float(g["cpu_aesni"]["end_to_end_ms_median"])
            kern = float(g["gpu_cuda"]["kernel_ms_median"])
            end = float(g["gpu_cuda"]["end_to_end_ms_median"])
            table.append(f"{size} & {sw:.6g} & {hw:.6g} & {kern:.6g} & {end:.6g} & {hw/end:.4g}" + r" \\")
        table.extend([r"\bottomrule", r"\end{tabular}"])
        (target / "aes_cpu_gpu_table.tex").write_text("\n".join(table) + "\n", encoding="utf-8")


def verify_acceleration_export(folder, metadata):
    """Reject missing, failed, incomplete or mismatched pre-measurement evidence."""
    import hashlib
    method = metadata.get("method", {})
    path = folder / "validation.json"
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != method.get("validation_sha256"):
        raise ValueError("AES acceleration export requires intact validation.json.")
    report = json.loads(path.read_text(encoding="utf-8"))
    if (report != method.get("acceleration_validation") or report.get("passed") is not True
            or report.get("backends_equal") is not True or report.get("mode") != "CBC"
            or report.get("session_id") != method.get("session_id")
            or report.get("purpose") != metadata.get("purpose")
            or not report["completed_utc"] < method["measurement_started_utc"]):
        raise ValueError("AES acceleration requires successful validation before measurement.")
    expected = {(name, backend) for name in ("AES-128", "AES-192", "AES-256")
                for backend in ("software", "aesni")}
    vectors = report.get("vectors", [])
    if (len(vectors) != 6 or {(v["algorithm"], v["backend"]) for v in vectors} != expected
            or any(v.get("passed") is not True or v.get("encrypt_passed") is not True
                   or v.get("decrypt_passed") is not True for v in vectors)):
        raise ValueError("Incomplete AES CBC KAT validation.")
    dispatch = report.get("dispatch", {})
    if (not all(dispatch.get(k) is True for k in ("passed", "available", "cpu_aesni", "aesni_library_loaded"))
            or dispatch.get("mode") != "CBC"
            or dispatch.get("paths") != {"software": "_raw_aes", "aesni": "_raw_aesni"}):
        raise ValueError("Unverified AES native dispatch.")
    records = dispatch.get("preflight", [])
    if (len(records) != 6 or {(r["key_bits"], r["requested"]) for r in records}
            != {(bits, b) for bits in (128, 192, 256) for b in ("software", "aesni")}
            or any(r["native_start_calls"] != {b: 2 if b == r["requested"] else 0
                                               for b in ("software", "aesni")} for r in records)):
        raise ValueError("Incomplete AES dispatch evidence.")


def verify_acceleration_summary(rows, metadata):
    groups = {}
    for row in rows:
        key = (row["algorithm"], int(row["bytes"]), row["operation"])
        backend = row["backend"]
        if (key[0] not in ("AES-128", "AES-192", "AES-256") or key[2] not in ("encrypt", "decrypt")
                or row["mode"] != "CBC" or backend not in ("software", "aesni")
                or row["session_id"] != metadata["method"]["session_id"]
                or backend in groups.setdefault(key, {})):
            raise ValueError("Invalid or duplicate AES summary group.")
        groups[key][backend] = row
        if int(row["seconds_count"]) != metadata["arguments"]["repeats"]:
            raise ValueError("Incomplete AES summary repeat count.")
        for field in ("seconds_median", "throughput_MB_s_mean", "throughput_MB_s_median",
                      "speedup_vs_software_median"):
            if not math.isfinite(float(row[field])) or float(row[field]) <= 0:
                raise ValueError("Invalid AES timing/throughput/speedup.")
    expected = {(name, size, op) for name in ("AES-128", "AES-192", "AES-256")
                for size in metadata["arguments"]["sizes"] for op in ("encrypt", "decrypt")}
    if set(groups) != expected or any(set(g) != {"software", "aesni"} for g in groups.values()):
        raise ValueError("Incomplete paired AES summary.")
    for group in groups.values():
        baseline = float(group["software"]["seconds_median"])
        for row in group.values():
            if not math.isclose(float(row["speedup_vs_software_median"]),
                                baseline / float(row["seconds_median"]), rel_tol=1e-12):
                raise ValueError("AES speedup must use median wall times.")


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("run_directory", type=Path)
    args = cli.parse_args()
    folder = args.run_directory.resolve()
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    if metadata["experiment"] == "aes_cpu_gpu":
        try:
            export_cpu_gpu(folder, metadata)
        except (ValueError, KeyError) as exc:
            cli.error(str(exc))
        return
    if metadata["experiment"] not in ("benchmark", "aes_acceleration"):
        cli.error("Exporter supports benchmark and aes_acceleration runs.")
    acceleration = metadata["experiment"] == "aes_acceleration"
    if acceleration:
        try:
            verify_acceleration_export(folder, metadata)
        except (ValueError, KeyError, TypeError) as exc:
            cli.error(str(exc))
    if not acceleration:
        import hashlib
        validation_path = folder / "validation.json"
        method = metadata.get("method", {})
        if (method.get("cpu_validation", {}).get("passed") is not True
                or not validation_path.is_file()
                or hashlib.sha256(validation_path.read_bytes()).hexdigest() != method.get("validation_sha256")):
            cli.error("CBC export requires recorded, intact pre-measurement validation.")
    with (folder / "summary.csv").open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    if not rows:
        cli.error("No measured data to export.")
    if acceleration:
        try:
            verify_acceleration_summary(rows, metadata)
        except (ValueError, KeyError, TypeError) as exc:
            cli.error(str(exc))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from common import ALGORITHMS
    lines = [
        "% Generated from measured data; purpose: " + metadata["purpose"],
        "% Run: " + metadata["run_id"],
        r"\begin{tabular}{lllrrrrr}" if acceleration else r"\begin{tabular}{llrrrr}",
        r"\toprule",
        (r"Algoritam & Putanja & Operacija & Bajtovi & Srednja MB/s & Medijana MB/s & SD MB/s & Faktor \\"
         if acceleration else
         r"Algoritam & Operacija & Bajtovi & Srednja MB/s & Medijana MB/s & SD MB/s \\"),
        r"\midrule",
    ]
    for row in rows:
        if row["algorithm"] not in ALGORITHMS or row["operation"] not in ("encrypt", "decrypt"):
            cli.error("Unexpected algorithm or operation in summary.")
        if acceleration and (row.get("backend") not in ("aesni", "software")
                             or not row["algorithm"].startswith("AES-")):
            cli.error("Unexpected acceleration backend or algorithm.")
        backend_cell = f'{row["backend"]} & ' if acceleration else ""
        speedup_cell = f' & {float(row["speedup_vs_software_median"]):.3f}' if acceleration else ""
        lines.append(
            f'{row["algorithm"]} & {backend_cell}{row["operation"]} & {int(row["bytes"])} & '
            f'{float(row["throughput_MB_s_mean"]):.3g} & '
            f'{float(row["throughput_MB_s_median"]):.3g} & '
            f'{float(row["throughput_MB_s_stdev"]):.3g}' + speedup_cell + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    prefix = "aes_acceleration" if acceleration else "benchmark"
    (folder / f"{prefix}_table.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    figure, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    series = ([(name, backend) for name in ALGORITHMS if name.startswith("AES-")
               for backend in ("aesni", "software")] if acceleration
              else [(name, None) for name in ALGORITHMS])
    for axis, operation in zip(axes, ("encrypt", "decrypt")):
        for name, backend in series:
            selected = sorted([r for r in rows if r["algorithm"] == name
                               and r["operation"] == operation
                               and (backend is None or r["backend"] == backend)],
                              key=lambda r: int(r["bytes"]))
            axis.errorbar([int(r["bytes"]) for r in selected],
                          [float(r["throughput_MB_s_mean"]) for r in selected],
                          yerr=[float(r["throughput_MB_s_stdev"]) for r in selected],
                          marker="o", label=f"{name} {backend}" if backend else name,
                          linestyle="--" if backend == "software" else "-", capsize=3)
        axis.set_xscale("log")
        axis.set_xlabel("Buffer size (bytes)")
        axis.set_title(operation)
        axis.grid(alpha=0.2)
    axes[0].set_ylabel("CBC throughput (MB/s), mean +/- sample SD")
    axes[1].legend(fontsize=8)
    figure.suptitle(f'{metadata["purpose"]}: {metadata["run_id"]}', fontsize=8)
    figure.tight_layout()
    for extension in ("png", "pdf"):
        figure.savefig(folder / f"{prefix}.{extension}", dpi=180)
    plt.close(figure)
    if acceleration:
        figure, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
        for axis, operation in zip(axes, ("encrypt", "decrypt")):
            for name in ("AES-128", "AES-192", "AES-256"):
                selected = sorted([r for r in rows if r["algorithm"] == name
                                   and r["operation"] == operation and r["backend"] == "aesni"],
                                  key=lambda r: int(r["bytes"]))
                axis.plot([int(r["bytes"]) for r in selected],
                          [float(r["speedup_vs_software_median"]) for r in selected],
                          marker="o", label=f"{name} AES-NI")
            axis.axhline(1, color="black", linestyle="--", label="software baseline (1.0)")
            axis.set(xscale="log", xlabel="Buffer size (bytes)", title=operation)
            axis.grid(alpha=.2)
        axes[0].set_ylabel("Speedup: median software wall time / median AES-NI wall time")
        axes[1].legend(fontsize=8)
        figure.suptitle(f'{metadata["purpose"]}: {metadata["run_id"]}', fontsize=8)
        figure.tight_layout()
        for extension in ("png", "pdf"):
            figure.savefig(folder / f"aes_acceleration_speedup.{extension}", dpi=180)
        plt.close(figure)
    # TODO: Add distribution plots for avalanche and log-scale brute-force illustrations.
    # TODO: Adapt typography and captions to the selected journal before inclusion.


if __name__ == "__main__":
    main()
