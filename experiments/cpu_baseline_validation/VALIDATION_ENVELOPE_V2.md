# Operation-envelope extension validation — 2026-10-27

No full benchmark campaign was launched. AES C code, input generation, cipher
semantics, existing component timers and the worker start/end timer placement
are unchanged. Raw schema 2 adds explicit operation duration/throughput fields;
summary schema 2 separates operation-envelope and per-worker transform rows.

## Passed

* Ubuntu WSL2 x86-64 shared-library compilation (GCC 13.3.0; warnings as errors).
* **14 automated tests**, final run 7.168 s, including both implementations' 37
  correctness cases (NIST ECB/CTR, counter carries, partial blocks, all five sizes).
* Envelope integer arithmetic, independent boundary pairing, one-/two-worker
  equivalent boundaries, per-worker versus aggregate byte counts, warmup exclusion,
  negative speedups, retained outliers, malformed/incomplete sample rejection,
  legacy read-only export and refusal to overwrite historical summaries.
* End-to-end single-thread and two-worker smoke pipelines with schema-2 fields.
* Windows native Python: nine numerical regression tests and one PE/IAT loader
  test passed; PyCryptodome passed all 37 correctness cases. The loader test uses
  synthetic PE memory and mocked module APIs; it is not a real DLL-binding proof.
* Oracle archives reanalyzed read-only: 13 unique sessions, including ten study
  sessions. All raw session count/pairing/envelope consistency checks passed.
  Archive SHA-256 hashes were unchanged after analysis. No Oracle raw records or
  existing summaries were rewritten; no ARM64 benchmark was rerun.

Separate retained local WSL2 smoke outputs (not Windows performance results):

* `results/single-smoke-2003-aa2cab8e-3e9f-4ea4-bcb3-b58421631b52/`: complete,
  24 raw rows including warmups, 16 boundary-specific summary rows.
* `results/multicore-smoke-2003-ad4a489b-ca08-411a-b97b-784596815c44/`: complete,
  48 raw worker rows including warmups, 24 summary rows (two transform workers
  plus one aggregate envelope per configuration).

These local runs used Python 3.12.3, PyCryptodome 3.23.0, OpenSSL 3.0.13 and Linux
6.6.87.2-microsoft-standard-WSL2. New Native metadata is outside all measured scopes.
The original `SMOKE_RESULTS.md` and old result directories were retained.

## Native Windows gate remains pending

`windows_readiness.ps1` and the smoke-mode `run_windows.ps1` were executed on the
i5-10300H. The launcher stopped before compilation because the MSVC x64 C++
toolset, Windows SDK development files and OpenSSL 3 development installation
are absent. It did not fall back to WSL or a runtime-only Git DLL.

Native Windows wrapper compilation, real resolved-IAT path/hash verification,
native EVP NIST checks and smoke timings therefore remain **unverified**, not
passed. Install only those missing components and execute the commands in
[WINDOWS_READINESS.md](WINDOWS_READINESS.md). That launcher gates the future
single-thread study on compilation, actual DLL provenance, correctness and smoke.
New ARM64 execution also needs its local smoke gate; the native C implementation
and pre-start capability control are unchanged, and historical ARM64 data pass
the new schema-1 reanalysis path.

The SJEE manuscript, historical experiments and completed Oracle archives were
not changed. The pre-existing user edit to repository-root `.gitignore` was left
untouched.
