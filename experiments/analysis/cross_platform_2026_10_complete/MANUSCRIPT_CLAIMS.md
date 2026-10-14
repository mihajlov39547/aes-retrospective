# Manuscript claims and evidence

This handoff uses the three primary studies only. It does not pool earlier runs or alter the audited analysis. SUPPORTED means supported as an observation under the stated conditions, not population-wide proof. CONDITIONAL marks mixed-direction session contrasts: a median benefit or penalty must retain the qualification that some sessions reversed it. UNSUPPORTED identifies generalizations that the design cannot establish. Numeric E rows record all five session values, extrema, IQR, sample CV, directional counts, exact estimators and original raw-file hashes. Counts above one in non-speedup contrasts have the meaning specified by their numerator and denominator.

## Authoritative studies and traceability

- **gtx1650ti**: Windows 10 (user label); captured Windows release 10, kernel 10.0.19045. Intel(R) Core(TM) i5-10300H CPU @ 2.50GHz; NVIDIA GeForce GTX 1650 Ti. Run `heterogeneous-core-v1-20261014T102836520134Z-1472bd2f13cf` at `C:\Projects\aes\experiments\results_orchestrated\first-gpu-windows\6748c32fac83b2916aa48311\heterogeneous-core-v1-20261014T102836520134Z-1472bd2f13cf`.
- **t600**: Windows 11 (user label); captured Windows release 10, kernel 10.0.22631. 11th Gen Intel(R) Core(TM) i7-11850H @ 2.50GHz; NVIDIA T600 Laptop GPU. Run `heterogeneous-core-v1-20261014T064407642462Z-636c48c0ebaf` at `C:\Projects\aes\experiments\results_orchestrated\second-gpu\aa12d1868e30b6956f14d503\heterogeneous-core-v1-20261014T064407642462Z-636c48c0ebaf`.
- **t4**: Google Colab/Linux (user label); captured Linux release 6.6.122+, kernel #1 SMP Thu Apr 30 18:17:14 UTC 2026. Intel(R) Xeon(R) CPU @ 2.00GHz; Tesla T4. Run `heterogeneous-core-v1-20261014T105540691660Z-9bb918a84386` at `C:/Projects/aes/experiments/results_orchestrated/t4-colab/heterogeneous-core-v1-20261014T105540691660Z-9bb918a84386.tar.gz`.

For T4 the authoritative source is the intact archive, not the adjacent incomplete extraction. Paths in the matrix are relative to the run root (archive members have the run ID prefix). See `archive_extraction_receipts.json` for that recovery distinction. Windows marketing editions are user-supplied labels, not conclusions inferred from NT versions.

All use seeds 2003?2007, five warmups, twenty measured repetitions per group, AES-128 ECB/CTR, five input sizes, and single-launch resident iterations=1. This yields 60 groups and 1200 raw rows per session, 15 sessions and 18000 rows. Persisted correctness/dispatch gates pass; active archived sources match. There are zero detected saved-estimator discrepancies at relative tolerance 1e-10 and absolute tolerance 1e-15 (M01?M02). Warmups are provenance-supported, not exported observations; AES-NI dispatch evidence is native initialization, not an instruction trace. T-table validation is not timed T-table performance evidence.

The session is the replication unit. Throughput is the median of five session medians of individual decimal MB/s rates. Paired speedup is the median of five CPU-median-time/GPU-median-time ratios, always using that platform's own host and matching seed, size and mode. It is not a ratio of aggregate throughput medians. No outliers are removed. CV is sample SD/mean across the five estimates; range is not a confidence interval. MiB denotes binary input size; MB/s denotes decimal rate.

## Practical 4 GB GPU claims

**Strongest all-five-session pipeline advantage over AES-NI among the tested laptop conditions:** the entry-level professional T600 Laptop GPU, Intel i7-11850H host, baseline CUDA, CTR, 32 MiB, prepared pinned-buffer pipeline. Median paired speedup **1.353841?**, range **1.128769?1.391103?**, IQR 0.030896, CV 8.180%; **5/5** sessions above one (E0314). This is a 35.38% speedup margin, equivalently 26.14% lower median paired latency ratio, not a 35.38% latency reduction. It is a selected strongest observed case, not a general deployment guarantee.

The only tested laptop pipeline/AES-NI conditions with 5/5 gains are T600 baseline CTR at 1 and 32 MiB and T600 v1 CTR at 1 MiB. The consumer GTX 1650 Ti has no 5/5 pipeline gain over AES-NI in this grid. Its defensible positive result is strong performance against software AES and resident-only gains against AES-NI at large sizes. The two GPU product categories must remain distinct; 4 GB capacity is descriptive and was not varied or stressed to a limit.

### Complete laptop operating-condition map

Each cell is paired-speedup median [minimum, maximum]; count of sessions >1; matrix ID. Every tested size is listed to avoid hiding small-buffer failures. A mixed count makes a median advantage conditional; 0/5 means no observed gain; 5/5 is descriptive consistency only.

#### gtx1650ti versus cpu_software

| Implementation | Scope | Mode | Input | Median [range]; gains; evidence |
|---|---|---|---|---|
| cuda_baseline | resident | ECB | 1 KiB | 0.166 [0.158, 0.167]; 0/5; E0066 |
| cuda_baseline | resident | ECB | 16 KiB | 1.051 [0.980, 1.122]; 4/5; E0069 |
| cuda_baseline | resident | ECB | 1 MiB | 17.704 [17.062, 18.328]; 5/5; E0072 |
| cuda_baseline | resident | ECB | 16 MiB | 13.508 [11.747, 14.646]; 5/5; E0075 |
| cuda_baseline | resident | ECB | 32 MiB | 17.440 [16.513, 18.447]; 5/5; E0078 |
| cuda_baseline | resident | CTR | 1 KiB | 0.163 [0.160, 0.170]; 0/5; E0051 |
| cuda_baseline | resident | CTR | 16 KiB | 1.149 [1.051, 1.179]; 5/5; E0054 |
| cuda_baseline | resident | CTR | 1 MiB | 18.509 [18.284, 18.852]; 5/5; E0057 |
| cuda_baseline | resident | CTR | 16 MiB | 13.743 [12.412, 14.827]; 5/5; E0060 |
| cuda_baseline | resident | CTR | 32 MiB | 17.598 [17.309, 19.050]; 5/5; E0063 |
| cuda_baseline | pipeline | ECB | 1 KiB | 0.046 [0.035, 0.046]; 0/5; E0036 |
| cuda_baseline | pipeline | ECB | 16 KiB | 0.305 [0.260, 0.308]; 0/5; E0039 |
| cuda_baseline | pipeline | ECB | 1 MiB | 5.210 [4.914, 5.326]; 5/5; E0042 |
| cuda_baseline | pipeline | ECB | 16 MiB | 4.046 [2.345, 4.141]; 5/5; E0045 |
| cuda_baseline | pipeline | ECB | 32 MiB | 4.399 [4.287, 4.546]; 5/5; E0048 |
| cuda_baseline | pipeline | CTR | 1 KiB | 0.046 [0.034, 0.048]; 0/5; E0021 |
| cuda_baseline | pipeline | CTR | 16 KiB | 0.319 [0.283, 0.326]; 0/5; E0024 |
| cuda_baseline | pipeline | CTR | 1 MiB | 5.493 [5.018, 5.513]; 5/5; E0027 |
| cuda_baseline | pipeline | CTR | 16 MiB | 4.192 [2.478, 4.356]; 5/5; E0030 |
| cuda_baseline | pipeline | CTR | 32 MiB | 4.566 [4.551, 4.727]; 5/5; E0033 |
| cuda_optimized_v1 | resident | ECB | 1 KiB | 0.169 [0.158, 0.170]; 0/5; E0126 |
| cuda_optimized_v1 | resident | ECB | 16 KiB | 1.057 [1.001, 1.129]; 5/5; E0129 |
| cuda_optimized_v1 | resident | ECB | 1 MiB | 17.767 [17.527, 18.217]; 5/5; E0132 |
| cuda_optimized_v1 | resident | ECB | 16 MiB | 14.006 [12.236, 14.419]; 5/5; E0135 |
| cuda_optimized_v1 | resident | ECB | 32 MiB | 17.789 [16.930, 18.432]; 5/5; E0138 |
| cuda_optimized_v1 | resident | CTR | 1 KiB | 0.166 [0.160, 0.169]; 0/5; E0111 |
| cuda_optimized_v1 | resident | CTR | 16 KiB | 1.180 [1.070, 1.190]; 5/5; E0114 |
| cuda_optimized_v1 | resident | CTR | 1 MiB | 18.529 [17.937, 19.036]; 5/5; E0117 |
| cuda_optimized_v1 | resident | CTR | 16 MiB | 13.973 [12.481, 14.788]; 5/5; E0120 |
| cuda_optimized_v1 | resident | CTR | 32 MiB | 17.624 [16.715, 18.579]; 5/5; E0123 |
| cuda_optimized_v1 | pipeline | ECB | 1 KiB | 0.046 [0.036, 0.047]; 0/5; E0096 |
| cuda_optimized_v1 | pipeline | ECB | 16 KiB | 0.302 [0.271, 0.311]; 0/5; E0099 |
| cuda_optimized_v1 | pipeline | ECB | 1 MiB | 5.146 [4.935, 5.558]; 5/5; E0102 |
| cuda_optimized_v1 | pipeline | ECB | 16 MiB | 4.043 [2.329, 4.231]; 5/5; E0105 |
| cuda_optimized_v1 | pipeline | ECB | 32 MiB | 4.394 [4.280, 4.557]; 5/5; E0108 |
| cuda_optimized_v1 | pipeline | CTR | 1 KiB | 0.047 [0.035, 0.047]; 0/5; E0081 |
| cuda_optimized_v1 | pipeline | CTR | 16 KiB | 0.322 [0.268, 0.327]; 0/5; E0084 |
| cuda_optimized_v1 | pipeline | CTR | 1 MiB | 5.109 [4.949, 5.173]; 5/5; E0087 |
| cuda_optimized_v1 | pipeline | CTR | 16 MiB | 4.199 [2.472, 4.346]; 5/5; E0090 |
| cuda_optimized_v1 | pipeline | CTR | 32 MiB | 4.579 [4.563, 4.793]; 5/5; E0093 |

#### gtx1650ti versus cpu_aesni

| Implementation | Scope | Mode | Input | Median [range]; gains; evidence |
|---|---|---|---|---|
| cuda_baseline | resident | ECB | 1 KiB | 0.103 [0.092, 0.106]; 0/5; E0067 |
| cuda_baseline | resident | ECB | 16 KiB | 0.162 [0.151, 0.168]; 0/5; E0070 |
| cuda_baseline | resident | ECB | 1 MiB | 2.875 [2.783, 2.938]; 5/5; E0073 |
| cuda_baseline | resident | ECB | 16 MiB | 2.245 [1.954, 2.384]; 5/5; E0076 |
| cuda_baseline | resident | ECB | 32 MiB | 3.091 [2.780, 3.252]; 5/5; E0079 |
| cuda_baseline | resident | CTR | 1 KiB | 0.111 [0.099, 0.112]; 0/5; E0052 |
| cuda_baseline | resident | CTR | 16 KiB | 0.222 [0.209, 0.228]; 0/5; E0055 |
| cuda_baseline | resident | CTR | 1 MiB | 3.629 [3.529, 3.742]; 5/5; E0058 |
| cuda_baseline | resident | CTR | 16 MiB | 2.690 [2.448, 3.012]; 5/5; E0061 |
| cuda_baseline | resident | CTR | 32 MiB | 3.693 [3.464, 3.909]; 5/5; E0064 |
| cuda_baseline | pipeline | ECB | 1 KiB | 0.028 [0.023, 0.029]; 0/5; E0037 |
| cuda_baseline | pipeline | ECB | 16 KiB | 0.045 [0.040, 0.047]; 0/5; E0040 |
| cuda_baseline | pipeline | ECB | 1 MiB | 0.850 [0.791, 0.867]; 0/5; E0043 |
| cuda_baseline | pipeline | ECB | 16 MiB | 0.673 [0.390, 0.678]; 0/5; E0046 |
| cuda_baseline | pipeline | ECB | 32 MiB | 0.761 [0.722, 0.818]; 0/5; E0049 |
| cuda_baseline | pipeline | CTR | 1 KiB | 0.031 [0.021, 0.032]; 0/5; E0022 |
| cuda_baseline | pipeline | CTR | 16 KiB | 0.061 [0.056, 0.063]; 0/5; E0025 |
| cuda_baseline | pipeline | CTR | 1 MiB | 1.080 [0.964, 1.092]; 4/5; E0028 |
| cuda_baseline | pipeline | CTR | 16 MiB | 0.820 [0.489, 0.909]; 0/5; E0031 |
| cuda_baseline | pipeline | CTR | 32 MiB | 0.935 [0.918, 1.008]; 1/5; E0034 |
| cuda_optimized_v1 | resident | ECB | 1 KiB | 0.105 [0.093, 0.109]; 0/5; E0127 |
| cuda_optimized_v1 | resident | ECB | 16 KiB | 0.163 [0.154, 0.169]; 0/5; E0130 |
| cuda_optimized_v1 | resident | ECB | 1 MiB | 2.905 [2.822, 2.946]; 5/5; E0133 |
| cuda_optimized_v1 | resident | ECB | 16 MiB | 2.314 [2.035, 2.374]; 5/5; E0136 |
| cuda_optimized_v1 | resident | ECB | 32 MiB | 3.082 [2.850, 3.239]; 5/5; E0139 |
| cuda_optimized_v1 | resident | CTR | 1 KiB | 0.111 [0.103, 0.115]; 0/5; E0112 |
| cuda_optimized_v1 | resident | CTR | 16 KiB | 0.224 [0.212, 0.234]; 0/5; E0115 |
| cuda_optimized_v1 | resident | CTR | 1 MiB | 3.677 [3.447, 3.778]; 5/5; E0118 |
| cuda_optimized_v1 | resident | CTR | 16 MiB | 2.735 [2.462, 3.080]; 5/5; E0121 |
| cuda_optimized_v1 | resident | CTR | 32 MiB | 3.698 [3.345, 3.913]; 5/5; E0124 |
| cuda_optimized_v1 | pipeline | ECB | 1 KiB | 0.028 [0.023, 0.030]; 0/5; E0097 |
| cuda_optimized_v1 | pipeline | ECB | 16 KiB | 0.046 [0.042, 0.047]; 0/5; E0100 |
| cuda_optimized_v1 | pipeline | ECB | 1 MiB | 0.830 [0.819, 0.888]; 0/5; E0103 |
| cuda_optimized_v1 | pipeline | ECB | 16 MiB | 0.669 [0.387, 0.689]; 0/5; E0106 |
| cuda_optimized_v1 | pipeline | ECB | 32 MiB | 0.765 [0.720, 0.820]; 0/5; E0109 |
| cuda_optimized_v1 | pipeline | CTR | 1 KiB | 0.032 [0.022, 0.032]; 0/5; E0082 |
| cuda_optimized_v1 | pipeline | CTR | 16 KiB | 0.062 [0.053, 0.064]; 0/5; E0085 |
| cuda_optimized_v1 | pipeline | CTR | 1 MiB | 1.011 [0.951, 1.015]; 3/5; E0088 |
| cuda_optimized_v1 | pipeline | CTR | 16 MiB | 0.822 [0.488, 0.907]; 0/5; E0091 |
| cuda_optimized_v1 | pipeline | CTR | 32 MiB | 0.954 [0.914, 1.023]; 1/5; E0094 |

#### t600 versus cpu_software

| Implementation | Scope | Mode | Input | Median [range]; gains; evidence |
|---|---|---|---|---|
| cuda_baseline | resident | ECB | 1 KiB | 0.280 [0.254, 0.378]; 0/5; E0346 |
| cuda_baseline | resident | ECB | 16 KiB | 1.741 [1.518, 2.537]; 5/5; E0349 |
| cuda_baseline | resident | ECB | 1 MiB | 13.498 [13.221, 18.428]; 5/5; E0352 |
| cuda_baseline | resident | ECB | 16 MiB | 11.959 [9.989, 14.143]; 5/5; E0355 |
| cuda_baseline | resident | ECB | 32 MiB | 13.229 [12.331, 13.615]; 5/5; E0358 |
| cuda_baseline | resident | CTR | 1 KiB | 0.260 [0.236, 0.323]; 0/5; E0331 |
| cuda_baseline | resident | CTR | 16 KiB | 1.861 [1.240, 2.674]; 5/5; E0334 |
| cuda_baseline | resident | CTR | 1 MiB | 13.928 [13.245, 22.635]; 5/5; E0337 |
| cuda_baseline | resident | CTR | 16 MiB | 11.864 [10.095, 14.268]; 5/5; E0340 |
| cuda_baseline | resident | CTR | 32 MiB | 13.414 [12.375, 14.336]; 5/5; E0343 |
| cuda_baseline | pipeline | ECB | 1 KiB | 0.105 [0.100, 0.128]; 0/5; E0316 |
| cuda_baseline | pipeline | ECB | 16 KiB | 0.630 [0.589, 0.970]; 0/5; E0319 |
| cuda_baseline | pipeline | ECB | 1 MiB | 6.553 [6.021, 8.432]; 5/5; E0322 |
| cuda_baseline | pipeline | ECB | 16 MiB | 3.519 [2.115, 7.907]; 5/5; E0325 |
| cuda_baseline | pipeline | ECB | 32 MiB | 6.270 [4.215, 7.065]; 5/5; E0328 |
| cuda_baseline | pipeline | CTR | 1 KiB | 0.100 [0.097, 0.117]; 0/5; E0301 |
| cuda_baseline | pipeline | CTR | 16 KiB | 0.622 [0.613, 1.043]; 1/5; E0304 |
| cuda_baseline | pipeline | CTR | 1 MiB | 6.639 [6.366, 10.015]; 5/5; E0307 |
| cuda_baseline | pipeline | CTR | 16 MiB | 3.628 [2.207, 8.185]; 5/5; E0310 |
| cuda_baseline | pipeline | CTR | 32 MiB | 6.319 [5.973, 7.210]; 5/5; E0313 |
| cuda_optimized_v1 | resident | ECB | 1 KiB | 0.287 [0.276, 0.366]; 0/5; E0406 |
| cuda_optimized_v1 | resident | ECB | 16 KiB | 1.673 [1.326, 2.633]; 5/5; E0409 |
| cuda_optimized_v1 | resident | ECB | 1 MiB | 13.470 [13.317, 18.946]; 5/5; E0412 |
| cuda_optimized_v1 | resident | ECB | 16 MiB | 11.785 [10.678, 14.043]; 5/5; E0415 |
| cuda_optimized_v1 | resident | ECB | 32 MiB | 13.059 [12.309, 14.505]; 5/5; E0418 |
| cuda_optimized_v1 | resident | CTR | 1 KiB | 0.276 [0.274, 0.331]; 0/5; E0391 |
| cuda_optimized_v1 | resident | CTR | 16 KiB | 1.861 [1.650, 2.804]; 5/5; E0394 |
| cuda_optimized_v1 | resident | CTR | 1 MiB | 13.608 [12.998, 22.397]; 5/5; E0397 |
| cuda_optimized_v1 | resident | CTR | 16 MiB | 11.952 [9.943, 14.194]; 5/5; E0400 |
| cuda_optimized_v1 | resident | CTR | 32 MiB | 13.446 [12.408, 14.140]; 5/5; E0403 |
| cuda_optimized_v1 | pipeline | ECB | 1 KiB | 0.106 [0.098, 0.134]; 0/5; E0376 |
| cuda_optimized_v1 | pipeline | ECB | 16 KiB | 0.619 [0.590, 0.981]; 0/5; E0379 |
| cuda_optimized_v1 | pipeline | ECB | 1 MiB | 6.437 [6.162, 8.460]; 5/5; E0382 |
| cuda_optimized_v1 | pipeline | ECB | 16 MiB | 3.544 [2.629, 7.985]; 5/5; E0385 |
| cuda_optimized_v1 | pipeline | ECB | 32 MiB | 6.308 [5.784, 7.045]; 5/5; E0388 |
| cuda_optimized_v1 | pipeline | CTR | 1 KiB | 0.103 [0.097, 0.116]; 0/5; E0361 |
| cuda_optimized_v1 | pipeline | CTR | 16 KiB | 0.645 [0.606, 1.098]; 1/5; E0364 |
| cuda_optimized_v1 | pipeline | CTR | 1 MiB | 6.474 [6.258, 10.843]; 5/5; E0367 |
| cuda_optimized_v1 | pipeline | CTR | 16 MiB | 3.620 [2.218, 8.162]; 5/5; E0370 |
| cuda_optimized_v1 | pipeline | CTR | 32 MiB | 6.356 [4.787, 7.031]; 5/5; E0373 |

#### t600 versus cpu_aesni

| Implementation | Scope | Mode | Input | Median [range]; gains; evidence |
|---|---|---|---|---|
| cuda_baseline | resident | ECB | 1 KiB | 0.166 [0.151, 0.212]; 0/5; E0347 |
| cuda_baseline | resident | ECB | 16 KiB | 0.242 [0.202, 0.272]; 0/5; E0350 |
| cuda_baseline | resident | ECB | 1 MiB | 2.161 [1.961, 2.388]; 5/5; E0353 |
| cuda_baseline | resident | ECB | 16 MiB | 2.117 [1.597, 2.188]; 5/5; E0356 |
| cuda_baseline | resident | ECB | 32 MiB | 2.215 [1.951, 2.417]; 5/5; E0359 |
| cuda_baseline | resident | CTR | 1 KiB | 0.167 [0.151, 0.242]; 0/5; E0332 |
| cuda_baseline | resident | CTR | 16 KiB | 0.336 [0.230, 0.469]; 0/5; E0335 |
| cuda_baseline | resident | CTR | 1 MiB | 2.657 [2.536, 3.679]; 5/5; E0338 |
| cuda_baseline | resident | CTR | 16 MiB | 2.327 [1.911, 2.720]; 5/5; E0341 |
| cuda_baseline | resident | CTR | 32 MiB | 2.666 [2.383, 3.072]; 5/5; E0344 |
| cuda_baseline | pipeline | ECB | 1 KiB | 0.062 [0.059, 0.072]; 0/5; E0317 |
| cuda_baseline | pipeline | ECB | 16 KiB | 0.087 [0.078, 0.093]; 0/5; E0320 |
| cuda_baseline | pipeline | ECB | 1 MiB | 1.047 [0.929, 1.093]; 4/5; E0323 |
| cuda_baseline | pipeline | ECB | 16 MiB | 0.623 [0.338, 1.220]; 2/5; E0326 |
| cuda_baseline | pipeline | ECB | 32 MiB | 1.118 [0.659, 1.144]; 3/5; E0329 |
| cuda_baseline | pipeline | CTR | 1 KiB | 0.066 [0.064, 0.088]; 0/5; E0302 |
| cuda_baseline | pipeline | CTR | 16 KiB | 0.118 [0.111, 0.161]; 0/5; E0305 |
| cuda_baseline | pipeline | CTR | 1 MiB | 1.320 [1.217, 1.628]; 5/5; E0308 |
| cuda_baseline | pipeline | CTR | 16 MiB | 0.744 [0.418, 1.560]; 1/5; E0311 |
| cuda_baseline | pipeline | CTR | 32 MiB | 1.354 [1.129, 1.391]; 5/5; E0314 |
| cuda_optimized_v1 | resident | ECB | 1 KiB | 0.170 [0.164, 0.206]; 0/5; E0407 |
| cuda_optimized_v1 | resident | ECB | 16 KiB | 0.233 [0.177, 0.277]; 0/5; E0410 |
| cuda_optimized_v1 | resident | ECB | 1 MiB | 2.144 [1.994, 2.455]; 5/5; E0413 |
| cuda_optimized_v1 | resident | ECB | 16 MiB | 2.021 [1.740, 2.172]; 5/5; E0416 |
| cuda_optimized_v1 | resident | ECB | 32 MiB | 2.158 [1.948, 2.646]; 5/5; E0419 |
| cuda_optimized_v1 | resident | CTR | 1 KiB | 0.184 [0.177, 0.248]; 0/5; E0392 |
| cuda_optimized_v1 | resident | CTR | 16 KiB | 0.336 [0.313, 0.429]; 0/5; E0395 |
| cuda_optimized_v1 | resident | CTR | 1 MiB | 2.716 [2.485, 3.641]; 5/5; E0398 |
| cuda_optimized_v1 | resident | CTR | 16 MiB | 2.345 [1.882, 2.706]; 5/5; E0401 |
| cuda_optimized_v1 | resident | CTR | 32 MiB | 2.541 [2.389, 3.030]; 5/5; E0404 |
| cuda_optimized_v1 | pipeline | ECB | 1 KiB | 0.062 [0.059, 0.075]; 0/5; E0377 |
| cuda_optimized_v1 | pipeline | ECB | 16 KiB | 0.083 [0.079, 0.098]; 0/5; E0380 |
| cuda_optimized_v1 | pipeline | ECB | 1 MiB | 0.994 [0.953, 1.096]; 2/5; E0383 |
| cuda_optimized_v1 | pipeline | ECB | 16 MiB | 0.627 [0.420, 1.235]; 2/5; E0386 |
| cuda_optimized_v1 | pipeline | ECB | 32 MiB | 1.112 [0.905, 1.151]; 4/5; E0389 |
| cuda_optimized_v1 | pipeline | CTR | 1 KiB | 0.066 [0.062, 0.087]; 0/5; E0362 |
| cuda_optimized_v1 | pipeline | CTR | 16 KiB | 0.119 [0.115, 0.158]; 0/5; E0365 |
| cuda_optimized_v1 | pipeline | CTR | 1 MiB | 1.299 [1.197, 1.763]; 5/5; E0368 |
| cuda_optimized_v1 | pipeline | CTR | 16 MiB | 0.745 [0.420, 1.556]; 1/5; E0371 |
| cuda_optimized_v1 | pipeline | CTR | 32 MiB | 1.354 [0.924, 1.371]; 4/5; E0374 |

### Compact practical reading of the full map

On both laptop hosts, both GPU candidates beat AES-NI in resident timing for ECB and CTR at 1, 16 and 32 MiB in 5/5 sessions. At 1 KiB or 16 KiB, neither laptop has an all-five resident win over AES-NI. In pipeline timing, both candidates and modes beat software CPU AES at 1, 16 and 32 MiB in 5/5 sessions on both laptops; no smaller pipeline case has an all-five software-CPU win. Against AES-NI, only the three T600 CTR conditions named above have all-five pipeline gains. The detailed map retains every median loss and mixed-direction case rather than treating ?not all-five? as ?always slower.?

At 32 MiB the GTX consumer GPU baseline CTR pipeline beats software CPU AES by 4.5658? (range 4.5514?4.7269?, 5/5), yet its AES-NI comparison is only 0.9351? (range 0.9178?1.0085?). This is a useful accessible-GPU result with an explicit CPU-baseline qualification. The T600 positive AES-NI example is stronger evidence for offloading under the prepared-buffer boundary, but does not transfer automatically to the consumer GPU.

## Datacenter contrast: matched workloads, independent hosts

The following full grid separates absolute GPU throughput from speedups relative to different CPUs. Rates are decimal MB/s; resident and pipeline are separate measurements. Every rate cell identifies a matrix row containing five-session variability; speedup cells additionally display the range and directional count. These are configurations of three systems, not a controlled consumer/professional/datacenter or Windows/Linux causal comparison.

| Platform | Implementation | Mode | MiB | Resident MB/s (evidence) | Pipeline MB/s (evidence) | Resident/AES-NI time speedup [range]; gains; evidence | Pipeline/AES-NI time speedup [range]; gains; evidence |
|---|---|---|---|---|---|---|---|
| gtx1650ti | cuda_baseline | ECB | 1 | 4928.851 (E0074) | 1441.595 (E0044) | 2.875 [2.783, 2.938]; 5/5; E0073 | 0.850 [0.791, 0.867]; 0/5; E0043 |
| gtx1650ti | cuda_baseline | ECB | 16 | 3745.706 (E0077) | 1116.151 (E0047) | 2.245 [1.954, 2.384]; 5/5; E0076 | 0.673 [0.390, 0.678]; 0/5; E0046 |
| gtx1650ti | cuda_baseline | ECB | 32 | 4797.553 (E0080) | 1207.776 (E0050) | 3.091 [2.780, 3.252]; 5/5; E0079 | 0.761 [0.722, 0.818]; 0/5; E0049 |
| gtx1650ti | cuda_baseline | CTR | 1 | 4847.696 (E0059) | 1437.885 (E0029) | 3.629 [3.529, 3.742]; 5/5; E0058 | 1.080 [0.964, 1.092]; 4/5; E0028 |
| gtx1650ti | cuda_baseline | CTR | 16 | 3582.058 (E0062) | 1092.670 (E0032) | 2.690 [2.448, 3.012]; 5/5; E0061 | 0.820 [0.489, 0.909]; 0/5; E0031 |
| gtx1650ti | cuda_baseline | CTR | 32 | 4585.632 (E0065) | 1188.868 (E0035) | 3.693 [3.464, 3.909]; 5/5; E0064 | 0.935 [0.918, 1.008]; 1/5; E0034 |
| gtx1650ti | cuda_optimized_v1 | ECB | 1 | 4976.933 (E0134) | 1438.281 (E0104) | 2.905 [2.822, 2.946]; 5/5; E0133 | 0.830 [0.819, 0.888]; 0/5; E0103 |
| gtx1650ti | cuda_optimized_v1 | ECB | 16 | 3780.917 (E0137) | 1113.437 (E0107) | 2.314 [2.035, 2.374]; 5/5; E0136 | 0.669 [0.387, 0.689]; 0/5; E0106 |
| gtx1650ti | cuda_optimized_v1 | ECB | 32 | 4778.471 (E0140) | 1209.197 (E0110) | 3.082 [2.850, 3.239]; 5/5; E0139 | 0.765 [0.720, 0.820]; 0/5; E0109 |
| gtx1650ti | cuda_optimized_v1 | CTR | 1 | 4865.010 (E0119) | 1337.752 (E0089) | 3.677 [3.447, 3.778]; 5/5; E0118 | 1.011 [0.951, 1.015]; 3/5; E0088 |
| gtx1650ti | cuda_optimized_v1 | CTR | 16 | 3641.964 (E0122) | 1094.470 (E0092) | 2.735 [2.462, 3.080]; 5/5; E0121 | 0.822 [0.488, 0.907]; 0/5; E0091 |
| gtx1650ti | cuda_optimized_v1 | CTR | 32 | 4594.419 (E0125) | 1195.639 (E0095) | 3.698 [3.345, 3.913]; 5/5; E0124 | 0.954 [0.914, 1.023]; 1/5; E0094 |
| t600 | cuda_baseline | ECB | 1 | 4364.486 (E0354) | 2067.046 (E0324) | 2.161 [1.961, 2.388]; 5/5; E0353 | 1.047 [0.929, 1.093]; 4/5; E0323 |
| t600 | cuda_baseline | ECB | 16 | 3737.591 (E0357) | 1099.733 (E0327) | 2.117 [1.597, 2.188]; 5/5; E0356 | 0.623 [0.338, 1.220]; 2/5; E0326 |
| t600 | cuda_baseline | ECB | 32 | 4451.074 (E0360) | 1997.819 (E0330) | 2.215 [1.951, 2.417]; 5/5; E0359 | 1.118 [0.659, 1.144]; 3/5; E0329 |
| t600 | cuda_baseline | CTR | 1 | 4305.352 (E0339) | 2071.302 (E0309) | 2.657 [2.536, 3.679]; 5/5; E0338 | 1.320 [1.217, 1.628]; 5/5; E0308 |
| t600 | cuda_baseline | CTR | 16 | 3590.724 (E0342) | 1097.683 (E0312) | 2.327 [1.911, 2.720]; 5/5; E0341 | 0.744 [0.418, 1.560]; 1/5; E0311 |
| t600 | cuda_baseline | CTR | 32 | 4328.940 (E0345) | 2049.409 (E0315) | 2.666 [2.383, 3.072]; 5/5; E0344 | 1.354 [1.129, 1.391]; 5/5; E0314 |
| t600 | cuda_optimized_v1 | ECB | 1 | 4420.540 (E0414) | 2064.971 (E0384) | 2.144 [1.994, 2.455]; 5/5; E0413 | 0.994 [0.953, 1.096]; 2/5; E0383 |
| t600 | cuda_optimized_v1 | ECB | 16 | 3682.846 (E0417) | 1107.539 (E0387) | 2.021 [1.740, 2.172]; 5/5; E0416 | 0.627 [0.420, 1.235]; 2/5; E0386 |
| t600 | cuda_optimized_v1 | ECB | 32 | 4427.220 (E0420) | 2039.173 (E0390) | 2.158 [1.948, 2.646]; 5/5; E0419 | 1.112 [0.905, 1.151]; 4/5; E0389 |
| t600 | cuda_optimized_v1 | CTR | 1 | 4228.690 (E0399) | 2036.219 (E0369) | 2.716 [2.485, 3.641]; 5/5; E0398 | 1.299 [1.197, 1.763]; 5/5; E0368 |
| t600 | cuda_optimized_v1 | CTR | 16 | 3616.652 (E0402) | 1095.398 (E0372) | 2.345 [1.882, 2.706]; 5/5; E0401 | 0.745 [0.420, 1.556]; 1/5; E0371 |
| t600 | cuda_optimized_v1 | CTR | 32 | 4171.661 (E0405) | 2029.702 (E0375) | 2.541 [2.389, 3.030]; 5/5; E0404 | 1.354 [0.924, 1.371]; 4/5; E0374 |
| t4 | cuda_baseline | ECB | 1 | 9961.395 (E0214) | 3118.836 (E0184) | 2.171 [1.598, 2.274]; 5/5; E0213 | 0.668 [0.596, 0.705]; 0/5; E0183 |
| t4 | cuda_baseline | ECB | 16 | 9002.353 (E0217) | 3626.664 (E0187) | 2.048 [2.012, 2.072]; 5/5; E0216 | 0.825 [0.811, 0.833]; 0/5; E0186 |
| t4 | cuda_baseline | ECB | 32 | 9176.905 (E0220) | 3712.965 (E0190) | 2.207 [2.153, 2.227]; 5/5; E0219 | 0.893 [0.868, 0.901]; 0/5; E0189 |
| t4 | cuda_baseline | CTR | 1 | 9990.267 (E0199) | 3102.515 (E0169) | 12.250 [8.821, 12.647]; 5/5; E0198 | 3.734 [3.409, 3.847]; 5/5; E0168 |
| t4 | cuda_baseline | CTR | 16 | 8991.468 (E0202) | 3619.284 (E0172) | 11.109 [11.046, 11.192]; 5/5; E0201 | 4.478 [4.454, 4.501]; 5/5; E0171 |
| t4 | cuda_baseline | CTR | 32 | 9166.796 (E0205) | 3713.938 (E0175) | 11.758 [11.570, 12.426]; 5/5; E0204 | 4.761 [4.691, 5.021]; 5/5; E0174 |
| t4 | cuda_optimized_v1 | ECB | 1 | 9718.663 (E0274) | 3058.469 (E0244) | 2.105 [1.596, 2.276]; 5/5; E0273 | 0.663 [0.598, 0.699]; 0/5; E0243 |
| t4 | cuda_optimized_v1 | ECB | 16 | 8997.024 (E0277) | 3619.418 (E0247) | 2.048 [2.010, 2.067]; 5/5; E0276 | 0.821 [0.810, 0.831]; 0/5; E0246 |
| t4 | cuda_optimized_v1 | ECB | 32 | 9162.831 (E0280) | 3705.928 (E0250) | 2.202 [2.148, 2.222]; 5/5; E0279 | 0.891 [0.867, 0.898]; 0/5; E0249 |
| t4 | cuda_optimized_v1 | CTR | 1 | 9947.829 (E0259) | 3072.385 (E0229) | 12.198 [8.949, 12.732]; 5/5; E0258 | 3.734 [3.360, 3.815]; 5/5; E0228 |
| t4 | cuda_optimized_v1 | CTR | 16 | 9018.535 (E0262) | 3625.625 (E0232) | 11.142 [11.089, 11.254]; 5/5; E0261 | 4.481 [4.458, 4.512]; 5/5; E0231 |
| t4 | cuda_optimized_v1 | CTR | 32 | 9217.683 (E0265) | 3715.627 (E0235) | 11.838 [11.630, 12.508]; 5/5; E0264 | 4.756 [4.699, 5.042]; 5/5; E0234 |

For a direct GPU-rate example, baseline CTR at 32 MiB has resident/pipeline medians of 4585.632/1188.868 MB/s on GTX (E0065/E0035), 4328.940/2049.409 MB/s on T600 (E0345/E0315), and 9166.796/3713.938 MB/s on T4 (E0205/E0175). These absolute rates support a T4 throughput advantage in this matched condition without using any CPU denominator. The full table supplies the other modes, sizes and candidate rather than extending this example to every workload.

At 32 MiB all four implementation/mode combinations on each GPU beat the paired AES-NI baseline in resident-only timing in 5/5 sessions. Pipeline inclusion changes the interpretation: GTX medians are below one for all four; only T600 baseline CTR retains a 5/5 gain; T4 retains a 5/5 CTR gain but loses in ECB in 5/5 sessions. T4's approximately 4.76? CTR pipeline speedup cannot be interpreted as a 4.76? absolute throughput advantage over laptop GPUs: its CPU reference is different.

## Cipher-mode effects and implementation variants

The next table reports same-session median-throughput ECB/CTR ratios at 32 MiB. A value above one means ECB throughput is greater. These mode differences are descriptive, not significance tests. In particular, large CTR speedup relative to a host CPU can result from slower CPU CTR, even when the GPU itself has similar ECB/CTR throughput.

| Platform | Backend | Scope | ECB/CTR median [range]; sessions ECB greater; evidence |
|---|---|---|---|
| gtx1650ti | cpu_aesni | transform | 1.256 [1.239, 1.290]; 5/5; E0439 |
| gtx1650ti | cpu_software | transform | 1.059 [1.051, 1.069]; 5/5; E0448 |
| t4 | cpu_aesni | transform | 5.378 [5.250, 5.795]; 5/5; E0523 |
| t4 | cpu_software | transform | 1.235 [1.183, 1.247]; 5/5; E0532 |
| t600 | cpu_aesni | transform | 1.257 [1.221, 1.303]; 5/5; E0607 |
| t600 | cpu_software | transform | 1.043 [1.033, 1.050]; 5/5; E0616 |

| gtx1650ti | cuda_baseline | resident | 1.037 [0.968, 1.135]; 4/5; G005 |
| gtx1650ti | cuda_baseline | pipeline | 1.019 [1.004, 1.032]; 5/5; G010 |
| gtx1650ti | cuda_optimized_v1 | resident | 1.028 [1.011, 1.174]; 5/5; G015 |
| gtx1650ti | cuda_optimized_v1 | pipeline | 1.004 [0.999, 1.024]; 4/5; G020 |
| t600 | cuda_baseline | resident | 1.028 [0.968, 1.030]; 4/5; G025 |
| t600 | cuda_baseline | pipeline | 1.016 [0.757, 1.038]; 3/5; G030 |
| t600 | cuda_optimized_v1 | resident | 1.025 [0.929, 1.112]; 4/5; G035 |
| t600 | cuda_optimized_v1 | pipeline | 1.026 [0.982, 1.364]; 3/5; G040 |
| t4 | cuda_baseline | resident | 1.001 [0.999, 1.004]; 4/5; G045 |
| t4 | cuda_baseline | pipeline | 1.000 [1.000, 1.002]; 3/5; G050 |
| t4 | cuda_optimized_v1 | resident | 0.993 [0.991, 0.995]; 0/5; G055 |
| t4 | cuda_optimized_v1 | pipeline | 0.997 [0.996, 1.001]; 1/5; G060 |

Across the twelve GPU implementation/scope/platform combinations at 32 MiB, median ECB/CTR throughput ratios are between approximately 0.993 and 1.037. Thus the much larger host CPU mode disparity, especially on T4, should not be described as an equally large GPU mode disparity. Some GPU mode contrasts reverse across sessions, and T600 pipeline ranges are wide; the data do not establish statistical or deployment-level importance for these small median differences. GTX baseline pipeline ECB is 1.0188 times CTR throughput (5/5 above one), while its AES-NI offloading outcome is less favorable for ECB because the CPU baseline also changes.

The T4 host's AES-NI ECB/CTR ratio is about 5.63? at 1 MiB and 5.38? at 32 MiB, with ECB faster in 5/5 sessions. The Windows hosts are approximately 1.26? at 32 MiB. Native AES-NI dispatch is recorded on all hosts; the T4 host exposes two logical processors and an Intel Xeon CPU @ 2.00 GHz, without an exact SKU. Counter processing, native mode implementation, virtualization and frequency behavior remain hypotheses. PyCryptodome version differences alone do not establish causality. Exact mode contrasts at every size and their IQR/CV are in matrix rows with `ecb_to_ctr_throughput_ratio`.

V1 is a candidate, not a uniformly successful optimization. Consult `v1_vs_baseline_time_speedup` rows before claiming a gain: at T4 32 MiB resident CTR its approximately 0.6% gain is directionally consistent, while resident ECB is slightly slower. Pipeline differences may reverse between sessions. Small effects should not be presented as strong evidence of general superiority.

## Variability, the 16 MiB feature, and scope qualifications

GTX has a joint 16 MiB local throughput dip below both 1 and 32 MiB in 5/5 sessions in all eight GPU implementation/mode/scope groups. T600 joint counts are 3?5/5, and only one group is 5/5. T4 resident counts are 4/5; T4 pipeline counts are 0/5. This is a repeatable feature of particular observed configurations, not a universal 16 MiB threshold. `anomaly_local_dips.csv` supplies joint counts; the matrix's `throughput_16MiB_over_*` rows supply each contrast and its variability. Do not confuse separate marginal counts with the joint local-dip criterion.

Resident excludes transfers and uses CUDA event timing. Pipeline includes synchronous H2D, launch/kernel/synchronization and completed D2H using host wall time, but starts with prepared pinned buffers. CPU timing covers the encrypt transform including output allocation, excluding cipher construction. GPU allocation/pinning/staging, compilation and key setup are outside the measured scopes. Recorded H2D/D2H intervals include synchronization and are not pure PCIe wire time. Independent pipeline-minus-resident timing is only an approximate residual overhead; component medians need not add to the median total. These boundaries are central findings, not hidden caveats.

## Claims to reject

- **U01 ? UNSUPPORTED:** All 4 GB NVIDIA GPUs outperform CPU AES-NI. Counterexamples in GTX pipeline and T600 mixed-session groups; capacity is descriptive, not an explanatory variable.
- **U02 ? UNSUPPORTED:** T4 universally wins over its CPU or all laptop GPUs. T4 ECB pipeline loses to its host AES-NI at 32 MiB; compare exact workload and scope.
- **U03 ? UNSUPPORTED:** Windows 11 causes the difference from Windows 10. Different CPUs, GPUs, drivers and libraries; no controlled OS intervention.
- **U04 ? UNSUPPORTED:** Optimized v1 is uniformly faster than baseline. Matched v1/baseline ratios vary by platform, mode, size and scope.
- **U05 ? UNSUPPORTED:** The pipeline measures full application encryption performance. Allocation, pinning, staging, compilation and key preparation are excluded; no application I/O or authentication.
- **U06 ? UNSUPPORTED:** 4 GB capacity, consumer/professional class, or library version causes the observed performance. No capacity, hardware-class or version-controlled experiment.
- **U07 ? UNSUPPORTED:** Five sessions establish statistical significance or population-wide reliability. One host per platform, five sessions; twenty repetitions are nested observations.
- **U08 ? UNSUPPORTED:** A pipeline-minus-resident subtraction measures PCIe transfer time. Different scopes and independent timing variation; only recorded copy intervals support component descriptions.
- **U09 ? UNSUPPORTED:** ECB throughput supports recommending ECB for application security. ECB is a primitive-performance probe; security suitability is outside this throughput comparison.

## Handoff verification

For this handoff, all selected source-artifact hashes were checked against the established reproducibility manifest, original raw CSVs were read directly (T4 from its archive), and all session-derived aggregate medians, extrema, IQRs and CVs were checked against the existing independent analysis. No benchmarks were executed. The four handoff files supplement the existing analysis; they do not change its manifest or historical outputs. Full precision is retained in the CSV; prose and tables round for readability. Exact point selection is platform + backend + mode + bytes + timing scope + metric + run ID, with five raw-file hashes in each numeric row.

Final handoff checks: 743 matrix records (592 SUPPORTED, 142 CONDITIONAL, 9 UNSUPPORTED); numeric session counts, medians, extrema, IQRs, CVs and directional counts validated; all referenced claim IDs and selected existing figure paths resolved. All 405 selected original artifact hashes matched the established manifest. The 23 analysis unit tests passed. All 1873 pre-existing files in the checked historical-results, orchestrated-results, scripts and completed-analysis trees remained byte-identical. Only the four requested handoff files were added; no benchmark, commit or push was performed.
