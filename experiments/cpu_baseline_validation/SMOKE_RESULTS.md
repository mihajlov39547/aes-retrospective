# Local readiness report — 2026-10-27

Implemented and smoke-tested on this Windows host through Ubuntu 24.04 WSL2,
Linux x86-64 (`6.6.87.2-microsoft-standard-WSL2`). This is Linux validation, not
native Windows validation. Compiler: GCC 13.3.0, `-O3 -std=c11 -Wall -Wextra
-Werror -fPIC -shared`. Loaded OpenSSL: 3.0.13; PyCryptodome: 3.23.0; Python: 3.12.3.
CPUID reported AES availability. Executed instructions were not traced.

Final verification:

* Native shared-library build passed with warnings treated as errors.
* All **8 automated tests passed** (7.131 seconds in the final run).
* Both implementations passed **37 correctness cases each**, including NIST
  ECB/CTR vectors, partial CTR blocks, counter carries, and all five study sizes.
* Numerical tests covered warmup exclusion, retained outliers, speedup below one,
  distinct paired-ratio/ratio-of-medians calculations, multicore envelopes, and
  rejection of incomplete, duplicate, mixed-session and invalid measurements.
* End-to-end single-thread and two-worker smoke tests passed, checking metadata,
  CSV row counts, actual execution order and summaries.
* Separate retained smoke outputs have complete status: 24 single-thread raw
  rows and 48 two-worker raw rows (warmups included), eight summary configurations
  each. No full study session was executed.
* Windows Python source compilation and PowerShell script parsing passed.

Retained local artifacts (ignored by Git):

* `results/single-smoke-2003-82c5c1e9-4911-45e2-81b3-1ffc40fa6b1e/`
* `results/multicore-smoke-2003-906f9515-9862-416d-8b3c-227ecf4e33c2/`

The Linux x86-64 implementation is ready for a deliberately launched study in
the tested environment. The Windows MSVC/OpenSSL development build and Linux
ARM64 capability-mask control are implemented but need their platform-local
build and smoke gate before study execution. Colab also needs its local gate.
This host had no usable MSVC compiler on PATH; its Git OpenSSL runtime alone
does not provide the development headers/import library required for the build.
No CPU performance conclusion or revised CUDA speedup is drawn from smoke data.
