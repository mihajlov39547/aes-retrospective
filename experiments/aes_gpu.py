"""CPU/GPU AES-128 experiment scaffold. CUDA implementation is intentionally pending."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
import random
from time import perf_counter_ns

from aes_acceleration import probe, verify_dispatch
from common import command_output, metadata, modules, parser, positive, print_plan, save_run, stats

SIZES = [1024, 16384, 1048576, 16777216, 104857600, 1073741824]
BACKENDS = ("cpu_software", "cpu_aesni", "gpu_cuda")
KERNEL_PATH = Path(__file__).with_name("aes_gpu_kernel.cu")
NIST_SOURCE = "https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38a.pdf"
# SP 800-38A, F.1.1 and F.5.1 (printed pages 24 and 55-56).
KEY = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")
COUNTER = bytes.fromhex("f0f1f2f3f4f5f6f7f8f9fafbfcfdfeff")
PLAINTEXT = bytes.fromhex(
    "6bc1bee22e409f96e93d7e117393172a ae2d8a571e03ac9c9eb76fac45af8e51 "
    "30c81c46a35ce411e5fbc1191a0a52ef f69f2445df4f9b17ad2b417be66c3710")
EXPECTED = {
    "ECB": bytes.fromhex(
        "3ad77bb40d7a3660a89ecaf32466ef97 f5d3d58503b9699de785895a96fdbaaf "
        "43b1cd7f598ece23881b00e3ed030688 7b0c785e27e8ad3f8223207104725dd4"),
    "CTR": bytes.fromhex(
        "874d6191b620e3261bef6864990db6ce 9806f66b7970fdff8617187bb9fffdff "
        "5ae4df3edbd5d35e5b4f09020db03eab 1e031dda2fbe03d1792170a0f3009cee"),
}


def cpu_cipher(mode, key, counter, backend):
    if backend not in BACKENDS[:2] or mode not in EXPECTED:
        raise ValueError("Invalid CPU backend or mode.")
    aes, _, _ = modules()
    options = {"nonce": b"", "initial_value": int.from_bytes(counter, "big")} if mode == "CTR" else {}
    return aes.new(key, getattr(aes, "MODE_" + mode),
                   use_aesni=backend == "cpu_aesni", **options)


def validate_encrypt(encrypt):
    """Accept a callable (mode, key, counter, plaintext) -> bytes; never time it."""
    for mode in EXPECTED:
        for length in (16, 64):
            data = PLAINTEXT[:length]
            reference = cpu_cipher(mode, KEY, COUNTER, "cpu_software").encrypt(data)
            actual = encrypt(mode, KEY, COUNTER, data)
            if actual != EXPECTED[mode][:length] or actual != reference:
                raise RuntimeError(f"NIST/CPU validation failed for {mode}/{length}.")
    rng = random.Random(2003)
    # Beyond a thread block, partial CTR blocks, and carry into higher counter bytes.
    for mode in EXPECTED:
        for length in ((16, 4096, 4112) if mode == "ECB" else (1, 15, 17, 4097, 4112)):
            data, key = rng.randbytes(length), rng.randbytes(16)
            counter = (2**64 - 2).to_bytes(16, "big")
            expected = cpu_cipher(mode, key, counter, "cpu_software").encrypt(data)
            if encrypt(mode, key, counter, data) != expected:
                raise RuntimeError(f"CPU differential validation failed for {mode}/{length}.")
    return {"passed": True, "source": NIST_SOURCE, "sections": ["F.1.1", "F.5.1"],
            "scope": "functional vectors and differential checks, not a security proof"}


def environment(args, method):
    result = metadata(args, method)
    result["aes_cpu_capability"] = probe()
    result["kernel_sha256"] = hashlib.sha256(KERNEL_PATH.read_bytes()).hexdigest()
    result["nvcc"] = command_output(["nvcc", "--version"])
    smi = command_output(["nvidia-smi", "--query-gpu=index,name,compute_cap,memory.total,driver_version",
                          "--format=csv,noheader,nounits"])
    fields = ("index", "name", "compute_capability", "memory_total_mib", "driver_version")
    result["nvidia_smi"] = [dict(zip(fields, (x.strip() for x in row)))
                            for row in csv.reader(io.StringIO(smi or ""))]
    result["cupy_version"] = None
    result["cuda_runtime_version"] = None
    try:
        import cupy as cp
        result["cupy_version"] = cp.__version__
        cp.cuda.Device(args.device).use()
        props = cp.cuda.runtime.getDeviceProperties(args.device)
        result["cuda_runtime_version"] = cp.cuda.runtime.runtimeGetVersion()
        result["cuda_driver_api_version"] = cp.cuda.runtime.driverGetVersion()
        result["gpu"] = {"device_index": args.device,
                         "name": props["name"].decode() if isinstance(props["name"], bytes) else props["name"],
                         "compute_capability": f'{props["major"]}.{props["minor"]}',
                         "total_memory_bytes": props["totalGlobalMem"],
                         "free_memory_bytes": cp.cuda.runtime.memGetInfo()[0]}
    except Exception as exc:
        result["gpu_environment_error"] = f"{type(exc).__name__}: {exc}"
    return result


def memory_skip_reason(size, host_free, device_free):
    # Budget for host plaintext/reference/result/staging and two device data buffers.
    if size * 6 > host_free * 0.7:
        return "Insufficient available host RAM (6x input budget, 30% reserve)."
    if size * 2 + 1024**2 > device_free * 0.7:
        return "Insufficient free GPU memory (two buffers plus reserve)."
    return None


class CudaAES:
    """Prepared RawKernel adapter; cannot compile the guarded skeleton."""
    def __init__(self, cp, threads):
        self.cp, self.threads = cp, threads
        source = KERNEL_PATH.read_text(encoding="utf-8")
        if '#error "AES GPU skeleton:' in source:
            raise RuntimeError("CUDA AES kernel is a skeleton. Implement it, then pass validation; no benchmark ran.")
        self.kernels = {name: cp.RawKernel(source, name, options=("-std=c++11",), backend="nvrtc")
                        for name in ("aes128_expand_key", "aes128_ecb", "aes128_ctr")}
        for kernel in self.kernels.values():
            kernel.compile()
        self.stream = cp.cuda.Stream(non_blocking=True)

    def prepare(self, size, key, counter):
        import numpy as np
        cp = self.cp
        with self.stream:
            self.d_input, self.d_output = cp.empty(size, dtype=cp.uint8), cp.empty(size, dtype=cp.uint8)
            self.d_key = cp.asarray(np.frombuffer(key, dtype=np.uint8))
            self.d_counter = cp.asarray(np.frombuffer(counter, dtype=np.uint8))
            self.round_keys = cp.empty(176, dtype=cp.uint8)
            self.kernels["aes128_expand_key"]((1,), (1,), (self.d_key, self.round_keys))
        self.stream.synchronize()
        self.host_output = np.empty(size, dtype=np.uint8)
        self.size = size

    def launch(self, mode):
        import numpy as np
        blocks = (self.size + 15) // 16
        grid = ((blocks + self.threads - 1) // self.threads,)
        arguments = (self.d_input, self.d_output, self.round_keys)
        if mode == "CTR":
            arguments += (self.d_counter,)
        self.kernels["aes128_" + mode.lower()](grid, (self.threads,),
                                               arguments + (np.uint64(self.size),), stream=self.stream)

    def encrypt(self, mode, key, counter, data):
        import numpy as np
        self.prepare(len(data), key, counter)
        self.d_input.set(np.frombuffer(data, dtype=np.uint8), stream=self.stream)
        self.launch(mode)
        self.d_output.get(stream=self.stream, out=self.host_output, blocking=True)
        self.stream.synchronize()
        return self.host_output.tobytes()

    def measure(self, mode, data):
        import numpy as np
        cp, stream = self.cp, self.stream
        host = np.frombuffer(data, dtype=np.uint8)
        kernel_start, kernel_stop = cp.cuda.Event(), cp.cuda.Event()
        # Pageable synchronous transfers: wall time includes host staging overhead.
        stream.synchronize()
        begin = perf_counter_ns()
        h2d_start = perf_counter_ns()
        self.d_input.set(host, stream=stream)
        stream.synchronize()
        h2d_ms = (perf_counter_ns() - h2d_start) / 1e6
        kernel_start.record(stream)
        self.launch(mode)
        kernel_stop.record(stream)
        kernel_stop.synchronize()
        d2h_start = perf_counter_ns()
        self.d_output.get(stream=stream, out=self.host_output, blocking=True)
        stream.synchronize()
        d2h_ms = (perf_counter_ns() - d2h_start) / 1e6
        end_ms = (perf_counter_ns() - begin) / 1e6
        kernel_ms = cp.cuda.get_elapsed_time(kernel_start, kernel_stop)
        output = self.host_output.tobytes()  # comparison/serialization excluded
        # A separate resident-input pass: CUDA events, no H2D/D2H in this region.
        start, stop = cp.cuda.Event(), cp.cuda.Event()
        stream.synchronize()
        resident_start = perf_counter_ns()
        start.record(stream)
        self.launch(mode)
        stop.record(stream)
        stop.synchronize()
        resident_ms = (perf_counter_ns() - resident_start) / 1e6
        resident_kernel_ms = cp.cuda.get_elapsed_time(start, stop)
        return output, {"kernel_ms": kernel_ms, "transfer_ms": h2d_ms + d2h_ms,
                        "end_to_end_ms": end_ms, "h2d_ms": h2d_ms, "d2h_ms": d2h_ms,
                        "resident_end_to_end_ms": resident_ms,
                        "resident_kernel_ms": resident_kernel_ms,
                        "crypto_ms": None}

    def release(self):
        self.stream.synchronize()
        for name in ("d_input", "d_output", "d_key", "d_counter", "round_keys", "host_output"):
            if hasattr(self, name):
                delattr(self, name)
        self.cp.get_default_memory_pool().free_all_blocks()


def summarize(rows):
    groups = {}
    for row in rows:
        groups.setdefault((row["backend"], row["mode"], row["input_bytes"]), []).append(row)
    output = []
    for (backend, mode, size), samples in groups.items():
        summary = {"backend": backend, "algorithm": "AES-128", "mode": mode,
                   "key_bits": 128, "input_bytes": size}
        for metric in ("kernel_ms", "transfer_ms", "end_to_end_ms", "crypto_ms",
                       "resident_end_to_end_ms", "resident_kernel_ms",
                       "throughput_mib_s", "kernel_throughput_mib_s"):
            values = [r[metric] for r in samples if r.get(metric) is not None]
            aggregates = {**stats(values), "min": min(values), "max": max(values)} if values else {
                name: None for name in ("count", "mean", "median", "stdev", "min", "max")}
            summary.update({f"{metric}_{name}": value for name, value in aggregates.items()})
        output.append(summary)
    return output


def run_suite(args, cp, gpu):
    import psutil
    rng = random.Random(args.seed)
    rows, skipped = [], []
    for size in args.sizes:
        reason = memory_skip_reason(size, psutil.virtual_memory().available, cp.cuda.runtime.memGetInfo()[0])
        if reason:
            skipped.append({"input_bytes": size, "reason": reason})
            continue
        size_rows = []
        try:
            data, key = rng.randbytes(size), rng.randbytes(16)
            # Leave ample counter space; each size has a fresh synthetic key.
            counter = rng.randbytes(8) + bytes(8)
            gpu.prepare(size, key, counter)
            for mode in args.modes:
                expected = cpu_cipher(mode, key, counter, "cpu_software").encrypt(data)
                for iteration in range(-args.warmup, args.repeats):
                    backends = list(BACKENDS)
                    rng.shuffle(backends)
                    for backend in backends:
                        if backend == "gpu_cuda":
                            result, timing = gpu.measure(mode, data)
                        else:
                            begin = perf_counter_ns()
                            cipher = cpu_cipher(mode, key, counter, backend)
                            start = perf_counter_ns()
                            result = cipher.encrypt(data)
                            crypto_ms = (perf_counter_ns() - start) / 1e6
                            end_ms = (perf_counter_ns() - begin) / 1e6
                            timing = {"kernel_ms": None, "transfer_ms": None, "end_to_end_ms": end_ms,
                                      "h2d_ms": None, "d2h_ms": None, "resident_end_to_end_ms": None,
                                      "resident_kernel_ms": None,
                                      "crypto_ms": crypto_ms}
                        if result != expected:
                            raise RuntimeError(f"Ciphertext mismatch: {backend}/{mode}/{size}")
                        if timing["end_to_end_ms"] <= 0 or (backend == "gpu_cuda" and timing["kernel_ms"] <= 0):
                            raise RuntimeError("Insufficient timing resolution.")
                        if iteration >= 0:
                            size_rows.append({"backend": backend, "algorithm": "AES-128", "mode": mode,
                                              "key_bits": 128, "input_bytes": size, "iteration": iteration,
                                              **timing,
                                              "throughput_mib_s": size / 2**20 * 1000 / timing["end_to_end_ms"],
                                              "kernel_throughput_mib_s": (
                                                  size / 2**20 * 1000 / timing["kernel_ms"]
                                                  if backend == "gpu_cuda" else None)})
            rows.extend(size_rows)
        except (MemoryError, cp.cuda.memory.OutOfMemoryError) as exc:
            skipped.append({"input_bytes": size, "reason": f"Allocation failed: {type(exc).__name__}",
                            "partial_samples_discarded": len(size_rows)})
        finally:
            gpu.release()
            # Avoid holding buffers from the previous size during the next allocation.
            data = expected = result = None
    return rows, skipped


def main():
    cli = parser(__doc__)
    cli.add_argument("--check", action="store_true", help="Print environment only, without measurements.")
    cli.add_argument("--validate-only", action="store_true")
    cli.add_argument("--sizes", nargs="+", type=positive, default=SIZES)
    cli.add_argument("--modes", nargs="+", choices=("ECB", "CTR"), default=["ECB", "CTR"])
    cli.add_argument("--repeats", type=positive, default=10)
    cli.add_argument("--warmup", type=positive, default=2)
    cli.add_argument("--threads", type=int, choices=(64, 128, 256), default=128)
    cli.add_argument("--device", type=int, default=0)
    args = cli.parse_args()
    if args.device < 0 or args.repeats < 2 or any(n % 16 for n in args.sizes):
        cli.error("Use nonnegative device, >=2 repeats and input sizes divisible by 16.")
    if len(set(args.sizes)) != len(args.sizes) or len(set(args.modes)) != len(args.modes):
        cli.error("Sizes and modes must be distinct.")
    if sum((args.check, args.validate_only, args.run)) > 1:
        cli.error("Choose only one of --check, --validate-only and --run.")
    method = {"modes": args.modes, "algorithm": "AES-128", "operation": "encryption",
              "status": "scaffold: CUDA kernel implementation pending",
              "gpu_e2e": "preallocated pageable host buffers -> H2D -> kernel -> D2H -> synchronization",
              "excluded": "JIT, allocations, GPU key expansion/upload, correctness and output serialization",
              "cpu_e2e": "cipher creation and encryption, including output allocation",
              "cpu_crypto": "encryption only", "resident": "separate pass, already-resident input",
              "breakdown": "same-pass transfer wall time plus device event kernel time; residual is an estimate",
              "counter": "128-bit big-endian, full-width increment; synthetic repeated test input only",
              "threads_per_block": args.threads, "stream": "one nonblocking stream, serialized transfers"}
    if not args.check and not args.validate_only and print_plan("aes_cpu_gpu", args, method):
        return
    if args.check:
        print(json.dumps(environment(args, method), indent=2, default=str))
        return
    try:
        import cupy as cp
        cp.cuda.Device(args.device).use()
        gpu = CudaAES(cp, args.threads)
        cpu_evidence = {mode: verify_dispatch(mode) for mode in args.modes}
        validation = validate_encrypt(gpu.encrypt)
        gpu.release()
        if args.validate_only:
            print(json.dumps(validation, indent=2))
            return
        method["status"] = "validated run"
        method["cpu_dispatch"] = cpu_evidence
        method["gpu_validation"] = validation
        method["hardware_execution_path"] = "CPU dispatch and GPU functional validation passed"
        env = environment(args, method)
        rows, skipped = run_suite(args, cp, gpu)
        method["skipped_sizes"] = skipped
        if not rows:
            raise RuntimeError(f"No sizes measured: {skipped}")
        folder = save_run("aes_cpu_gpu", args, method, rows, summarize(rows))
        env.update(run_id=folder.name, experiment="aes_cpu_gpu", method=method)
        (folder / "aes_cpu_gpu_environment.json").write_text(
            json.dumps(env, indent=2, default=str, allow_nan=False) + "\n", encoding="utf-8")
        # Keep common exporter names and explicit CPU/GPU filenames in the same run directory.
        for source, target in (("raw.csv", "aes_cpu_gpu_raw.csv"), ("summary.csv", "aes_cpu_gpu_summary.csv")):
            (folder / target).write_bytes((folder / source).read_bytes())
    except (ImportError, RuntimeError, OSError, AttributeError) as exc:
        cli.exit(2, f"GPU experiment incomplete: {exc}\nNo valid benchmark should be inferred.\n")


if __name__ == "__main__":
    main()
