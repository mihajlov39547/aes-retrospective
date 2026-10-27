# Timing comparability and historical evidence

The historical **4.761×** is reproducible from the authoritative T4 archive:
`4.761336931964933`, the median of five session ratios
`median(PyCryptodome AES-NI time) / median(baseline CUDA pipeline time)` at 32 MiB
CTR. It refers to **baseline CUDA**, not optimized-v1. The same archive gives
4.7247172456022914 when using the median of five session medians of per-repetition
ratios. These are different estimators, not contradictory data. The new framework
reports both, explicitly labelled. `review_existing.py` independently checks these
values by reading the archive without extraction or mutation.

The inspected archive is
`experiments/results_orchestrated/t4-colab/heterogeneous-core-v1-20261014T105540691660Z-9bb918a84386.tar.gz`,
SHA-256 `1104a0dd49cc13949e993bb2ef70204a390ee393d3e9777d47297937a65f4c6b`.
All five archived baseline and optimized CUDA sources match the reused current
files byte-for-byte. Archived GPU metadata reports Tesla T4, CC7.5, CUDA runtime
13.0, driver API version 13000 and CuPy 14.0.1; library metadata reports PyCryptodome
4.0.0 and Python 3.13.15. These are **recorded historical values**, not assumptions
about a new Colab runtime. Its simple `cpu` metadata field is `x86_64`; the new
collector explicitly records `/proc/cpuinfo` model and flags as well as CPUID.

The five completed native Windows Phase 1 sessions (2026-10-27, seeds 2003–2007)
report i5-10300H-class AMD64, Python 3.12.10, OpenSSL 3.6.5, verified native DLL
bindings and separate CPU transform/operation fields. Oracle archives contain
five single-thread and five two-worker ARM64 study sessions with OpenSSL default
and armcap-zero control. Their operation envelopes expose allocation and copying
costs that are absent from native transform time. They informed this protocol,
but **none of those rows is imported into a Colab CPU–GPU pair**. An earlier
Windows-readiness report was superseded by these now-completed Windows sessions.

## Primary comparison

For a service with prepared input/output buffers and a prepared cipher key, compare
native OpenSSL EVP transformation to **H2D + CUDA kernel + D2H + synchronization**.
The CPU input is already host resident; the GPU must move that host input to the
device and return output to prepared pinned host memory. Both sides exclude input
generation, output-buffer allocation, cipher/key preparation, and validation.
This addresses whether native CPU transformation can compete with the existing
GPU prepared pipeline even after the GPU's required transfers are included.

It is a **declared prepared-buffer comparison, not identical call boundaries**:
OpenSSL's interval is inside C and excludes ctypes entry; PyCryptodome includes
its Python method and internal FFI; the GPU pipeline includes host launch/event
and synchronization overhead. These choices expose an optimized native baseline
and the actual existing prepared pipeline, without correcting timings by estimated
FFI subtraction. Fixed comparison labels retain those differences. Claiming
equivalent Python/native/GPU API overhead would require another matched native
driver implementation; this experiment deliberately does not change the CUDA
algorithm or timing driver to obtain that match.

The original CPU interval allocated its output but excluded cipher construction.
It is therefore **neither** the new preallocated CPU transform interval **nor**
the full CPU operation envelope. The historical GPU resident and pipeline methods
are reused exactly at one resident iteration, so their scope definitions match,
but hardware, software, cache/preparation schedules and actual inputs may differ.
The old harness generated new messages/keys per repetition; the CPU Phase 1 design
replays one deterministic seed/size message. Historical size order was fixed;
the new size order is randomized. Old/new timing distributions are not paired.

## Allocation, copying, transfers, and secondary ratios

The CPU operation envelope is measured around the same `measure` call/assignment
as Phase 1: checks, fresh zeroed output, bindings, no-op FFI probe where applicable,
fresh cipher/key setup, encryption, cleanup, conversion to bytes, local releases
and replacement of the prior CPU result. Those extra costs remain visible beside
transform time. Raw diagnostics isolate allocation, setup and native outer-call
costs; the residual cannot be asserted to be pure copy time. Previous-result
lifetime/order effects remain a limitation, even though the timestamp placement
is unchanged. GPU result conversion/checking occurs outside GPU timers.

GPU preparation allocates device buffers and pinned host buffers, copies the
plaintext into staging memory, expands/uploads the key and uploads the counter.
All occur before GPU timing. The transfer-inclusive pipeline **is not a complete
application operation envelope**: it excludes those allocation/staging/setup
costs. CPU-operation / GPU-pipeline ratios are deliberately marked asymmetric;
they do not establish an allocation-inclusive end-to-end application speedup.

H2D/D2H intervals include their synchronous host-call/synchronization costs, not
just PCIe wire time. The embedded CUDA event interval is diagnostic and is never
substituted for pipeline completion. Resident launch time excludes transfers and
is labelled compute-only. No resident ratio is used for an end-to-end claim.
Pinned host memory, warm reused buffers, library caches and sequential validation
can affect memory/cache state. No cold-cache or streaming-input claim is made.

## Interpretation limits

The kernel itself is unchanged; an improved CPU reference can change relative
performance without showing that an earlier measurement was incorrect. To say
whether the GPU remains competitive, inspect the **new same-runtime** OpenSSL/
baseline-CUDA prepared-pipeline ratios, all five session estimates and their
directional consistency. Discuss allocation-envelope and resident observations
separately. The historical 4.761 number is context, not a null hypothesis or a
paired observation in a new runtime. Avoid selecting a favorable size/kernel/
estimator after seeing the results.

CPUID AES, Linux flags and OpenSSL's effective AES capability bit establish
availability and allowed dispatch. Actual AES-NI instruction execution is not
traced. CPU/compiler/library differences, OpenSSL assembly dispatch, cloud
contention, scheduling, DVFS, temperatures and Colab runtime lifetime remain
uncontrolled variables. Runtime fingerprint checks catch observable identity/
version changes, not host contention or hidden VM migration. The primary CPU
is one calling thread; the comparison does not claim the GPU uses equal hardware
resources or that a multicore CPU would have the same result. Five sessions
support descriptive consistency estimates, not universal hardware claims.
