"""Paired AES-128 ECB/CTR CPU and CUDA comparison; no legacy results imported."""
from __future__ import annotations

import hashlib
import json
import random
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import aes_cuda_baseline as base
from aes_acceleration import verify_dispatch
from common import parser, positive, print_plan, save_run

OPTIMIZED = base.ROOT / 'experiments' / 'aes_cuda_optimized.cu'
PROTOCOL = base.ROOT / 'experiments' / 'cuda_optimized_cpu_gpu_protocol.md'
METRICS = (*base.METRICS, 'wall_elapsed_ns', 'seconds', 'throughput_MB_s',
           'process_cpu_ns', 'process_to_wall_ratio', 'resident_batch_ns')


def method(args):
    return dict(protocol='cuda-paired-v1', profiles=args.profile, modes=args.modes,
                hardware_execution_path='Explicit CPU software/AES-NI native dispatch and both CUDA kernels; '
                'verified by persisted premeasurement validation for each run.',
                measurements=args.measurements, host_memory='pinned',
                pairing='Same data/key/counter for all jobs of mode/size/repeat; pair hash records identity.',
                order='Size CLI order; modes and backend/measurement jobs seeded-shuffled per repeat.',
                cpu='Explicit use_aesni False/True; dispatch verified separately for ECB/CTR, not instruction trace.',
                cpu_timing='process start, wall start, encrypt(data), wall end, process end. '
                'New output allocation included; construction/key schedule outside; process time is diagnostic, not cycles.',
                gpu_pipeline=base.METHOD['end_to_end_timer'], gpu_kernel_timer=base.METHOD['kernel_timer'],
                gpu_resident='H2D before event interval; N launches over unchanged device input; '
                'event duration/N. N=1 single launch, N>1 batch average. D2H/check after events.',
                resident_iterations=args.resident_iterations,
                gpu_excluded='Compilation, allocation/pinning/staging, key expansion/upload, counter, reference and checks.',
                allocation_asymmetry='CPU output allocated in transform; GPU host/device buffers preallocated. '
                'Practical comparison includes GPU H2D/D2H but excludes setup on both sides.',
                throughput='Payload bytes/1e6/seconds; decimal MB/s. GPU kernel and end-to-end separate.',
                speedup='CPU transform-only median / GPU median: resident kernel for isolated; pipeline end-to-end for practical. '
                'AES-NI is primary CPU reference, software secondary. No speedup from mean throughput.',
                statistics='Per session mean/median/sample SD/min/max/IQR/CV; no outlier removal. '
                'Future study: median of five session medians; speedup median of five session ratios.',
                study='Pending pilot review and user approval; proposed seeds 2003-2007, warmup5 repeats20.',
                scope='Encryption only. ECB primitive benchmark, not secure data protection. '
                'CTR full 128-bit big-endian counter, reject wrap, partial tail supported; no authentication.',
                wall_clock=vars(time.get_clock_info('perf_counter')),
                process_clock=vars(time.get_clock_info('process_time')))


class GPU(base.GPU):
    def __init__(self, profile):
        if profile not in ('baseline', 'optimized'):
            raise ValueError('Explicit baseline/optimized required')
        super().__init__()
        self.profile = profile
        if profile == 'optimized':
            self.module = self.cp.RawModule(code=OPTIMIZED.read_text(encoding='utf-8'), options=('--std=c++11',))
            self.expand = self.module.get_function('expand_key')
            self.kernels = {m:self.module.get_function('aes_' + m.lower() + '_optimized') for m in base.EXPECTED}


class CPU:
    def __init__(self, backend):
        if backend not in ('software', 'aesni'):
            raise ValueError('Explicit CPU backend required')
        self.backend = backend

    def cipher(self, mode, key, counter, data):
        from Crypto.Cipher import AES
        base.check_input(mode, key, counter, len(data))
        opts = dict(nonce=b'', initial_value=int.from_bytes(counter,'big')) if mode=='CTR' else {}
        return AES.new(key, getattr(AES,'MODE_'+mode), use_aesni=self.backend=='aesni', **opts)

    def encrypt(self, mode, key, counter, data):
        return self.cipher(mode,key,counter,data).encrypt(data)


def validate(gpus, session, purpose):
    report = dict(session_id=session, purpose=purpose, passed=False,
                  started_utc=datetime.now(timezone.utc).isoformat(), paths={}, dispatch={})
    try:
        for mode in ('ECB','CTR'):
            report['dispatch'][mode] = verify_dispatch(mode)
        paths = {'cpu_software':CPU('software'), 'cpu_aesni':CPU('aesni'),
                 **{'cuda_'+k:v for k,v in gpus.items()}}
        # Reuse the exact 18 KAT/differential cases on every encryption path.
        # Legacy validator calls its tested-path flag "cuda_passed", even for adapters.
        for name, path in paths.items():
            evidence = base.validate(path, session, purpose)
            for test in evidence['tests']:
                test['tested_path_passed'] = test.pop('cuda_passed')
            report['paths'][name] = evidence
            if not evidence['passed']:
                raise RuntimeError('Functional validation failed: '+name)
            try:
                path.encrypt('CTR', base.KEY, (2**128-1).to_bytes(16,'big'), bytes(17))
            except ValueError:
                evidence['wrap_rejected'] = True
            else:
                raise RuntimeError('Counter wrap accepted: '+name)
        hashes = [[t['actual_sha256'] for t in x['tests']] for x in report['paths'].values()]
        if not all(h == hashes[0] for h in hashes):
            raise RuntimeError('Cross-backend validation mismatch')
        report.update(all_backends_equal=True, passed=True)
    except Exception as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
    report['completed_utc'] = datetime.now(timezone.utc).isoformat()
    return report


def material(rng, size):
    # One synthetic message is replayed identically across all paired backends.
    return rng.randbytes(size), rng.randbytes(16), rng.randbytes(8)+bytes(8)


def cpu_measure(cpu, mode, key, counter, data):
    cipher = cpu.cipher(mode,key,counter,data)
    process_start = time.process_time_ns()
    wall_start = time.perf_counter_ns()
    output = cipher.encrypt(data)
    wall = time.perf_counter_ns()-wall_start
    process = time.process_time_ns()-process_start
    if wall <= 0:
        raise RuntimeError('Nonpositive CPU timer')
    return output, dict(wall_elapsed_ns=wall, seconds=wall/1e9, throughput_MB_s=len(data)*1e3/wall,
                        process_cpu_ns=process, process_to_wall_ratio=process/wall)


def summarize(raw):
    summaries=[]
    for backend,mode,size,measurement in sorted({(r['backend'],r['mode'],r['bytes'],r['measurement']) for r in raw}):
        group=[r for r in raw if (r['backend'],r['mode'],r['bytes'],r['measurement'])==(backend,mode,size,measurement)]
        row={k:group[0][k] for k in ('session_id','algorithm','backend','profile','mode','bytes',
                                    'measurement','host_memory','resident_iterations','seed')}
        for metric in METRICS:
            row.update({metric+'_'+k:v for k,v in base.extended_stats([r[metric] for r in group if r[metric] is not None]).items()})
        summaries.append(row)
    for row in summaries:
        for cpu in ('cpu_aesni','cpu_software'):
            for scope in ('isolated','pipeline'):
                row['speedup_'+scope+'_vs_'+cpu]=None
            if not row['backend'].startswith('cuda_'):
                continue
            numerator=next(r['seconds_median'] for r in summaries if r['backend']==cpu and
                           (r['mode'],r['bytes'])==(row['mode'],row['bytes']))
            scope='isolated' if row['measurement']=='resident' else 'pipeline'
            denominator=row['kernel_seconds_median'] if scope=='isolated' else row['end_to_end_seconds_median']
            row['speedup_'+scope+'_vs_'+cpu]=numerator/denominator
    return summaries


def run(args, gpus=None, validator=validate):
    # Both kernels are always validated even when only one profile is timed.
    gpus = {p:GPU(p) for p in ('baseline','optimized')} if gpus is None else gpus
    session=str(uuid.uuid4())
    gate=args.output.resolve()/('aes_cuda_cpu_gpu-validation-'+session)
    gate.mkdir(parents=True,exist_ok=False)
    report=validator(gpus,session,args.purpose)
    base.write_json(gate/'validation.json',report)
    if report.get('passed') is not True:
        raise RuntimeError('Validation failed; no performance export: '+str(gate))
    before=base.telemetry(gpus['baseline'])
    rng,order=random.Random(args.seed),random.Random(args.seed)
    raw=[]
    for size in args.sizes:
        for repeat in range(-args.warmup,args.repeats):
            modes=list(args.modes); order.shuffle(modes)
            for mode in modes:
                data,key,counter=material(rng,size)
                expected=base.reference(mode,key,counter,data)
                pair_id=f'{size}:{mode}:{repeat}'
                pair_hash=hashlib.sha256(key+counter+data).hexdigest()
                jobs=[('cpu_software','transform'),('cpu_aesni','transform')]
                jobs += [('cuda_'+p,m) for p in args.profile for m in args.measurements]
                order.shuffle(jobs)
                for job_order,(backend,measurement) in enumerate(jobs):
                    timing=dict.fromkeys(METRICS)
                    if backend.startswith('cpu_'):
                        output,measured=cpu_measure(CPU(backend[4:]),mode,key,counter,data)
                    else:
                        gpu=gpus[backend[5:]]
                        job=gpu.prepare(mode,key,counter,data)
                        measured=gpu.measure_diagnostic(job,measurement,args.resident_iterations)
                        output=job[2].tobytes()
                    if output!=expected:
                        raise RuntimeError('Measured output mismatch: '+backend+'; no performance export')
                    if repeat>=0:
                        timing.update(measured)
                        raw.append(dict(session_id=session,seed=args.seed,algorithm='AES-128',operation='encrypt',
                                        backend=backend,profile=backend[5:] if backend.startswith('cuda_') else backend[4:],
                                        measurement=measurement,host_memory='pinned' if backend.startswith('cuda_') else 'bytes',
                                        mode=mode,bytes=size,repeat=repeat,pair_id=pair_id,pair_sha256=pair_hash,
                                        job_order=job_order,global_order=len(raw),validation_checked=True,
                                        resident_iterations=args.resident_iterations if measurement=='resident' else None,**timing))
                    # Release previous outputs/buffers outside the next timed call.
                    del output
                    if backend.startswith('cuda_'):
                        del job
    after=base.telemetry(gpus['baseline'])
    directory=save_run('aes_cuda_cpu_gpu',args,method(args),raw,summarize(raw))
    shutil.copy2(gate/'validation.json',directory/'validation.json')
    source=directory/'source'; source.mkdir()
    paths=[Path(__file__),Path(__file__).with_name('aes_cuda_cpu_gpu_smoke_check.py'),base.KERNEL,OPTIMIZED,PROTOCOL]
    # Include local transitive imports needed to replay the archived harness.
    paths += [Path(__file__).with_name(n) for n in ('aes_cuda_baseline.py','aes_acceleration.py',
                                                  'common.py','cpu_validation.py','benchmark.py')]
    hashes={}
    for path in paths:
        shutil.copy2(path,source/path.name); hashes[path.name]=base.digest(source/path.name)
    meta=json.loads((directory/'metadata.json').read_text())
    meta.update(schema_version=1,session_id=session,gpu=gpus['baseline'].info,
                validation_passed=True, cpu_dispatch=report.get('dispatch'),
                source_sha256=hashes,kernel_sha256={p:hashes['aes_cuda_'+p+'.cu'] for p in ('baseline','optimized')},
                validation_sha256=base.digest(directory/'validation.json'),validation_file='validation.json',
                environment_before=before,environment_after=after,backends=sorted({r['backend'] for r in raw}))
    base.write_json(directory/'metadata.json',meta)
    return directory


def arguments(argv=None):
    p=parser(__doc__)
    p.add_argument('--profile',nargs='+',choices=['baseline','optimized'],default=['baseline','optimized'])
    p.add_argument('--measurements',nargs='+',choices=['pipeline','resident'],default=['pipeline','resident'])
    p.add_argument('--host-memory',choices=['pinned'],default='pinned')
    p.add_argument('--modes',nargs='+',choices=['ECB','CTR'],default=['ECB','CTR'])
    p.add_argument('--sizes',nargs='+',type=positive,default=list(base.SIZES))
    p.add_argument('--warmup',type=int,default=5)
    p.add_argument('--repeats',type=positive,default=20)
    p.add_argument('--resident-iterations',type=positive,default=1)
    args=p.parse_args(argv)
    if args.warmup<0 or args.repeats<2:
        p.error('Nonnegative warmup and at least two repeats required')
    for name in ('profile','measurements','modes','sizes'):
        values=getattr(args,name)
        if len(values)!=len(set(values)):
            p.error('Duplicate '+name)
    if max(args.sizes)>33554432 or ('ECB' in args.modes and any(n%16 for n in args.sizes)):
        p.error('Sizes <=32 MiB required; ECB sizes must be aligned')
    if 'resident' not in args.measurements and args.resident_iterations!=1:
        p.error('Batch iterations require resident measurement')
    return args


if __name__=='__main__':
    args=arguments()
    if not print_plan('aes_cuda_cpu_gpu',args,method(args)):
        run(args)
