# Scientific contribution revision

The manuscript now centers on how much of an optimized implementation's advantage survives expansion from transform timing to the broader instrumented operation. CBC and GCM remain supporting workloads. No benchmarks or new measurements were executed. The existing LaTeX structure and PDF/DOCX build scripts were preserved.

## Main analytical changes

- Abstract and Introduction establish one central contribution, supported by Arm64 implementation sensitivity and Windows attenuation.
- Section 4.1 retains all five validated transform rates and explicitly distinguishes library/interface contrasts from instruction speedups.
- Section 4.2 distinguishes between-library ratios from within-library throughput retention. Figure 2 now has measured-throughput and relative-advantage panels, generated from existing Windows session summaries.
- Section 4.3 retains all CBC/GCM table values and explains separate campaign scopes, encryption/verification requirements and the absence of a measured GCM-versus-CTR authentication penalty.
- Discussion provides practical configuration and interface checks, treats reuse/conversion changes as hypotheses, consolidates validity limits, and motivates matched interfaces, instruction profiling, Arm64 GCM, realistic requests and optional energy measurements.

## Exact contrasts and rounding

| Derived quantity | Unrounded value | Manuscript presentation |
|---|---:|---|
| Windows transform OpenSSL/PyCryptodome | 1.9247174326 | approximately 1.93; exact ratio also stated |
| Windows operation OpenSSL/PyCryptodome | 1.2299336908 | 1.23 |
| OpenSSL operation/transform throughput | 0.2671100504 | 26.7% |
| PyCryptodome operation/transform throughput | 0.4179992582 | 41.8% |
| Arm64 default OpenSSL/PyCryptodome | 19.2596034221 | 19.3 |
| Arm64 default/masked OpenSSL | 18.4881680225 | 18.5 |

The requested approximate 1.93 wording is retained; the precise transform ratio is 1.9247174 (1.925 to three decimals, as plotted). Ordinary direct rounding to two decimals gives 1.92. Section 4.2 states the unrounded ratio to avoid concealing this distinction. All calculations use unrounded source summaries rather than the rounded table values. Retention is a throughput ratio, not a decomposition of individual overhead components.

## Oracle archive audit: verified and included

Both requested archives were found in experiments/results/. The audit reads TAR members directly; it neither extracts executable code nor runs archived scripts. The multicore archive also contains earlier single-worker and smoke sessions. Only five single-study sessions from the single archive and five multicore-study sessions from the multicore archive were selected. Their seeds are 2003?2007.

Checks passed for complete-study metadata, one/two workers, two available logical CPUs, common recorded host/OS/Python, identical archived source hashes, source-file integrity, known-answer/differential validation, 128-bit keys, 32 MiB per worker, default provider and unmasked OpenSSL 3.0.13. Each selected session contains 20 measured repetitions after five warm-ups.

The archived run.py places Python wall timestamps immediately around `actual, metrics = measure(...)`; the ciphertext comparison follows the end timestamp. The two-worker interval is `max(end) - min(start)`. The one-worker interval is `end - start`. The numerator is N ? 33554432 bytes. The session rate is 1000 ? bytes / median(duration_ns); the reported campaign rate is the median of five session rates. The reconstructed multicore summaries exactly match the archived summary.csv rates. Original single-worker summaries report transforms, so the operation rate was reconstructed from raw timestamps.

| Campaign | Seed | Session ID | Median operation duration (ns) | MB/s |
|---|---:|---|---:|---:|
| 1 worker(s) | 2003 | single-study-2003-1c5425a9-c04e-4aa1-b128-2be572105d71 | 31668465.0 | 1059.553471 |
| 1 worker(s) | 2004 | single-study-2004-5b197896-348b-4641-a0df-4bb8599e647b | 31760725.0 | 1056.475631 |
| 1 worker(s) | 2005 | single-study-2005-a4baeb88-145b-4ee8-90a5-f91640219970 | 31549164.5 | 1063.560083 |
| 1 worker(s) | 2006 | single-study-2006-41f6eadf-495c-4bec-a6db-ab540c55c78b | 31679225.0 | 1059.193588 |
| 1 worker(s) | 2007 | single-study-2007-e076b8a5-072a-4ee9-8e45-85680d4868c6 | 31664505.0 | 1059.685980 |
| 2 worker(s) | 2003 | multicore-study-2003-bff4ac10-6aa6-4e48-b983-7b2b1e67aeb7 | 33029244.0 | 2031.801394 |
| 2 worker(s) | 2004 | multicore-study-2004-efc41901-9172-4ff6-b77d-cf08a5b81a98 | 33040345.0 | 2031.118743 |
| 2 worker(s) | 2005 | multicore-study-2005-cc6321a8-8aa7-445b-8366-61022ede48cb | 32851844.0 | 2042.773124 |
| 2 worker(s) | 2006 | multicore-study-2006-42f7f25f-4247-4c52-9481-bdb1cfe84e75 | 33299566.0 | 2015.307467 |
| 2 worker(s) | 2007 | multicore-study-2007-4f6887b6-8da2-40ee-91fe-71f4bb4d41f5 | 33191685.5 | 2021.857673 |

Campaign medians: **1059.553471 MB/s** and **2031.118743 MB/s**. Descriptive aggregate ratio: **1.916957284**. Single-worker payload is 32 MiB; two-worker aggregate payload is 64 MiB. This is not single-operation speedup or a statistically paired causal scaling estimate. No transform rates are summed or substituted for operation rates.

This verification supersedes the previous revision?s decision to omit these values pending provenance inspection. They are now included as one secondary paragraph in Section 4.2, not as another main contribution.

### Archive hashes

- `experiments\results\oracle-phase1-single-study.tar.gz`: `3b5a7fd89fc68d8c36c624855a1d688c67c714e93dd48aa694fefe314a95c8a0`
- `experiments\results\oracle-phase1-multicore-study.tar.gz`: `eee5c0ba0ac2c93a4011f254b4939b2b1c563878237b9fc40c9cbce32baf7038`

The generated build/evidence/audit.json preserves individual durations, member hashes, session identifiers and configuration checks.

## Second Windows computer: assessed and excluded

CPU_ECB_CTR_INVESTIGATION.md reports median session contrasts of 1.25641 on the i5-10300H and 1.2572 on the i7-11850H at 32 MiB, with ECB faster in 5/5 sessions on both. It identifies historical cpu_aesni paths and traces them to experiments/cuda_paired/seed-<seed>/native/raw.csv through the analysis manifest. These are PyCryptodome mode contrasts, not matched native OpenSSL measurements or boundary-retention comparisons.

The SJEE manuscript explicitly retains the GTX 1650 Ti/i5 and T600/i7 historical campaigns, including ECB/CTR configurations (content/03_methodology.tex, content/04_results.tex and content/focused_results_table.tex). Reusing this mode contrast would add a separate question and substantive dataset overlap without strengthening the primary attenuation finding. It is therefore omitted; the i7 is not added to the main comparison. This is a scope/overlap decision, not a claim that historical CPU evidence is absent.

## Reproducibility and literature

Run `python facta_cpu_aes/analyze_evidence.py`, then `python facta_cpu_aes/plot_windows_boundaries.py`. The first uses the Python standard library; the second was run with matplotlib 3.11.2. Both process existing evidence only. The normal build remains `./facta_cpu_aes/build_facta.ps1 -Target All`.

Cloud capability-diagnostic guidance was checked against the official OpenSSL 3.0 documentation, added to references.bib and cited in Section 5.1: https://docs.openssl.org/3.0/man1/openssl-info/ . Capability reporting is explicitly distinguished from instruction execution and from a separate CLI installation.

## Validation

PDF and DOCX builds passed. The PDF has 14 pages including references, retaining the original fonts and geometry. The manuscript has three figures and three tables (six combined), two display equations and ten references. The abstract contains 127 whitespace-delimited words. PDF/DOCX citation numbering and structural validation are checked. PDF pages are visually reviewed; DOCX pagination in Microsoft Word has not been verified and can differ from the PDF.
