# Execution-boundary matrix

The selected measurements encrypt AES-128 CTR in memory. “Pipeline E2E” means a **prepared in-memory H2D–kernel–D2H pipeline**, not application end-to-end. Baseline and optimized v1 use the same timing adapter. Archived sources match across the five September sessions.

I = included; E = excluded; N/A = not part of that path; partial entries specify the actual interval.

| Component | CPU software transform | CPU AES-NI transform | CUDA baseline resident | CUDA baseline pipeline E2E | CUDA v1 resident | CUDA v1 pipeline E2E |
|---|---|---|---|---|---|---|
| Input generation | E | E | E | E | E | E |
| Input/buffer preparation | E | E | E | E | E | E |
| General host/device allocation | E except output | E except output | E | E | E | E |
| Output allocation | I | I | E | E | E | E |
| Pinned allocation and host staging copy | N/A | N/A | E | E | E | E |
| Key schedule | E | E | E | E | E | E |
| Cipher initialization / GPU key-counter upload | E | E | E | E | E | E |
| H2D payload copy | N/A | N/A | E | I | E | I |
| AES transform / CUDA kernel | I | I | I | I | I | I |
| D2H payload copy | N/A | N/A | E | I | E | I |
| CUDA synchronization | N/A | N/A | completion wait outside event elapsed metric | I after copies and kernel | same as baseline | I |
| CUDA event allocation | N/A | N/A | E | E | E | E |
| CUDA event recording and launch bookkeeping | N/A | N/A | device interval; submission gaps may affect elapsed events | I within wall interval | same as baseline | I |
| Python cipher method / native FFI return | I | I | N/A | N/A | N/A | N/A |
| GPU output `.tobytes()` conversion | N/A | N/A | E | E | E | E |
| Reference encryption / validation | E | E | E | E | E | E |
| File I/O | E | E | E | E | E | E |
| Full application orchestration | E; method overhead only | E; method overhead only | E | E; timed launch/copy bookkeeping only | E | E; timed launch/copy bookkeeping only |
| Compilation/JIT | N/A | N/A | E | E | E | E |

## Exact source attribution

- `scripts/aes_cuda_cpu_gpu.py`, `cpu_measure`, 128–138: construction before clocks, one encrypt call within wall time, outer process-time diagnostic. `run`, 181–205: material/reference before timing, GPU preparation before timing, output conversion and validation after timing.
- `scripts/aes_cuda_baseline.py`, `GPU.prepare`, 161–177: allocates device source/output/key/counter/expanded-key buffers; performs key expansion and synchronization; allocates pinned input/output at 174–175 and stages input at 176. **Pinning is not included in pipeline E2E** even though prepare is called again for each GPU job.
- `GPU.measure`, 193–212: event objects created before timer; wall start 198; H2D and sync 199; event-bracketed kernel and completion wait 201; D2H and sync 203; wall end 204. H2D/D2H durations and their sum are recorded at 208–210.
- `GPU.measure_diagnostic`, 214–234: pipeline delegates to `measure`; resident uploads before event start and downloads after elapsed-time measurement. Event interval divided by N, where selected N=1. Resident completion wait establishes completion but its host waiting duration is not separately added to CUDA event elapsed time.
- `scripts/aes_cuda_cpu_gpu.py`, `GPU.__init__`, 61–69: v1 substitutes compiled kernel entrypoints while inheriting preparation and timers.
- `experiments/aes_cuda_baseline.cu`, `expand_key`, 25 onward; `aes_ctr`, 72 onward; `experiments/aes_cuda_optimized.cu`, `expand_key`, 27 onward; `aes_ctr_optimized`, 77 onward: separate key expansion and block-parallel AES-128 CTR kernels. GPU parallel threads do not describe CPU threading.
- `experiments/cuda_optimized_cpu_gpu_protocol.md`, “Timing and metrics” and “Pairing and validation”; `experiments/aes_acceleration_protocol.md`, “Tajmeri i metadata”: documented scopes agree with the selected archived implementation. CBC protocol does not supply CTR numbers.

CPU and GPU pipeline start/end with host-resident data at a broad functional level, making a conditional comparison possible, but allocations are asymmetric: CPU output allocation is timed, GPU host/device allocation and pinned staging are not. CPU Python/native method time and GPU host-controlled pipeline time also include different bookkeeping. Setup/key scheduling is excluded on both sides; startup, storage, networking, authentication, scheduling queues and concurrent service workloads are absent. CPU input is an ordinary bytes object; GPU input is already staged in pinned memory. Do not call the rates equal-scope production performance.

## Components versus residuals

`cross_platform_2026_10_complete/pipeline_recorded_components.csv` contains aggregates of recorded fields (`h2d_ns_median`, `d2h_ns_median`, `transfer_ns_median`, `kernel_ns_median`, `end_to_end_ns_median`). H2D/D2H are directly instrumented host intervals around synchronous copy operations and synchronization. `transfer_ns` is their arithmetic sum, not an independently instrumented wire-only duration. CSV values are medians across session medians, not new measurements.

The new `derived_pipeline_nonkernel_fraction` uses **pipeline's own kernel event component**: `(median(E2E)-median(pipeline kernel))/median(E2E)`, computed per session. `median_sample_nonkernel_fraction` separately summarizes `(E2E_i-kernel_i)/E2E_i` within the same pipeline observations. These are DERIVED combined non-kernel fractions: transfers, synchronization and host launch/event overhead, subject to mixed host/device clock boundaries. Median components need not add to the median total. This is not a pure PCIe fraction, nor a measured additive decomposition.

Subtracting separately measured resident time from pipeline time would additionally mix independent executions. It is only an approximate scope contrast and is **not used as the pipeline kernel component** here. Historical baseline median session non-kernel fractions using the component-median formula are 0.7353, 0.7178 and 0.7410 at 1, 16 and 32 MiB. They are descriptive derived indicators, not energy or utilization measurements.
