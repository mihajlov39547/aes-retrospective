# CPU reduced-keyspace exhaustive search demonstration

This is an educational reduced-keyspace exhaustive search demonstration, not
an implementation of full-space search or a cryptanalytic attack evaluation.
No final study protocol or results are established by the smoke test.

## Implementation and measured workload

The existing `scripts/brute_force_demo.py` retains AES-128 ECB and a two-block
known plaintext/ciphertext check. It now uses a fixed 32-byte plaintext (first
two SP 800-38A example blocks) and explicit `use_aesni=False`, rather than an
automatic backend. It runs on CPU only. ECB is a candidate-check construction,
not a recommendation for protecting messages.

Candidate i maps to its 16-byte big-endian encoding. Only the low b bits vary;
all upper bits are zero. Candidates are visited in ascending order. Targets
are start=0, middle=N/2, end=N-1, or seeded uniform random, where N=2^b.
The CLI scenario order is preserved within each repeat; the RNG is initialized
once per session. The same fixed plaintext is used throughout. Matching both
blocks is followed by an untimed check of the recovered known index.

The wall timer is `perf_counter_ns`. It includes enumeration, candidate key
encoding, a fresh cipher and key schedule for every candidate, encryption of
both blocks, output allocation, comparison and stop-on-match control flow.
Target construction, validation, post-checks and export are outside the timer.
The validation gate primes the library; no separate performance warmup is used.
This measures the Python/native candidate-check implementation, not raw AES
bulk throughput. Previous CUDA fixed-key MB/s cannot be converted to this rate.

## Validation and audit

Before the first timed search, a persisted validation report must pass:
SP 800-38A F.1.1 AES-128 ECB KAT (first two blocks), key mapping, start/middle/end/
random targets in 1-, 4- and 8-bit spaces, exact candidate counts, complete
no-match scan, seed determinism, rate formulas and integer extrapolation sizes.
The no-match ciphertext is explicitly chosen outside the complete 8-bit output
set. A failed gate leaves only its validation record, without benchmark CSVs.
The isolated smoke additionally injects failures, checks gate-before-timer
ordering, exports, sample statistics and archived source hashes.

Successful runs export metadata, validation, raw/summary CSV, results JSON,
extrapolations CSV, report and source snapshots. Metadata records software and
hardware context, Git state, arguments, seed and validation SHA-256. Validation
staging records are retained separately. Raw rows are not filtered. Summary
statistics are count, mean, median, sample SD, min and max per target scenario.
All `expected_*_time` fields are seconds; they are projections, not additional
measured searches. Output schema differs from the old demo, whose summary held
only extrapolations; use the dedicated smoke check, not the old omnibus checker
which assumes that obsolete ten-row summary format.

## Extrapolation and interpretation

For rate r, full scan takes N/r; the approximate half-space time is N/(2r).
For a uniform successful target and counting its check, the exact expected
count is (N+1)/2. All three are separately exported. Spaces use exact integers
and Decimal arithmetic; displayed times use scientific notation and a
365.25-day year. Display precision is arithmetic, not measurement precision.

Use the median end-target rate for illustrations; never pool early-stop and
full-scan rates. If no end scenario was requested, the longest median checked
scenario is explicitly marked as a partial-scan extrapolation basis. A start
target checks latency and correctness and cannot establish sustained rate.

Illustrations include DES 2^56, nominal Double-DES 2^112, nominal three-key
TDEA 2^168 and AES-128/192/256. These assume the same measured AES-128/Python
rate purely mathematically. They are not measurements of DES, TDEA or other AES
key lengths. Double-DES admits meet-in-the-middle attacks; nominal TDEA key
space is not its security strength. No TDEA 112-bit attack model is benchmarked.
DES/TDEA are legacy constructions, not recommendations for modern protection.

Sources: [NIST SP 800-38A, F.1.1](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38a.pdf),
[NIST SP 800-57 Part 1](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-57p1.pdf),
[Handbook of Applied Cryptography, chapter 7, multiple encryption](https://cacr.uwaterloo.ca/hac/about/toc/toc7.html).

## Manual workflow

Without `--run`, the script prints a plan and performs no search or export.
Profile and purpose must match. Defaults: smoke 8 bits, pilot 20, study 24;
caps: smoke 12, pilot 22, study 28. Large spaces require explicit study profile
and are not time guarantees. `--bits` remains an alias for `--reduced-key-bits`.

```powershell
.\.venv\Scripts\python.exe scripts\brute_force_demo_smoke_check.py
.\.venv\Scripts\python.exe scripts\brute_force_demo.py --run --profile pilot --purpose pilot --algorithm AES-128 --mode ECB --reduced-key-bits 20 --target-position start middle end random --repeats 3 --seed 2003
```

The pilot is manual. Review duration and variance before choosing study bits.
A proposed later protocol uses five independent processes/seeds 2003--2007,
all four scenarios and at least three repeats, with one bit width locked before
study. Repeated random targets are samples, not guaranteed distinct keys.
Do not select positions according to measured speed. Aggregate session medians
separately by scenario; do not pool early-stop counts into sustained throughput.
Desktop scheduling, Python/native setup overhead and short-search resolution
limit interpretation. No LaTeX study results are produced at this stage.
