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

Multicore results measure synchronized independent processes, including allocation,
setup, wrappers and copying in an operation envelope. They are kept separate from
single-thread transform results. Scheduling skew, frequency scaling, memory
bandwidth and virtual-machine contention are not eliminated. There is no CPU
pinning or thermal/governor control; record conditions and preserve all outliers.
Five seeded sessions are repeated measurements on one machine, not independent
hardware samples; do not pool repetitions to exaggerate the replication count.

Reference API semantics: [PyCryptodome CTR](https://www.pycryptodome.org/src/cipher/classic#ctr-mode)
and [OpenSSL EVP encryption](https://docs.openssl.org/3.0/man3/EVP_EncryptInit/).
