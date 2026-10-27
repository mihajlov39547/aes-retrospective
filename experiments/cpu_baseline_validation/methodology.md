# Remaining comparability limitations

Phase 1 measures current implementations on the same host, not CPU performance
in the year of a historical CUDA report. A faster native CPU baseline can reduce
an apparent CUDA advantage, but these CPU-only data cannot establish a revised
CUDA speedup. That requires matched GPU runs, identical message semantics and
explicit matching of resident/kernel-only versus transfer-inclusive boundaries.
Historical Windows/CUDA data and new WSL, Colab, or Oracle data are not paired.
The SJEE manuscript remains unchanged pending this analysis.

PyCryptodome transform time includes Python dispatch and internal FFI; the EVP
transform interval is inside compiled C. Both use preallocated output, but the
boundaries are intentionally not declared equivalent. Setup includes different
library machinery and cached algorithm lookup. FFI no-op and residual values
are diagnostics, not corrections or isolated overhead measurements. Repeated
data and reference checks warm memory; this is not a streaming cold-cache study.

AES availability from CPUID/HWCAP and OpenSSL capability settings do not prove
the executed instruction stream. The ARM zero mask is a broad architectural
fallback control, not a selective AES toggle. Software-path naming does not
imply constant-time behavior. Library versions and build options can affect
dispatch, so they must accompany every result.

Both single-thread and multicore results now expose the same operation boundary:
Python wall timestamps immediately around `actual, metrics = measure(...)`.
It includes checks, allocation, bindings/no-op diagnostics where applicable,
setup, transform, cleanup, output conversion, local-object release and replacement
of the prior result at assignment. Single-thread uses end minus start; multicore
uses latest end minus earliest start and N times the bytes. This is an instrumented
operation envelope, not an uninstrumented application API or pure EVP transform.
Individual implementation machinery still differs within the common boundary.
The existing timing placement is unchanged, so schema-1 timestamps support a
read-only retrospective envelope derivation without new measurements.

Transform results remain separately labelled per worker; neither transform time
nor throughput is summed to represent aggregate completion. Ratios are computed
within a boundary/scope/worker and session. The Oracle single-thread and two-worker
campaigns are distinct sessions on the recorded same host; identical seed numbers
do not make them simultaneous paired trials. Their descriptive session-level
operation rates can be compared without treating different machines as paired or
claiming a causal estimate of scaling efficiency.

Overhead diagnosis uses the worker that finishes last: group envelope equals
that worker's duration plus its start lag from the earliest worker. For EVP,
non-overlapping recorded components are allocation + binding + no-op + native
call. The native call already includes setup/transform/cleanup/FFI residual.
Subtracting those components from the worker duration produces an uninstrumented
remainder, not a measured copy time. Input checks, result conversion, object
release, Python/timer bookkeeping and scheduling may contribute. Attribution
among them requires additional controlled profiling. Median components need not
sum to median elapsed time; decomposition is exact only per recorded sample.

Scheduling skew, frequency scaling, memory
bandwidth and virtual-machine contention are not eliminated. There is no CPU
pinning or thermal/governor control; record conditions and preserve all outliers.
Five seeded sessions are repeated measurements on one machine, not independent
hardware samples; do not pool repetitions to exaggerate the replication count.

Windows readiness is distinct from Linux/WSL validation. Native Windows loads
only an x64 PE wrapper and verifies resolved libcrypto import addresses against
the configured DLL's absolute path/hash before accepting measurements. Missing
MSVC/SDK/OpenSSL development components block the native gate. Mocked loader
tests and WSL smoke tests do not constitute native Windows EVP validation.

Reference API semantics: [PyCryptodome CTR](https://www.pycryptodome.org/src/cipher/classic#ctr-mode)
and [OpenSSL EVP encryption](https://docs.openssl.org/3.0/man3/EVP_EncryptInit/).
