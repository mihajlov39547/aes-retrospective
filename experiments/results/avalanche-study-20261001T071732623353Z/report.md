# Avalanche diffusion demonstration

Diffusion indicator, normalized by block size; not a proof of cryptographic security or a complete SAC test.
CPU software AES; DES/TDEA odd parity, one effective bit; ECB single block.
Each sample draws a fresh key/plaintext; both variants share that pair.
No timing or security ranking. Percentiles use linear interpolation (n-1)*p.
Raw status is accepted; invalid TDEA proposals are retried and recorded in metadata, not silently skipped.
TDEA audit (initial and changed proposals): {"generated": 4000, "rejected": 0, "accepted": 4000, "rejections": []}

| Algorithm | Variant | Count | Mean bits | Median bits | SD bits | Mean normalized |
|---|---|---:|---:|---:|---:|---:|
| DES | plaintext_bit_flip | 2000 | 32.02 | 32 | 4.024581515908094 | 0.5003 |
| DES | key_bit_flip | 2000 | 31.9 | 32 | 3.9661882613741786 | 0.4985 |
| TDEA | plaintext_bit_flip | 2000 | 31.99 | 32 | 4.005742626154793 | 0.4999 |
| TDEA | key_bit_flip | 2000 | 32.02 | 32 | 4.049462535128792 | 0.5004 |
| AES-128 | plaintext_bit_flip | 2000 | 63.97 | 64 | 5.631132441728586 | 0.4998 |
| AES-128 | key_bit_flip | 2000 | 63.91 | 64 | 5.601034350269283 | 0.4993 |
| AES-192 | plaintext_bit_flip | 2000 | 64.04 | 64 | 5.661839649275406 | 0.5003 |
| AES-192 | key_bit_flip | 2000 | 64.09 | 64 | 5.616695058634646 | 0.5007 |
| AES-256 | plaintext_bit_flip | 2000 | 63.88 | 64 | 5.653669758738163 | 0.499 |
| AES-256 | key_bit_flip | 2000 | 64 | 64 | 5.660610303183063 | 0.5 |

An idealized 0.5 center is not evidence of security; finite samples and correlated variants do not establish SAC or independence of output bits.
DES/TDEA are legacy algorithms; no recommendation for modern protection. Synthetic seeded keys are not production keys.
