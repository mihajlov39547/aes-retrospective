"""Isolated sessions; smoke by default. Never resumes or overwrites an output directory."""
import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
import uuid

from engines import CPU, GPU, HERE, REPO, hash_file
from protocol import material, schedule, SEEDS
from validation import validate, reference, require_equal


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, default=str, allow_nan=False)+'\n')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def metadata(cpu, gpu):
    sources = list(HERE.glob('*.py')) + list(HERE.glob('*.c')) + list(HERE.glob('*.cu'))
    sources += [REPO/p for p in ('experiments/aes_cuda_baseline.cu', 'scripts/aes_cuda_baseline.py',
        'scripts/common.py', 'experiments/cpu_baseline_validation/core.py',
        'experiments/cpu_baseline_validation/native.c', 'experiments/cpu_baseline_validation/windows_native.py')]
    info = dict(schema=1, platform=platform.platform(), machine=platform.machine(),
        cpu=platform.processor(), logical_cores=os.cpu_count(), python=sys.version,
        affinity=sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None,
        native=cpu.metadata(), gpu=gpu.info, threads=1,
        packages={p:importlib.metadata.version(p) for p in ('pycryptodome','numpy')},
        source_hashes={str(p.relative_to(REPO)):hash_file(p) for p in sources})
    info['nvrtc_version']=gpu.cp.cuda.nvrtc.getVersion()
    info['cuda_compile_options']=['--std=c++11']
    info['thread_environment']={k:os.environ.get(k) for k in
        ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','CUDA_VISIBLE_DEVICES')}
    info['openssl_environment']={k:os.environ.get(k) for k in
        ('OPENSSL_ia32cap','OPENSSL_armcap','OPENSSL_CONF','OPENSSL_MODULES')}
    for name, path in [('cpuinfo','/proc/cpuinfo'),('boot_id','/proc/sys/kernel/random/boot_id'),
                       ('cpu_quota','/sys/fs/cgroup/cpu.max')]:
        info[name] = Path(path).read_text() if Path(path).exists() else None
    info['gpu_identity'] = subprocess.check_output(['nvidia-smi','--query-gpu=uuid,name,driver_version',
        '--format=csv,noheader'], text=True).strip()
    info['runtime_id'] = os.environ.get('PAGE_BATCH_RUNTIME_ID',str(uuid.uuid4()))
    info['cpu_model'] = next((line.split(':',1)[1].strip() for line in (info['cpuinfo'] or '').splitlines()
                              if line.startswith('model name')), info['cpu'])
    if os.name == 'nt':
        info['cpu_model'] = subprocess.check_output(['powershell','-NoProfile','-Command',
            '(Get-CimInstance Win32_Processor).Name'],text=True).strip()
    # Exclude dynamic /proc CPU MHz values, retaining their raw metadata above.
    stable={k:v for k,v in info.items() if k not in ('cpuinfo',)}
    info['fingerprint'] = digest(json.dumps(stable,sort_keys=True,default=str).encode())
    return info


def session(args):
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    meta = dict(status='initializing', seed=args.seed, profile=args.profile, session_id=str(uuid.uuid4()))
    write(out/'metadata.json',meta)
    try:
        for var in ('OPENSSL_ia32cap','OPENSSL_armcap','OPENSSL_CONF','OPENSSL_MODULES'):
            if var in os.environ:
                raise RuntimeError('Remove OpenSSL override: '+var)
        cpu, gpu = CPU(), GPU()
        expected = args.local_gpu or 'Tesla T4'
        if gpu.info['gpu_name'] != expected or str(gpu.info['compute_capability']) != '75':
            raise RuntimeError('Unexpected GPU: '+str(gpu.info))
        if gpu.cp.cuda.runtime.getDeviceCount() != 1:
            raise RuntimeError('Exactly one visible GPU required')
        if args.profile == 'study' and (args.local_gpu or platform.system() != 'Linux' or
                                       platform.machine() != 'x86_64'):
            raise RuntimeError('Study requires native Linux x86-64 Tesla T4')
        meta.update(metadata(cpu,gpu))
        if meta['native']['cpu_aes_available'] != 1:
            raise RuntimeError('AES CPU capability unavailable; refusing AES-NI study label')
        caps=re.search(r'OPENSSL_ia32cap=(0x[0-9a-fA-F]+)',meta['native']['openssl_cpu_settings'])
        if not caps or not (int(caps[1],16)&(1<<57)):
            raise RuntimeError('OpenSSL AES-NI capability mask not enabled/inspectable')
        write(out/'metadata.json',meta)
        for name in meta['source_hashes']:
            dest=out/'sources'/name
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes((REPO/name).read_bytes())
        write(out/'validation.json',validate(cpu,gpu))
        warmups,repeats = (5,20) if args.profile == 'study' else (1,2)
        plan = schedule(args.seed,warmups,repeats)
        write(out/'planned_order.json',plan)
        rows=[]
        current=None
        cache={}
        nonces=set()
        with (out/'raw.jsonl').open('w') as raw, (out/'execution.jsonl').open('w') as log, (out/'inputs.jsonl').open('w') as inputs:
            for job in plan:
                group=(job['pages'],job['repeat'])
                if group != current:
                    cache.clear()
                    for layout in ('pages','continuous'):
                        data,key,ivs,size=material(args.seed,*group,layout)
                        for iv in ivs:
                            if iv[:12] in nonces:
                                raise RuntimeError('Logical-message nonce reuse')
                            nonces.add(iv[:12])
                        expected_ct=reference(data,key,ivs,size)
                        pair_hash=digest(key+b''.join(ivs)+data)
                        cache[layout]=(data,key,ivs,size,expected_ct,gpu.prepare(layout,key,ivs,data,size),pair_hash)
                        inputs.write(json.dumps(dict(pages=group[0],repeat=group[1],layout=layout,
                            key=key.hex(),ivs=[v.hex() for v in ivs],plaintext_sha256=digest(data),
                            ciphertext_sha256=digest(expected_ct),pair_hash=pair_hash))+'\n')
                        inputs.flush()
                    current=group
                data,key,ivs,size,expected_ct,prepared,pair_hash=cache[job['layout']]
                log.write(json.dumps(dict(job,event='started',wall_ns=time.time_ns()))+'\n'); log.flush()
                # Previous returned output disposal is outside the next operation envelope.
                actual=None
                metrics=None
                if job['measurement']=='cpu':
                    begin=time.perf_counter_ns()
                    actual,metrics=cpu.measure(data,key,ivs,size)
                    metrics['cpu_operation_ns']=time.perf_counter_ns()-begin
                else:
                    metrics=gpu.measure(prepared) if job['measurement']=='pipeline' else gpu.measure_diagnostic(prepared,'resident',1)
                    if job['measurement']=='pipeline':
                        metrics['pipeline_residual_ns']=metrics['end_to_end_ns']-metrics['transfer_ns']-metrics['kernel_ns']
                    actual=prepared[2].tobytes()
                row=dict(job,**metrics,seed=args.seed,session_id=meta['session_id'],pair_hash=pair_hash,
                         plaintext_sha256=digest(data),validated=actual==expected_ct,
                         actual_ciphertext_sha256=digest(actual))
                rows.append(row)
                raw.write(json.dumps(row)+'\n'); raw.flush()
                require_equal(actual,expected_ct)
                log.write(json.dumps(dict(job,event='completed',wall_ns=time.time_ns()))+'\n'); log.flush()
        fields=sorted(set().union(*(r.keys() for r in rows)))
        with (out/'raw.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader(); writer.writerows(rows)
        meta.update(status='complete',warmups=warmups,repeats=repeats,rows=len(rows))
        write(out/'metadata.json',meta)
        from aggregate import summarize
        write(out/'summary.json',summarize(rows))
        print(out)
    except Exception as exc:
        meta.update(status='failed',error=repr(exc)); write(out/'metadata.json',meta)
        raise


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--profile',choices=['smoke','study'],default='smoke')
    p.add_argument('--seed',type=int,choices=SEEDS,default=2003)
    p.add_argument('--local-gpu',choices=['NVIDIA GeForce GTX 1650 Ti'])
    p.add_argument('--output',default=str(HERE/'results'/('smoke-'+str(uuid.uuid4()))))
    p.add_argument('--campaign',action='store_true',help='Explicitly run smoke gate then five fresh study processes')
    args=p.parse_args()
    if args.campaign:
        if args.local_gpu:
            p.error('Local GPU is smoke-only')
        root=Path(args.output); root.mkdir(parents=True,exist_ok=False)
        os.environ['PAGE_BATCH_RUNTIME_ID']=str(uuid.uuid4())
        for seed,profile,name in [(2003,'smoke','gate')]+[(s,'study',str(s)) for s in SEEDS]:
            subprocess.run([sys.executable,__file__,'--profile',profile,'--seed',str(seed),
                            '--output',str(root/name)],check=True)
        from aggregate import campaign
        write(root/'campaign_summary.json',campaign([root/str(s) for s in SEEDS]))
    else:
        session(args)


if __name__=='__main__':
    main()
