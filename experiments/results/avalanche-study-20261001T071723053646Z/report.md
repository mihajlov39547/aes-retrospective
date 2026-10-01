# Avalanche diffusion demonstration

Diffusion indicator, normalized by block size; not a proof of cryptographic security or a complete SAC test.
CPU software AES; DES/TDEA odd parity, one effective bit; ECB single block.
Each sample draws a fresh key/plaintext; both variants share that pair.
No timing or security ranking. Percentiles use linear interpolation (n-1)*p.
Raw status is accepted; invalid TDEA proposals are retried and recorded in metadata, not silently skipped.
TDEA audit (initial and changed proposals): {"generated": 4000, "rejected": 0, "accepted": 4000, "rejections": []}

| Algorithm | Variant | Count | Mean bits | Median bits | SD bits | Mean normalized |
|---|---|---:|---:|---:|---:|---:|
| DES | plaintext_bit_flip | 2000 | 31.96 | 32 | 3.939367850243204 | 0.4994 |
| DES | key_bit_flip | 2000 | 31.88 | 32 | 3.9785879820817818 | 0.4981 |
| TDEA | plaintext_bit_flip | 2000 | 31.97 | 32 | 3.986113840794802 | 0.4995 |
| TDEA | key_bit_flip | 2000 | 32.04 | 32 | 4.020660873156111 | 0.5006 |
| AES-128 | plaintext_bit_flip | 2000 | 64 | 64 | 5.564348905251151 | 0.5 |
| AES-128 | key_bit_flip | 2000 | 64.05 | 64 | 5.60761283086042 | 0.5004 |
| AES-192 | plaintext_bit_flip | 2000 | 64.03 | 64 | 5.594496666052563 | 0.5002 |
| AES-192 | key_bit_flip | 2000 | 63.87 | 64 | 5.611583460527628 | 0.499 |
| AES-256 | plaintext_bit_flip | 2000 | 63.98 | 64 | 5.545430542342945 | 0.4998 |
| AES-256 | key_bit_flip | 2000 | 64.06 | 64 | 5.7424265542857125 | 0.5004 |

An idealized 0.5 center is not evidence of security; finite samples and correlated variants do not establish SAC or independence of output bits.
DES/TDEA are legacy algorithms; no recommendation for modern protection. Synthetic seeded keys are not production keys.
