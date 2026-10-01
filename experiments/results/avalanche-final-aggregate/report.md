# Final avalanche distribution aggregate

Median across five session summaries separately for each statistic: session means, medians, sample SDs and type-7 quantiles. No raw pooling or outlier removal.

## Accepted study sessions
- Seed 2003: avalanche-study-20261001T071723053646Z; validation PASS; 20000 raw rows; 10 groups.
- Seed 2004: avalanche-study-20261001T071725373676Z; validation PASS; 20000 raw rows; 10 groups.
- Seed 2005: avalanche-study-20261001T071727768343Z; validation PASS; 20000 raw rows; 10 groups.
- Seed 2006: avalanche-study-20261001T071730229310Z; validation PASS; 20000 raw rows; 10 groups.
- Seed 2007: avalanche-study-20261001T071732623353Z; validation PASS; 20000 raw rows; 10 groups.

100000 accepted Hamming observations; 10000 per algorithm/variant across five sessions. Paired variants share the original key/plaintext; observations are not all independent.
All validation/file/source hashes verified; archived sources consistent across sessions. Summary means, medians, SDs, min/max and type-7 percentiles verified against raw without running any encryption.
TDEA totals (initial and modified proposals): {"generated": 20000, "accepted": 20000, "rejected": 0}
Degenerate candidates are forbidden and audited. No proposals were rejected in these study runs; the guard remained active. Accepted proposal count is not the number of unique initial keys.
ECB single block without padding; odd DES/TDEA parity restored after effective-bit flip; three distinct effective TDEA components. AES software use_aesni=False.

| Algorithm | Variant | Mean bits | Median bits | Q05 | Q25 | Q75 | Q95 | Mean normalized |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| DES | plaintext_bit_flip | 32.0185 | 32 | 25 | 29 | 35 | 39 | 0.50028906 |
| DES | key_bit_flip | 31.9375 | 32 | 25 | 29 | 35 | 38.05 | 0.49902344 |
| TDEA | plaintext_bit_flip | 31.9710 | 32 | 25 | 29 | 35 | 39 | 0.49954688 |
| TDEA | key_bit_flip | 32.0235 | 32 | 25 | 29 | 35 | 39 | 0.50036719 |
| AES-128 | plaintext_bit_flip | 63.9865 | 64 | 55 | 60 | 68 | 73 | 0.49989453 |
| AES-128 | key_bit_flip | 63.9920 | 64 | 55 | 60 | 68 | 73 | 0.49993750 |
| AES-192 | plaintext_bit_flip | 64.0275 | 64 | 55 | 60 | 68 | 73 | 0.50021484 |
| AES-192 | key_bit_flip | 64.0895 | 64 | 55 | 60 | 68 | 73 | 0.50069922 |
| AES-256 | plaintext_bit_flip | 63.9760 | 64 | 55 | 60 | 68 | 73 | 0.49981250 |
| AES-256 | key_bit_flip | 63.9965 | 64 | 55 | 60 | 68 | 73 | 0.49997266 |

Median normalized distance is 0.5 in all groups. Fractional DES key Q95 is type-7 interpolation, not a fractional observed bit count.
Each reported mean is the median of session means, not a pooled mean; each reported percentile is the median of session percentiles, not a pooled quantile.
Finite seeded single-block samples provide one diffusion indicator, not a security ranking or a complete SAC/BIC test. No formal binomial goodness-of-fit test was performed. No linear/differential cryptanalysis or mode-security evaluation is implied; ECB is not a protection recommendation.
Double-DES MITM study omitted; it would require a separate time/memory/false-positive protocol.
No new experiments, benchmark changes or prior-result edits. results.json was not needed.
