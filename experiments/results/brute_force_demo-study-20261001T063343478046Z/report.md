# Educational reduced-keyspace exhaustive search demonstration

Purpose: study; CPU software AES-128, ECB, fixed two-block plaintext.
Actually searched: 24 variable bits, 16777216 candidates; upper key bits zero.
Each row measures a stop-on-match search; end targets traverse the entire reduced space.

| Scenario | Median candidates | Median seconds | Median candidates/s |
|---|---:|---:|---:|
| start | 1 | 9.2e-06 | 108696 |
| middle | 8388609 | 54.656 | 153480 |
| end | 16777216 | 109.011 | 153903 |
| random | 2389649 | 15.4064 | 154598 |

Extrapolation rate: 153903 candidates/s from end median repeat rate.
Start and short searches are overhead-sensitive; partial-scan projections are not measured full scans.
Full=N/r; half=N/(2r); exact uniform first-hit expectation=(N+1)/(2r).
No pooling of positions or automatic outlier deletion. Year=365.25 days.
Linear extrapolation under fixed-rate assumption, not an implementation of full-space search; not a cryptanalytic attack evaluation. AES/Python candidate rate is not DES/TDEA or GPU search rate.
Double-DES nominal 112 bits has MITM alternatives. TDEA nominal 168 bits is not a security-strength claim.
Software/native library and Python setup dominate this workload; fixed-key CUDA MB/s cannot be converted into candidate-check rate.

| Space | Extent | Seconds | Days | Years |
|---|---|---:|---:|---:|
| DES | full | 4.68200251E+11 | 5.41898438E+6 | 1.48363707E+4 |
| DES | half | 2.34100125E+11 | 2.70949219E+6 | 7.41818533E+3 |
| DES | uniform_expected | 2.34100125E+11 | 2.70949219E+6 | 7.41818533E+3 |
| Double-DES nominal | full | 3.37373836E+28 | 3.90478977E+23 | 1.06907317E+21 |
| Double-DES nominal | half | 1.68686918E+28 | 1.95239488E+23 | 5.34536587E+20 |
| Double-DES nominal | uniform_expected | 1.68686918E+28 | 1.95239488E+23 | 5.34536587E+20 |
| Three-key TDEA nominal | full | 2.43103469E+45 | 2.81369756E+40 | 7.70348407E+37 |
| Three-key TDEA nominal | half | 1.21551735E+45 | 1.40684878E+40 | 3.85174204E+37 |
| Three-key TDEA nominal | uniform_expected | 1.21551735E+45 | 1.40684878E+40 | 3.85174204E+37 |
| AES-128 | full | 2.21101317E+33 | 2.55904302E+28 | 7.00627795E+25 |
| AES-128 | half | 1.10550659E+33 | 1.27952151E+28 | 3.50313898E+25 |
| AES-128 | uniform_expected | 1.10550659E+33 | 1.27952151E+28 | 3.50313898E+25 |
| AES-192 | full | 4.07859941E+52 | 4.72060117E+47 | 1.29243016E+45 |
| AES-192 | half | 2.03929971E+52 | 2.36030058E+47 | 6.46215081E+44 |
| AES-192 | uniform_expected | 2.03929971E+52 | 2.36030058E+47 | 6.46215081E+44 |
| AES-256 | full | 7.52368795E+71 | 8.70797216E+66 | 2.38411284E+64 |
| AES-256 | half | 3.76184397E+71 | 4.35398608E+66 | 1.19205642E+64 |
| AES-256 | uniform_expected | 3.76184397E+71 | 4.35398608E+66 | 1.19205642E+64 |
