# Avalanche diffusion demonstration

Diffusion indicator, normalized by block size; not a proof of cryptographic security or a complete SAC test.
CPU software AES; DES/TDEA odd parity, one effective bit; ECB single block.
Each sample draws a fresh key/plaintext; both variants share that pair.
No timing or security ranking. Percentiles use linear interpolation (n-1)*p.
Raw status is accepted; invalid TDEA proposals are retried and recorded in metadata, not silently skipped.
TDEA audit (initial and changed proposals): {"generated": 4000, "rejected": 0, "accepted": 4000, "rejections": []}

| Algorithm | Variant | Count | Mean bits | Median bits | SD bits | Mean normalized |
|---|---|---:|---:|---:|---:|---:|
| DES | plaintext_bit_flip | 2000 | 32.02 | 32 | 4.020830422766462 | 0.5004 |
| DES | key_bit_flip | 2000 | 32.05 | 32 | 4.061384791325689 | 0.5008 |
| TDEA | plaintext_bit_flip | 2000 | 32.08 | 32 | 4.079230296257488 | 0.5012 |
| TDEA | key_bit_flip | 2000 | 31.89 | 32 | 4.016066750699375 | 0.4983 |
| AES-128 | plaintext_bit_flip | 2000 | 64.08 | 64 | 5.66032186556656 | 0.5006 |
| AES-128 | key_bit_flip | 2000 | 64.2 | 64 | 5.4958708179890845 | 0.5015 |
| AES-192 | plaintext_bit_flip | 2000 | 63.95 | 64 | 5.641290262689375 | 0.4996 |
| AES-192 | key_bit_flip | 2000 | 64.1 | 64 | 5.773202116792783 | 0.5008 |
| AES-256 | plaintext_bit_flip | 2000 | 64.14 | 64 | 5.591792026625679 | 0.5011 |
| AES-256 | key_bit_flip | 2000 | 63.83 | 64 | 5.629856716056072 | 0.4987 |

An idealized 0.5 center is not evidence of security; finite samples and correlated variants do not establish SAC or independence of output bits.
DES/TDEA are legacy algorithms; no recommendation for modern protection. Synthetic seeded keys are not production keys.
