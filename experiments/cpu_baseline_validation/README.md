# Phase 1: native CPU baseline validation

This isolated experiment compares AES-128 ECB and CTR in PyCryptodome and a
compiled OpenSSL 3 EVP shared library. No historical source, result, or SJEE
manuscript is changed. **Smoke timings are not study results.** Phase 1 establishes
CPU performance; it does not by itself establish that any CUDA speedup survives.

Repository inspection: `scripts/benchmark.py` includes output allocation in its
Python transform boundary; `scripts/cpu_validation.py` gates with published KATs.
`scripts/aes_cuda_baseline.py`, `scripts/aes_cuda_cpu_gpu.py`, and
`experiments/cuda_optimized_cpu_gpu_protocol.md` use full 128-bit big-endian CTR,
reject wrap, distinguish resident and pipeline CUDA times, and retain negative
pilot outcomes. Existing `experiments/results/` stores separate sessions with raw
CSV, metadata, validation, and source snapshots. This experiment follows that
session convention without importing or modifying the historical harness.

## Requirements

* 64-bit Python 3.10+ (tested locally with 3.12), PyCryptodome 3.23.0 (only Python
  dependency), OpenSSL **3.x** headers and shared libcrypto, and a C compiler.
* Linux x86-64 or ARM64: GCC/compatible `cc`, `pkg-config`, `libssl-dev`, Python venv.
* Windows x86-64: MSVC x64 Build Tools / C++ workload and OpenSSL 3 x64 **development**
  installation, including `include/openssl`, `bin/libcrypto-3-x64.dll`, and
  `lib/VC/x64/MD/libcrypto.lib` or `lib/libcrypto.lib`. A runtime-only installation
  (e.g. Git's OpenSSL DLL) is insufficient. Use an x64 Developer PowerShell.
* Roughly 1 GiB free RAM for single-thread validation; budget several GiB for
  multicore runs. Each process keeps independent inputs, reference and output.
  No CUDA, NumPy, pandas, plotting package, or administrator rights at run time.
* Use one otherwise idle machine per campaign. Record power mode, virtualization,
  VM shape, physical/logical cores, competing load and thermal conditions in notes.

## Commands

All commands below start at the repository root. Scripts default to tests and a
smoke run only. `--study` / `-Study` is the explicit full-campaign switch. The
convenience scripts rebuild and pass correctness + single-thread smoke first.

Windows (native x86-64):

```powershell
./experiments/cpu_baseline_validation/run_windows.ps1 -OpenSSLRoot 'C:/OpenSSL-Win64'
# After reviewing smoke output, full SINGLE-thread study:
./experiments/cpu_baseline_validation/run_windows.ps1 -OpenSSLRoot 'C:/OpenSSL-Win64' -Study -Notes 'AC power; idle; native Windows'
# Separate multicore study, after single-thread study (choose a suitable worker count):
./experiments/cpu_baseline_validation/run_windows.ps1 -OpenSSLRoot 'C:/OpenSSL-Win64' -Study -Workers 4
```

Oracle Ubuntu 24.04 ARM64 (same commands work on Ubuntu x86-64):

```bash
sudo apt-get update
sudo apt-get install -y build-essential pkg-config libssl-dev python3-venv
bash experiments/cpu_baseline_validation/run_linux.sh
# Full SINGLE-thread study, only after reviewing smoke output:
bash experiments/cpu_baseline_validation/run_linux.sh --study --notes 'Oracle Ubuntu 24.04 ARM64; record VM shape and load'
# Separate multicore smoke, then study:
bash experiments/cpu_baseline_validation/run_linux.sh --workers 4
bash experiments/cpu_baseline_validation/run_linux.sh --study --workers 4
```

Google Colab, CPU runtime, repository checked out at `/content/aes` (not the
Windows path). In notebook cells:

```python
%cd /content/aes
!apt-get update -qq
!apt-get install -y -qq build-essential pkg-config libssl-dev python3-venv
!bash experiments/cpu_baseline_validation/run_linux.sh
# Run this separately AFTER reviewing the smoke gate:
!bash experiments/cpu_baseline_validation/run_linux.sh --study --notes 'Colab CPU runtime; shared host; record runtime identity'
```

Keep all five sessions on the same live Colab runtime; a reset or machine change
starts a new campaign. Download the entire `results/` directory before the runtime
expires. WSL is a Linux environment and must not be labelled a native Windows run.

Manual commands, from this directory, with dependencies installed:

```bash
python build.py                         # Windows: append --openssl-root PATH
python -m unittest discover -s . -v     # correctness + numerical tests
python run.py                          # 1/2 warmup/measured, 1 and 16 KiB, seed 2003
python run.py --workers 2              # separate multicore smoke
python run.py --study                  # five independent process sessions
python run.py --study --seed 2005       # one session, e.g. an independently launched replicate
python aggregate.py results/SINGLE_SESSION_DIRECTORY
```

Build artifacts are platform-specific; rebuild after switching OS, compiler, or
OpenSSL. The manifest records compiler command/version and native source/binary
hashes; the loader rejects changed C source or binary. Archive system package
versions alongside the output when reproducing an environment exactly.

## Fixed study design and validation

Study sessions use seeds **2003–2007**, **five warmups** and **twenty measured
repetitions** for every implementation/mode/size. Sizes are **1024, 16384,
1048576, 16777216, 33554432 bytes**. Sessions create fresh processes and contexts;
they are repeated sessions on one machine, not five independent machines.
The seed randomizes size order, mode order per size, and implementation order
within each warmup/measured round. `planned_order.json` records the schedule;
`execution_order.jsonl` records actual started/completed jobs, including warmups.
Input generation is independent of order: SHAKE-256 domain
`aes-phase1-v1:{seed}:{size}:{worker}:` plus `plaintext`, `key`, or `counter`.
The top counter bit is cleared to prevent wrap. Worker 0 is the single-thread
dataset; multicore worker indices produce distinct messages. Inputs are identical
across implementations for each pair. They stay fixed across repetitions to
measure a warm-cache, repeated-message workload. These keys/counters are synthetic
and their reuse is for benchmarking only.

CTR has an empty nonce and a 128-bit big-endian initial value; block zero uses that
initial value. ECB has no padding. Both implementations must pass the four-block
NIST SP 800-38A F.1.1/F.5.1 vectors, CTR partial blocks and carries at 8/32/64/96/120
bits, and equality at all five sizes. Every configuration passes another equality
gate before warmups. Every timed ciphertext is compared outside timing before
its row is written. Errors leave a failed/incomplete session; aggregation rejects
it. Published vectors come from [NIST SP 800-38A](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38a.pdf).

## Timing boundaries (nanoseconds)

| Raw field | PyCryptodome | Native OpenSSL |
|---|---|---|
| `allocation_ns` | `bytearray(n+16)` zero initialization | Identical Python allocation |
| `setup_ns` | `AES.new`, Python dispatch, CTR integer conversion and key setup | C timer around default-provider cipher fetch, context allocation, EVP init/key setup, disable padding |
| `transform_ns` | `cipher.encrypt(plain, output=preallocated_view)`: Python method, checks, internal FFI and native transform | C timer around `EVP_EncryptUpdate` + `EVP_EncryptFinal_ex`; no Python/ctypes entry |
| `cleanup_ns` | Python cipher deletion | C context/cipher frees |
| `buffer_binding_ns` | blank | ctypes objects/pointers and argument tuple construction (no input copy) |
| `native_call_ns` | blank | Python wall interval around complete C call: setup, transform, cleanup, native timers, ctypes entry/exit |
| `ffi_noop_ns` | blank | Same-signature C no-op call, Python wall interval; diagnostic proxy only |
| `ffi_residual_ns` | blank | Outer C-call time minus the three inner intervals; includes ctypes, native bookkeeping and timer calls; **not pure FFI** |

Neither transform includes output allocation, input/key generation, reference
encryption, ciphertext comparison, IPC, or output conversion to bytes. The
output-buffer pages are zeroed before transformation on both paths. No-op time
is never subtracted. PyCryptodome's internal FFI is not independently separable
through its public API. Native initialization is a fresh context per repetition,
but OpenSSL fetch/provider caches may be warm; this is not a pure key-schedule
microbenchmark. Timer reads have cost and small intervals have limited precision.

Single-thread throughput is `bytes * 1000 / transform_ns` in decimal MB/s. The
primary ratio is labelled `python_transform_vs_native_EVP`, deliberately exposing
the boundary difference. It is an optimized native baseline comparison, **not a
claim of identical library-call boundaries**. Raw allocation/setup/outer-call
fields permit analysis without pretending that subtracting overhead yields an
exact equivalent boundary. See [methodology.md](methodology.md).

## ARM control and CPU capabilities

On ARM64 each session automatically adds `openssl_armcap0` alongside
`openssl_default` and PyCryptodome. All implementations run in persistent spawned
processes. The parent sets `OPENSSL_armcap=0` **before** starting fallback workers;
default workers have capability overrides removed. Worker startup verifies that
OpenSSL reports an effective zero ARM mask, failing closed if it cannot do so.
Inherited `OPENSSL_ia32cap` overrides are also removed. OpenSSL uses the explicitly
fetched default provider. Configuration/module environment paths are recorded.

`OPENSSL_armcap=0` is a broad software fallback control: it may disable NEON,
PMULL, SHA and other architectural optimizations as well as AES. Its ratio is
not the isolated effect of AES instructions. It does not disable PyCryptodome
hardware paths. See [OpenSSL capability documentation](https://docs.openssl.org/master/man3/OPENSSL_armcap/)
and the [OpenSSL ARM dispatch source](https://github.com/openssl/openssl/blob/openssl-3.0/crypto/armcap.c).

CPU AES availability is queried through CPUID on x86-64 and Linux HWCAP on ARM64;
raw `/proc/cpuinfo` is captured on Linux. OpenSSL's effective CPU settings, library
version and build flags are captured from the **loaded library**, not the `openssl`
CLI. Availability and capability masks are evidence about allowed dispatch, not
an instruction trace. No instruction usage is inferred from cipher names. Actual
instruction-level attribution would require profiling/disassembly of the loaded
build. PyCryptodome uses its default automatic path.

## Separate multicore experiment

`--workers N` with N > 1 selects `multicore-*` directories. Each implementation
gets N persistent processes with independent ciphers/data; only one implementation
group runs at a time. All workers synchronize before each operation. Aggregate
elapsed time is **max(worker end) - min(worker start)**, using the shared system
monotonic clock, not the sum of per-worker throughput. Total bytes are N times
the per-worker size. The envelope includes the entire Python `measure` operation:
input checks, output allocation, bindings/no-op diagnostic where applicable,
setup, transformation, cleanup, conversion to bytes and release skew. It excludes
startup, data/reference preparation, barriers, IPC and ciphertext validation.
Thus this is an aggregate operation benchmark, not aggregate pure EVP throughput.
Individual worker component times remain in raw CSV. The summary deduplicates
the common envelope per repetition. No mixed single/multicore summary is produced.
Unpinned OS scheduling is deliberate and recorded; no claim of linear scaling.

## Output schema (version 1)

Each unique UUID session directory contains:

* `metadata.json`: status (`incomplete`, `failed`, `complete`), ID, seed, purpose,
  experiment, sizes/repetition counts, UTC start/end, hostname/OS/architecture/CPU,
  logical cores, Python, worker PIDs and affinity, library versions, effective
  capabilities, build settings/hashes, environment, Git state and source hashes.
* `validation.json`: per-implementation/per-worker passed cases and vector source.
* `inputs.json`: per mode/size, worker-indexed plaintext and ciphertext SHA-256,
  synthetic key and initial counter. Plaintext is reproducible rather than stored.
* `raw.csv`: one row per executed job/worker, including warmups. Identity fields:
  `session_id, seed, experiment, workers, worker, bytes, mode, repeat,
  implementation, warmup, execution_index, validation_passed`; timing fields are
  above plus `operation_start_ns, operation_end_ns, aggregate_envelope_ns` and
  `throughput_MB_s` (per-worker transform throughput). Blank means not applicable,
  never zero. Negative residuals are retained. A failure may leave partial raw
  records for diagnosis, but the session is not accepted for aggregation.
* `planned_order.json`, `execution_order.jsonl`: planned order and actual events.
* `summary.csv/json`: per-session medians, extrema, sample counts, throughput at
  median duration, ratio of PyCryptodome/session implementation medians, median
  of paired per-round ratios, and ARM fallback/default median-time ratio.
  `median_worker_*` fields also summarize each available timing component over
  measured worker samples; multicore component medians are diagnostics, not
  aggregate elapsed time. Not-applicable fields are omitted in JSON / blank in CSV.
  Ratios below one, slowdowns, and outliers are retained; only predeclared warmups
  are excluded. Pairing is by same session/mode/size/repetition/worker count.
* `source/`: exact source, requirements and protocol snapshot.

`aggregate.py` accepts one complete session, checks expected configurations and
sample counts, rejects duplicates/mixed IDs/invalid timing, and writes only that
session's summary. It never pairs across hosts or pools the five session samples.
Report all five session-level results; any later across-session uncertainty
analysis must use sessions as the replication unit. Build/results/venv are locally
ignored; intentionally archive complete final sessions separately.
