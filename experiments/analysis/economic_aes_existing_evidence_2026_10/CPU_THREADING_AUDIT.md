# CPU execution and threading audit

Strongest supported description: **single-stream CPU AES-NI transform path, with single-threaded application-level orchestration and one synchronous encryption call per observation**. Do not describe it as measured total multicore capacity, pinned single-core execution, or independently proven single-thread execution throughout the native binary.

## Source identity

The source paths below refer to the repository root. The corresponding files under each selected session's `source/` were hash-verified. For the paired harness, baseline adapter and dispatch validator, public GitHub bytes at recorded commit `cd6b18f46414ac2e2f9d5ae61d848867b17361f9` also match local Git blobs and archived hashes (`git_provenance.json`). The current paired source has the same hash. Thus current line references for these files describe the historical code, not an assumed later replacement.

Selected example archive: `experiments/results/aes_cuda_cpu_gpu-study-20260930T205447700308Z/source/`. The other four archives have the same complete source hash map.

| Question | Evidence: file, function and lines | Determination |
|---|---|---|
| Which CPU produced the manuscript CTR values? | `scripts/aes_cuda_cpu_gpu.py`, `CPU.cipher`, 78–82; `run`, 185–191; historical metadata `cpu`, `library_versions`, `arguments` | PyCryptodome 3.23.0 AES-128 CTR on i5-10300H, explicit AES-NI backend. Neither `benchmark.py` CBC nor later EVP produced these values. |
| Explicit AES-NI selection? | `CPU.__init__`, 73–76; `CPU.cipher`, 82 | Only software/aesni accepted; `use_aesni=self.backend=='aesni'`. |
| Dispatch independently checked? | `scripts/aes_acceleration.py`, `verify_dispatch`, 52–97; `StartObserver`, 35–49; paired `validate`, 94–95 | Separate untimed initialization observer checks native start symbols, CPU capability and loaded module; two AESNI starts and zero software starts for requested AES-NI. Saved ECB/CTR records pass in all five sessions. This is library dispatch evidence, not instruction tracing or a thread trace. |
| One synchronous encryption call? | paired `cpu_measure`, 128–138 | Exactly one `cipher.encrypt(data)` at line 132; returned output is available before ending the timer. |
| Application threading, multiprocessing, async tasks or worker pools? | paired `run`, 164–210, especially nested loops 177–191 | Sequential nested loops; no worker/thread creation or async CPU dispatch in this call chain. Seed-shuffled jobs execute serially. CUDA driver activity is not evidence of CPU encryption parallelism. |
| CPU affinity? | paired `run`, 164–229; protocol Workflow/provenance; `scripts/benchmark.py`, `environment_snapshot`, 15–28 | No affinity setter or pinning in paired path. The separate CBC helper reads `psutil.Process().cpu_affinity()`; a read is not pinning and does not prove the paired session's affinity. No restriction to one core is established. |
| Native worker count? | paired `CPU.cipher`, 82; dispatch `verify_dispatch`, 64–96 | Native library initialization is verified; compiled native worker behavior is not independently traced or binary-audited in these archives. Application code alone cannot establish all native threads or CPU-core residency. |
| Wall time/process time? | paired `cpu_measure`, 130–138 | Inner `perf_counter_ns` is the performance measure; outer `process_time_ns` is diagnostic. No throughput is derived from process time. Process time can include all process threads and has coarse observed granularity; zero readings or ratios cannot prove a thread count. |
| Key schedule / cipher construction? | paired `cpu_measure`, 129 before 130–131; `CPU.cipher`, 82 | Excluded. |
| Output allocation? | paired `cpu_measure`, 132, no `output=`; method description 39–40 | Included, along with Python method/FFI/return overhead. Later preallocated-output measurements have another boundary. |
| Input generation / validation? | paired `material`, 123–125; `run`, 181–184 and 197–205 | Generation and reference precede timing; output comparison follows timing. Warmups precede retained repetitions. |
| Capacity interpretation? | paired `run`, 185–191 and `cpu_measure`, 128–138 | Single-stream transform throughput. Four physical/eight logical CPU counts do not turn it into aggregate CPU capacity. |

## GIL

The native AES transform is not a Python bytecode encryption loop. Python call and return overhead remain inside the wall interval, but the GIL does not prove native seriality or explain the measured throughput. Targeted inspection of the currently installed `.venv/Lib/site-packages/Crypto/Cipher/_mode_ctr.py`, `CtrMode.encrypt`, lines 189–204, shows output allocation and a call to `raw_ctr_lib.CTR_encrypt`. `_raw_api.py` offers CFFI (`load_lib`, 93 onward) or ctypes `CDLL` (`load_lib`, 184–196). These installed files are contextual evidence, not archived proof of the exact historical loaded binary/binding branch.

Both binding families allow the GIL to be released during native calls; see [Python 3.12 ctypes documentation](https://docs.python.org/3.12/library/ctypes.html#loading-shared-libraries) and [CFFI reference, function-call footnote](https://cffi.readthedocs.io/en/latest/ref.html#conversions). Releasing the GIL neither creates workers nor pins execution. No competing application encryption workers are launched by the historical harness. The retained evidence does not independently identify runtime GIL transitions, native worker count or CPU migration.

## Other inspected CPU paths are not substitutes

- `scripts/benchmark.py`, `main`, 88–104: CBC encrypt/decrypt timers. `environment_snapshot`, 15–28, reads affinity; no pinning. Its DES/TDEA/AES CBC measurements are excluded from the CTR economic model.
- `scripts/aes_acceleration.py`, `verify_dispatch`, 52–97: reused dispatch verification; its separate CBC performance experiment is not the CTR dataset.
- `scripts/cpu_validation.py`, `verify_software_dispatch`, 47–76, and `validate_cpu`, 79 onward: software dispatch and CBC correctness. It does not verify native CPU threading.
- `experiments/cpu_baseline_validation/core.py`, `measure`, 90–130: separately allocates output (94–96); PyCryptodome uses `encrypt(..., output=view)` (103); EVP invokes a ctypes wrapper (121–128). Different scope from the original allocating call.
- `experiments/cpu_baseline_validation/native.c`, `baseline_encrypt`, 64–89: default-provider AES-128 ECB/CTR selected at 74; setup at 73–78; native transform brackets `EVP_EncryptUpdate` and `EVP_EncryptFinal_ex` at 79–82. No worker pool is created in this wrapper, but wrapper source alone is not a trace of OpenSSL internals.
- `experiments/cpu_baseline_validation/windows_native.py`, `verify_bindings`, 21–90: checks x64 PE imports, resolved DLL identity and hashes. Library identity is distinct from instruction or thread verification.
- `experiments/cpu_baseline_validation/methodology.md`: no pinning; one-worker transform and multicore operation-envelope scopes must remain separate. Oracle two-worker evidence cannot establish Windows multicore AES-NI capacity.

Recommended wording: “CPU performance was measured through a single-stream PyCryptodome AES-NI transform path, using sequential application-level orchestration and one synchronous encryption call per observation. CPU affinity and native thread execution were not independently controlled or traced.”
