"""Best-effort telemetry without benchmark imports or buffer allocations."""
import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from .configuration import ROOT


def probe(argv, env=None):
    try:
        p=subprocess.run(argv,cwd=ROOT,env=env,capture_output=True,text=True,timeout=20)
        return p.stdout.strip() if p.returncode==0 else None
    except (OSError,subprocess.SubprocessError): return None


def child_environment(config):
    env=os.environ.copy()
    if config.get('cuda_device') is not None: env['CUDA_VISIBLE_DEVICES']=str(config['cuda_device'])
    return env


FINGERPRINT_FIELDS=('os','release','kernel','architecture','host_id','python_version','cpu','physical_cpus','logical_cpus','ram_bytes','cpu_features','packages','gpus','cuda')


def fingerprint(environment):
    selected={k:environment.get(k) for k in FINGERPRINT_FIELDS}
    # Exclude volatile telemetry, available memory and probe failures.
    selected['gpus']=[{k:g.get(k) for k in ('name','local_id','compute_cap','memory.total','driver_version','driver_model.current')} for g in environment.get('gpus',[])]
    selected['cuda']={k:environment.get('cuda',{}).get(k) for k in ('available','name','compute_capability','vram_bytes','driver_version','runtime_version','cupy_version','pci_bus_id')}
    return hashlib.sha256(json.dumps(selected,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:24]


def detect(config=None):
    config=config or {}
    result=dict(os=platform.system(),release=platform.release(),kernel=platform.version(),architecture=platform.machine(),
                host_id=hashlib.sha256(('aes-orchestrator:'+platform.node()).encode()).hexdigest()[:24],
                python_version=platform.python_version(),python_executable=sys.executable,cpu=platform.processor() or None,
                physical_cpus=None,logical_cpus=os.cpu_count(),ram_bytes=None,available_ram_bytes=None,
                cpu_features={'aesni':None,'vaes':None},packages={},gpus=[],cuda={},cloud=config.get('cloud'),cloud_source='explicit' if config.get('cloud') else None,telemetry_errors=[])
    for package in ('pycryptodome','psutil','matplotlib','numpy','cupy','cupy-cuda11x','cupy-cuda12x','cupy-cuda13x','nvidia-cuda-runtime-cu12','nvidia-cuda-nvrtc-cu12'):
        try: result['packages'][package]=importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError: result['packages'][package]=None
    imports=probe([sys.executable,'-c',"""import json
result={}
for name,code in [('pycryptodome','from Crypto.Cipher import AES, DES, DES3'),('psutil','import psutil'),('numpy','import numpy')]:
 try: exec(code); result[name]=True
 except Exception: result[name]=False
print(json.dumps(result))
"""])
    result['package_imports']=json.loads(imports) if imports else {}
    result['optional_telemetry_tools']=['nvidia-smi']
    try:
        import psutil
        result.update(physical_cpus=psutil.cpu_count(logical=False),ram_bytes=psutil.virtual_memory().total,available_ram_bytes=psutil.virtual_memory().available)
    except ImportError: pass
    if os.name=='nt':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:
                result['cpu']=winreg.QueryValueEx(key,'ProcessorNameString')[0].strip()
        except OSError: pass
    elif Path('/proc/cpuinfo').exists():
        fields=dict(line.split(':',1) for line in Path('/proc/cpuinfo').read_text().splitlines() if ':' in line)
        fields={k.strip():v.strip() for k,v in fields.items()}
        result['cpu']=fields.get('model name',result['cpu'])
        flags=fields.get('flags','').split()
        if flags: result['cpu_features'].update(aesni='aes' in flags,vaes='vaes' in flags)
    aes=probe([sys.executable,'-c','from Crypto.Cipher import AES; print(int(bool(AES._cpu_features.have_aes_ni() and AES._raw_aesni_lib)))'])
    if aes in ('0','1'): result['cpu_features']['aesni']=aes=='1'
    basic=['index','name','uuid','memory.total','driver_version']
    raw=probe(['nvidia-smi','--query-gpu='+','.join(basic),'--format=csv,noheader,nounits'])
    if raw:
        for row in csv.reader(raw.splitlines()):
            gpu=dict(zip(basic,(v.strip() for v in row)))
            uuid=gpu.pop('uuid')
            gpu['local_id']=hashlib.sha256(uuid.encode()).hexdigest()[:24]
            for field in ('compute_cap','memory.free','driver_model.current','pcie.link.gen.current','pcie.link.width.current','power.limit','clocks.current.graphics','clocks.current.memory'):
                value=probe(['nvidia-smi','-i',uuid,'--query-gpu='+field,'--format=csv,noheader,nounits'])
                gpu[field]=None if not value or 'N/A' in value or 'Not Supported' in value else value
            result['gpus'].append(gpu)
    else: result['telemetry_errors'].append('nvidia-smi unavailable or query failed')
    # A separate interpreter discovers the selected CUDA device, never compiles kernels.
    code='''import json, os, importlib.metadata, ctypes
from pathlib import Path
handles=[]
if os.name=='nt':
 for package,folder in [('nvidia-cuda-runtime-cu12','cuda_runtime'),('nvidia-cuda-nvrtc-cu12','cuda_nvrtc')]:
  try: p=Path(importlib.metadata.distribution(package).locate_file('nvidia'))/folder
  except importlib.metadata.PackageNotFoundError: continue
  if (p/'bin').is_dir():
   handles.append(os.add_dll_directory(str(p/'bin')))
   if folder=='cuda_runtime': os.environ.setdefault('CUDA_PATH',str(p))
import cupy as cp
d=cp.cuda.Device(); p=cp.cuda.runtime.getDeviceProperties(d.id)
print(json.dumps(dict(available=True,name=p['name'].decode() if isinstance(p['name'],bytes) else p['name'],compute_capability=d.compute_capability,vram_bytes=p['totalGlobalMem'],driver_version=cp.cuda.runtime.driverGetVersion(),runtime_version=cp.cuda.runtime.runtimeGetVersion(),cupy_version=cp.__version__,pci_bus_id=d.pci_bus_id)))
'''
    raw=probe([sys.executable,'-c',code],child_environment(config))
    try: result['cuda']=json.loads(raw) if raw else {'available':False,'reason':'CuPy/device/runtime discovery failed; no kernel validation attempted'}
    except ValueError: result['cuda']={'available':False,'reason':'Invalid discovery response'}
    result['git']={k:probe(['git',*args]) for k,args in dict(commit=['rev-parse','HEAD'],branch=['rev-parse','--abbrev-ref','HEAD'],working_tree=['status','--porcelain']).items()}
    result['fingerprint']=fingerprint(result)
    result['fingerprint_fields']=list(FINGERPRINT_FIELDS)
    return result
