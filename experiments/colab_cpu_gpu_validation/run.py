"""Isolated paired CPU/GPU sessions. Default smoke; --study is an explicit five-session campaign."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
from uuid import uuid4
from contextlib import redirect_stdout

from dependencies import HERE, REPO, cpu, cuda_base, cuda_paired, native, source_paths, PROFILES, BACKENDS
from protocol import SCHEMA, SIZES, SEEDS, JOBS, schedule, target_check, software_check, aes_capabilities, digest

CPU_METRICS = ('setup_ns', 'transform_ns', 'cleanup_ns', 'allocation_ns', 'native_call_ns',
               'ffi_noop_ns', 'ffi_residual_ns', 'buffer_binding_ns')
TIMINGS = (*CPU_METRICS, 'cpu_transform_ns', 'cpu_operation_ns', 'operation_start_ns', 'operation_end_ns',
           'gpu_resident_ns', 'gpu_pipeline_ns', 'gpu_pipeline_kernel_ns', 'resident_batch_ns',
           'h2d_ns', 'd2h_ns', 'transfer_ns')


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False), encoding='utf-8')


def command(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=30)
        return dict(returncode=result.returncode, stdout=result.stdout.strip(), stderr=result.stderr.strip())
    except (OSError, subprocess.SubprocessError) as exc:
        return dict(error=str(exc))


def probe(study=False, local_name=None):
    for name in ('OPENSSL_ia32cap', 'OPENSSL_armcap'):
        if name in os.environ:
            raise RuntimeError(f'Remove {name} before starting Python; default OpenSSL dispatch is required')
    lib = native()
    gpus = {'baseline': cuda_paired.GPU('baseline')}
    gpu = gpus['baseline']
    if gpu.cp.cuda.runtime.getDeviceCount() != 1:
        raise RuntimeError('Exactly one visible GPU required; no silent GPU selection')
    target_check(gpu.info, platform.system(), platform.machine(), study, local_name)
    if gpu.info['runtime_version'] // 1000 not in (12, 13):
        raise RuntimeError('Supported CUDA runtime families are 12.x and 13.x')
    if not local_name:
        software_check(gpu.info['runtime_version'], gpu.info['cupy_version'],
                       __import__('Crypto').__version__, gpu.np.__version__)
    if not lib.metadata()['openssl_version'].startswith('OpenSSL 3.'):
        raise RuntimeError('This protocol requires OpenSSL 3.x')
    gpus['optimized'] = cuda_paired.GPU('optimized')
    capabilities = aes_capabilities(lib.metadata())
    if study and (capabilities['cpu_aes_available'] != 1 or
                  capabilities['openssl_aes_capability_enabled'] is not True):
        raise RuntimeError('AES-capable default OpenSSL path not established; cannot label this an AES-NI study')
    smi = command(['nvidia-smi', '-i', gpu.info['pci_bus_id'],
                   '--query-gpu=uuid,name,driver_version', '--format=csv,noheader'])
    if smi.get('returncode') != 0 or not smi.get('stdout'):
        raise RuntimeError('GPU UUID/driver identity unavailable from nvidia-smi')
    cpuinfo = Path('/proc/cpuinfo').read_text() if Path('/proc/cpuinfo').exists() else ''
    model = next((line.split(':', 1)[1].strip() for line in cpuinfo.splitlines() if line.startswith('model name')),
                 platform.processor())
    flags = next((line.split(':', 1)[1].strip() for line in cpuinfo.splitlines() if line.startswith('flags')), '')
    sources = {str(p.relative_to(REPO)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in source_paths()}
    affinity = sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None
    quota = Path('/sys/fs/cgroup/cpu.max')
    identity = dict(hostname=platform.node(), os=platform.platform(), architecture=platform.machine(),
        boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip() if Path('/proc/sys/kernel/random/boot_id').exists() else None,
        cpu_model=model, cpu_flags=flags, logical_cpus=os.cpu_count(),
        affinity=affinity, available_logical_cpus=len(affinity) if affinity is not None else os.cpu_count(),
        cgroup_cpu_max=quota.read_text().strip() if quota.exists() else None,
        gpu=gpu.info, gpu_uuid_driver=smi['stdout'], python=sys.version,
        openssl=lib.metadata(), pycryptodome=__import__('Crypto').__version__,
        numpy=gpu.np.__version__, source_sha256=sources)
    captured = io.StringIO()
    with redirect_stdout(captured):
        gpu.cp.show_config()
    info = dict(identity=identity, runtime_fingerprint=digest(identity), capabilities=capabilities,
        python_wall_clock=vars(time.get_clock_info('perf_counter')),
        cpuinfo=cpuinfo, cupy_config=captured.getvalue(),
        cuda_compiler=dict(backend='NVRTC via unchanged CuPy RawModule', options=['--std=c++11'],
                           nvrtc_version=list(gpu.cp.cuda.nvrtc.getVersion()),
                           nvcc=command(['nvcc', '--version']), resident_iterations=1,
                           threads_per_block=128, stream='CUDA default stream; no overlap'),
        environment={k: os.environ.get(k) for k in ('CUDA_VISIBLE_DEVICES', 'CUDA_PATH', 'OPENSSL_CONF',
                     'OPENSSL_MODULES', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')},
        git_commit=command(['git', '-C', str(REPO), 'rev-parse', 'HEAD']),
        git_status=command(['git', '-C', str(REPO), 'status', '--short']),
        packages=command([sys.executable, '-m', 'pip', 'freeze']))
    return lib, gpus, info


def validation(lib, gpus, session_id, purpose):
    report = dict(passed=False, cpu={}, gpu={})
    for implementation in ('pycryptodome', 'openssl_default'):
        report['cpu'][implementation] = cpu.validate(implementation, lib)
    for profile, gpu in gpus.items():
        result = cuda_base.validate(gpu, session_id, purpose)
        if not result['passed']:
            raise RuntimeError(f'Historical CUDA KAT/differential gate failed: {profile}: {result}')
        try:
            gpu.encrypt('CTR', bytes(16), b'\xff'*16, bytes(17))
        except ValueError:
            result['wrap_rejected'] = True
        else:
            raise RuntimeError('CUDA accepted counter wrap')
        result['all_size_equality'] = []
        for size in SIZES:
            data, key, iv = cpu.inputs(2003, size)
            for mode in ('ECB', 'CTR'):
                expected = cpu.py_cipher(mode, key, iv).encrypt(data)
                if gpu.encrypt(mode, key, iv, data) != expected:
                    raise RuntimeError(f'CUDA equality gate failed: {profile}/{mode}/{size}')
                result['all_size_equality'].append(dict(mode=mode, bytes=size, passed=True,
                    ciphertext_sha256=hashlib.sha256(expected).hexdigest()))
        report['gpu'][BACKENDS[profile]] = result
    report['passed'] = True
    return report


def assert_equal(actual, expected):
    if actual != expected:
        raise RuntimeError('Ciphertext mismatch; refusing timing sample')


def session(args):
    dest = args.session_dir.resolve()
    dest.mkdir(parents=True, exist_ok=False)
    session_id = dest.name
    purpose = 'study' if args.session_study else 'smoke'
    sizes, warmups, repeats = (SIZES, 5, 20) if args.session_study else ([1024, 16384], 1, 2)
    metadata = dict(schema_version=SCHEMA, status='incomplete', session_id=session_id,
        campaign_id=args.campaign_id, seed=args.seed, purpose=purpose, sizes=sizes,
        warmups=warmups, repetitions=repeats, workers=1, notes=args.notes,
        primary_comparison='prepared_cpu_transform_over_gpu_pipeline',
        primary_cpu='openssl_default', primary_gpu='cuda_baseline',
        operation_boundary='measure_call_v1', local_diagnostic=bool(args.local_smoke_gpu),
        created_utc=datetime.now(timezone.utc).isoformat())
    write_json(dest / 'metadata.json', metadata)
    try:
        lib, gpus, info = probe(args.session_study, args.local_smoke_gpu)
        metadata.update(info)
        if args.expected_fingerprint and info['runtime_fingerprint'] != args.expected_fingerprint:
            raise RuntimeError('Runtime/software/source fingerprint changed; do not pair these sessions')
        write_json(dest / 'metadata.json', metadata)
        for source in source_paths():
            target = dest / 'source' / source.relative_to(REPO)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        write_json(dest / 'validation.json', validation(lib, gpus, session_id, purpose))
        metadata['telemetry_before'] = cuda_base.telemetry(gpus['baseline'])
        jobs = schedule(args.seed, sizes, warmups, repeats)
        write_json(dest / 'planned_order.json', jobs)
        manifests, config = {}, None
        gpu_by_backend = {BACKENDS[p]: g for p, g in gpus.items()}
        actual, metrics = None, None  # Retained across CPU calls as in the Phase 1 operation boundary.
        with (dest / 'raw.csv').open('x', newline='', encoding='utf-8') as raw, \
             (dest / 'execution_order.jsonl').open('x', encoding='utf-8') as order:
            writer = None
            for job in jobs:
                current = job['mode'], job['bytes']
                if config != current:
                    data, key, iv = cpu.inputs(args.seed, job['bytes'])
                    expected = cpu.py_cipher(job['mode'], key, iv).encrypt(data)
                    pair_hash = hashlib.sha256(key + iv + data).hexdigest()
                    prepared = {}
                    for profile, gpu in gpus.items():
                        prepared[BACKENDS[profile]] = gpu.prepare(job['mode'], key, iv, data)
                        assert_equal(gpu.encrypt(job['mode'], key, iv, data), expected)
                    for implementation in ('pycryptodome', 'openssl_default'):
                        assert_equal(cpu.measure(implementation, lib, job['mode'], data, key, iv)[0], expected)
                    manifests[f'{job["mode"]}:{job["bytes"]}'] = dict(pair_hash=pair_hash,
                        key_hex=key.hex(), counter_hex=iv.hex(), plaintext_sha256=hashlib.sha256(data).hexdigest(),
                        ciphertext_sha256=hashlib.sha256(expected).hexdigest())
                    write_json(dest / 'inputs.json', manifests)
                    config = current
                order.write(json.dumps(dict(job, event='started')) + '\n')
                order.flush()
                timing = dict.fromkeys(TIMINGS)
                if job['measurement'] == 'cpu':
                    start = time.perf_counter_ns()
                    actual, metrics = cpu.measure(job['backend'], lib, job['mode'], data, key, iv)
                    end = time.perf_counter_ns()
                    assert_equal(actual, expected)
                    timing.update(metrics, cpu_transform_ns=metrics['transform_ns'], cpu_operation_ns=end-start,
                                  operation_start_ns=start, operation_end_ns=end)
                else:
                    gpu = gpu_by_backend[job['backend']]
                    gpu_job = prepared[job['backend']]
                    measured = gpu.measure_diagnostic(gpu_job, job['measurement'], 1)
                    assert_equal(gpu_job[2].tobytes(), expected)  # Copy/comparison outside GPU timers.
                    if job['measurement'] == 'pipeline':
                        timing.update(gpu_pipeline_ns=measured['end_to_end_ns'],
                            gpu_pipeline_kernel_ns=measured['kernel_ns'],
                            **{k: measured[k] for k in ('h2d_ns', 'd2h_ns', 'transfer_ns')})
                    else:
                        timing.update(gpu_resident_ns=measured['kernel_ns'], resident_batch_ns=measured['resident_batch_ns'])
                row = dict(schema_version=SCHEMA, session_id=session_id, campaign_id=args.campaign_id,
                    runtime_fingerprint=info['runtime_fingerprint'], seed=args.seed, **job,
                    pair_hash=pair_hash, validation_passed=True, **timing)
                if writer is None:
                    writer = csv.DictWriter(raw, fieldnames=list(row))
                    writer.writeheader()
                writer.writerow(row)
                raw.flush()
                order.write(json.dumps(dict(job, event='completed')) + '\n')
                order.flush()
        metadata['telemetry_after'] = cuda_base.telemetry(gpus['baseline'])
        metadata['status'] = 'complete'
    except BaseException as exc:
        metadata['status'], metadata['error'] = 'failed', repr(exc)
        if not (dest / 'validation.json').exists():
            write_json(dest / 'validation.json', dict(passed=False, error=repr(exc)))
        raise
    finally:
        metadata['finished_utc'] = datetime.now(timezone.utc).isoformat()
        write_json(dest / 'metadata.json', metadata)
    from aggregate import aggregate_session
    aggregate_session(dest, dest)
    print(dest, flush=True)


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--study', action='store_true')
    p.add_argument('--output', type=Path, default=HERE / 'results')
    p.add_argument('--notes', default='')
    p.add_argument('--local-smoke-gpu', help='Explicit exact name of a CC7.5 device; smoke only, never target study')
    p.add_argument('--session-dir', type=Path, help=argparse.SUPPRESS)
    p.add_argument('--campaign-id', help=argparse.SUPPRESS)
    p.add_argument('--seed', type=int, choices=SEEDS, default=2003, help=argparse.SUPPRESS)
    p.add_argument('--session-study', action='store_true', help=argparse.SUPPRESS)
    p.add_argument('--expected-fingerprint', help=argparse.SUPPRESS)
    args = p.parse_args()
    if args.local_smoke_gpu and (args.study or args.session_study):
        p.error('Local device override is smoke-only')
    if args.session_dir:
        session(args)
        return
    campaign_id = ('study-' if args.study else 'smoke-') + str(uuid4())
    directory = args.output.resolve() / campaign_id
    directory.mkdir(parents=True, exist_ok=False)
    manifest = dict(schema_version=SCHEMA, campaign_id=campaign_id, status='incomplete',
                    purpose='study' if args.study else 'smoke', sessions=[], smoke_gate=None)
    write_json(directory / 'campaign.json', manifest)
    env = os.environ.copy()
    env.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    fingerprint = None
    try:
        # A target smoke gate always precedes the five fresh-process study sessions.
        for index, seed in enumerate(([2003] + SEEDS) if args.study else [2003]):
            study = args.study and index > 0
            child_dir = directory / (('study-' if study else 'smoke-') + str(seed) + '-' + str(uuid4()))
            cmd = [sys.executable, str(Path(__file__).resolve()), '--session-dir', str(child_dir),
                   '--campaign-id', campaign_id, '--seed', str(seed), '--notes', args.notes]
            if study:
                cmd.append('--session-study')
            if fingerprint:
                cmd += ['--expected-fingerprint', fingerprint]
            if args.local_smoke_gpu:
                cmd += ['--local-smoke-gpu', args.local_smoke_gpu]
            subprocess.run(cmd, env=env, check=True)
            meta = json.loads((child_dir / 'metadata.json').read_text())
            fingerprint = meta['runtime_fingerprint']
            manifest['runtime_fingerprint'] = fingerprint
            if study:
                manifest['sessions'].append(child_dir.name)
            else:
                manifest['smoke_gate'] = child_dir.name
            write_json(directory / 'campaign.json', manifest)
        manifest['status'] = 'complete'
    except BaseException as exc:
        manifest['status'], manifest['error'] = 'failed', repr(exc)
        raise
    finally:
        write_json(directory / 'campaign.json', manifest)
    if args.study:
        from aggregate import aggregate_campaign
        aggregate_campaign(directory, directory / 'comparison')
    print(directory)


if __name__ == '__main__':
    main()
