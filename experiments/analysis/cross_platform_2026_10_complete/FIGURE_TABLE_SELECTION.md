# Final figure and table selection

Use four central figures and three central tables. Keep full-resolution vector exports for layout and PNG counterparts for review. All selections below refer to the primary studies; no historical runs are pooled. Existing files live in `figures/` relative to this document. No new chart was rendered for this writing handoff.

## Four central figures

| Order | Figure and exact source | Purpose and proposed caption |
|---|---|---|
| 1 | Reuse `figures/03_pipeline_speedup_vs_aesni.pdf` (PNG counterpart: `03_pipeline_speedup_vs_aesni.png`). | **Prepared-buffer GPU pipeline versus paired CPU AES-NI transform.** Baseline/v1, ECB/CTR and all five sizes, separately for each platform. The estimator is the median of five session-specific CPU/GPU median-time ratios; the five-session range is descriptive, not a confidence interval. The equality line identifies observed offloading gains and losses. Each panel uses its own host CPU. |
| 2 | New, derived only from existing observations: **32 MiB resident/pipeline speedup reversal and consistency**. Suggested eventual filenames `manuscript_resident_pipeline_reversal.pdf` and `.png`; not yet generated. | **Resident-only gains versus prepared-buffer pipeline gains at 32 MiB.** Three platform columns and ECB/CTR rows; baseline/v1 separate colors; resident/pipeline separate horizontal positions. Show all five session ratios, a median marker and equality line. Connect resident/pipeline values only for the same seed, implementation and platform, identifying the connection as a scope contrast rather than repeated measurements of an identical timer. This directly exposes GTX/T4 ECB reversal and T600 mixed-session outcomes. |
| 3 | Reuse `figures/02_pipeline_throughput.pdf` (PNG counterpart: `02_pipeline_throughput.png`). | **Absolute prepared-buffer GPU pipeline throughput across input sizes.** Decimal MB/s, binary workload labels, logarithmic size axis and common rate scale; separate platform panels and modes/implementations. Median of five session throughput medians, with observed session range. These are GPU rates, not CPU-relative speedups or a controlled hardware-class comparison. |
| 4 | Reuse `figures/05_session_variability.pdf` (PNG counterpart: `05_session_variability.png`). | **Between-session variability of CPU transform and GPU pipeline latency.** CV across five session median times, sample SD divided by their mean. This figure covers CPU transform and GPU pipeline, not resident timing. It does not pool repetitions or measure uncertainty of the population mean. Read with the individual session points in Figure 2. |

For new Figure 2, use `CLAIM_EVIDENCE_MATRIX.csv` rows where `input_bytes=33554432`, `metric` is `speedup_isolated_vs_cpu_aesni` or `speedup_pipeline_vs_cpu_aesni`, and `implementation` is baseline/v1. The `session_values` JSON provides all five values keyed by seed. Verify against the matching CPU/GPU latency medians in `session_level_statistics.csv` before export. Use a shared log speedup scale including one across panels. Do not derive this figure from ratios of the plotted throughput aggregates. Show seed identities in the caption/legend or accompanying data table. This adds no new measurements, estimator, model, or hypothesis test.

These four panels prioritize the offloading decision, the timing-boundary reversal, the absolute GPU contrast, and variability. The consumer GTX 1650 Ti and professional T600 must retain distinct labels rather than a pooled “4 GB GPU” curve. The new Figure 2's fixed size is disclosed; Figure 1 retains the complete size grid to prevent selection of a favorable point from obscuring failures elsewhere.

## Three central tables

| Table | Contents and exact evidence | Editorial limits |
|---|---|---|
| 1. Platforms and common protocol | Three rows from `platform_environment.csv`: user label plus captured OS/kernel, CPU and exposed logical processors, GPU/model/capacity, NVIDIA driver, CUDA runtime, CuPy and PyCryptodome. Add a common-protocol note: AES-128; five seeds 2003–2007; five warmups; twenty repetitions; five sizes; validated baseline/v1; resident N=1; pinned prepared-buffer pipeline. Source identity and full commits link to `source_comparison.csv` and `reproducibility_manifest.json`. | Distinguish the two 4 GB product classes and the T4. Do not infer Windows marketing edition from the NT version. Put verbose environment fields and full run IDs in supplementary inventory. |
| 2. Decisive 32 MiB paired comparisons | Twelve rows: platform × baseline/v1 × ECB/CTR. Columns: resident/AES-NI speedup, pipeline/AES-NI speedup, pipeline/software-CPU speedup; each with median [session min, max] and count >1/5. Source: corresponding matrix E rows. Add the T600 baseline CTR IQR=0.030896 and CV=8.180% in a note. | Speeds are median paired timing ratios, not aggregate-throughput ratios. Mark mixed-direction cases explicitly. Twelve rows retain negative/mixed cases alongside the strongest positive result. |
| 3. Evidence-qualified practical conclusions | Five rows: software-only baseline can overstate practical benefit; resident/pipeline reversal; T600 CTR pipeline positive case; T4 host-mode dependence; configuration-specific size/variation limits. Give exact operating conditions, supporting matrix IDs/run IDs, descriptive session counts and one qualification per row. Use `MANUSCRIPT_CLAIMS.md` and the seven findings in `RESEARCH_FRAMING.md`. | This is a compact claim/qualification table, not a repetition of every numerical plot. Full ranges, IQRs, CVs, source paths and hashes remain in the machine-readable supplement. |

The 36-row representative grid in `MANUSCRIPT_CLAIMS.md` covers 1, 16 and 32 MiB, both modes and both implementations on all platforms, with separate resident/pipeline throughput and host-paired speedups. Retain it in supplementary material rather than adding a fourth central table or shrinking it into an unreadable central table.

## Supplementary material rather than additional central figures

- `figures/01_resident_throughput.pdf`: useful full-size resident reference; Figure 2 gives the central scope comparison.
- `figures/04_v1_vs_baseline.pdf`: candidate-specific detail; avoid making a small conditional v1 gain the main contribution.
- `figures/06_16MiB_anomaly.pdf`: observed size feature, with `anomaly_local_dips.csv` joint counts; no asserted cause.
- `figures/07_cpu_ecb_ctr.pdf`: the host-mode disparity supporting the T4 interpretation.
- `figures/08_pipeline_resident_ratio.pdf`: throughput retention, not an independently measured pure transfer penalty. Keep the distinction between throughput ratios and latency ratios.

The existing figures have PDF and PNG versions; reuse the PDFs without rasterization where possible. Captions must spell out measurement scope, estimator, session unit, decimal MB/s versus binary MiB, and whether a band is an observed range. Do not add significance stars, fitted performance models, causal labels, or application-level claims. Existing analytical figures and their underlying artifacts remain unchanged.
