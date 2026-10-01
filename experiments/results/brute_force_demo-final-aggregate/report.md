# Final reduced-keyspace aggregate

Median of five session medians, separately for each metric; no raw pooling or outlier removal

## Accepted sessions
- Seed 2003: brute_force_demo-study-20261001T060310082847Z (validation PASS; 12 raw, 4 summary rows)
- Seed 2004: brute_force_demo-study-20261001T061333155317Z (validation PASS; 12 raw, 4 summary rows)
- Seed 2005: brute_force_demo-study-20261001T062340379137Z (validation PASS; 12 raw, 4 summary rows)
- Seed 2006: brute_force_demo-study-20261001T063343478046Z (validation PASS; 12 raw, 4 summary rows)
- Seed 2007: brute_force_demo-study-20261001T064427326224Z (validation PASS; 12 raw, 4 summary rows)

All archived source hashes match. Validation hashes and summary medians were checked against raw; no experimental code was executed.
AES-128 ECB, software use_aesni=False, 24 variable low bits, upper bits zero, two fixed known blocks; three repeats per scenario.

| Scenario | Checked | Seconds | Candidates/s |
|---|---:|---:|---:|
| start | 1 | 8.8e-06 | 113636.364 |
| middle | 8388609 | 54.3785826 | 154263.105 |
| end | 16777216 | 109.011366 | 153903.365 |
| random | 6800733 | 43.0032438 | 154078.594 |

Extrapolation basis: end scenario only, 153903.364959 candidates/s.
Linear mathematical illustration under fixed-rate assumption; not full-space search or evaluation of all cryptanalytic attacks. AES/Python rate is not DES/TDEA/GPU search rate.
Double-DES uses a distinct MITM attack model; nominal TDEA 168 bits is not a security-strength claim.
Fixed-key CUDA MB/s is not candidate-check throughput. Start measures one candidate and is not sustained throughput.
CPU/Python/native workload includes per-key construction, schedule, encryption, allocation and comparison. Not an optimized C/GPU search engine.
No model of parallel farms, ASIC/FPGA/GPU hardware or specific attacks is included. ECB is not a data-protection recommendation.
Full=N/r; half=N/(2r); uniform=(N+1)/(2r). Years use 365.25 days.
Metrics are aggregated independently; especially for random targets, count/time is not the median rate.
CSV/JSON retain arithmetic precision for audit, not measurement precision.

| Space | Extent | Years |
|---|---|---:|
| DES | full | 1.483637065473E+4 |
| DES | half | 7.418185327366E+3 |
| DES | uniform_expected | 7.418185327366E+3 |
| Double-DES nominal | full | 1.069073173635E+21 |
| Double-DES nominal | half | 5.345365868175E+20 |
| Double-DES nominal | uniform_expected | 5.345365868175E+20 |
| Three-key TDEA nominal | full | 7.703484074263E+37 |
| Three-key TDEA nominal | half | 3.851742037131E+37 |
| Three-key TDEA nominal | uniform_expected | 3.851742037131E+37 |
| AES-128 | full | 7.006277950734E+25 |
| AES-128 | half | 3.503138975367E+25 |
| AES-128 | uniform_expected | 3.503138975367E+25 |
| AES-192 | full | 1.292430162665E+45 |
| AES-192 | half | 6.462150813323E+44 |
| AES-192 | uniform_expected | 6.462150813323E+44 |
| AES-256 | full | 2.384112844382E+64 |
| AES-256 | half | 1.192056422191E+64 |
| AES-256 | uniform_expected | 1.192056422191E+64 |
