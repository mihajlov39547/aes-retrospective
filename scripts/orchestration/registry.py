"""Audited legacy interfaces. `list` serializes this registry as JSON."""
from copy import deepcopy
import sys

SIZES = [1024, 16384, 1048576, 16777216, 33554432]
BASE = dict(sizes=[1024, 1048576, 10485760], warmup=2, repeats=10)
ARTIFACTS = ['metadata.json', 'raw.csv', 'summary.csv', 'results.json', 'validation.json', 'source']


def entry(script, native, defaults, gate, smoke, cuda=False, aesni=False, notes=''):
    return dict(script='scripts/'+script+'.py', native_name=native, classification='CUDA' if cuda else 'CPU',
                required_capabilities=['pycryptodome', 'psutil'] + (['numpy', 'cuda'] if cuda else []) + (['aesni'] if aesni else []),
                required_packages=['pycryptodome', 'psutil'] + (['numpy'] if cuda else []),
                optional_tools=['nvidia-smi'] if cuda else [],
                optional_packages={'matplotlib':'Only required for separate plotting/export tools.'},
                cpu_only_compatible=not cuda, modes=['smoke', 'pilot', 'study'], status='active',
                defaults=defaults, supported_arguments=['run', 'seed', 'output', 'purpose', 'notes', *defaults],
                expected_artifacts=ARTIFACTS + (['report.md'] if native in ('avalanche', 'brute_force_demo') else []) + (['extrapolations.csv'] if native=='brute_force_demo' else []),
                validation=gate, smoke_script='scripts/'+smoke+'.py', historical_notes=notes)


REGISTRY = {
    'cpu_cbc': entry('benchmark', 'benchmark', dict(BASE, aes_backend='software'), 'CBC KAT: five algorithms; software dispatch; round trip outside timers', 'cpu_smoke_check'),
    'cpu_aesni': entry('aes_acceleration', 'aes_acceleration', dict(BASE), 'Six CBC KAT records; both dispatch paths; paired output equality', 'aes_acceleration_smoke_check', aesni=True),
    'cpu_gcm': entry('aes_gcm_benchmark', 'aes_gcm', dict(BASE, sizes=[1024,16384,1048576,16777216,104857600]), 'Four GCM KAT records; tag/ciphertext/AAD rejection; AES-NI dispatch', 'aes_gcm_smoke_check', aesni=True),
    'cuda_baseline': entry('aes_cuda_baseline', 'aes_cuda_baseline', dict(BASE, sizes=SIZES, profile='baseline', measurement='pipeline', host_memory='pinned', resident_iterations=10, modes=['ECB','CTR']), '18 KAT/differential tests before timing; every timed output checked', 'aes_cuda_baseline_smoke_check', cuda=True, notes='Diagnostic profile is smoke/pilot only; pinned pipeline baseline <=32 MiB.'),
    'cuda_paired': entry('aes_cuda_cpu_gpu', 'aes_cuda_cpu_gpu', dict(BASE, sizes=SIZES, warmup=5, repeats=20, profile=['baseline','optimized'], measurements=['resident','pipeline'], resident_iterations=1, host_memory='pinned', modes=['ECB','CTR']), 'All five paths, 18 tests each; dispatch, wrap rejection and cross-backend hashes', 'aes_cuda_cpu_gpu_smoke_check', cuda=True, aesni=True, notes='optimized means v1. T-table is optional timing candidate, validated even when not timed; no T-table final performance results.'),
    'avalanche': entry('avalanche_test', 'avalanche', dict(algorithms=['DES','TDEA','AES-128','AES-192','AES-256'], variants=['plaintext','key'], samples_per_group=8, profile='smoke'), 'Distance, bit mapping, parity, TDEA rejection, reproducibility and statistics', 'avalanche_smoke_check', notes='samples_per_group/--trials, not repeats; not a security test.'),
    'keyspace': entry('brute_force_demo', 'brute_force_demo', dict(reduced_key_bits=8, target_position=['start','middle','end','random'], algorithm='AES-128', mode='ECB', repeats=3, profile='smoke'), 'ECB KAT, bounded searches, no-match, candidate counts and rate formulas', 'brute_force_demo_smoke_check', notes='--bits aliases --reduced-key-bits. No performance warmup. Never inherits global repeats or scales bits.'),
}
REGISTRY['legacy_gpu_scaffold'] = dict(entry('aes_gpu','aes_cpu_gpu',dict(BASE, sizes=SIZES, modes=['ECB','CTR'], threads=128, device=0), 'Incomplete CUDA source; compilation blocker', 'smoke_check', cuda=True), status='disabled', modes=[], historical_notes='Intentionally incomplete; never executable through this orchestrator.')
REGISTRY['exporter'] = dict(script='scripts/export_results.py', status='optional', classification='utility', cpu_only_compatible=True, required_capabilities=['matplotlib'], modes=[], supported_arguments=['run_directory'], defaults={}, expected_artifacts=['*.tex','*.png','*.pdf'], validation='Checks persisted validation for CBC/AES-NI and legacy GPU', historical_notes='Not a benchmark; supports benchmark, aes_acceleration and legacy aes_cpu_gpu only. Run manually on a copy of a completed result.')
REGISTRY['avalanche']['argument_aliases']={'trials':'samples_per_group'}
REGISTRY['keyspace']['argument_aliases']={'bits':'reduced_key_bits'}
REGISTRY['legacy_gpu_scaffold']['supported_arguments'] += ['check','validate-only']
REGISTRY['legacy_gpu_scaffold']['defaults']['sizes']=[1024,16384,1048576,16777216,104857600,1073741824]


def command(experiment, options, seed, purpose, output, root, run=True):
    spec = REGISTRY[experiment]
    if spec['status'] != 'active':
        raise ValueError('Not an executable experiment: '+experiment)
    argv = [sys.executable, str(root/spec['script']), '--seed', str(seed), '--purpose', purpose, '--output', str(output)]
    if run:
        argv.append('--run')
    for key, value in options.items():
        if key not in spec['supported_arguments']:
            raise ValueError('Unsupported argument: '+key)
        argv.append('--'+key.replace('_','-'))
        argv.extend(str(v) for v in (value if isinstance(value,list) else [value]))
    return argv


def defaults(experiment, purpose):
    result = deepcopy(REGISTRY[experiment]['defaults'])
    if purpose == 'smoke':
        for key, value in dict(sizes=[1024], warmup=1, repeats=2).items():
            if key in result and experiment!='keyspace': result[key]=value
    if experiment in ('avalanche','keyspace'):
        result['profile']=purpose
    if experiment=='avalanche': result['samples_per_group']={'smoke':8,'pilot':200,'study':2000}[purpose]
    return result
