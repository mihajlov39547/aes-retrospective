# Educational reduced-keyspace exhaustive search demonstration

Purpose: study; CPU software AES-128, ECB, fixed two-block plaintext.
Actually searched: 24 variable bits, 16777216 candidates; upper key bits zero.
Each row measures a stop-on-match search; end targets traverse the entire reduced space.

| Scenario | Median candidates | Median seconds | Median candidates/s |
|---|---:|---:|---:|
| start | 1 | 8.5e-06 | 117647 |
| middle | 8388609 | 54.3786 | 154263 |
| end | 16777216 | 111.331 | 150697 |
| random | 6922757 | 45.23 | 153057 |

Extrapolation rate: 150697 candidates/s from end median repeat rate.
Start and short searches are overhead-sensitive; partial-scan projections are not measured full scans.
Full=N/r; half=N/(2r); exact uniform first-hit expectation=(N+1)/(2r).
No pooling of positions or automatic outlier deletion. Year=365.25 days.
Linear extrapolation under fixed-rate assumption, not an implementation of full-space search; not a cryptanalytic attack evaluation. AES/Python candidate rate is not DES/TDEA or GPU search rate.
Double-DES nominal 112 bits has MITM alternatives. TDEA nominal 168 bits is not a security-strength claim.
Software/native library and Python setup dominate this workload; fixed-key CUDA MB/s cannot be converted into candidate-check rate.

| Space | Extent | Seconds | Days | Years |
|---|---|---:|---:|---:|
| DES | full | 4.78160957E+11 | 5.53427034E+6 | 1.51520064E+4 |
| DES | half | 2.39080479E+11 | 2.76713517E+6 | 7.57600320E+3 |
| DES | uniform_expected | 2.39080479E+11 | 2.76713517E+6 | 7.57600320E+3 |
| Double-DES nominal | full | 3.44551282E+28 | 3.98786206E+23 | 1.09181713E+21 |
| Double-DES nominal | half | 1.72275641E+28 | 1.99393103E+23 | 5.45908563E+20 |
| Double-DES nominal | uniform_expected | 1.72275641E+28 | 1.99393103E+23 | 5.45908563E+20 |
| Three-key TDEA nominal | full | 2.48275364E+45 | 2.87355745E+40 | 7.86737153E+37 |
| Three-key TDEA nominal | half | 1.24137682E+45 | 1.43677873E+40 | 3.93368576E+37 |
| Three-key TDEA nominal | uniform_expected | 1.24137682E+45 | 1.43677873E+40 | 3.93368576E+37 |
| AES-128 | full | 2.25805128E+33 | 2.61348528E+28 | 7.15533272E+25 |
| AES-128 | half | 1.12902564E+33 | 1.30674264E+28 | 3.57766636E+25 |
| AES-128 | uniform_expected | 1.12902564E+33 | 1.30674264E+28 | 3.57766636E+25 |
| AES-192 | full | 4.16536940E+52 | 4.82102940E+47 | 1.31992591E+45 |
| AES-192 | half | 2.08268470E+52 | 2.41051470E+47 | 6.59962957E+44 |
| AES-192 | uniform_expected | 2.08268470E+52 | 2.41051470E+47 | 6.59962957E+44 |
| AES-256 | full | 7.68375034E+71 | 8.89322956E+66 | 2.43483355E+64 |
| AES-256 | half | 3.84187517E+71 | 4.44661478E+66 | 1.21741678E+64 |
| AES-256 | uniform_expected | 3.84187517E+71 | 4.44661478E+66 | 1.21741678E+64 |
