# Avalanche diffusion protocol

## Scope and review

The existing avalanche_test.py supported DES, three-key TDEA and AES-128/192/256,
plaintext and key flips, LSB-first indexing and mean/median/sample SD/min/max.
It excluded DES parity bits but silently rejected initial TDEA key candidates
through common.key_for. Changed keys were tested only for library rejection,
which permits the two-key K1=K3 case. There was no validation gate, percentile
export, source snapshot or validation/report artifact.

The revised script remains a single-block ECB demonstration, not a throughput
benchmark or a complete strict avalanche criterion (SAC) test. AES uses explicit
software dispatch use_aesni=False. No instruction trace or AES-NI measurement is
claimed. DES/TDEA are legacy algorithms, not recommendations for protection.
Double-DES MITM is omitted from this experimental workflow; it remains optional
future-work context only.

## Sampling and effective bits

Each sample draws a new seeded random plaintext block and key. Both variants
share that original pair when requested together. Plaintext flip selects one
uniform physical bit; key flip selects one uniform effective bit. Algorithms
run in CLI order, samples in ascending order, variants in CLI order. Repeating
all arguments reproduces the sample sequence; changing selected groups changes
RNG consumption. Keys are synthetic, not production secrets.

Blocks: DES/TDEA 64 bits, AES 128 bits. Effective key representation lengths:
DES 56, three-key TDEA 168, AES 128/192/256. These lengths are not security-strength
claims. Bit indices are physical LSB-first indices within the key or block;
DES/TDEA indices divisible by eight are parity and never selected. Odd parity
is restored after a key flip. Consequently two representation bits may change
(one effective and one parity), but exactly one effective bit changes.

All three TDEA effective 8-byte components must be distinct, initially and
after modification. Both initial proposals and changed-key proposals count
in metadata.method.tdea_candidates: generated, accepted, rejected, and a list
of rejection stage/sample/reason. These accepted counts include initial AND
modified keys, not unique original samples. Rejected changes are resampled;
this conditions the key-flip distribution on valid three-key TDEA. There is no
silent skip. A 1000-proposal limit aborts without statistics. Raw contains only
accepted samples, status=accepted, empty skip_reason; skipped_count is zero.
Rejections are audited separately and never counted as Hamming observations.

## Statistics and validation

Hamming distance counts XOR one-bits between ciphertext blocks; unequal lengths
are rejected. normalized_distance=distance/block_bits. Each algorithm/variant
summary has count, mean, median, sample SD, min, max, q05/q25/q75/q95 in bits and
mean/median/sample SD of normalized distance. Percentiles interpolate at (n-1)p
(type 7); sample SD is null for one observation. Raw data retain the full
empirical distribution; no outlier removal. An idealized center near 0.5 is a
diffusion indicator, not a security proof or a ranking of algorithms.

Before collecting study/pilot samples, persist validation.json and require
passed=true. Checks cover known distances, invalid lengths, cipher key/block
lengths, every single-bit mapping, DES/TDEA parity, duplicate TDEA components,
reproducibility, normalization, schema and percentile arithmetic. Validation
uses small synthetic samples outside the collected experiment. The isolated
smoke injects corruption and rejected TDEA proposals, checks gate ordering and
failure (no raw/summary), verifies summary statistics against raw and verifies
source/validation hashes. It performs no pilot or study.

Export: metadata.json, validation.json, raw.csv, summary.csv, report.md,
results.json and source/. Common metadata includes environment/library versions,
Git state, arguments and seed. Validation staging records are retained separately.
The new schema replaces the old change/hamming_bits/fraction fields; the legacy
omnibus smoke checker assumes that old schema. Use avalanche_smoke_check.py for
this experiment. No changes to common.py or unrelated scripts are required.

## Manual workflow, not an executed study

Without --run the command prints a plan only. --purpose must match --profile.
Default samples per algorithm/variant: smoke 8, pilot 200, study 2000.
Caps are smoke 20, pilot 500, study 10000; --trials remains an alias for
--samples-per-group. Duplicate algorithms/variants and nonpositive counts fail.

```powershell
.\.venv\Scripts\python.exe scripts\avalanche_smoke_check.py
.\.venv\Scripts\python.exe scripts\avalanche_test.py --run --profile pilot --purpose pilot --algorithms DES TDEA AES-128 AES-192 AES-256 --variants plaintext key --samples-per-group 200 --seed 2003
```

Pilot: 2000 accepted rows, 10 summary groups. Inspect distributions, rejection
counts and artifact completeness; do not select a study design to force a 0.5
mean. Proposed study, only after pilot review and approval: five independent
processes with seeds 2003--2007, 2000 samples per algorithm/variant, 20000 rows
per session. Lock this choice before study. Preserve session identity; show
per-session distributions/statistics and predefine any across-session summary.
Variants share input/key samples and are not statistically independent replicas.

Limitations: finite seeded sampling, conditional TDEA rejection, single-block
ECB only, no round-by-round diffusion, no full SAC matrix, no bit-independence
assessment and no cryptanalytic or side-channel security conclusion. A small
sample deviation from 0.5 is not evidence of a practical attack. No final LaTeX
results are produced in this preparation step.
