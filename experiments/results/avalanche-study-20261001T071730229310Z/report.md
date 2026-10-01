# Avalanche diffusion demonstration

Diffusion indicator, normalized by block size; not a proof of cryptographic security or a complete SAC test.
CPU software AES; DES/TDEA odd parity, one effective bit; ECB single block.
Each sample draws a fresh key/plaintext; both variants share that pair.
No timing or security ranking. Percentiles use linear interpolation (n-1)*p.
Raw status is accepted; invalid TDEA proposals are retried and recorded in metadata, not silently skipped.
TDEA audit (initial and changed proposals): {"generated": 4000, "rejected": 0, "accepted": 4000, "rejections": []}

| Algorithm | Variant | Count | Mean bits | Median bits | SD bits | Mean normalized |
|---|---|---:|---:|---:|---:|---:|
| DES | plaintext_bit_flip | 2000 | 32.06 | 32 | 4.0270711939572905 | 0.5009 |
| DES | key_bit_flip | 2000 | 31.94 | 32 | 4.048306824349167 | 0.499 |
| TDEA | plaintext_bit_flip | 2000 | 31.97 | 32 | 4.077246830995204 | 0.4995 |
| TDEA | key_bit_flip | 2000 | 31.98 | 32 | 4.090334511773958 | 0.4996 |
| AES-128 | plaintext_bit_flip | 2000 | 63.9 | 64 | 5.750454035187604 | 0.4992 |
| AES-128 | key_bit_flip | 2000 | 63.99 | 64 | 5.59683824128852 | 0.4999 |
| AES-192 | plaintext_bit_flip | 2000 | 63.7 | 64 | 5.655509892668657 | 0.4977 |
| AES-192 | key_bit_flip | 2000 | 64.12 | 64 | 5.593639615856213 | 0.5009 |
| AES-256 | plaintext_bit_flip | 2000 | 64.22 | 64 | 5.7495466250128455 | 0.5017 |
| AES-256 | key_bit_flip | 2000 | 64.07 | 64 | 5.735626182366833 | 0.5006 |

An idealized 0.5 center is not evidence of security; finite samples and correlated variants do not establish SAC or independence of output bits.
DES/TDEA are legacy algorithms; no recommendation for modern protection. Synthetic seeded keys are not production keys.
