# Avalanche diffusion demonstration

Diffusion indicator, normalized by block size; not a proof of cryptographic security or a complete SAC test.
CPU software AES; DES/TDEA odd parity, one effective bit; ECB single block.
Each sample draws a fresh key/plaintext; both variants share that pair.
No timing or security ranking. Percentiles use linear interpolation (n-1)*p.
Raw status is accepted; invalid TDEA proposals are retried and recorded in metadata, not silently skipped.
TDEA audit (initial and changed proposals): {"generated": 4000, "rejected": 0, "accepted": 4000, "rejections": []}

| Algorithm | Variant | Count | Mean bits | Median bits | SD bits | Mean normalized |
|---|---|---:|---:|---:|---:|---:|
| DES | plaintext_bit_flip | 2000 | 31.91 | 32 | 3.9976901785132988 | 0.4986 |
| DES | key_bit_flip | 2000 | 32.05 | 32 | 3.975409027819557 | 0.5007 |
| TDEA | plaintext_bit_flip | 2000 | 31.97 | 32 | 4.032051397146943 | 0.4995 |
| TDEA | key_bit_flip | 2000 | 32.05 | 32 | 4.0368228806184625 | 0.5007 |
| AES-128 | plaintext_bit_flip | 2000 | 63.99 | 64 | 5.653520929425284 | 0.4999 |
| AES-128 | key_bit_flip | 2000 | 63.86 | 64 | 5.760263020473329 | 0.4989 |
| AES-192 | plaintext_bit_flip | 2000 | 64.15 | 64 | 5.5880643322612835 | 0.5012 |
| AES-192 | key_bit_flip | 2000 | 64.08 | 64 | 5.636953731731958 | 0.5007 |
| AES-256 | plaintext_bit_flip | 2000 | 63.8 | 64 | 5.706117211976846 | 0.4984 |
| AES-256 | key_bit_flip | 2000 | 63.85 | 64 | 5.547358433776963 | 0.4988 |

An idealized 0.5 center is not evidence of security; finite samples and correlated variants do not establish SAC or independence of output bits.
DES/TDEA are legacy algorithms; no recommendation for modern protection. Synthetic seeded keys are not production keys.
