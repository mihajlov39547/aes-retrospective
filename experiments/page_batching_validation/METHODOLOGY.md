# Measurement and comparability

## Workload and correctness

Each session uses deterministic SHAKE-256 plaintext and a seed-derived AES-128 key. Each logical message receives a unique structured 96-bit nonce: `seed32 || message32 || page32`, all big-endian, where `message=(layout<<24)|(batch_pages<<16)|(repeat+5)`. Counter32 starts at one. The fixed domain makes this injective: 1,425 distinct logical segment nonces per full session. CPU/GPU and timing variants replay the **same logical message**, deliberately. Distinct messages never share a nonce under a session key. Re-running the synthetic experiment reproduces keys/nonces; this is not a production nonce generator.

Continuous and page layouts share plaintext/key at equal total sizes but have distinct nonce domains. Partial-page support is tested, though study pages are exactly 1 MiB. Both Python and C reject duplicate nonces, zero counters, counter overflow and invalid dimensions. The last counter cannot exceed `0xffffffff`. The continuous control is capped at 32 MiB, so the original full-128-bit CUDA addition never carries into the nonce.

Before timing, 25 cases cover published NIST SP800-38A and RFC 3686 vectors in both layouts, explicit AES-ECB counter-block oracles, partial blocks, page/launch boundaries, counter carries and the final legal counter, plus every study size/layout. Every timed output must exactly match the independent PyCryptodome reference. Reference generation and equality checks are outside timing. A mismatch leaves a failed session, never an accepted summary.

The page kernel maps block index to page and within-page counter, then calls the unchanged historical `encrypt_block`. The original CUDA source is concatenated verbatim and hashed. AES rounds, key expansion, 128 threads per CUDA block, default stream and synchronous transfers are preserved. One launch processes all independent pages. CPU uses one sequential native loop over preinitialized EVP contexts, with one contiguous transformation timer.

## Boundaries

| Metric | Includes | Excludes |
|---|---|---|
| `cpu_transform_ns` | Single C interval over sequential EVP Update + Final calls, loop and length checks | Allocation, binding, fetching cipher, creating/initializing all contexts, cleanup, FFI, output conversion |
| `cpu_operation_ns` | Python call entry to return: input checks, zeroed output allocation, IV packing, buffer binding, FFI, native checks, setup, transform, cleanup, output-to-bytes copy and local buffer release | Plaintext/key/nonce generation, reference checks, logging |
| Resident `kernel_ns` | One CUDA-event interval around one launch with input already resident | Upload/download, preparation, host output conversion; CUDA-event clock differs from host wall clock |
| Pipeline `end_to_end_ns` | Host wall time from H2D start through completed D2H and synchronization; launch, event recording and waits included | Pinned/device allocation, staging copy, key expansion/upload and nonce-table upload, event creation, initial pre-sync, final bytes conversion |

The inherited Phase 1 `GPU.measure` and `measure_diagnostic` define GPU boundaries unchanged. GPU preparation is outside each measurement, with per-message key and nonce table prepared for both GPU variants. CPU contexts are freshly initialized on each call, but setup is outside CPU transform. CPU output allocation is ordinary zeroed pageable memory; GPU transfers use prepared pinned memory. These are intentional prepared-workload policies, not equal allocation costs.

The **primary prepared-workload comparison** is CPU transform / GPU prepared pipeline: plaintext is on the host, output storage and crypto parameters are prepared on both sides; GPU includes payload transfers needed to return host output. However GPU host launch/events/synchronization overhead remains included, while CPU FFI/setup are excluded. Report this specific boundary, not an application-wide end-to-end speedup. The compute-only CPU transform / GPU resident comparison answers a separate question. CPU operation / GPU prepared pipeline is explicitly labeled **asymmetric diagnostic**, since GPU allocation, staging, setup and result conversion are excluded. No symmetric application-envelope GPU metric is claimed.

`h2d_ns`, `d2h_ns`, their sum `transfer_ns`, and signed `pipeline_residual_ns=end_to_end_ns-transfer_ns-kernel_ns` expose measured components. The residual mixes host overhead, event/synchronization effects and different clocks; it is not pure launch overhead. Pipeline-minus-resident is likewise not a causal transfer estimate. CPU diagnostics retain allocation, binding, setup, cleanup, output-copy and outer native-call times. Signed native residual includes C checks, FFI and timer overhead; do not interpret it solely as FFI. Nested instrumentation itself adds overhead. No samples are filtered or clamped.

## Sessions and analysis

Batch order is seeded and shuffled per session; the six layout/path jobs are shuffled within each batch/repetition. Warm-ups are retained but excluded from statistics. Paired CPU/GPU observations must share session, seed, size, repetition, layout and input/key/IV digest. Continuous/page contrasts share plaintext at equal byte counts. No historical or different-machine observation enters these pairs.

Session summaries report latency and throughput medians, mean, sample SD, CV, extrema, inclusive quartiles and descriptive Tukey flags. Speedups include both median paired repetition ratio and ratio of session timing medians; they are different estimators. Campaign summaries use five session units, report their distributions and favorable-session count, and do not pool repetitions as independent sessions. Batch scaling is `N * median(time_1) / median(time_N)` (throughput gain), not completion-latency speedup. Correlated repeated plaintext prefixes, CPU caches, GPU/CPU clocks, thermal/power state, shared Colab scheduling and only five sessions limit generalization. Single CPU calling thread does not mean CPU affinity is pinned; available affinity/quota are recorded.

## Relationship to previous experiments

Inspection covered the Phase 1 native CPU adapters and envelope, existing CUDA timing driver/kernel, completed Windows sessions, Oracle single/multicore archives and saved T4 comparison summaries. The imported Colab tree contains truncated filenames for some metadata/raw artifacts; saved summary interpretation is not a complete audit of that imported provenance.

Saved Phase 1 32 MiB CTR baseline summaries report median session ratios about 0.942 for OpenSSL transform / CUDA prepared pipeline, 2.299 for transform / resident, and 5.248 for CPU operation / prepared pipeline. They answer different boundary questions. The historical 4.761× PyCryptodome-based figure is not a Phase 2 paired observation and is not invalidated merely by using a faster baseline. These values motivate the experiment; Phase 2 must establish its own same-runtime results.

## Parquet scope

[Parquet encryption](https://github.com/apache/parquet-format/blob/master/Encryption.md) uses a 96-bit nonce and a 32-bit CTR counter starting at one for the relevant data-page mode. This experiment borrows that layout. It does **not** implement Parquet files, format framing, GCM metadata/footer encryption, AAD, authentication, key management, compression or Parquet's nonce-generation requirements. Deterministic structured test nonces are for reproducibility only. References: [NIST SP800-38A](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38a.pdf), [RFC 3686 vectors](https://www.rfc-editor.org/rfc/rfc3686#section-6).
