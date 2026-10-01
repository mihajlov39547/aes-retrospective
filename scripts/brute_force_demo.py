"""Educational CPU reduced-keyspace exhaustive search, not full-space cryptanalysis."""
import hashlib
import json
import math
import random
import shutil
import uuid
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path
from time import perf_counter_ns, get_clock_info

from Crypto.Cipher import AES
from common import parser, positive, print_plan, save_run, stats, write_csv

POSITIONS = ('start', 'middle', 'end', 'random')
PLAINTEXT = bytes.fromhex('6bc1bee22e409f96e93d7e117393172aae2d8a571e03ac9c9eb76fac45af8e51')
SOURCE = 'https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38a.pdf'
WARNING = ('Linear extrapolation under fixed-rate assumption, not an implementation of full-space search; '
           'not a cryptanalytic attack evaluation. AES/Python candidate rate is not DES/TDEA or GPU search rate.')
SPACES = [('DES',56,'Effective DES key space, parity excluded; DES is not measured.'),
          ('Double-DES nominal',112,'Nominal two-key space; meet-in-the-middle changes the attack model.'),
          ('Three-key TDEA nominal',168,'Nominal three-component space, not 168-bit security; special attacks apply. '
           'No TDEA candidate checker or 112-bit attack model is measured.'),
          ('AES-128',128,'AES-128 nominal space; fixed-rate illustration only.'),
          ('AES-192',192,'AES-192 is not measured; different key schedule and round count.'),
          ('AES-256',256,'AES-256 is not measured; different key schedule and round count.')]


def reduced_key(number: int) -> bytes:
    if not 0 <= number < 2**128:
        raise ValueError('AES-128 index out of range')
    return number.to_bytes(16, 'big')


def encrypt(key, plaintext=PLAINTEXT):
    return AES.new(key, AES.MODE_ECB, use_aesni=False).encrypt(plaintext)


def target_index(position, bits, rng):
    n=1<<bits
    if position=='random': return rng.randrange(n)
    return {'start':0, 'middle':n//2, 'end':n-1}[position]


def search(bits, expected):
    if not 1 <= bits <= 28 or len(expected)!=len(PLAINTEXT):
        raise ValueError('Bounded space and two-block ciphertext required')
    for candidate in range(1<<bits):
        if encrypt(reduced_key(candidate))==expected:
            return candidate, candidate+1
    return None, 1<<bits


def rates(checked, elapsed_ns, size):
    if checked < 1 or checked > size or elapsed_ns <= 0:
        raise ValueError('Invalid count/timer')
    seconds=elapsed_ns/1e9
    rate=checked/seconds
    return dict(elapsed_seconds=seconds,candidates_per_second=rate,
                expected_full_scan_time=size/rate, expected_half_scan_time=(size/2)/rate,
                expected_uniform_hit_time=((size+1)/2)/rate)


def extrapolate(rate):
    if not math.isfinite(rate) or rate<=0: raise ValueError('Positive finite rate required')
    rows=[]
    with localcontext() as ctx:
        ctx.prec=120
        speed=Decimal(str(rate))
        for name,bits,note in SPACES:
            n=1<<bits
            for extent,count in [('full',Decimal(n)),('half',Decimal(n)/2),('uniform_expected',(Decimal(n)+1)/2)]:
                seconds=count/speed
                rows.append(dict(space=name,keyspace_bits=bits,keyspace_size=n,extent=extent,
                                 candidate_count=str(count),assumed_candidates_per_second=str(speed),
                                 seconds=format(seconds,'.8E'),days=format(seconds/86400,'.8E'),
                                 years=format(seconds/Decimal(31557600),'.8E'),note=note,scope=WARNING))
    return rows


def validate(session, purpose):
    report=dict(session_id=session,purpose=purpose,passed=False,tests=[],timestamp=datetime.now(timezone.utc).isoformat())
    def check(name, condition):
        report['tests'].append(dict(test=name,passed=bool(condition)))
        if not condition: raise RuntimeError(name)
    try:
        key=bytes.fromhex('2b7e151628aed2a6abf7158809cf4f3c')
        expected=bytes.fromhex('3ad77bb40d7a3660a89ecaf32466ef97f5d3d58503b9699de785895a96fdbaaf')
        report['kat']=dict(source=SOURCE,section='F.1.1, first two blocks',key=key.hex(),
                           plaintext=PLAINTEXT.hex(),expected_ciphertext=expected.hex())
        check('NIST AES-128 ECB KAT',encrypt(key)==expected)
        check('Key mapping',reduced_key(0)==bytes(16) and reduced_key(257)==bytes(14)+bytes([1,1]))
        for bits in (1,4,8):
            for pos in POSITIONS:
                index=target_index(pos,bits,random.Random(2003))
                found,checked=search(bits,encrypt(reduced_key(index)))
                check(f'{bits}/{pos}: index and exact count',found==index and checked==index+1)
        outputs={encrypt(reduced_key(i)) for i in range(256)}
        wrong=bytes(32)
        while wrong in outputs:
            wrong=(int.from_bytes(wrong,'big')+1).to_bytes(32,'big')
        check('Wrong ciphertext, complete no-hit scan',search(8,wrong)==(None,256))
        a=random.Random(2003); b=random.Random(2003)
        check('Seed reproducibility',[target_index('random',8,a) for _ in range(10)]==[target_index('random',8,b) for _ in range(10)])
        r=rates(128,500000000,256)
        check('Wall formula and full/half',r['candidates_per_second']==256 and r['expected_full_scan_time']==1 and r['expected_half_scan_time']==0.5)
        e=extrapolate(1)
        check('Integer spaces and exact expected counts',all(isinstance(x['keyspace_size'],int) and x['keyspace_size']==1<<x['keyspace_bits'] for x in e))
        with localcontext() as ctx:
            ctx.prec=120
            for bits in (56,112,168,128,192,256):
                g=[x for x in e if x['keyspace_bits']==bits]
                counts={x['extent']:Decimal(x['candidate_count']) for x in g}
                check(f'Full/half/uniform {bits}',counts['full']==2*counts['half'] and counts['uniform_expected']==counts['half']+Decimal('0.5'))
        report['passed']=True
    except Exception as exc:
        report['error']=str(exc)
    report['completed_utc']=datetime.now(timezone.utc).isoformat()
    return report


def method(args):
    return dict(algorithm='AES-128',mode='ECB',backend='software',use_aesni=False,
                reduced_key_bits=args.reduced_key_bits,keyspace_size=1<<args.reduced_key_bits,
                plaintext_hex=PLAINTEXT.hex(),mapping='128-bit big-endian candidate, low b bits variable, upper bits zero',
                timed='Sequential search: integer enumeration, key conversion, new cipher/key schedule per candidate, two-block encryption, output allocation and comparison; stop at first match.',
                excluded='Target/reference construction, validation, post-checks and export',
                wall_timer=vars(get_clock_info('perf_counter')),warmup='Functional gate primes library; no separate timed warmup',
                expected_half='N/(2r) approximation; exact uniform successful-search expectation (N+1)/(2r) also exported',
                hardware_execution_path='PyCryptodome CPU AES with explicit use_aesni=False; no GPU; no instruction trace claimed',
                scenario_order='CLI order; seed controls random target sequence',extrapolation=WARNING,
                short_search_note='Start target tests correctness/latency, not sustained rate. Use end scenario for extrapolation.')


def write_json(path,obj):
    path.write_text(json.dumps(obj,indent=2,default=str,allow_nan=False)+'\n',encoding='utf-8')


def run(args, validator=validate):
    session=str(uuid.uuid4()); gate=args.output.resolve()/('brute_force_demo-validation-'+session)
    gate.mkdir(parents=True,exist_ok=False)
    report=validator(session,args.purpose);write_json(gate/'validation.json',report)
    if report.get('passed') is not True: raise RuntimeError('Validation failed; no performance output: '+str(gate))
    rng=random.Random(args.seed);raw=[];size=1<<args.reduced_key_bits
    for repeat in range(args.repeats):
        for pos in args.target_position:
            index=target_index(pos,args.reduced_key_bits,rng)
            expected=encrypt(reduced_key(index))
            start=perf_counter_ns()
            found,checked=search(args.reduced_key_bits,expected)
            elapsed=perf_counter_ns()-start
            if found!=index or checked!=index+1: raise RuntimeError('Search correctness failure; no export')
            raw.append(dict(session_id=session,algorithm='AES-128',mode='ECB',backend='software',
                            seed=args.seed,repeat=repeat,scenario=pos,reduced_key_bits=args.reduced_key_bits,
                            keyspace_size=size,target_index=index,found_index=found,found=True,
                            candidates_checked=checked,wall_elapsed_ns=elapsed,**rates(checked,elapsed,size)))
    summary=[]
    for pos in args.target_position:
        group=[r for r in raw if r['scenario']==pos]
        row=dict(session_id=session,algorithm='AES-128',mode='ECB',scenario=pos,reduced_key_bits=args.reduced_key_bits,keyspace_size=size)
        for metric in ('candidates_checked','elapsed_seconds','candidates_per_second','expected_full_scan_time','expected_half_scan_time','expected_uniform_hit_time'):
            row.update({metric+'_'+k:v for k,v in stats([r[metric] for r in group]).items()})
        summary.append(row)
    # Never pool very short early-stop searches into the illustrative sustained rate.
    basis=next((r for r in summary if r['scenario']=='end'),max(summary,key=lambda r:r['candidates_checked_median']))
    rate=basis['candidates_per_second_median']
    info=method(args);info['extrapolation_rate_basis']=dict(scenario=basis['scenario'],statistic='median of repeat rates',rate=rate,
                                                          full_scan_measured=basis['scenario']=='end')
    directory=save_run('brute_force_demo',args,info,raw,summary)
    shutil.copy2(gate/'validation.json',directory/'validation.json')
    write_csv(directory/'extrapolations.csv',extrapolate(rate))
    source=directory/'source';source.mkdir();hashes={}
    for path in (Path(__file__),Path(__file__).with_name('common.py'),Path(__file__).with_name('brute_force_demo_smoke_check.py')):
        shutil.copy2(path,source/path.name);hashes[path.name]=hashlib.sha256((source/path.name).read_bytes()).hexdigest()
    meta=json.loads((directory/'metadata.json').read_text())
    meta.update(session_id=session,algorithm='AES-128',mode='ECB',reduced_key_bits=args.reduced_key_bits,keyspace_size=size,
                validation_passed=True,validation_sha256=hashlib.sha256((directory/'validation.json').read_bytes()).hexdigest(),
                source_sha256=hashes,measurements=[{k:r[k] for k in ('scenario','repeat','target_index','candidates_checked','candidates_per_second')} for r in raw])
    write_json(directory/'metadata.json',meta)
    lines=['# Educational reduced-keyspace exhaustive search demonstration','',f'Purpose: {args.purpose}; CPU software AES-128, ECB, fixed two-block plaintext.',
           f'Actually searched: {args.reduced_key_bits} variable bits, {size} candidates; upper key bits zero.',
           'Each row measures a stop-on-match search; end targets traverse the entire reduced space.',
           '', '| Scenario | Median candidates | Median seconds | Median candidates/s |','|---|---:|---:|---:|']
    lines += [f"| {r['scenario']} | {r['candidates_checked_median']} | {r['elapsed_seconds_median']:.6g} | {r['candidates_per_second_median']:.6g} |" for r in summary]
    lines += ['',f"Extrapolation rate: {rate:.6g} candidates/s from {basis['scenario']} median repeat rate.",
              'Start and short searches are overhead-sensitive; partial-scan projections are not measured full scans.',
              'Full=N/r; half=N/(2r); exact uniform first-hit expectation=(N+1)/(2r).',
              'No pooling of positions or automatic outlier deletion. Year=365.25 days.',WARNING,
              'Double-DES nominal 112 bits has MITM alternatives. TDEA nominal 168 bits is not a security-strength claim.',
              'Software/native library and Python setup dominate this workload; fixed-key CUDA MB/s cannot be converted into candidate-check rate.',
              '', '| Space | Extent | Seconds | Days | Years |','|---|---|---:|---:|---:|']
    lines += [f"| {r['space']} | {r['extent']} | {r['seconds']} | {r['days']} | {r['years']} |" for r in extrapolate(rate)]
    (directory/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return directory


def arguments(argv=None):
    cli=parser(__doc__);cli.set_defaults(purpose=None)
    cli.add_argument('--profile',choices=('smoke','pilot','study'),default='smoke')
    cli.add_argument('--reduced-key-bits','--bits',dest='reduced_key_bits',type=positive)
    cli.add_argument('--target-position',nargs='+',choices=POSITIONS,default=list(POSITIONS))
    cli.add_argument('--algorithm',choices=['AES-128'],default='AES-128')
    cli.add_argument('--mode',choices=['ECB'],default='ECB')
    cli.add_argument('--repeats',type=positive,default=3)
    args=cli.parse_args(argv)
    if args.purpose is None: args.purpose=args.profile
    if args.purpose!=args.profile: cli.error('Purpose must match profile')
    if args.reduced_key_bits is None: args.reduced_key_bits={'smoke':8,'pilot':20,'study':24}[args.profile]
    if args.reduced_key_bits>{'smoke':12,'pilot':22,'study':28}[args.profile]: cli.error('Keyspace exceeds explicit profile cap')
    if len(set(args.target_position))!=len(args.target_position): cli.error('Duplicate target positions')
    return args


if __name__=='__main__':
    args=arguments()
    if not print_plan('brute_force_demo',args,method(args)): run(args)
