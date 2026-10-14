# The 16 MiB feature

gtx1650ti: 8/8 GPU backend/scope/mode groups show a local 16 MiB dip in every session. Direction counts range from 5 to 5 of five; this is observed repeatability, not a causal or significance claim.

t4: 0/8 GPU backend/scope/mode groups show a local 16 MiB dip in every session. Direction counts range from 0 to 4 of five; this is observed repeatability, not a causal or significance claim.

t600: 1/8 GPU backend/scope/mode groups show a local 16 MiB dip in every session. Direction counts range from 3 to 5 of five; this is observed repeatability, not a causal or significance claim.

For each session, divide median throughput at 16 MiB by that at 1 MiB or 32 MiB for the same backend/mode/scope. Below one means lower throughput at 16 MiB. A local dip requires both contrasts below one in the same session; the individual counts below must not be interpreted as a joint test. Full session contrasts permit that check.

| platform | backend | scope | mode | reference | ratio | min | max | IQR | CV | sessions_lower |
|---|---|---|---|---|---|---|---|---|---|---|
| gtx1650ti | cpu_aesni | transform | CTR | 1 MiB | 0.993604 | 0.930488 | 1.0065 | 0.0242864 | 0.0309191 | 4 |
| gtx1650ti | cpu_aesni | transform | CTR | 32 MiB | 1.04817 | 1.01923 | 1.06968 | 0.0224966 | 0.0193191 | 0 |
| gtx1650ti | cpu_aesni | transform | ECB | 1 MiB | 0.970825 | 0.938153 | 0.994241 | 0.01286 | 0.0211232 | 5 |
| gtx1650ti | cpu_aesni | transform | ECB | 32 MiB | 1.04814 | 1.00847 | 1.09207 | 0.0636017 | 0.0353925 | 0 |
| gtx1650ti | cpu_software | transform | CTR | 1 MiB | 0.998156 | 0.981507 | 1.00382 | 0.00505176 | 0.0086115 | 3 |
| gtx1650ti | cpu_software | transform | CTR | 32 MiB | 1.00559 | 0.999736 | 1.02585 | 0.00592135 | 0.00987199 | 1 |
| gtx1650ti | cpu_software | transform | ECB | 1 MiB | 0.995837 | 0.936078 | 1.00365 | 0.00829895 | 0.0279589 | 4 |
| gtx1650ti | cpu_software | transform | ECB | 32 MiB | 0.999282 | 0.988223 | 1.01341 | 0.015972 | 0.0106716 | 3 |
| gtx1650ti | cuda_baseline | pipeline | CTR | 1 MiB | 0.756056 | 0.491382 | 0.780387 | 0.0534794 | 0.17297 | 5 |
| gtx1650ti | cuda_baseline | pipeline | CTR | 32 MiB | 0.9197 | 0.54736 | 0.945284 | 0.138896 | 0.203493 | 5 |
| gtx1650ti | cuda_baseline | pipeline | ECB | 1 MiB | 0.774247 | 0.43919 | 0.823914 | 0.0383989 | 0.218257 | 5 |
| gtx1650ti | cuda_baseline | pipeline | ECB | 32 MiB | 0.921414 | 0.540318 | 0.932852 | 0.026034 | 0.201768 | 5 |
| gtx1650ti | cuda_baseline | resident | CTR | 1 MiB | 0.73892 | 0.679146 | 0.789843 | 0.023284 | 0.0545273 | 5 |
| gtx1650ti | cuda_baseline | resident | CTR | 32 MiB | 0.788253 | 0.709331 | 0.852588 | 0.0874938 | 0.0776809 | 5 |
| gtx1650ti | cuda_baseline | resident | ECB | 1 MiB | 0.759955 | 0.664704 | 0.803573 | 0.0459375 | 0.0716219 | 5 |
| gtx1650ti | cuda_baseline | resident | ECB | 32 MiB | 0.779043 | 0.686422 | 0.857947 | 0.0787493 | 0.0873486 | 5 |
| gtx1650ti | cuda_optimized_v1 | pipeline | CTR | 1 MiB | 0.807631 | 0.483293 | 0.854492 | 0.168618 | 0.214022 | 5 |
| gtx1650ti | cuda_optimized_v1 | pipeline | CTR | 32 MiB | 0.902552 | 0.544884 | 0.930047 | 0.195756 | 0.208348 | 5 |
| gtx1650ti | cuda_optimized_v1 | pipeline | ECB | 1 MiB | 0.739644 | 0.455509 | 0.807822 | 0.0416755 | 0.201306 | 5 |
| gtx1650ti | cuda_optimized_v1 | pipeline | ECB | 32 MiB | 0.917476 | 0.543255 | 0.941717 | 0.00521236 | 0.200987 | 5 |
| gtx1650ti | cuda_optimized_v1 | resident | CTR | 1 MiB | 0.750442 | 0.674401 | 0.779838 | 0.0380077 | 0.0572694 | 5 |
| gtx1650ti | cuda_optimized_v1 | resident | CTR | 32 MiB | 0.802959 | 0.712663 | 0.84515 | 0.073521 | 0.0691607 | 5 |
| gtx1650ti | cuda_optimized_v1 | resident | ECB | 1 MiB | 0.759688 | 0.683616 | 0.810735 | 0.0151943 | 0.0609174 | 5 |
| gtx1650ti | cuda_optimized_v1 | resident | ECB | 32 MiB | 0.778812 | 0.731384 | 0.818705 | 0.029269 | 0.0419844 | 5 |
| t4 | cpu_aesni | transform | CTR | 1 MiB | 0.994782 | 0.978515 | 1.01319 | 0.00750639 | 0.0127635 | 4 |
| t4 | cpu_aesni | transform | CTR | 32 MiB | 1.03013 | 1.02647 | 1.09832 | 0.0217713 | 0.0290852 | 0 |
| t4 | cpu_aesni | transform | ECB | 1 MiB | 0.974729 | 0.930097 | 1.01212 | 0.0394079 | 0.0341718 | 4 |
| t4 | cpu_aesni | transform | ECB | 32 MiB | 1.05312 | 1.03545 | 1.06134 | 0.00918273 | 0.0094847 | 0 |
| t4 | cpu_software | transform | CTR | 1 MiB | 0.983006 | 0.978979 | 1.01043 | 0.0064402 | 0.0131654 | 4 |
| t4 | cpu_software | transform | CTR | 32 MiB | 1.00836 | 0.990853 | 1.07311 | 0.0141935 | 0.0320804 | 2 |
| t4 | cpu_software | transform | ECB | 1 MiB | 0.977277 | 0.940046 | 0.997272 | 0.00616313 | 0.0217028 | 5 |
| t4 | cpu_software | transform | ECB | 32 MiB | 1.02362 | 0.977424 | 1.08331 | 0.0596323 | 0.0419048 | 1 |
| t4 | cuda_baseline | pipeline | CTR | 1 MiB | 1.16723 | 1.15029 | 1.33422 | 0.0399817 | 0.0629648 | 0 |
| t4 | cuda_baseline | pipeline | CTR | 32 MiB | 0.974584 | 0.969076 | 0.981927 | 0.00242037 | 0.00475708 | 5 |
| t4 | cuda_baseline | pipeline | ECB | 1 MiB | 1.16346 | 1.15411 | 1.34645 | 0.0725651 | 0.0682299 | 0 |
| t4 | cuda_baseline | pipeline | ECB | 32 MiB | 0.976757 | 0.975696 | 0.978621 | 0.00202915 | 0.00129991 | 5 |
| t4 | cuda_baseline | resident | CTR | 1 MiB | 0.90078 | 0.854675 | 1.27595 | 0.0682763 | 0.175892 | 4 |
| t4 | cuda_baseline | resident | CTR | 32 MiB | 0.980638 | 0.980019 | 0.981868 | 0.000922465 | 0.000760917 | 5 |
| t4 | cuda_baseline | resident | ECB | 1 MiB | 0.903895 | 0.845934 | 1.24659 | 0.0652028 | 0.167644 | 4 |
| t4 | cuda_baseline | resident | ECB | 32 MiB | 0.98055 | 0.979241 | 0.982588 | 0.00234908 | 0.00151741 | 5 |
| t4 | cuda_optimized_v1 | pipeline | CTR | 1 MiB | 1.17979 | 1.16982 | 1.35115 | 0.0290835 | 0.0634283 | 0 |
| t4 | cuda_optimized_v1 | pipeline | CTR | 32 MiB | 0.976644 | 0.973994 | 0.979009 | 0.00116235 | 0.00187111 | 5 |
| t4 | cuda_optimized_v1 | pipeline | ECB | 1 MiB | 1.17963 | 1.16076 | 1.34066 | 0.0131462 | 0.0618708 | 0 |
| t4 | cuda_optimized_v1 | pipeline | ECB | 32 MiB | 0.977957 | 0.97354 | 0.978238 | 0.00350682 | 0.00229718 | 5 |
| t4 | cuda_optimized_v1 | resident | CTR | 1 MiB | 0.90656 | 0.852182 | 1.26149 | 0.0569417 | 0.169569 | 4 |
| t4 | cuda_optimized_v1 | resident | CTR | 32 MiB | 0.978661 | 0.977716 | 0.979413 | 0.000921929 | 0.00071642 | 5 |
| t4 | cuda_optimized_v1 | resident | ECB | 1 MiB | 0.925795 | 0.892206 | 1.24491 | 0.0628258 | 0.151538 | 4 |
| t4 | cuda_optimized_v1 | resident | ECB | 32 MiB | 0.981792 | 0.979272 | 0.983209 | 0.00129336 | 0.00160958 | 5 |
| t600 | cpu_aesni | transform | CTR | 1 MiB | 0.956133 | 0.9447 | 1.33405 | 0.0313251 | 0.163172 | 4 |
| t600 | cpu_aesni | transform | CTR | 32 MiB | 0.957351 | 0.886347 | 1.00836 | 0.0538101 | 0.0497455 | 4 |
| t600 | cpu_aesni | transform | ECB | 1 MiB | 0.934918 | 0.8497 | 1.06688 | 0.02784 | 0.0830458 | 4 |
| t600 | cpu_aesni | transform | ECB | 32 MiB | 0.937518 | 0.799974 | 1.01413 | 0.0608193 | 0.0895491 | 4 |
| t600 | cpu_software | transform | CTR | 1 MiB | 0.972372 | 0.933159 | 1.55256 | 0.0816043 | 0.244018 | 3 |
| t600 | cpu_software | transform | CTR | 32 MiB | 0.919977 | 0.866313 | 1.02341 | 0.0371931 | 0.0623659 | 4 |
| t600 | cpu_software | transform | ECB | 1 MiB | 0.976502 | 0.940166 | 1.31585 | 0.0443356 | 0.155014 | 4 |
| t600 | cpu_software | transform | ECB | 32 MiB | 0.905283 | 0.868219 | 1.01943 | 0.0530019 | 0.0638033 | 4 |
| t600 | cuda_baseline | pipeline | CTR | 1 MiB | 0.538707 | 0.34227 | 1.15035 | 0.20971 | 0.473298 | 4 |
| t600 | cuda_baseline | pipeline | CTR | 32 MiB | 0.558707 | 0.30244 | 1.07404 | 0.0639867 | 0.45035 | 4 |
| t600 | cuda_baseline | pipeline | ECB | 1 MiB | 0.547107 | 0.330185 | 1.18715 | 0.629072 | 0.530016 | 3 |
| t600 | cuda_baseline | pipeline | ECB | 32 MiB | 0.703172 | 0.402915 | 1.06342 | 0.456726 | 0.384396 | 4 |
| t600 | cuda_baseline | resident | CTR | 1 MiB | 0.828378 | 0.692827 | 1.00525 | 0.0812273 | 0.136961 | 4 |
| t600 | cuda_baseline | resident | CTR | 32 MiB | 0.821353 | 0.609535 | 0.976804 | 0.0875104 | 0.166633 | 5 |
| t600 | cuda_baseline | resident | ECB | 1 MiB | 0.832482 | 0.71353 | 1.00574 | 0.201266 | 0.147739 | 4 |
| t600 | cuda_baseline | resident | ECB | 32 MiB | 0.837185 | 0.655588 | 1.01495 | 0.159304 | 0.166635 | 4 |
| t600 | cuda_optimized_v1 | pipeline | CTR | 1 MiB | 0.545571 | 0.317627 | 1.17644 | 0.339575 | 0.4904 | 4 |
| t600 | cuda_optimized_v1 | pipeline | CTR | 32 MiB | 0.548307 | 0.299998 | 1.43326 | 0.20731 | 0.60581 | 4 |
| t600 | cuda_optimized_v1 | pipeline | ECB | 1 MiB | 0.536346 | 0.432806 | 1.18013 | 0.623099 | 0.479069 | 3 |
| t600 | cuda_optimized_v1 | pipeline | ECB | 32 MiB | 0.554647 | 0.40322 | 1.07245 | 0.465609 | 0.422705 | 3 |
| t600 | cuda_optimized_v1 | resident | CTR | 1 MiB | 0.844445 | 0.689752 | 0.978296 | 0.0814765 | 0.126237 | 5 |
| t600 | cuda_optimized_v1 | resident | CTR | 32 MiB | 0.817774 | 0.609001 | 1.0537 | 0.0839317 | 0.191822 | 4 |
| t600 | cuda_optimized_v1 | resident | ECB | 1 MiB | 0.826973 | 0.763589 | 0.982514 | 0.145871 | 0.110398 | 5 |
| t600 | cuda_optimized_v1 | resident | ECB | 32 MiB | 0.816963 | 0.750431 | 0.981032 | 0.209346 | 0.131127 | 5 |

## Joint local-dip check

A session qualifies only if 16 MiB throughput is lower than both 1 MiB and 32 MiB. Even tiny differences count directionally; these are descriptive counts, not significance tests.

| platform | backend | scope | mode | sessions_local_dip | seeds |
|---|---|---|---|---|---|
| gtx1650ti | cpu_aesni | transform | CTR | 0 | [] |
| gtx1650ti | cpu_aesni | transform | ECB | 0 | [] |
| gtx1650ti | cpu_software | transform | CTR | 1 | [2003] |
| gtx1650ti | cpu_software | transform | ECB | 2 | [2006, 2007] |
| gtx1650ti | cuda_baseline | pipeline | CTR | 5 | [2003, 2004, 2005, 2006, 2007] |
| gtx1650ti | cuda_baseline | pipeline | ECB | 5 | [2003, 2004, 2005, 2006, 2007] |
| gtx1650ti | cuda_baseline | resident | CTR | 5 | [2003, 2004, 2005, 2006, 2007] |
| gtx1650ti | cuda_baseline | resident | ECB | 5 | [2003, 2004, 2005, 2006, 2007] |
| gtx1650ti | cuda_optimized_v1 | pipeline | CTR | 5 | [2003, 2004, 2005, 2006, 2007] |
| gtx1650ti | cuda_optimized_v1 | pipeline | ECB | 5 | [2003, 2004, 2005, 2006, 2007] |
| gtx1650ti | cuda_optimized_v1 | resident | CTR | 5 | [2003, 2004, 2005, 2006, 2007] |
| gtx1650ti | cuda_optimized_v1 | resident | ECB | 5 | [2003, 2004, 2005, 2006, 2007] |
| t4 | cpu_aesni | transform | CTR | 0 | [] |
| t4 | cpu_aesni | transform | ECB | 0 | [] |
| t4 | cpu_software | transform | CTR | 2 | [2003, 2004] |
| t4 | cpu_software | transform | ECB | 1 | [2004] |
| t4 | cuda_baseline | pipeline | CTR | 0 | [] |
| t4 | cuda_baseline | pipeline | ECB | 0 | [] |
| t4 | cuda_baseline | resident | CTR | 4 | [2003, 2004, 2006, 2007] |
| t4 | cuda_baseline | resident | ECB | 4 | [2003, 2004, 2006, 2007] |
| t4 | cuda_optimized_v1 | pipeline | CTR | 0 | [] |
| t4 | cuda_optimized_v1 | pipeline | ECB | 0 | [] |
| t4 | cuda_optimized_v1 | resident | CTR | 4 | [2003, 2004, 2006, 2007] |
| t4 | cuda_optimized_v1 | resident | ECB | 4 | [2003, 2004, 2006, 2007] |
| t600 | cpu_aesni | transform | CTR | 3 | [2005, 2006, 2007] |
| t600 | cpu_aesni | transform | ECB | 3 | [2005, 2006, 2007] |
| t600 | cpu_software | transform | CTR | 3 | [2005, 2006, 2007] |
| t600 | cpu_software | transform | ECB | 3 | [2005, 2006, 2007] |
| t600 | cuda_baseline | pipeline | CTR | 4 | [2003, 2004, 2005, 2006] |
| t600 | cuda_baseline | pipeline | ECB | 3 | [2003, 2004, 2006] |
| t600 | cuda_baseline | resident | CTR | 4 | [2003, 2004, 2005, 2006] |
| t600 | cuda_baseline | resident | ECB | 3 | [2003, 2004, 2006] |
| t600 | cuda_optimized_v1 | pipeline | CTR | 4 | [2003, 2004, 2005, 2006] |
| t600 | cuda_optimized_v1 | pipeline | ECB | 3 | [2003, 2004, 2006] |
| t600 | cuda_optimized_v1 | resident | CTR | 4 | [2003, 2004, 2005, 2006] |
| t600 | cuda_optimized_v1 | resident | ECB | 5 | [2003, 2004, 2005, 2006, 2007] |

These are observed size effects, not causal diagnoses. A persistent reduction from 1 MiB through both 16 and 32 MiB is a large-buffer transition, not necessarily a narrow 16 MiB anomaly. Fixed size order confounds size with time. Candidate explanations include output allocation/page behavior, working-set/cache changes, pinned-buffer/copy behavior, driver scheduling, clocks and thermal state. None is established by these data. Repeat with randomized size order, dense sizes and per-iteration telemetry before assigning a cause.

All numeric rows are traceable by platform/run_id, seed(s), backend, mode, bytes and scope to `experiments/cuda_paired/seed-<seed>/native/raw.csv`. Full input hashes and selected paths are in `reproducibility_manifest.json`. Derived contrasts retain per-session values in `session_contrasts.csv`; no platforms are pooled.
