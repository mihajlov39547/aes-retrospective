# Educational reduced-keyspace exhaustive search demonstration

Purpose: study; CPU software AES-128, ECB, fixed two-block plaintext.
Actually searched: 24 variable bits, 16777216 candidates; upper key bits zero.
Each row measures a stop-on-match search; end targets traverse the entire reduced space.

| Scenario | Median candidates | Median seconds | Median candidates/s |
|---|---:|---:|---:|
| start | 1 | 8.8e-06 | 113636 |
| middle | 8388609 | 53.5733 | 156582 |
| end | 16777216 | 107.355 | 156278 |
| random | 6800733 | 43.0032 | 157515 |

Extrapolation rate: 156278 candidates/s from end median repeat rate.
Start and short searches are overhead-sensitive; partial-scan projections are not measured full scans.
Full=N/r; half=N/(2r); exact uniform first-hit expectation=(N+1)/(2r).
No pooling of positions or automatic outlier deletion. Year=365.25 days.
Linear extrapolation under fixed-rate assumption, not an implementation of full-space search; not a cryptanalytic attack evaluation. AES/Python candidate rate is not DES/TDEA or GPU search rate.
Double-DES nominal 112 bits has MITM alternatives. TDEA nominal 168 bits is not a security-strength claim.
Software/native library and Python setup dominate this workload; fixed-key CUDA MB/s cannot be converted into candidate-check rate.

| Space | Extent | Seconds | Days | Years |
|---|---|---:|---:|---:|
| DES | full | 4.61086208E+11 | 5.33664593E+6 | 1.46109403E+4 |
| DES | half | 2.30543104E+11 | 2.66832296E+6 | 7.30547013E+3 |
| DES | uniform_expected | 2.30543104E+11 | 2.66832296E+6 | 7.30547013E+3 |
| Double-DES nominal | full | 3.32247628E+28 | 3.84545866E+23 | 1.05282920E+21 |
| Double-DES nominal | half | 1.66123814E+28 | 1.92272933E+23 | 5.26414601E+20 |
| Double-DES nominal | uniform_expected | 1.66123814E+28 | 1.92272933E+23 | 5.26414601E+20 |
| Three-key TDEA nominal | full | 2.39409647E+45 | 2.77094499E+40 | 7.58643392E+37 |
| Three-key TDEA nominal | half | 1.19704823E+45 | 1.38547249E+40 | 3.79321696E+37 |
| Three-key TDEA nominal | uniform_expected | 1.19704823E+45 | 1.38547249E+40 | 3.79321696E+37 |
| AES-128 | full | 2.17741805E+33 | 2.52015979E+28 | 6.89982145E+25 |
| AES-128 | half | 1.08870903E+33 | 1.26007989E+28 | 3.44991073E+25 |
| AES-128 | uniform_expected | 1.08870903E+33 | 1.26007989E+28 | 3.44991073E+25 |
| AES-192 | full | 4.01662736E+52 | 4.64887426E+47 | 1.27279240E+45 |
| AES-192 | half | 2.00831368E+52 | 2.32443713E+47 | 6.36396202E+44 |
| AES-192 | uniform_expected | 2.00831368E+52 | 2.32443713E+47 | 6.36396202E+44 |
| AES-256 | full | 7.40936969E+71 | 8.57565937E+66 | 2.34788758E+64 |
| AES-256 | half | 3.70468485E+71 | 4.28782968E+66 | 1.17394379E+64 |
| AES-256 | uniform_expected | 3.70468485E+71 | 4.28782968E+66 | 1.17394379E+64 |
