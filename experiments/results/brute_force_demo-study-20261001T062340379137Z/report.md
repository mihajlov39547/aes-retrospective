# Educational reduced-keyspace exhaustive search demonstration

Purpose: study; CPU software AES-128, ECB, fixed two-block plaintext.
Actually searched: 24 variable bits, 16777216 candidates; upper key bits zero.
Each row measures a stop-on-match search; end targets traverse the entire reduced space.

| Scenario | Median candidates | Median seconds | Median candidates/s |
|---|---:|---:|---:|
| start | 1 | 8.9e-06 | 112360 |
| middle | 8388609 | 54.3438 | 154362 |
| end | 16777216 | 108.268 | 154961 |
| random | 2563625 | 16.6384 | 154079 |

Extrapolation rate: 154961 candidates/s from end median repeat rate.
Start and short searches are overhead-sensitive; partial-scan projections are not measured full scans.
Full=N/r; half=N/(2r); exact uniform first-hit expectation=(N+1)/(2r).
No pooling of positions or automatic outlier deletion. Year=365.25 days.
Linear extrapolation under fixed-rate assumption, not an implementation of full-space search; not a cryptanalytic attack evaluation. AES/Python candidate rate is not DES/TDEA or GPU search rate.
Double-DES nominal 112 bits has MITM alternatives. TDEA nominal 168 bits is not a security-strength claim.
Software/native library and Python setup dominate this workload; fixed-key CUDA MB/s cannot be converted into candidate-check rate.

| Space | Extent | Seconds | Days | Years |
|---|---|---:|---:|---:|
| DES | full | 4.65006114E+11 | 5.38201521E+6 | 1.47351546E+4 |
| DES | half | 2.32503057E+11 | 2.69100760E+6 | 7.36757729E+3 |
| DES | uniform_expected | 2.32503057E+11 | 2.69100760E+6 | 7.36757729E+3 |
| Double-DES nominal | full | 3.35072218E+28 | 3.87815067E+23 | 1.06177979E+21 |
| Double-DES nominal | half | 1.67536109E+28 | 1.93907533E+23 | 5.30889893E+20 |
| Double-DES nominal | uniform_expected | 1.67536109E+28 | 1.93907533E+23 | 5.30889893E+20 |
| Three-key TDEA nominal | full | 2.41444978E+45 | 2.79450207E+40 | 7.65092968E+37 |
| Three-key TDEA nominal | half | 1.20722489E+45 | 1.39725103E+40 | 3.82546484E+37 |
| Three-key TDEA nominal | uniform_expected | 1.20722489E+45 | 1.39725103E+40 | 3.82546484E+37 |
| AES-128 | full | 2.19592929E+33 | 2.54158482E+28 | 6.95848001E+25 |
| AES-128 | half | 1.09796464E+33 | 1.27079241E+28 | 3.47924000E+25 |
| AES-128 | uniform_expected | 1.09796464E+33 | 1.27079241E+28 | 3.47924000E+25 |
| AES-192 | full | 4.05077456E+52 | 4.68839648E+47 | 1.28361300E+45 |
| AES-192 | half | 2.02538728E+52 | 2.34419824E+47 | 6.41806499E+44 |
| AES-192 | uniform_expected | 2.02538728E+52 | 2.34419824E+47 | 6.41806499E+44 |
| AES-256 | full | 7.47236015E+71 | 8.64856499E+66 | 2.36784805E+64 |
| AES-256 | half | 3.73618008E+71 | 4.32428250E+66 | 1.18392402E+64 |
| AES-256 | uniform_expected | 3.73618008E+71 | 4.32428250E+66 | 1.18392402E+64 |
