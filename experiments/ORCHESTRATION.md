# Reproducible experiment orchestration

`scripts/run_all_experiments.py` runs the existing programs in separate Python
processes, sequentially, from the repository root. No benchmark modules are
imported by the orchestrator. Algorithms, kernels, timer intervals, native result
columns and within-session estimators are unchanged. Historical data under
`experiments/results/` is never an execution destination.

## Quick start

Use Python 3.10 or later. The management layer uses the standard library;
experiments require the existing `experiments/requirements.txt` dependencies
(PyCryptodome, psutil, matplotlib). CuPy and a working CUDA runtime/NVRTC are
additional requirements for CUDA experiments. Nothing is installed automatically.

Windows, from the repository root with the existing environment:

```powershell
.\.venv\Scripts\python.exe scripts/run_all_experiments.py list
.\.venv\Scripts\python.exe scripts/run_all_experiments.py doctor --config experiments/configs/all-smoke.json
.\.venv\Scripts\python.exe scripts/run_all_experiments.py plan --config experiments/configs/local-windows.json
.\.venv\Scripts\python.exe scripts/run_all_experiments.py run --config experiments/configs/all-smoke.json --platform-alias gtx1650ti-windows
```

Linux, with an already prepared environment:

```bash
.venv/bin/python scripts/run_all_experiments.py list
.venv/bin/python scripts/run_all_experiments.py doctor --config experiments/configs/t4-linux.json
.venv/bin/python scripts/run_all_experiments.py plan --config experiments/configs/t4-linux.json
.venv/bin/python scripts/run_all_experiments.py run --config experiments/configs/all-smoke.json --platform-alias t4-linux-cloud
```

`plan` only resolves configuration and displays argument arrays; it does not
initialize CUDA or write outputs. `doctor` probes capabilities, packages and
telemetry without compiling kernels or allocating benchmark buffers. Its JSON
includes individual preflight failures when a configuration is supplied. The
doctor command itself succeeds if it can produce a diagnostic report; inspect
the report, not just its exit code.

Portable CPU development:

```bash
python scripts/run_all_experiments.py run --config experiments/configs/cpu-smoke.json
python -m unittest discover -s tests -p test_orchestration.py -v
```

The CPU development configuration runs CBC software, avalanche and bounded
keyspace only. AES-NI comparison and GCM also run without CUDA, but require x86
AES-NI and its PyCryptodome native backend. CPU absence of AES-NI is a failure
for those comparisons, never an automatic substitute backend.

## Registry and audited interfaces

`list` emits the machine-readable registry including script paths, capabilities,
supported arguments, aliases, defaults, expected artifacts, validation gates,
smoke-check paths and compatibility notes. All active experiments support smoke,
pilot and study purposes. The registry's defaults describe orchestrator defaults;
smoke overrides size/warmup/repeats as described below.

| ID | Existing executable | Gate before measurements | Statistical unit |
|---|---|---|---|
| `cpu_cbc` | `benchmark.py` | Five CBC KATs, software dispatch, round trips | Transform repetitions, DES/TDEA/AES, encrypt/decrypt |
| `cpu_aesni` | `aes_acceleration.py` | Six algorithm/backend KAT records, dispatch, equality | Paired CBC backend repetitions |
| `cpu_gcm` | `aes_gcm_benchmark.py` | Four GCM KAT records, tamper rejection, dispatch | AES-128/256 AEAD encrypt/decrypt repetitions |
| `cuda_baseline` | `aes_cuda_baseline.py` | 18 KAT/differential cases and output checks | Pinned pipeline repetitions; diagnostics separate |
| `cuda_paired` | `aes_cuda_cpu_gpu.py` | All five backends, 18 tests each, wrap/dispatch/equality | Paired ECB/CTR CPU and CUDA jobs |
| `avalanche` | `avalanche_test.py` | Bit mapping, parity, rejection, determinism, statistics | Samples per algorithm/variant, not timing repeats |
| `keyspace` | `brute_force_demo.py` | ECB KAT, bounded searches/counts/rate checks | Stop-on-match search repetitions per target position |
| `legacy_gpu_scaffold` | `aes_gpu.py` | Intentionally blocked CUDA source | **Disabled**, no executable modes |
| `exporter` | `export_results.py` | Persisted validation required | Optional utility, not a benchmark |

Every active script uses `--output` as a root and creates a timestamped child.
CPU CBC/AES-NI/GCM additionally write a validation JSON beside that child;
CUDA/avalanche/keyspace create a sibling validation directory. These are retained.
The registry never treats a validation-only directory as a measurement result.

`--purpose` applies to all active scripts. Avalanche and keyspace additionally
require matching `--profile`; CUDA `--profile` instead selects a kernel or a
diagnostic scope. Paired CUDA uses plural `--measurements`, baseline uses singular
`--measurement`. The adapter sends only supported arguments. Avalanche uses
`--samples-per-group` (`--trials` alias), and keyspace uses `--reduced-key-bits`
(`--bits` alias). Keyspace has **no performance warmup**.

Paired CUDA explicitly selects `baseline optimized`: `optimized` is v1. The
legacy paired CLI defaults include `ttable`, but the orchestrator does not.
T-table remains an optional timed candidate through `options.profile`; all
three kernels are validated even when only baseline/v1 are timed. The archived
final paired study has no T-table performance rows. Its five seeds are 2003–2007,
five warmups, twenty measured repetitions, resident N=1 and pinned pipeline.

The exporter supports CBC, AES-NI and the old `aes_cpu_gpu` scaffold schema,
not the new paired CUDA/GCM/avalanche/keyspace schemas. It is not invoked during
orchestration. For its supported formats, first copy the native result to a
separate report workspace and run `python scripts/export_results.py COPY_PATH`.
Adding plots inside an accepted native folder would invalidate its hash inventory.

The dedicated smoke checks listed by `list` are retained unchanged. They include
negative validation injection and timing-boundary checks. The old omnibus
`smoke_check.py` assumes obsolete avalanche/keyspace schemas; it is not the new
suite driver. The orchestration tests never invoke expensive real benchmarks.

## Versioned JSON configuration

No YAML dependency was added. Paths are relative to the repository root,
regardless of the current terminal directory. Unknown keys and unsupported
options fail validation. Use `options` for script-specific settings:

```json
{
  "schema_version": 1,
  "suite_id": "aes-retrospective-v1",
  "execution_profile": "pilot",
  "seeds": [2003, 2004],
  "warmup": 5,
  "repeats": 10,
  "platform_alias": "my-cuda-host",
  "cuda_device": 1,
  "gpu_unavailable": "fail",
  "fail_fast": true,
  "experiments": {
    "cuda_paired": {
      "options": {
        "profile": ["baseline", "optimized"],
        "measurements": ["resident", "pipeline"],
        "resident_iterations": 1,
        "sizes": [1024, 16384, 1048576, 16777216, 33554432],
        "modes": ["ECB", "CTR"]
      }
    },
    "avalanche": {"seeds": [2003], "options": {"samples_per_group": 200}}
  }
}
```

Precedence: registry defaults, smoke adjustments, applicable global warmup/repeats,
then explicit experiment options. Per-experiment seeds override the global list.
Experiment order follows the JSON object; seeds follow their list. No seed is
derived, incremented or separately assigned to CPU/GPU backends. The same seed
means reproducible inputs only under the underlying experiment's RNG protocol
and identical options; it does not imply equal inputs across unrelated scripts.

Smoke defaults are one 1 KiB size, one warmup and two measured repetitions for
timing experiments; avalanche has eight samples per group. Keyspace retains
eight variable bits and three repeats unless explicitly overridden. Global
repeats never affect keyspace. Pilot/study keyspace requires explicit bits **and**
repeats, within both the script cap and the orchestrator budget. Its bits never
scale automatically. `execution_profile` labels purpose; it is not evidence that
the selected workloads are sufficient for a scientific study.

Example files:

- `cpu-smoke.json`: works without CUDA or AES-NI.
- `all-smoke.json`: all seven active experiments; explicitly skips absent CUDA.
- `local-windows.json` and `t4-linux.json`: identical selected study workloads,
  differing only in the human-readable alias. CBC/AES-NI warmup=3; GPU warmup=5;
  all timing repeats=20; avalanche samples/group=2000. Keyspace is disabled pending
  an explicit search budget.
- `future-cuda.json`: model-independent paired/baseline pilot using the same five
  buffer sizes and baseline/v1 scopes, with ten repeats.
- `keyspace-bounded-study.json`: explicitly bounded 12-bit educational search;
  a new workload, not a claim to reproduce a historical larger keyspace.

Select a subset using `--select cpu_cbc avalanche`; selection must be enabled in
the configuration and is saved in the resolved configuration. `--platform-alias`
overrides its label. Both options apply only to a fresh plan/run.

## Platform identity and resources

`environment.json` records OS/release/kernel/architecture, a hashed hostname,
Python version/executable, CPU model/counts/RAM, AES-NI availability and VAES where
Linux exposes it, library versions, CUDA runtime/driver, selected device model,
VRAM/compute capability/PCI bus, NVIDIA driver model, PCIe and clock/power telemetry,
and Git commit/branch/status. Missing readings are null, with discovery failures
recorded. AES-NI discovery includes native-library availability; the benchmark
still independently validates actual dispatch. VAES is null on this Windows
implementation. Cloud provider/instance type/region are accepted only through an
explicit `cloud` object; there are no cloud metadata network calls.

The stable 24-hex SHA-256 fingerprint includes OS/release/kernel/architecture,
hashed hostname, Python version, CPU/model/counts/total RAM/features, recorded
package versions, each GPU's model/hashed UUID/compute capability/total memory/
driver/model, and selected CUDA device/runtime identity. It excludes timestamps,
alias, absolute Python path, Git status, available RAM/VRAM, clocks, power readings
and cloud labels. See `platform.FINGERPRINT_FIELDS` and `fingerprint()` for the
exact normalization. Full GPU UUIDs and hostnames are not recorded by the probe.
No environment dump, credentials, tokens or automatic identifier transmission is
performed. Native artifacts retain the original scripts' local provenance fields.

`cuda_device` accepts one NVIDIA index or GPU UUID and sets `CUDA_VISIBLE_DEVICES`
only for child processes. The active scripts select their default visible device;
no unsupported `--device` flag is sent. If unset, inherited device visibility is
honored. This supports nonzero devices without changing CUDA kernels or timings.

Configurable `limits` defaults:

| Limit | Default |
|---|---:|
| `max_workload_bytes` | 104857600 |
| `min_free_ram_bytes` | 268435456, beyond 8 × largest input |
| `min_free_disk_bytes` | 104857600 |
| `max_key_bits` | 12 |
| `max_key_candidates` | 1000000 per invocation (worst-case scenarios × repeats × 2^bits) |
| `timeout_seconds` | 600; explicit null disables timeout |

CUDA preflight requires device capacity of at least 4 × input + 64 MiB and checks
free memory when telemetry exists. Telemetry failures do not prove allocation
will succeed; native allocation/compilation failures remain fatal. No workload is
silently shrunk. Optional `required_cpu_features` accepts `aesni`/`vaes`;
`min_compute_capability` accepts a string such as `"7.5"`. Resource checks are
conservative estimates, not guarantees against allocation failure or other jobs.
An OS file lock prevents concurrent suites in the same checkout; unrelated
applications and other checkouts must be controlled by the researcher.

## Artifacts, states and recovery

```text
results_orchestrated/<alias-or-os>/<fingerprint>/<suite-id>-<UTC>-<UUID>/
  manifest.json                 # immutable source/config/environment identity
  config.resolved.json          # immutable full workload and seed choices
  environment.json             # immutable discovery manifest
  status.json                  # durable timestamped transitions
  experiments/<id>/seed-2003/
    orchestration.json         # command, timing, outcome, native/source hashes
    native/                    # unchanged legacy result files and source/
  attempts/<id>-seed-2003-<UTC>-<UUID>/
    command.json, execution.json, stdout.log, stderr.log
    preflight.json, verification.json
    staging/                   # preserved original gate records
  failed-attempts/              # logs, partial artifacts and failure evidence
  aggregates/<UTC>-<UUID>/      # each aggregation is a fresh export
  reports/                     # reserved for explicitly derived reports
```

`logs/` and `validation/` are reserved at suite level; actual per-attempt logs and
validation evidence live together in attempts. `orchestration.json` maps the
original legacy child path to `native/`. Legacy metadata is not rewritten to
replace those historical paths.

States are PENDING → PREFLIGHT → VALIDATING → RUNNING → VERIFYING → COMPLETED,
with FAILED, SKIPPED and INTERRUPTED outcomes. VALIDATING records delegation to
the legacy internal gate. RUNNING means the subprocess is active, not that its
internal gate already passed. Gates precede warmup/timers inside the unmodified
script. Discovery, compilation, known-answer tests, cross-backend equality,
performance and export remain separate evidence. Missing evidence is unknown.
Standalone baseline cross-backend comparison means its CPU differential tests;
the five-path equality condition applies only to paired CUDA.

Acceptance requires exactly one native result directory, expected files and
source snapshots, matching experiment/seed/purpose/options, intact passing
validation with session identity, CSV/JSON equality, complete raw and summary
groups, correct sample indices, raw-derived summary medians, paired input hashes
and paired timing-ratio formulas. Whole native file hashes protect subsequent
reuse. Promotion is a same-filesystem rename of a verified bundle. A zero exit
code alone is insufficient. Timing correctness does not establish low variance,
absence of throttling, or generalizable scientific performance.

Copy the run directory printed by `run` into these commands:

```bash
python scripts/run_all_experiments.py verify --run-dir RUN_DIRECTORY
python scripts/run_all_experiments.py resume --run-dir RUN_DIRECTORY
python scripts/run_all_experiments.py resume --run-dir RUN_DIRECTORY --retry-failed
python scripts/run_all_experiments.py resume --run-dir RUN_DIRECTORY --retry-skipped
python scripts/run_all_experiments.py aggregate --run-dir RUN_DIRECTORY
```

Ctrl+C terminates/waits for the active subprocess, preserves its attempt and
records interruption. Timeouts are failures, preserving logs and partial output.
Hard-killed parent processes can leave an orphan child: resume refuses to start
another measurement while that recorded child is alive. Wait for it to exit.
Each retry gets a separate attempt. Interrupted work is retried; FAILED and
SKIPPED require their explicit flags. Completed results are verified and reused,
never overwritten. A crash after promotion is recovered by verifying the bundle.

Resume accepts no new config. Its original resolved config/environment hashes,
current source hashes and hardware/software fingerprint must match. Fixing code,
changing packages, changing workloads or moving hosts requires a **new run**.
Already completed artifacts remain offline-verifiable even after code changes.
The suite manifest is immutable; `status.json` and append-only attempt history
are lifecycle records. Verification cannot authenticate malicious edits to all
manifests together; these are integrity hashes, not digital signatures.

`fail_fast` defaults true for every purpose, including study. Explicit CUDA
absence can instead be skipped through `gpu_unavailable: "skip"`. A suite with
skips is labeled COMPLETED_WITH_SKIPS and has no fabricated GPU rows.

## Aggregation and history

Aggregation verifies all completed native results before reading them and rejects
unfinished/failed suites. Explicit skips remain in the validation summary.
Outputs are `summary.csv`, `summary.json`, `paired_speedups.csv`,
`session_variability.csv` and `validation_summary.json`, inside a unique aggregate
directory. Re-running aggregation never modifies native files or old aggregates.

Groups remain separated by experiment, algorithm/backend/profile, mode, size,
operation, measurement, memory policy, resident iteration count, avalanche
variant and keyspace scenario/bits. Native median fields become medians of
session medians. Paired CUDA ratios are checked against **within-session CPU
median time / GPU median time**, then aggregated by their median. There is no
division of aggregate throughput medians. GPU pipeline kernel components are
never substituted for resident measurements. Throughput remains decimal MB/s.
CPU reference timings come only from the same paired session.

Session variability is descriptive min/max/sample SD of session values; one
session has null SD. Native means, percentiles, outlier flags, extrapolation
tables and confidence intervals are not combined. Raw observations are never
pooled. Every native result is retained for more specialized analysis.
Cross-platform pooling/comparison is deliberately outside this command: export
each platform separately and perform a separately documented compatibility review
of workload, source, library stack, estimator and timing scope before comparing.

Optional read-only historical index:

```bash
python scripts/run_all_experiments.py import-history --source experiments/results --destination experiments/history-index
```

It hashes native historical files, retains recorded source revisions/hashes and
platform fields, records whether commits differ from the current checkout, and
leaves missing metadata null. It does not migrate data, validate old experiments
retroactively, or make them eligible for automatic aggregation. Older READMEs
contain preparation-era descriptions; current scripts and per-run artifacts
are authoritative. The archived paired final aggregation selects baseline/v1,
not the earlier three-profile pilot.

## First complete study and NVIDIA T4

1. Prepare Python and the existing CPU dependencies. On the cloud host, provision
   a functioning NVIDIA driver and one compatible CuPy/runtime/NVRTC stack using
   the platform's installation procedure. The orchestrator never installs CUDA.
2. Run `doctor`, unit tests, then `all-smoke.json` on that host. Confirm both CUDA
   tasks are COMPLETED, not skipped. Driver discovery alone is insufficient.
3. Run a controlled pilot and inspect durations, raw data and variation. Keep
   resident N=1, pinned pipeline and the standard five sizes for comparison.
   Record cloud provider/type/region explicitly if known. CPU AES-NI is required
   for GCM and paired CPU/GPU; a T4 alone does not satisfy CPU requirements.
4. Review `local-windows.json` or `t4-linux.json`, choose a bounded keyspace
   workload explicitly if including it, then lock the configuration. To include
   keyspace, enable it and copy the explicit options and appropriate limits from
   `keyspace-bounded-study.json`. Do not infer historical search settings from
   global throughput repetitions. These examples are study templates.
5. Inspect the plan and launch the selected full study on an otherwise controlled
   machine. Study measurements were not launched during implementation:

```powershell
.\.venv\Scripts\python.exe scripts/run_all_experiments.py plan --config experiments/configs/local-windows.json
.\.venv\Scripts\python.exe scripts/run_all_experiments.py run --config experiments/configs/local-windows.json
```

```bash
.venv/bin/python scripts/run_all_experiments.py plan --config experiments/configs/t4-linux.json
.venv/bin/python scripts/run_all_experiments.py run --config experiments/configs/t4-linux.json
```

6. Verify the printed run directory, aggregate it, and archive the entire suite
   including attempts/config/environment/source snapshots. Generated orchestrated
   output is gitignored; decide explicitly which artifacts to publish.

The implementation uses cross-platform paths, subprocess argument arrays,
`sys.executable`, and OS-specific file-lock branches. The test workflow covers
Windows/Linux with Python 3.10/3.12 when run by CI. Local validation was on Windows
10 / i5-10300H / GTX 1650 Ti; Linux/T4 hardware execution has **not** been performed
here. Cloud portability remains conditional on that host passing its own smoke
and pilot gates. WDDM versus Linux scheduling, clocks, power policy, CPU/library
differences and variance remain scientific interpretation limits.
