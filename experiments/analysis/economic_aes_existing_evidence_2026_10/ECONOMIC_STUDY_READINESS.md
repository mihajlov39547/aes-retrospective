# Research handoff and readiness

**READY WITH EXPLICIT LIMITATIONS.** The evidence supports a narrow secondary study of conditional resource-charge thresholds for specific AES-128-CTR paths. It does not support empirically measured TCO, comprehensive investment ROI, energy efficiency, universal GPU superiority or total CPU multicore capacity.

The historical results reconstruct completely. Five sessions are repeated measurements on one local hardware pair, not five independent machines. Their application-level CPU path is serial and synchronous; native thread count/core residency is not independently verified. CPU output allocation is timed; GPU buffers, pinning/staging and key preparation are outside GPU pipeline timing. The compared scope is prepared in-memory encryption, without authentication or business-application I/O.

## Economic model and attribution

For a selected unrounded rate R in decimal MB/s:

```text
t_seconds_per_GB = 1000 / R
c = Cost_per_GB = (t_seconds_per_GB / 3600) * h
GPU cheaper in variable resource charges when h_GPU / h_CPU < R_GPU / R_CPU
```

This assumes repeated batches at the observed rate, linear attributable occupied-resource charging, no minimum billing unit, no queue/utilization loss and comparable accounting periods. It is an illustrative model, not an observed charging arrangement. Define h consistently: CPU resource attributable to the single-stream service versus the GPU service **including its required host allocation**. Comparing a whole GPU-server hourly charge to one CPU core price without explaining resource allocation is invalid. The measurements do not establish how much otherwise idle capacity can be resold, or whether marginal cost is proportional to benchmark wall time.

Resident compute-only thresholds apply only if the workload already resides on the device and excluded preparation/transfer costs are separately accounted for. They cannot justify host-memory offload economics. Both v1 and baseline are available in the CSV; baseline is the manuscript reproduction reference, not a fastest-path selection.

The economic model uses the ratio of unrounded aggregate rate medians, preserving the published throughput estimator. Original paired-time speedups remain separate. At session level, rate ratios and time ratios also differ slightly because twenty repetitions have an even-sample median. There is no algebraic identity between these different estimators. For rates defined as bytes/median time, the time and throughput threshold identities do hold.

| Input | CPU s/decimal GB | Baseline resident s/GB | Baseline pipeline s/GB | Pipeline aggregate-rate hourly threshold | Paired-time threshold median [min, max] |
|---|---:|---:|---:|---:|---:|
| 1 MiB | 0.723750 | 0.199318 | 0.761580 | 0.950326 | 0.952927 [0.922557, 0.985641] |
| 16 MiB | 0.691302 | 0.273553 | 0.906509 | 0.762598 | 0.749551 [0.561937, 0.766807] |
| 32 MiB | 0.686887 | 0.208306 | 0.830245 | 0.827330 | 0.823251 [0.821742, 0.842243] |

Median paired GPU relative elapsed-time increases are 4.94%, 33.41% and 21.47% respectively. These are derived ratios of time medians; they are not percentages calculated from rounded publication values. Paired resident thresholds are 3.656319, 2.579649 and 3.296983; their aggregate-rate counterparts are 3.631132, 2.527121 and 3.297491. Neither is a host-memory deployment threshold.

At equal normalized hourly charge 1.0, modeled CPU versus baseline pipeline cost per decimal GB is:

| Input | CPU normalized units/GB | GPU normalized units/GB |
|---|---:|---:|
| 1 MiB | 0.000201042 | 0.000211550 |
| 16 MiB | 0.000192028 | 0.000251808 |
| 32 MiB | 0.000190802 | 0.000230624 |

These are normalized cost units, not EUR/USD. Under the aggregate-rate model, GPU pipeline is cheaper at hourly ratios 0.50 and 0.75 for these three large sizes; CPU is cheaper at 1.00, 1.25, 1.50 and 2.00. At 16 MiB and 0.75, the median paired-time threshold lies slightly below the scenario price ratio and session outcomes vary; do not describe the aggregate-rate result as robust across all sessions. Exact session counts and ranges are in the sensitivity CSV. At 1 KiB and 16 KiB, baseline pipeline loses throughout the supplied 0.50–2.00 range. No supplied scenario is equal within the model tolerance. Equal cost occurs at each unrounded threshold. The full CSV also retains v1 and resident outcomes.

## Fixed-cost break-even

```text
Delta_C(V) = (F_GPU - F_CPU) + (c_GPU - c_CPU) * V
V* = (F_GPU - F_CPU) / (c_CPU - c_GPU)
```

F is fixed attributable cost over the same period; c is variable cost per decimal GB; V is period volume. `economic_model.break_even` checks finite nonnegative costs, zero denominator, positivity and optional feasible volume. No fixed costs, target volume, billing period or capacity utilization have been supplied, so no empirical V* is estimable.

- If GPU variable cost is lower and fixed premium is positive, a positive candidate exists; GPU is cheaper above it. Demand, sustainable capacity, utilization and period must still make it feasible.
- If GPU variable cost is higher and GPU fixed cost is lower, a positive crossing can exist but GPU is cheaper **below** it. Calling that an investment-payback volume would reverse the meaning.
- Equal variable costs give no unique crossing; if fixed costs also match, all volumes tie.
- At equal hourly charges, the historical large-batch baseline pipeline has higher modeled variable costs. Assuming a nonnegative GPU fixed premium: **no positive break-even under these assumptions**. A zero fixed premium ties only at V=0, not at a positive volume.
- When fixed and variable costs favor the same alternative, there is no positive crossing. A finite positive algebraic candidate outside feasible demand/capacity is not an economically realizable break-even.

No invented fixed-price scenario is needed. This linear model omits financing, depreciation rules, labor, maintenance, redundancy, licensing, procurement, idle reservations, power and cooling, service-level penalties and opportunity costs. It is not complete TCO.

## Evidence quality and safe scope

`CLAIM_EVIDENCE_MATRIX.csv` separates EMPIRICALLY MEASURED, VERIFIED FROM SOURCE CODE, DERIVED FROM MEASUREMENTS, ILLUSTRATIVE ASSUMPTION and UNSUPPORTED / UNKNOWN. Unsafe claims include “GPU is more energy efficient,” “GPU has better investment ROI,” “CPU benchmark measures all cores,” “GIL guarantees one native thread,” “pipeline-minus-resident is PCIe time,” “v1 represents production-optimal CUDA,” “CTR provides authenticated security,” and “the economic study is novel because the repository has no identical paper.”

The later three-platform campaign is valid separate context and cautions against hardware-general conclusions. Windows EVP and Oracle operation-envelope evidence show why implementation and boundary choice matter. Completed T4 page batches provide a methodologically distinct example where prepared GPU pipeline time exceeds native EVP transform time throughout the tested grid. None supplies missing market prices, energy observations or a matched Windows multicore GPU comparison. No new benchmark is necessary for the narrow proposed study.

There is substantial technical overlap with the earlier retrospective/validated manuscript and the SJEE cross-platform work. The new contribution must be the explicitly conditional economic decision model, estimator-sensitive thresholds and resource-allocation assumptions. Reusing measurements requires disclosure and citation of prior dissemination, with author/editor review of overlap. The audit establishes neither novelty nor journal acceptance criteria.

## Recommended titles

Serbian: **Uslovna analiza troškovne efikasnosti CPU AES-NI i CUDA infrastrukture za AES-128-CTR enkripciju na osnovu postojećih merenja**

English: **Conditional Cost-Efficiency Analysis of CPU AES-NI and CUDA Infrastructure for AES-128-CTR Encryption Using Existing Measurements**

## At most three remaining actions

1. Author-review the selected campaign, threading/boundary wording and disclosure/citation of overlapping technical manuscripts.
2. Define the attributable resource and workload scenario (billing period, host allocation, utilization and volume); retain normalized costs unless documented prices are explicitly added.
3. Archive the selected raw sessions, source snapshots and this audit together in an accessible research supplement; local/GitHub source availability alone does not ensure raw-data availability.
