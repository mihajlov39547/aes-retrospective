# Dataset and provenance audit

Audit date: 2026-10-29. Repository HEAD `60670157fcde24ea2304d20052ca9d93be54e59f`, branch `main`, initially clean working tree. Remote main returned the same SHA by read-only `git ls-remote`. Public raw source files were byte-compared with Git blobs at current and historical commits; four checks passed (`git_provenance.json`). This verifies source availability, **not publication of all local results**. No fetch, checkout, commit or push was used.

## Exact manuscript campaign

`chapters/09_eksperimentalna_analiza.tex:405–407` and `univerzitetska-misao/mihajlovic2026validiran.tex:247–249` contain the supplied reference values. Their source is `experiments/results/aes_cuda_cpu_gpu-final-aggregate/aggregate.csv`, reconstructed from these five directories under `experiments/results/`:

| Seed | Original study directory |
|---|---|
| 2003 | `aes_cuda_cpu_gpu-study-20260930T205447700308Z` |
| 2004 | `aes_cuda_cpu_gpu-study-20260930T205542542732Z` |
| 2005 | `aes_cuda_cpu_gpu-study-20260930T205652619168Z` |
| 2006 | `aes_cuda_cpu_gpu-study-20260930T205851562886Z` |
| 2007 | `aes_cuda_cpu_gpu-study-20260930T205950403576Z` |

Each contains `raw.csv`, `summary.csv`, `results.json`, `metadata.json`, `validation.json`, `requirements-lock.txt` and `source/`. Exact UUIDs and SHA-256 maps are in `reconstruction_manifest.json`; original raw paths accompany each session estimate. Recorded source commit is `cd6b18f46414ac2e2f9d5ae61d848867b17361f9`. Session Git status records the untracked validation directory created during execution, not a clean tree; archived source hashes are therefore checked directly.

All five have Windows-10-10.0.19045-SP0, Intel i5-10300H (four physical/eight logical cores), NVIDIA GTX 1650 Ti (4 GB class), Python 3.12.10, PyCryptodome 3.23.0, CuPy 13.6.0, driver API 13030 and runtime 12090. Source and GPU metadata maps match across sessions. Library binaries and machine scheduling are not independently attested.

The intended protocol is AES-128 encryption, ECB and full 128-bit big-endian CTR, sizes 1 KiB, 16 KiB, 1 MiB, 16 MiB and 32 MiB; seeds 2003–2007; five warmups and twenty retained repetitions per group; explicit CPU software/AES-NI; baseline/v1 CUDA; pinned host buffers; resident N=1 and pipeline scopes. Six jobs per mode/size/repetition yield 1,200 raw rows and 60 groups per session. Warmups are supported by source/configuration but are not exported in this historical campaign. All 6,000 retained rows and 300 session groups were checked. No samples were dropped.

Validation passes for all five paths (including the untimed T-table candidate): 18 KAT/differential cases per path, counter-wrap rejection, matching output hashes, dispatch checks, per-observation validation flags and identical pair hashes across six measured jobs. Validation-file hashes and every archived source hash match metadata. This verifies retained correctness evidence without rerunning cryptography.

The T-table candidate was rejected after a separate pilot and does not contribute timed final rows. The economic baseline is selected to reproduce the manuscript, not because it wins. Both final GPU profiles, both scopes and all five sizes are exported to avoid selecting favorable results.

## Reconstruction and discrepancies

| Binary input | CPU AES-NI MB/s | Baseline resident MB/s | Baseline pipeline MB/s |
|---|---:|---:|---:|
| 1 MiB | 1381.7 | 5017.1 | 1313.1 |
| 16 MiB | 1446.5 | 3655.6 | 1103.1 |
| 32 MiB | 1455.8 | 4800.6 | 1204.5 |

All nine reference cells agree after rounding to one decimal. All 60 historical aggregate time/throughput groups and GPU paired AES-NI speedups agree within the stated tolerance. No numerical discrepancy was found. Full-precision minus rounded manuscript values are retained rather than concealed in `RECONSTRUCTED_RESULTS.csv`. Rounded-value differences are rounding, not failed reconstruction.

Documented estimator: first median of twenty individual rates, then median of five session medians. Latencies are summarized separately. Since twenty is even, rate median generally differs from bytes/median(time). Paired speedup is median across five ratios of CPU session median time to GPU session median time. It is neither a pooled 100-repetition statistic nor ratio of aggregated throughput medians. Original aggregate code was inspected, not executed, because its writer targets the old results directory.

## Discovery inventory and exclusions

`DATASET_INVENTORY.csv` has 136 location records, including historical campaigns, native orchestrated sessions, incomplete extracted artifacts, smoke/pilot evidence and deduplicated Oracle archive sessions. This is an inventory of discovered locations, **not 136 independent eligible sessions**. Source hashes, seed, purpose, warmups/repetitions, hardware, OS, mode/backend labels, raw count and file locations are retained per record. Boundary details for selected and supplementary campaigns are below. Generic missing fields remain unknown; inventory candidate labels do not replace verification.

| Campaign | Evidence and session count | Workload/scope | Suitability |
|---|---|---|---|
| September paired historical study | Five validated sessions above | AES-128 ECB/CTR; allocating PyCryptodome transform; baseline/v1 resident and prepared pipeline | Primary CTR economic model; ECB audit-only |
| Historical standalone CUDA, fixed-order aggregate and diagnostics | Separate pilot/study/validation directories in inventory | Standalone GPU scopes, different campaigns/order; no matched historical CPU numerator | Excluded from paired economic model |
| CBC benchmark/AES acceleration, GCM, avalanche, keyspace | Study records exist; local metadata inventoried | Different modes, key sizes, operations or objectives | Excluded, even where study purpose is recorded; not revalidated for this paper |
| October GTX study | Five seeds 2003–2007, run `heterogeneous-core-v1-20261014T102836520134Z-1472bd2f13cf` | Same application sources/scopes, later campaign, i5-10300H/GTX, Windows | Separate validated contextual evidence; never pooled with September |
| October T4 study | Five seeds, run `heterogeneous-core-v1-20261014T105540691660Z-9bb918a84386` | Xeon @2 GHz/Linux, PyCryptodome 4.0.0, Tesla T4; AES-128 ECB/CTR | Validated contextual comparison to its own host only; authoritative `.tar.gz`, not incomplete adjacent extraction |
| October T600 study | Five seeds, run `heterogeneous-core-v1-20261014T064407642462Z-636c48c0ebaf` | i7-11850H/Windows kernel 10.0.22631, T600 Laptop GPU; PyCryptodome 3.24.1 | Validated contextual evidence, separate hardware/software strata |
| Windows CPU phase 1 | Five `single-study-*` sessions, seeds 2003–2007, five warmups/twenty reps; native OpenSSL 3.6.5 | AES-128 ECB/CTR, one worker, PyCryptodome preallocated transform and EVP native transform; instrumented operation envelope | Validated, complete; useful implementation/boundary caution, not replacement CPU for old GPU |
| Oracle ARM64 phase 1 | Ten unique study sessions (five single, five two-worker) plus three smoke sessions across archives | AES-128 ECB/CTR, PyCryptodome/OpenSSL 3.0.13 default and ARM capability-mask control; aarch64, notes identify Neoverse-N1/2 vCPU; five warmups/twenty reps | Study records validated; one/two-worker campaigns separate; smoke excluded; no x86 AES-NI substitution |
| Integrated Colab CPU/GPU validation | Two locally retained smoke result sessions; no final integrated five-session study found | Local diagnostic GTX, new EVP/PyCryptodome versus CUDA boundaries | Smoke only; no T4 final performance claim from this framework |
| T4 page batching phase 2 | Five complete study sessions 2003–2007 plus smoke gate; five warmups/twenty reps, 600 rows/session including warmups | AES-128 CTR; independent 1 MiB pages in batches 1/4/16/32, continuous control; Xeon/Linux/T4/OpenSSL 3.0.13; prepared EVP transform, operation, CUDA resident/pipeline | Validated study, useful separate workload example. Counter/message layout and CPU implementation differ; no pooling |
| Local page smoke / orchestrated smoke and pilot | Individually inventoried; incomplete no-GPU suite also retained | Diagnostic/preparation only | Never final performance evidence |

`experiments/configs/` contains execution templates, including heterogeneous-core smoke/pilot/study and local/T4 broader suites. Configuration availability alone is not a completed experiment. Existing source README/readiness statements are sometimes stale: phase-2 page READINESS says no study launched, but the five complete local records and campaign summary establish that it subsequently ran. No old document was edited.

## Supplementary verification and use

All 405 inputs referenced by the existing cross-platform audit were rechecked against its manifest, with T4 read directly from the intact archive. The existing audit reports zero estimator discrepancies, matching source snapshots and complete raw grids on three platforms. That numerical audit is reused with explicit provenance; this audit does not claim to have independently recomputed all cross-platform extended statistics again. `independent_aggregates.csv`, `session_level_statistics.csv`, `session_contrasts.csv`, `platform_comparison.csv`, `platform_environment.csv`, `pipeline_recorded_components.csv`, `session_provenance.json` and the claim matrix retain their original meanings. Their hashes are captured in `supplementary_manifest.json`.

The 16 MiB GTX dip is retained, not corrected or excluded. Fixed ascending sizes, dynamic clocks, Windows/WDDM, allocation and memory effects prevent causal attribution. The later analysis's repeated dip and T4 CPU ECB/CTR disparity do not establish causes for the earlier campaign.

Windows CPU records were checked against full expected raw grids, saved validation and source hashes; all saved summary fields reproduce with the existing pure statistics implementation. At 32 MiB CTR, median-of-session EVP transform rates are 5536.6 MB/s, whereas operation-envelope rates are 1478.9 MB/s. Those scopes cannot be interchanged with the old PyCryptodome allocating transform.

Oracle archives are read in place without extraction; duplicate session IDs must have identical metadata/raw hashes. Ten study sessions pass source/validation/grid checks. At 32 MiB per worker, default EVP single-worker transform is 4029.7 MB/s, single-worker operation envelope 1059.6 MB/s, and two-worker aggregate operation envelope 2031.1 MB/s (64 MiB numerator). Both workers' individual transforms remain separate. Identical seeds do not make the single/two-worker campaigns statistically paired. These observations support boundary-aware reasoning, not a Windows multicore capacity claim.

All page-study source hashes and saved correctness cases pass; complete schedule, pairing, session summaries and campaign summary reproduce using inspected pure statistical/protocol modules. For independent pages, median-of-session **ratios of median times**, CPU EVP transform / GPU prepared pipeline, are 0.5404, 0.7137, 0.8240 and 0.9125 for 1/4/16/32 pages; all five sessions at every size remain below one. Median-of-per-repetition-ratio estimates are separately retained in `SUPPLEMENTARY_RESULTS.csv`. This is useful evidence that batching does not guarantee a GPU advantage against the tested EVP path. It does not revise the older T4 PyCryptodome speedup of 4.7613 at 32 MiB; the baseline, timing boundary, software environment and campaign differ.

No validated integrated energy measurement or market-price dataset was found in the inspected evidence. Before/after `nvidia-smi power.draw` snapshots are point power telemetry, not joules per encryption or comparative CPU/GPU energy. No price or energy values are inferred.
