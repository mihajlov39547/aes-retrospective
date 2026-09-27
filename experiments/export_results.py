"""Export a verified benchmark run to a LaTeX table and PNG/PDF figure."""
import argparse
import csv
import json
from pathlib import Path


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("run_directory", type=Path)
    args = cli.parse_args()
    folder = args.run_directory.resolve()
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    if metadata["experiment"] != "benchmark":
        cli.error("Initial exporter supports benchmark runs only.")
    with (folder / "summary.csv").open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    if not rows:
        cli.error("No measured data to export.")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from common import ALGORITHMS
    lines = [
        "% Generated from measured data; purpose: " + metadata["purpose"],
        "% Run: " + metadata["run_id"],
        r"\begin{tabular}{llrrrr}",
        r"\toprule",
        r"Algoritam & Operacija & Bajtovi & Srednja MB/s & Medijana MB/s & SD MB/s \\",
        r"\midrule",
    ]
    for row in rows:
        if row["algorithm"] not in ALGORITHMS or row["operation"] not in ("encrypt", "decrypt"):
            cli.error("Unexpected algorithm or operation in summary.")
        lines.append(
            f'{row["algorithm"]} & {row["operation"]} & {int(row["bytes"])} & '
            f'{float(row["throughput_MB_s_mean"]):.3f} & '
            f'{float(row["throughput_MB_s_median"]):.3f} & '
            f'{float(row["throughput_MB_s_stdev"]):.3f}' + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    (folder / "benchmark_table.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    figure, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=True)
    for axis, operation in zip(axes, ("encrypt", "decrypt")):
        for name in ALGORITHMS:
            selected = sorted([r for r in rows if r["algorithm"] == name
                               and r["operation"] == operation], key=lambda r: int(r["bytes"]))
            axis.errorbar([int(r["bytes"]) for r in selected],
                          [float(r["throughput_MB_s_mean"]) for r in selected],
                          yerr=[float(r["throughput_MB_s_stdev"]) for r in selected],
                          marker="o", label=name, capsize=3)
        axis.set_xscale("log")
        axis.set_xlabel("Buffer size (bytes)")
        axis.set_title(operation)
        axis.grid(alpha=0.2)
    axes[0].set_ylabel("CBC throughput (MB/s), mean +/- sample SD")
    axes[1].legend(fontsize=8)
    figure.suptitle(f'{metadata["purpose"]}: {metadata["run_id"]}', fontsize=8)
    figure.tight_layout()
    for extension in ("png", "pdf"):
        figure.savefig(folder / f"benchmark.{extension}", dpi=180)
    plt.close(figure)
    # TODO: Add distribution plots for avalanche and log-scale brute-force illustrations.
    # TODO: Adapt typography and captions to the selected journal before inclusion.


if __name__ == "__main__":
    main()
