# Research framing for the manuscript handoff

## Recommended positioning

A validation-first, reproducible assessment of AES acceleration across two accessible NVIDIA laptop GPUs and a datacenter GPU, showing how workload size, cipher mode, hardware-accelerated CPU baselines, and explicitly defined measurement boundaries determine the observed advantage of GPU offloading.

The contribution is the paired assessment and its interpretation, not a new AES algorithm or a claim that a hardware category always wins. The consumer GeForce GTX 1650 Ti and entry-level professional T600 Laptop GPU both have 4 GB of memory; memory capacity and product class describe the tested devices rather than explain their performance.

## Motivation and practical relevance

The historical progression from software AES to CPU instruction acceleration and GPU execution makes the choice of baseline central to a retrospective performance assessment. A GPU can appear compelling against software AES or with input already resident on the device, while providing little or no advantage over AES-NI when host-device movement is included. Accessible laptop GPUs make this distinction practically relevant beyond dedicated accelerator installations. We therefore examine two Windows laptop configurations and a Linux/Colab T4 configuration using validated paired inputs and separate CPU transform, GPU resident, and prepared-buffer GPU pipeline measurements. The objective is to establish when the observed speedup survives a more inclusive timing boundary, rather than to infer full application performance from kernel throughput.

## Research questions

1. Under which tested input sizes and AES modes do baseline and optimized-v1 CUDA implementations outperform software AES and AES-NI on each host, and which advantages persist across all five sessions when transfers are included?
2. How do resident-only and prepared-buffer pipeline boundaries change the magnitude and direction of paired CPU–GPU comparisons, including the observed differences between the two 4 GB laptop configurations and the T4 configuration?
3. How consistent are these comparisons across sessions, and which size- and mode-dependent features constrain their practical interpretation?

## Exactly three principal contributions

1. **A reproducible, validation-first paired methodology.** The study makes input identity, CPU dispatch, cryptographic correctness, archived source identity, seed configuration, and distinct timing boundaries explicit, with independent reconstruction of session-based estimators from raw observations.
2. **A matched-workload, three-configuration empirical assessment.** Fifteen sessions and 18,000 raw measurements document software CPU AES, CPU AES-NI, and baseline/v1 CUDA resident and prepared-buffer pipeline execution, preserving the independence of each platform and the five-session replication structure.
3. **An evidence-qualified interpretation of practical offloading.** The analysis identifies observed laptop GPU advantages, resident-to-pipeline reversals, mode-dependent T4 comparisons, and session variability, separating reproducible observations from unsupported hardware-class, operating-system, and application-level generalizations.

These are study contributions, not priority claims that no earlier work has used these methods. The full claim IDs, conditions, original run IDs and input hashes are in `CLAIM_EVIDENCE_MATRIX.csv`; `MANUSCRIPT_CLAIMS.md` supplies the complete workload map.

## Seven defensible key findings

1. **The evidence is internally complete and reproducible.** All three selected five-session studies pass the existing audit; the 18,000 raw observations reproduce the saved estimators with zero detected discrepancies at the stated floating-point tolerances. Matching archived active sources support source-level comparability, while different environments remain explicit confounders (M01–M02).
2. **Software CPU AES is an insufficient sole baseline for an offloading claim.** At 32 MiB, both laptop GPUs beat their paired software CPU in every session for both timed CUDA implementations and both modes, including the pipeline. Median pipeline speedups span approximately 4.39–4.58× on GTX and 6.27–6.36× on T600. Several of those same conditions lose to AES-NI or reverse direction between sessions. See the software/AES-NI maps in `MANUSCRIPT_CLAIMS.md`.
3. **Resident-only gains do not guarantee transfer-inclusive gains.** At 32 MiB every tested GPU/implementation/mode combination beats its host AES-NI in resident measurements in 5/5 sessions. The GTX pipeline median is below one for all four implementation/mode combinations; ECB loses in all five sessions, while CTR occasionally crosses one. This supports a scope-dependent reversal, not a blanket claim that GPU encryption is slower.
4. **A defensible 4 GB pipeline gain exists under specific conditions.** T600 baseline CTR at 32 MiB achieves a median paired AES-NI speedup of 1.353841×, with range 1.128769–1.391103× and a gain in 5/5 sessions. The speedup IQR is 0.030896 and sample CV is 8.180%. This selected strongest all-five laptop pipeline case corresponds to approximately 26.14% lower paired latency, not 35.38% lower latency. T600 baseline and v1 CTR also show 5/5 pipeline gains at 1 MiB. No tested GTX pipeline condition has a 5/5 gain over AES-NI.
5. **The T4 contrast depends strongly on the host CPU's cipher-mode behavior.** At 32 MiB T4 baseline/v1 pipeline speedups over its own AES-NI are approximately 4.76× for CTR in 5/5 sessions, but approximately 0.89× for ECB, losing in 5/5. Its host AES-NI ECB/CTR throughput ratio is approximately 5.38×, compared with approximately 1.26× on the Windows hosts. These paired speedups must not be interpreted as direct T4/laptop GPU throughput ratios.
6. **The size feature is configuration-dependent.** All eight GTX GPU implementation/mode/scope groups show a 16 MiB throughput dip below both 1 and 32 MiB in 5/5 sessions. T600 counts vary from 3–5/5; T4 resident counts are 4/5 and T4 pipeline counts are 0/5. This supports an observed feature of these runs, not a universal size threshold or a demonstrated cache, driver or thermal mechanism (`anomaly_local_dips.csv` and matrix size-contrast rows).
7. **V1 is not uniformly better and session variation matters.** The baseline/v1 comparisons change with platform, scope, mode and size. For example, at T4 32 MiB resident CTR, v1 has an approximately 0.6% directionally consistent advantage; resident ECB is slightly slower. T600 32 MiB v1 CTR pipeline has a median advantage over AES-NI but reverses in at least one session. Small or mixed effects require the session range and counts, not a single peak number.

## Practical implications

For Windows laptop users, a 4 GB NVIDIA GPU is a plausible accelerator for selected prepared-buffer workloads, but neither the capacity nor the product label predicts a win over AES-NI. The professional T600's observed all-five CTR pipeline advantage is a stronger offloading example than a resident-only maximum. The consumer GTX's software-CPU and resident-only gains remain useful findings, provided the manuscript does not turn them into an AES-NI pipeline recommendation. Software AES represents the selected software backend, not every possible CPU implementation.

For Linux/datacenter environments, the T4 results demonstrate substantial throughput in the recorded configuration and a large paired CTR advantage. The ECB result shows why the host CPU and mode must accompany any GPU speedup claim. Absolute GPU rates at 1, 16 and 32 MiB should be compared separately from host-specific CPU/GPU ratios. Neither this Colab allocation nor this T4 represents all cloud CPUs or datacenter GPUs.

Resident throughput is relevant to work already on the device; pipeline timing is relevant to the tested sequence with prepared pinned buffers. Neither includes the full cost of application I/O, initialization, allocation/pinning, key setup, authentication or service orchestration. ECB is a performance probe, not an application security recommendation. CTR measurements do not assess authenticated encryption or counter-management correctness in an application.

## Limitations and threats to validity

- One machine/allocation per platform and five sessions per machine limit external validity. The twenty repetitions are nested timing observations, not 100 independent sessions. Directional consistency is descriptive, not a significance test, confidence guarantee, or proof of future reliability. Selecting the strongest observed case is disclosed.
- CPU, GPU, memory system, driver model, runtime, CuPy, PyCryptodome, Python and OS differ. This is not an isolated Windows 10/11, consumer/professional/datacenter, or library-version experiment. The cloud CPU's precise SKU is unavailable. Marketing OS labels are user-provided; captured kernel facts are reported separately.
- Identical active archived source bytes do not imply identical compiled binaries. Commits differ and a dirty tree was recorded on one host. Native AES-NI initialization supports dispatch but is not an instruction trace. Warmup execution is provenance-supported rather than directly observable in raw exports.
- The prepared-buffer pipeline excludes several application costs; CPU output allocation is inside its transform boundary while GPU buffers are preallocated. These are intentionally disclosed scopes, not interchangeable full-encryption implementations. Transfer component host intervals include synchronization, and independent pipeline-minus-resident differences cannot identify pure PCIe transfer time.
- Fixed ascending size order confounds size with elapsed time. Before/after telemetry cannot determine the cause of the 16 MiB feature. Frequency, temperature, cache, allocation, driver and virtualization explanations remain hypotheses. No measurements were discarded as outliers.
- The study covers AES-128 encryption, ECB/CTR, five sizes from 1 KiB to 32 MiB, and two timed CUDA candidates. It does not establish capacity limits, cost efficiency, energy efficiency, multi-stream scaling, full application behavior, GCM performance, or key-search speed. T-table was validated but not timed in the final study.
- The intact T4 archive is authoritative. The earlier incomplete extraction is an import failure, not a numerical discrepancy. Hashes establish internal consistency rather than authenticity against coordinated tampering. Dataset integrity/completeness does not itself establish publication readiness.

## Recommended manuscript outline

1. **Introduction and AES-retrospective motivation:** the three research questions and three contributions, with methodological rather than hardware novelty.
2. **Background and measurement semantics:** software AES, AES-NI, CUDA candidates, ECB/CTR, and the three timing boundaries; distinguish encryption throughput from key-search rate.
3. **Experimental design and reproducibility:** platform/confounder table, paired inputs, validation, seeds, repetitions, provenance and exact session estimators.
4. **Results:** pipeline versus AES-NI first; resident/pipeline reversals; matched GPU throughput; five-session variation and mode/size features.
5. **Practical interpretation and threats to validity:** the qualified T600 positive result, GTX limits, host-dependent T4 contrast, exclusions and unresolved mechanisms.
6. **Conclusion:** answer the research questions within the measured configurations; preserve the methodology as the principal contribution. Link the complete evidence matrix and secondary analyses as supplementary material.

This is proposed framing and claim language for an author handoff, not a rewrite of the manuscript or a request for a new experiment campaign.
