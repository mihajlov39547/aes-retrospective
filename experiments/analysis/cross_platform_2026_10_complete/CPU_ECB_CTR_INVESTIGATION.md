# CPU ECB versus CTR

T4 dispatch and raw distributions passed the same checks as the other platforms. Ratios below summarize five session-level throughput-median contrasts, separately for every size. Consistency does not establish a library-version cause. At 32 MiB, T4-host CPU ECB/CTR throughput ratio is 5.378, range 5.250–5.795 across five sessions; ECB is faster in 5/5. This is a reproducible mode disparity on the captured cloud CPU, not a T4 GPU AES-NI property.

| platform | backend | bytes | ECB_over_CTR | min | max | IQR | sessions_ECB_faster |
|---|---|---|---|---|---|---|---|
| gtx1650ti | cpu_aesni | 1024 | 1.07407 | 0.940277 | 1.2591 | 0.071665 | 4 |
| gtx1650ti | cpu_aesni | 16384 | 1.37209 | 1.32756 | 1.38202 | 0.0227771 | 5 |
| gtx1650ti | cpu_aesni | 1048576 | 1.29576 | 1.2554 | 1.30665 | 0.0311655 | 5 |
| gtx1650ti | cpu_aesni | 16777216 | 1.25652 | 1.25256 | 1.3087 | 0.0216369 | 5 |
| gtx1650ti | cpu_aesni | 33554432 | 1.25641 | 1.23915 | 1.29031 | 0.00842883 | 5 |
| gtx1650ti | cpu_software | 1024 | 0.994186 | 0.982922 | 1.04849 | 0.0473045 | 2 |
| gtx1650ti | cpu_software | 16384 | 1.06141 | 1.0496 | 1.06995 | 0.0105854 | 5 |
| gtx1650ti | cpu_software | 1048576 | 1.06237 | 1.05207 | 1.0701 | 0.00129387 | 5 |
| gtx1650ti | cpu_software | 16777216 | 1.05206 | 1.02057 | 1.06362 | 0.00756273 | 5 |
| gtx1650ti | cpu_software | 33554432 | 1.05943 | 1.0512 | 1.06886 | 0.00743615 | 5 |
| t4 | cpu_aesni | 1024 | 1.21223 | 1.09976 | 1.38694 | 0.0943164 | 5 |
| t4 | cpu_aesni | 16384 | 2.18508 | 2.10806 | 2.29039 | 0.0552532 | 5 |
| t4 | cpu_aesni | 1048576 | 5.63123 | 5.42089 | 5.78005 | 0.125961 | 5 |
| t4 | cpu_aesni | 16777216 | 5.43931 | 5.40457 | 5.50934 | 0.0439488 | 5 |
| t4 | cpu_aesni | 33554432 | 5.37821 | 5.2504 | 5.79501 | 0.0504378 | 5 |
| t4 | cpu_software | 1024 | 1.06401 | 1.03615 | 1.11729 | 0.0227481 | 5 |
| t4 | cpu_software | 16384 | 1.26789 | 1.21305 | 1.2885 | 0.0271248 | 5 |
| t4 | cpu_software | 1048576 | 1.25409 | 1.24286 | 1.28025 | 0.0256189 | 5 |
| t4 | cpu_software | 16777216 | 1.2423 | 1.22934 | 1.26484 | 0.0171231 | 5 |
| t4 | cpu_software | 33554432 | 1.23541 | 1.18267 | 1.24745 | 0.0110116 | 5 |
| t600 | cpu_aesni | 1024 | 1.11768 | 1.07317 | 1.14358 | 0.0351654 | 5 |
| t600 | cpu_aesni | 16384 | 1.49586 | 1.34667 | 1.60449 | 0.148532 | 5 |
| t600 | cpu_aesni | 1048576 | 1.3081 | 1.25626 | 1.55794 | 0.0580819 | 5 |
| t600 | cpu_aesni | 16777216 | 1.24593 | 1.14421 | 1.28614 | 0.0397276 | 5 |
| t600 | cpu_aesni | 33554432 | 1.2572 | 1.22139 | 1.30258 | 0.0305221 | 5 |
| t600 | cpu_software | 1024 | 0.986667 | 0.860062 | 1 | 0.00678524 | 0 |
| t600 | cpu_software | 16384 | 1.04149 | 1.03522 | 1.11059 | 0.0649715 | 5 |
| t600 | cpu_software | 1048576 | 1.03585 | 1.01299 | 1.24112 | 0.0376839 | 5 |
| t600 | cpu_software | 16777216 | 1.03267 | 1.01553 | 1.0519 | 0.014087 | 5 |
| t600 | cpu_software | 33554432 | 1.04347 | 1.03335 | 1.04959 | 0.0158773 | 5 |

## Captured CPU/library facts

| platform | cpu | physical_cpus | logical_cpus | python | pycryptodome | eligible |
|---|---|---|---|---|---|---|
| gtx1650ti | Intel(R) Core(TM) i5-10300H CPU @ 2.50GHz | 4 | 8 | 3.12.10 | 3.23.0 | True |
| t4 | Intel(R) Xeon(R) CPU @ 2.00GHz | 1 | 2 | 3.13.15 | 4.0.0 | True |
| t600 | 11th Gen Intel(R) Core(TM) i7-11850H @ 2.50GHz | 8 | 16 | 3.10.5 | 3.24.1 | True |

Native dispatch details and before/after session telemetry are preserved in `session_provenance.json`. AES-NI dispatch does not guarantee identical bulk implementations for ECB and CTR. Counter generation, native mode implementation, allocation/memory effects, CPU virtualization and clock behavior are hypotheses. A version difference alone is not evidence of a version effect. A controlled same-host/library-version and allocation-policy experiment is needed; retain mode-specific validation and the same timer scope.

All numeric rows are traceable by platform/run_id, seed(s), backend, mode, bytes and scope to `experiments/cuda_paired/seed-<seed>/native/raw.csv`. Full input hashes and selected paths are in `reproducibility_manifest.json`. Derived contrasts retain per-session values in `session_contrasts.csv`; no platforms are pooled.
