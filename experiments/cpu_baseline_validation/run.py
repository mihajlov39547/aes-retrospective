"""Explicit --study runs five sessions; default is a small smoke experiment."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import platform
import random
import shutil
import subprocess
import sys
import traceback
from time import perf_counter_ns
from uuid import uuid4

from core import ROOT, SEEDS, SIZES, IMPLEMENTATIONS, Native, inputs, measure, py_cipher, validate


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False), encoding='utf-8')


def command(args):
    result = subprocess.run(args, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else result.stderr.strip()


def worker(conn, implementation, seed, index, barrier):
    """Spawned with capability environment already installed, before any crypto imports."""
    try:
        import Crypto
        native = Native()
        info = native.metadata()
        if implementation == 'openssl_armcap0':
            # Require OpenSSL's reported effective mask, not just the environment request.
            import re
            match = re.search(r'OPENSSL_armcap=0x([0-9a-fA-F]+)', info['openssl_cpu_settings'])
            if not match or int(match.group(1), 16) != 0:
                raise RuntimeError('Cannot verify effective ARM capability mask is zero')
        info.update(pid=os.getpid(), pycryptodome_version=Crypto.__version__,
                    environment={k: os.environ.get(k) for k in
                                 ('OPENSSL_armcap', 'OPENSSL_ia32cap', 'OPENSSL_CONF',
                                  'OPENSSL_MODULES', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')},
                    affinity=sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None)
        conn.send(dict(metadata=info, validation=validate(implementation, native)))
        prepared = None
        while True:
            job = conn.recv()
            if job['op'] == 'stop':
                break
            mode, size = job['mode'], job['bytes']
            if job['op'] == 'prepare':
                data, key, iv = inputs(seed, size, index)
                reference = py_cipher(mode, key, iv).encrypt(data)
                actual, _ = measure(implementation, native, mode, data, key, iv)
                if actual != reference:
                    raise RuntimeError('Configuration equality gate failed')
                prepared = (mode, size, data, key, iv, reference)
                conn.send(dict(ready=True, plaintext_sha256=hashlib.sha256(data).hexdigest(),
                               key_hex=key.hex(), counter_hex=iv.hex(),
                               ciphertext_sha256=hashlib.sha256(reference).hexdigest()))
                continue
            if prepared is None or prepared[:2] != (mode, size):
                raise RuntimeError('Unprepared configuration')
            _, _, data, key, iv, reference = prepared
            if barrier:
                barrier.wait(timeout=120)
            start = perf_counter_ns()
            actual, metrics = measure(implementation, native, mode, data, key, iv)
            end = perf_counter_ns()
            if actual != reference:
                raise RuntimeError('Timed ciphertext mismatch; session invalid')
            conn.send(dict(metrics=metrics, start_ns=start, end_ns=end, validation_passed=True))
    except BaseException:
        conn.send(dict(error=traceback.format_exc()))
    finally:
        conn.close()


def receive(conn):
    if not conn.poll(180):
        raise TimeoutError('Worker did not respond within 180 seconds')
    result = conn.recv()
    if 'error' in result:
        raise RuntimeError(result['error'])
    return result


def schedule(seed, sizes, implementations, warmups, repetitions):
    rng = random.Random(seed)
    sizes = list(sizes)
    rng.shuffle(sizes)
    jobs = []
    for size in sizes:
        modes = ['ECB', 'CTR']
        rng.shuffle(modes)
        for mode in modes:
            for repeat in range(-warmups, repetitions):
                order = list(implementations)
                rng.shuffle(order)
                for implementation in order:
                    jobs.append(dict(bytes=size, mode=mode, repeat=repeat,
                                     implementation=implementation, warmup=repeat < 0,
                                     execution_index=len(jobs)))
    return jobs


def session(args, seed):
    arm = platform.machine().lower() in ('aarch64', 'arm64')
    implementations = IMPLEMENTATIONS + (['openssl_armcap0'] if arm else [])
    purpose = 'study' if args.study else 'smoke'
    experiment = 'single' if args.workers == 1 else 'multicore'
    session_id = f'{experiment}-{purpose}-{seed}-{uuid4()}'
    dest = args.output.resolve() / session_id
    dest.mkdir(parents=True, exist_ok=False)
    source = dest / 'source'
    source.mkdir()
    for path in ROOT.iterdir():
        if path.is_file() and path.suffix in ('.py', '.c', '.md', '.txt', '.ps1', '.sh'):
            shutil.copy2(path, source / path.name)
    sizes = SIZES if args.study else [1024, 16384]
    warmups, repetitions = (5, 20) if args.study else (1, 2)
    jobs = schedule(seed, sizes, implementations, warmups, repetitions)
    meta = dict(schema_version=1, session_id=session_id, status='incomplete', seed=seed,
                purpose=purpose, experiment=experiment, workers=args.workers,
                created_utc=datetime.now(timezone.utc).isoformat(),
                hostname=platform.node(), architecture=platform.machine(), os=platform.platform(),
                cpu=platform.processor(), logical_cpus=os.cpu_count(), python=sys.version,
                executable=sys.executable, sizes=sizes, warmups=warmups, repetitions=repetitions,
                implementations=implementations, notes=args.notes,
                git_commit=command(['git', 'rev-parse', 'HEAD']),
                git_status=command(['git', 'status', '--short']),
                source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir()},
                thread_policy='one serial cipher per spawned process; no internal thread pool',
                affinity_policy='OS scheduling; no pinning; record available affinity',
                timer='Python perf_counter_ns; native CLOCK_MONOTONIC or QueryPerformanceCounter',
                cpuinfo=Path('/proc/cpuinfo').read_text() if Path('/proc/cpuinfo').exists() else
                    command(['powershell', '-NoProfile', '-Command',
                             'Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors | ConvertTo-Json']))
    write_json(dest / 'metadata.json', meta)
    write_json(dest / 'planned_order.json', jobs)
    pools, processes, validation, worker_meta, manifests = {}, [], {}, {}, {}
    ctx = mp.get_context('spawn')
    # All workers for a variant share a barrier only in the multicore experiment.
    try:
        for implementation in implementations:
            barrier = ctx.Barrier(args.workers) if args.workers > 1 else None
            pools[implementation] = []
            validation[implementation], worker_meta[implementation] = [], []
            for index in range(args.workers):
                parent, child = ctx.Pipe()
                env_before = {k: os.environ.get(k) for k in
                              ('OPENSSL_armcap', 'OPENSSL_ia32cap', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS')}
                try:
                    os.environ.pop('OPENSSL_armcap', None)
                    os.environ.pop('OPENSSL_ia32cap', None)
                    os.environ['OMP_NUM_THREADS'] = os.environ['OPENBLAS_NUM_THREADS'] = '1'
                    if implementation == 'openssl_armcap0':
                        os.environ['OPENSSL_armcap'] = '0'
                    process = ctx.Process(target=worker,
                        args=(child, implementation, seed, index, barrier))
                    process.start()
                finally:
                    for k, v in env_before.items():
                        if v is None:
                            os.environ.pop(k, None)
                        else:
                            os.environ[k] = v
                child.close()
                processes.append(process)
                pools[implementation].append(parent)
                ready = receive(parent)
                validation[implementation].append(ready['validation'])
                worker_meta[implementation].append(ready['metadata'])
        meta['worker_metadata'] = worker_meta
        write_json(dest / 'metadata.json', meta)
        write_json(dest / 'validation.json', validation)
        current = None
        with (dest / 'raw.csv').open('w', newline='', encoding='utf-8') as raw, \
             (dest / 'execution_order.jsonl').open('w', encoding='utf-8') as actual_order:
            writer = None
            for job in jobs:
                config = job['mode'], job['bytes']
                if config != current:
                    manifest = {}
                    for implementation, conns in pools.items():
                        for conn in conns:
                            conn.send(dict(op='prepare', mode=config[0], bytes=config[1]))
                        manifest[implementation] = [receive(c) for c in conns]
                    # Verify all implementation inputs AND ciphertext hashes agree per worker.
                    if any(m != manifest[implementations[0]] for m in manifest.values()):
                        raise RuntimeError('Cross-implementation input/ciphertext mismatch')
                    manifests[f'{config[0]}:{config[1]}'] = manifest[implementations[0]]
                    write_json(dest / 'inputs.json', manifests)
                    current = config
                actual_order.write(json.dumps(dict(job, event='started')) + '\n')
                actual_order.flush()
                conns = pools[job['implementation']]
                for conn in conns:
                    conn.send(dict(job, op='measure'))
                results = [receive(c) for c in conns]
                envelope = max(r['end_ns'] for r in results) - min(r['start_ns'] for r in results)
                for index, result in enumerate(results):
                    row = dict(session_id=session_id, seed=seed, experiment=experiment,
                               workers=args.workers, worker=index, **job,
                               validation_passed=result['validation_passed'], **result['metrics'],
                               operation_start_ns=result['start_ns'], operation_end_ns=result['end_ns'],
                               aggregate_envelope_ns=envelope if args.workers > 1 else None,
                               throughput_MB_s=job['bytes'] * 1000 / result['metrics']['transform_ns'])
                    if writer is None:
                        writer = csv.DictWriter(raw, fieldnames=list(row))
                        writer.writeheader()
                    writer.writerow(row)
                raw.flush()
                actual_order.write(json.dumps(dict(job, event='completed')) + '\n')
                actual_order.flush()
        meta['status'] = 'complete'
    except BaseException as exc:
        meta['status'], meta['error'] = 'failed', str(exc)
        raise
    finally:
        for conns in pools.values():
            for conn in conns:
                try:
                    conn.send(dict(op='stop'))
                except (BrokenPipeError, EOFError, OSError):
                    pass
                conn.close()
        for process in processes:
            process.join(timeout=5)
            if process.is_alive():
                process.terminate()
                process.join()
        meta['finished_utc'] = datetime.now(timezone.utc).isoformat()
        write_json(dest / 'metadata.json', meta)
    from aggregate import aggregate
    aggregate(dest)
    print(dest, flush=True)
    return dest


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--study', action='store_true', help='Full protocol: seeds 2003-2007, 5 warmups, 20 repetitions')
    p.add_argument('--seed', type=int, choices=SEEDS, help='One independently launched session; default all five for study, 2003 for smoke')
    p.add_argument('--workers', type=int, default=1, help='>1 selects separate multicore experiment')
    p.add_argument('--output', type=Path, default=ROOT / 'results')
    p.add_argument('--notes', default='')
    args = p.parse_args()
    if not 1 <= args.workers <= (os.cpu_count() or 1):
        p.error('workers must be between 1 and logical CPU count')
    for seed in ([args.seed] if args.seed is not None else SEEDS if args.study else [2003]):
        session(args, seed)


if __name__ == '__main__':
    main()
