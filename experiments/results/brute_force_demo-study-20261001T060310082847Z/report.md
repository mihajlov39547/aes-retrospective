# Educational reduced-keyspace exhaustive search demonstration

Purpose: study; CPU software AES-128, ECB, fixed two-block plaintext.
Actually searched: 24 variable bits, 16777216 candidates; upper key bits zero.
Each row measures a stop-on-match search; end targets traverse the entire reduced space.

| Scenario | Median candidates | Median seconds | Median candidates/s |
|---|---:|---:|---:|
| start | 1 | 8.5e-06 | 117647 |
| middle | 8388609 | 54.5381 | 153812 |
| end | 16777216 | 109.44 | 153300 |
| random | 7430575 | 48.1609 | 153853 |

Extrapolation rate: 153300 candidates/s from end median repeat rate.
Start and short searches are overhead-sensitive; partial-scan projections are not measured full scans.
Full=N/r; half=N/(2r); exact uniform first-hit expectation=(N+1)/(2r).
No pooling of positions or automatic outlier deletion. Year=365.25 days.
Linear extrapolation under fixed-rate assumption, not an implementation of full-space search; not a cryptanalytic attack evaluation. AES/Python candidate rate is not DES/TDEA or GPU search rate.
Double-DES nominal 112 bits has MITM alternatives. TDEA nominal 168 bits is not a security-strength claim.
Software/native library and Python setup dominate this workload; fixed-key CUDA MB/s cannot be converted into candidate-check rate.

| Space | Extent | Seconds | Days | Years |
|---|---|---:|---:|---:|
| DES | full | 4.70042387E+11 | 5.44030541E+6 | 1.48947444E+4 |
| DES | half | 2.35021194E+11 | 2.72015270E+6 | 7.44737222E+3 |
| DES | uniform_expected | 2.35021194E+11 | 2.72015270E+6 | 7.44737222E+3 |
| Double-DES nominal | full | 3.38701235E+28 | 3.92015319E+23 | 1.07327945E+21 |
| Double-DES nominal | half | 1.69350618E+28 | 1.96007659E+23 | 5.36639724E+20 |
| Double-DES nominal | uniform_expected | 1.69350618E+28 | 1.96007659E+23 | 5.36639724E+20 |
| Three-key TDEA nominal | full | 2.44059961E+45 | 2.82476807E+40 | 7.73379348E+37 |
| Three-key TDEA nominal | half | 1.22029981E+45 | 1.41238403E+40 | 3.86689674E+37 |
| Three-key TDEA nominal | uniform_expected | 1.22029981E+45 | 1.41238403E+40 | 3.86689674E+37 |
| AES-128 | full | 2.21971242E+33 | 2.56911159E+28 | 7.03384420E+25 |
| AES-128 | half | 1.10985621E+33 | 1.28455580E+28 | 3.51692210E+25 |
| AES-128 | uniform_expected | 1.10985621E+33 | 1.28455580E+28 | 3.51692210E+25 |
| AES-192 | full | 4.09464669E+52 | 4.73917440E+47 | 1.29751524E+45 |
| AES-192 | half | 2.04732334E+52 | 2.36958720E+47 | 6.48757619E+44 |
| AES-192 | uniform_expected | 2.04732334E+52 | 2.36958720E+47 | 6.48757619E+44 |
| AES-256 | full | 7.55328995E+71 | 8.74223374E+66 | 2.39349315E+64 |
| AES-256 | half | 3.77664497E+71 | 4.37111687E+66 | 1.19674658E+64 |
| AES-256 | uniform_expected | 3.77664497E+71 | 4.37111687E+66 | 1.19674658E+64 |
