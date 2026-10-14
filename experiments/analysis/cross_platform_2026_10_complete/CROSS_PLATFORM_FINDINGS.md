# Cross-platform findings

Validated primary platforms: gtx1650ti, t4, t600. Comparisons retain platform, mode and scope. All three primary studies pass the source, raw-data and saved-estimator checks.

gtx1650ti, 32 MiB resident: median GPU speedups relative to AES-NI (CPU time / GPU time) range 3.082–3.698 across baseline/v1 and ECB/CTR. 4/4 combinations beat AES-NI in all five sessions.

gtx1650ti, 32 MiB pipeline: median GPU speedups relative to AES-NI (CPU time / GPU time) range 0.761–0.954 across baseline/v1 and ECB/CTR. 0/4 combinations beat AES-NI in all five sessions.

t4, 32 MiB resident: median GPU speedups relative to AES-NI (CPU time / GPU time) range 2.202–11.838 across baseline/v1 and ECB/CTR. 4/4 combinations beat AES-NI in all five sessions.

t4, 32 MiB pipeline: median GPU speedups relative to AES-NI (CPU time / GPU time) range 0.891–4.761 across baseline/v1 and ECB/CTR. 2/4 combinations beat AES-NI in all five sessions.

t600, 32 MiB resident: median GPU speedups relative to AES-NI (CPU time / GPU time) range 2.158–2.666 across baseline/v1 and ECB/CTR. 4/4 combinations beat AES-NI in all five sessions.

t600, 32 MiB pipeline: median GPU speedups relative to AES-NI (CPU time / GPU time) range 1.112–1.354 across baseline/v1 and ECB/CTR. 1/4 combinations beat AES-NI in all five sessions.

## GPU timing speedups at 32 MiB

| platform | backend | mode | scope | metric | median | min | max | all_five_above_one |
|---|---|---|---|---|---|---|---|---|
| gtx1650ti | cuda_baseline | CTR | pipeline | speedup_pipeline_vs_cpu_aesni | 0.935136 | 0.917762 | 1.00849 | False |
| gtx1650ti | cuda_baseline | CTR | pipeline | speedup_pipeline_vs_cpu_software | 4.5658 | 4.55141 | 4.72688 | True |
| gtx1650ti | cuda_baseline | ECB | pipeline | speedup_pipeline_vs_cpu_aesni | 0.760917 | 0.721734 | 0.817549 | False |
| gtx1650ti | cuda_baseline | ECB | pipeline | speedup_pipeline_vs_cpu_software | 4.39867 | 4.28712 | 4.54563 | True |
| gtx1650ti | cuda_baseline | CTR | resident | speedup_isolated_vs_cpu_aesni | 3.69253 | 3.46361 | 3.90919 | True |
| gtx1650ti | cuda_baseline | CTR | resident | speedup_isolated_vs_cpu_software | 17.5982 | 17.3091 | 19.0495 | True |
| gtx1650ti | cuda_baseline | ECB | resident | speedup_isolated_vs_cpu_aesni | 3.09069 | 2.77988 | 3.25181 | True |
| gtx1650ti | cuda_baseline | ECB | resident | speedup_isolated_vs_cpu_software | 17.4404 | 16.5126 | 18.4467 | True |
| gtx1650ti | cuda_optimized_v1 | CTR | pipeline | speedup_pipeline_vs_cpu_aesni | 0.954472 | 0.914293 | 1.02263 | False |
| gtx1650ti | cuda_optimized_v1 | CTR | pipeline | speedup_pipeline_vs_cpu_software | 4.57904 | 4.56255 | 4.79318 | True |
| gtx1650ti | cuda_optimized_v1 | ECB | pipeline | speedup_pipeline_vs_cpu_aesni | 0.765211 | 0.720483 | 0.819602 | False |
| gtx1650ti | cuda_optimized_v1 | ECB | pipeline | speedup_pipeline_vs_cpu_software | 4.39403 | 4.27969 | 4.55704 | True |
| gtx1650ti | cuda_optimized_v1 | CTR | resident | speedup_isolated_vs_cpu_aesni | 3.69793 | 3.34463 | 3.91307 | True |
| gtx1650ti | cuda_optimized_v1 | CTR | resident | speedup_isolated_vs_cpu_software | 17.624 | 16.7145 | 18.5793 | True |
| gtx1650ti | cuda_optimized_v1 | ECB | resident | speedup_isolated_vs_cpu_aesni | 3.08164 | 2.85016 | 3.23885 | True |
| gtx1650ti | cuda_optimized_v1 | ECB | resident | speedup_isolated_vs_cpu_software | 17.7888 | 16.93 | 18.4324 | True |
| t4 | cuda_baseline | CTR | pipeline | speedup_pipeline_vs_cpu_aesni | 4.76134 | 4.69135 | 5.02056 | True |
| t4 | cuda_baseline | CTR | pipeline | speedup_pipeline_vs_cpu_software | 16.9016 | 16.8492 | 17.9072 | True |
| t4 | cuda_baseline | ECB | pipeline | speedup_pipeline_vs_cpu_aesni | 0.893452 | 0.867869 | 0.901474 | False |
| t4 | cuda_baseline | ECB | pipeline | speedup_pipeline_vs_cpu_software | 13.6939 | 13.5135 | 14.4484 | True |
| t4 | cuda_baseline | CTR | resident | speedup_isolated_vs_cpu_aesni | 11.758 | 11.5696 | 12.4262 | True |
| t4 | cuda_baseline | CTR | resident | speedup_isolated_vs_cpu_software | 41.8004 | 41.5779 | 44.3214 | True |
| t4 | cuda_baseline | ECB | resident | speedup_isolated_vs_cpu_aesni | 2.20749 | 2.15263 | 2.22745 | True |
| t4 | cuda_baseline | ECB | resident | speedup_isolated_vs_cpu_software | 33.8345 | 33.3906 | 35.6984 | True |
| t4 | cuda_optimized_v1 | CTR | pipeline | speedup_pipeline_vs_cpu_aesni | 4.75555 | 4.69863 | 5.04189 | True |
| t4 | cuda_optimized_v1 | CTR | pipeline | speedup_pipeline_vs_cpu_software | 16.948 | 16.8273 | 17.9832 | True |
| t4 | cuda_optimized_v1 | ECB | pipeline | speedup_pipeline_vs_cpu_aesni | 0.891456 | 0.866984 | 0.89831 | False |
| t4 | cuda_optimized_v1 | ECB | pipeline | speedup_pipeline_vs_cpu_software | 13.6833 | 13.4661 | 14.4161 | True |
| t4 | cuda_optimized_v1 | CTR | resident | speedup_isolated_vs_cpu_aesni | 11.8375 | 11.6302 | 12.5076 | True |
| t4 | cuda_optimized_v1 | CTR | resident | speedup_isolated_vs_cpu_software | 42.0505 | 41.8087 | 44.6116 | True |
| t4 | cuda_optimized_v1 | ECB | resident | speedup_isolated_vs_cpu_aesni | 2.20161 | 2.14753 | 2.22201 | True |
| t4 | cuda_optimized_v1 | ECB | resident | speedup_isolated_vs_cpu_software | 33.8128 | 33.309 | 35.6496 | True |
| t600 | cuda_baseline | CTR | pipeline | speedup_pipeline_vs_cpu_aesni | 1.35384 | 1.12877 | 1.3911 | True |
| t600 | cuda_baseline | CTR | pipeline | speedup_pipeline_vs_cpu_software | 6.31867 | 5.97304 | 7.21015 | True |
| t600 | cuda_baseline | ECB | pipeline | speedup_pipeline_vs_cpu_aesni | 1.11801 | 0.659378 | 1.14376 | False |
| t600 | cuda_baseline | ECB | pipeline | speedup_pipeline_vs_cpu_software | 6.27038 | 4.21496 | 7.06471 | True |
| t600 | cuda_baseline | CTR | resident | speedup_isolated_vs_cpu_aesni | 2.66566 | 2.38259 | 3.07164 | True |
| t600 | cuda_baseline | CTR | resident | speedup_isolated_vs_cpu_software | 13.4142 | 12.3748 | 14.336 | True |
| t600 | cuda_baseline | ECB | resident | speedup_isolated_vs_cpu_aesni | 2.2151 | 1.95137 | 2.41658 | True |
| t600 | cuda_baseline | ECB | resident | speedup_isolated_vs_cpu_software | 13.2293 | 12.3307 | 13.615 | True |
| t600 | cuda_optimized_v1 | CTR | pipeline | speedup_pipeline_vs_cpu_aesni | 1.35367 | 0.923547 | 1.37121 | False |
| t600 | cuda_optimized_v1 | CTR | pipeline | speedup_pipeline_vs_cpu_software | 6.35611 | 4.78678 | 7.03072 | True |
| t600 | cuda_optimized_v1 | ECB | pipeline | speedup_pipeline_vs_cpu_aesni | 1.1124 | 0.90491 | 1.15061 | False |
| t600 | cuda_optimized_v1 | ECB | pipeline | speedup_pipeline_vs_cpu_software | 6.30792 | 5.78449 | 7.04506 | True |
| t600 | cuda_optimized_v1 | CTR | resident | speedup_isolated_vs_cpu_aesni | 2.54098 | 2.38904 | 3.02958 | True |
| t600 | cuda_optimized_v1 | CTR | resident | speedup_isolated_vs_cpu_software | 13.446 | 12.4083 | 14.1397 | True |
| t600 | cuda_optimized_v1 | ECB | resident | speedup_isolated_vs_cpu_aesni | 2.1584 | 1.94793 | 2.64581 | True |
| t600 | cuda_optimized_v1 | ECB | resident | speedup_isolated_vs_cpu_software | 13.0593 | 12.3089 | 14.505 | True |

A speedup >1 means GPU faster than the named CPU reference in all five sessions only when the minimum also exceeds one. Small-input behavior is separately shown in figures/CSVs; these rows do not claim a universal crossover.

## Optimized v1 versus baseline (same scope)

| platform | scope | mode | bytes | median | min | max | sessions_v1_faster |
|---|---|---|---|---|---|---|---|
| gtx1650ti | pipeline | CTR | 1024 | 1.0098 | 0.976038 | 1.04266 | 4 |
| gtx1650ti | pipeline | CTR | 16384 | 1.00816 | 0.94722 | 1.01018 | 4 |
| gtx1650ti | pipeline | CTR | 1048576 | 0.938364 | 0.900915 | 1.01415 | 1 |
| gtx1650ti | pipeline | CTR | 16777216 | 0.997687 | 0.868582 | 1.00176 | 1 |
| gtx1650ti | pipeline | CTR | 33554432 | 1.0029 | 0.99622 | 1.02068 | 4 |
| gtx1650ti | pipeline | ECB | 1024 | 1.01082 | 1.00027 | 1.01853 | 5 |
| gtx1650ti | pipeline | ECB | 16384 | 1.01553 | 0.987743 | 1.04095 | 4 |
| gtx1650ti | pipeline | ECB | 1048576 | 1.0276 | 0.957336 | 1.06089 | 3 |
| gtx1650ti | pipeline | ECB | 16777216 | 0.992942 | 0.986875 | 1.02175 | 2 |
| gtx1650ti | pipeline | ECB | 33554432 | 0.998266 | 0.987534 | 1.00564 | 2 |
| gtx1650ti | resident | CTR | 1024 | 1.0024 | 0.992647 | 1.03832 | 3 |
| gtx1650ti | resident | CTR | 16384 | 1.01941 | 1.00993 | 1.02745 | 5 |
| gtx1650ti | resident | CTR | 1048576 | 1.00111 | 0.976583 | 1.01329 | 3 |
| gtx1650ti | resident | CTR | 16777216 | 1.00561 | 0.98624 | 1.02255 | 3 |
| gtx1650ti | resident | CTR | 33554432 | 1.00146 | 0.965649 | 1.00573 | 3 |
| gtx1650ti | resident | ECB | 1024 | 1.02028 | 1.00123 | 1.02463 | 5 |
| gtx1650ti | resident | ECB | 16384 | 1.00655 | 0.983547 | 1.02158 | 4 |
| gtx1650ti | resident | ECB | 1048576 | 1.00279 | 0.981538 | 1.04131 | 3 |
| gtx1650ti | resident | ECB | 16777216 | 0.998182 | 0.978695 | 1.08308 | 2 |
| gtx1650ti | resident | ECB | 33554432 | 0.999222 | 0.976196 | 1.02528 | 2 |
| t4 | pipeline | CTR | 1024 | 1.01124 | 0.976031 | 1.04926 | 3 |
| t4 | pipeline | CTR | 16384 | 1.01653 | 0.945406 | 1.04781 | 4 |
| t4 | pipeline | CTR | 1048576 | 0.990294 | 0.985892 | 1.00237 | 1 |
| t4 | pipeline | CTR | 16777216 | 1.00237 | 0.998439 | 1.00652 | 4 |
| t4 | pipeline | CTR | 33554432 | 1.00155 | 0.998698 | 1.00425 | 3 |
| t4 | pipeline | ECB | 1024 | 1.00908 | 0.982807 | 1.08899 | 3 |
| t4 | pipeline | ECB | 16384 | 0.992337 | 0.894335 | 1.04855 | 2 |
| t4 | pipeline | ECB | 1048576 | 0.993117 | 0.974012 | 1.03264 | 2 |
| t4 | pipeline | ECB | 16777216 | 0.998002 | 0.995562 | 0.999013 | 0 |
| t4 | pipeline | ECB | 33554432 | 0.99898 | 0.996491 | 0.999588 | 0 |
| t4 | resident | CTR | 1024 | 1.07169 | 1.03805 | 1.07852 | 5 |
| t4 | resident | CTR | 16384 | 1.06194 | 1.01468 | 1.07478 | 5 |
| t4 | resident | CTR | 1048576 | 1.00678 | 0.99575 | 1.01451 | 4 |
| t4 | resident | CTR | 16777216 | 1.00384 | 1.00214 | 1.00561 | 5 |
| t4 | resident | CTR | 33554432 | 1.00598 | 1.00524 | 1.00676 | 5 |
| t4 | resident | ECB | 1024 | 1.03165 | 1.01912 | 1.08052 | 5 |
| t4 | resident | ECB | 16384 | 1.04366 | 1.01022 | 1.09196 | 5 |
| t4 | resident | ECB | 1048576 | 0.987844 | 0.913553 | 1.01013 | 1 |
| t4 | resident | ECB | 16777216 | 0.999091 | 0.997365 | 1.00047 | 1 |
| t4 | resident | ECB | 33554432 | 0.99763 | 0.996735 | 0.999882 | 0 |
| t600 | pipeline | CTR | 1024 | 0.991678 | 0.963329 | 1.09059 | 2 |
| t600 | pipeline | CTR | 16384 | 1.02951 | 0.974391 | 1.05255 | 3 |
| t600 | pipeline | CTR | 1048576 | 0.98301 | 0.966548 | 1.08263 | 1 |
| t600 | pipeline | CTR | 16777216 | 1.00198 | 0.997239 | 1.0881 | 3 |
| t600 | pipeline | CTR | 33554432 | 1.01283 | 0.663895 | 1.03313 | 3 |
| t600 | pipeline | ECB | 1024 | 1.02983 | 0.932225 | 1.04164 | 4 |
| t600 | pipeline | ECB | 16384 | 1.01163 | 0.9375 | 1.06214 | 3 |
| t600 | pipeline | ECB | 1048576 | 1.00335 | 0.94358 | 1.0264 | 3 |
| t600 | pipeline | ECB | 16777216 | 1.00709 | 1.00188 | 1.2428 | 5 |
| t600 | pipeline | ECB | 33554432 | 1.00599 | 0.994975 | 1.40898 | 4 |
| t600 | resident | CTR | 1024 | 1.06205 | 0.991284 | 1.1686 | 4 |
| t600 | resident | CTR | 16384 | 1.03811 | 0.914612 | 1.39201 | 3 |
| t600 | resident | CTR | 1048576 | 0.988171 | 0.976771 | 1.02218 | 1 |
| t600 | resident | CTR | 16777216 | 0.999039 | 0.984928 | 1.00743 | 2 |
| t600 | resident | CTR | 33554432 | 1.00271 | 0.920815 | 1.00494 | 3 |
| t600 | resident | ECB | 1024 | 1.02624 | 0.968859 | 1.08899 | 4 |
| t600 | resident | ECB | 16384 | 0.960814 | 0.873957 | 1.03769 | 2 |
| t600 | resident | ECB | 1048576 | 1.01625 | 0.986547 | 1.02811 | 3 |
| t600 | resident | ECB | 16777216 | 0.985491 | 0.953666 | 1.08928 | 1 |
| t600 | resident | ECB | 33554432 | 0.994612 | 0.943834 | 1.09486 | 1 |

A value >1 means v1 has lower median time. The candidate name does not imply a gain. Full CPU software/AES-NI contrasts and pipeline/resident contrasts are in `derived_comparisons.csv`, retaining session extrema and direction counts. No cross-platform raw samples, CBC references or independently collected standalone GPU baselines are substituted.

## Resident versus pipeline at 32 MiB

| platform | backend | mode | metric | median | min | max |
|---|---|---|---|---|---|---|
| gtx1650ti | cuda_baseline | CTR | approximate_additional_pipeline_seconds | 0.0209245 | 0.0206987 | 0.0214867 |
| gtx1650ti | cuda_baseline | CTR | approximate_relative_additional_pipeline_time | 2.86655 | 2.77398 | 3.18035 |
| gtx1650ti | cuda_baseline | ECB | approximate_additional_pipeline_seconds | 0.0207441 | 0.0207157 | 0.020825 |
| gtx1650ti | cuda_baseline | ECB | approximate_relative_additional_pipeline_time | 2.97057 | 2.85167 | 3.15058 |
| gtx1650ti | cuda_baseline | CTR | pipeline_to_resident_throughput_ratio | 0.258624 | 0.239187 | 0.26497 |
| gtx1650ti | cuda_baseline | ECB | pipeline_to_resident_throughput_ratio | 0.25186 | 0.24093 | 0.2596 |
| gtx1650ti | cuda_baseline | CTR | resident_to_pipeline_latency_ratio | 0.258629 | 0.239215 | 0.264973 |
| gtx1650ti | cuda_baseline | ECB | resident_to_pipeline_latency_ratio | 0.251853 | 0.24093 | 0.259627 |
| gtx1650ti | cuda_optimized_v1 | CTR | approximate_additional_pipeline_seconds | 0.0207435 | 0.0205401 | 0.0208663 |
| gtx1650ti | cuda_optimized_v1 | CTR | approximate_relative_additional_pipeline_time | 2.84254 | 2.65816 | 2.99456 |
| gtx1650ti | cuda_optimized_v1 | ECB | approximate_additional_pipeline_seconds | 0.0209232 | 0.0207121 | 0.0210232 |
| gtx1650ti | cuda_optimized_v1 | ECB | approximate_relative_additional_pipeline_time | 2.95591 | 2.90218 | 3.19487 |
| gtx1650ti | cuda_optimized_v1 | CTR | pipeline_to_resident_throughput_ratio | 0.260237 | 0.250327 | 0.273299 |
| gtx1650ti | cuda_optimized_v1 | ECB | pipeline_to_resident_throughput_ratio | 0.252787 | 0.238387 | 0.2562 |
| gtx1650ti | cuda_optimized_v1 | CTR | resident_to_pipeline_latency_ratio | 0.260245 | 0.250341 | 0.273361 |
| gtx1650ti | cuda_optimized_v1 | ECB | resident_to_pipeline_latency_ratio | 0.252787 | 0.238387 | 0.256267 |
| t4 | cuda_baseline | CTR | approximate_additional_pipeline_seconds | 0.00537617 | 0.00536857 | 0.00540485 |
| t4 | cuda_baseline | CTR | approximate_relative_additional_pipeline_time | 1.46948 | 1.46616 | 1.47506 |
| t4 | cuda_baseline | ECB | approximate_additional_pipeline_seconds | 0.00537969 | 0.00537418 | 0.00540321 |
| t4 | cuda_baseline | ECB | approximate_relative_additional_pipeline_time | 1.4709 | 1.47075 | 1.48036 |
| t4 | cuda_baseline | CTR | pipeline_to_resident_throughput_ratio | 0.404944 | 0.40403 | 0.405489 |
| t4 | cuda_baseline | ECB | pipeline_to_resident_throughput_ratio | 0.40471 | 0.403167 | 0.404736 |
| t4 | cuda_baseline | CTR | resident_to_pipeline_latency_ratio | 0.404944 | 0.40403 | 0.405489 |
| t4 | cuda_baseline | ECB | resident_to_pipeline_latency_ratio | 0.40471 | 0.403167 | 0.404736 |
| t4 | cuda_optimized_v1 | CTR | approximate_additional_pipeline_seconds | 0.00539032 | 0.00537366 | 0.00541173 |
| t4 | cuda_optimized_v1 | CTR | approximate_relative_additional_pipeline_time | 1.48115 | 1.47523 | 1.4892 |
| t4 | cuda_optimized_v1 | ECB | approximate_additional_pipeline_seconds | 0.00539285 | 0.00536919 | 0.00540379 |
| t4 | cuda_optimized_v1 | ECB | approximate_relative_additional_pipeline_time | 1.47289 | 1.46462 | 1.47701 |
| t4 | cuda_optimized_v1 | CTR | pipeline_to_resident_throughput_ratio | 0.403039 | 0.401735 | 0.404003 |
| t4 | cuda_optimized_v1 | ECB | pipeline_to_resident_throughput_ratio | 0.404385 | 0.403712 | 0.405743 |
| t4 | cuda_optimized_v1 | CTR | resident_to_pipeline_latency_ratio | 0.403039 | 0.401735 | 0.404003 |
| t4 | cuda_optimized_v1 | ECB | resident_to_pipeline_latency_ratio | 0.404385 | 0.403712 | 0.405743 |
| t600 | cuda_baseline | CTR | approximate_additional_pipeline_seconds | 0.00915637 | 0.00589763 | 0.00946185 |
| t600 | cuda_baseline | CTR | approximate_relative_additional_pipeline_time | 1.14953 | 0.731243 | 1.26883 |
| t600 | cuda_baseline | ECB | approximate_additional_pipeline_seconds | 0.00884629 | 0.00583848 | 0.0157371 |
| t600 | cuda_baseline | ECB | approximate_relative_additional_pipeline_time | 1.11284 | 0.745388 | 2.11962 |
| t600 | cuda_baseline | CTR | pipeline_to_resident_throughput_ratio | 0.465191 | 0.440605 | 0.577632 |
| t600 | cuda_baseline | ECB | pipeline_to_resident_throughput_ratio | 0.473225 | 0.344522 | 0.57294 |
| t600 | cuda_baseline | CTR | resident_to_pipeline_latency_ratio | 0.465218 | 0.440756 | 0.57762 |
| t600 | cuda_baseline | ECB | resident_to_pipeline_latency_ratio | 0.473297 | 0.320552 | 0.572939 |
| t600 | cuda_optimized_v1 | CTR | approximate_additional_pipeline_seconds | 0.00894468 | 0.00615218 | 0.0139588 |
| t600 | cuda_optimized_v1 | CTR | approximate_relative_additional_pipeline_time | 1.17893 | 0.76487 | 1.65778 |
| t600 | cuda_optimized_v1 | ECB | approximate_additional_pipeline_seconds | 0.00856313 | 0.00589369 | 0.00943506 |
| t600 | cuda_optimized_v1 | ECB | approximate_relative_additional_pipeline_time | 1.08477 | 0.751109 | 1.29949 |
| t600 | cuda_optimized_v1 | CTR | pipeline_to_resident_throughput_ratio | 0.458943 | 0.422762 | 0.566634 |
| t600 | cuda_optimized_v1 | ECB | pipeline_to_resident_throughput_ratio | 0.478845 | 0.434889 | 0.571093 |
| t600 | cuda_optimized_v1 | CTR | resident_to_pipeline_latency_ratio | 0.458941 | 0.376254 | 0.566614 |
| t600 | cuda_optimized_v1 | ECB | resident_to_pipeline_latency_ratio | 0.479669 | 0.434879 | 0.571067 |

Absolute residuals use seconds; relative residuals are (pipeline time − resident time)/resident time, not fractions of total pipeline time. Independently measured host H2D/D2H intervals and the pipeline kernel component are exported in `pipeline_recorded_components.csv` for every size. These are supported by raw fields, not reconstructed from resident subtraction. Pure PCIe service bandwidth, overlap potential, enqueue versus wait costs and allocation-inclusive application latency cannot be established without a separately instrumented experiment.

All numeric rows are traceable by platform/run_id, seed(s), backend, mode, bytes and scope to `experiments/cuda_paired/seed-<seed>/native/raw.csv`. Full input hashes and selected paths are in `reproducibility_manifest.json`. Derived contrasts retain per-session values in `session_contrasts.csv`; no platforms are pooled.
