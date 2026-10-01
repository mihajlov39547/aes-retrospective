"""Single-block empirical diffusion distributions; not a security proof."""
import hashlib
import json
import random
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from common import cipher, parser, positive, print_plan, save_run, stats

ALGORITHMS = ('DES', 'TDEA', 'AES-128', 'AES-192', 'AES-256')
KEY_BYTES = dict(zip(ALGORITHMS, (8, 24, 16, 24, 32)))
WARNING = 'Diffusion indicator, normalized by block size; not a proof of cryptographic security or a complete SAC test.'


def flip(value, position):
    if not 0 <= position < len(value)*8:
        raise ValueError('Bit outside input')
    changed = bytearray(value)
    changed[position//8] ^= 1 << (position%8)
    return bytes(changed)


def distance(left, right):
    if len(left) != len(right):
        raise ValueError('Hamming distance requires equal lengths')
    return sum((a ^ b).bit_count() for a, b in zip(left, right))


def effective(key):
    return bytes(b & 254 for b in key)


def parity(key):
    return bytes((b & 254) | (1 ^ ((b & 254).bit_count() % 2)) for b in key)


def positions(name):
    return [i for i in range(KEY_BYTES[name]*8) if name not in ('DES', 'TDEA') or i%8 != 0]


def encrypt(name, key, plaintext):
    return cipher('3DES' if name == 'TDEA' else name, key, 'ECB', aes_backend='software').encrypt(plaintext)


def audit_record(audit, stage, key, sample_id):
    """Count every initial/modified TDEA proposal; require three effective keys."""
    audit['generated'] += 1
    reason = None
    components = [effective(key[i:i+8]) for i in (0, 8, 16)]
    if len(set(components)) != 3:
        reason = 'Repeated effective component; not three independent TDEA keys'
    else:
        try:
            cipher('3DES', parity(key), 'ECB')
        except ValueError as exc:
            reason = str(exc)
    if reason:
        audit['rejected'] += 1
        audit['rejections'].append(dict(stage=stage, sample_id=sample_id, reason=reason))
        return False
    audit['accepted'] += 1
    return True


def new_audit():
    return dict(generated=0, rejected=0, accepted=0, rejections=[])


def new_key(name, rng, audit, sample_id):
    for _ in range(1000):
        key = rng.randbytes(KEY_BYTES[name])
        if name in ('DES', 'TDEA'):
            key = parity(key)
        if name != 'TDEA' or audit_record(audit, 'initial', key, sample_id):
            return key
    raise RuntimeError('TDEA initial-key rejection limit; no statistics exported')


def changed_key(name, key, rng, audit, sample_id):
    for _ in range(1000):
        bit = rng.choice(positions(name))
        changed = flip(key, bit)
        if name in ('DES', 'TDEA'):
            changed = parity(changed)
        if name != 'TDEA' or audit_record(audit, 'key_flip', changed, sample_id):
            return changed, bit
    raise RuntimeError('TDEA key-flip rejection limit; no statistics exported')


def quantile(values, probability):
    ordered = sorted(values)
    index = (len(ordered)-1)*probability
    lo = int(index)
    hi = min(lo+1, len(ordered)-1)
    return ordered[lo]+(ordered[hi]-ordered[lo])*(index-lo)


def summarize(raw):
    summary = []
    for name, variant in dict.fromkeys((r['algorithm'], r['variant']) for r in raw):
        selected = [r for r in raw if r['algorithm']==name and r['variant']==variant]
        values = [r['hamming_distance_bits'] for r in selected]
        normalized = stats([r['normalized_distance'] for r in selected])
        summary.append(dict(algorithm=name, variant=variant, **stats(values),
                            **{'q'+str(q).zfill(2):quantile(values, q/100) for q in (5,25,75,95)},
                            mean_normalized=normalized['mean'], median_normalized=normalized['median'],
                            stdev_normalized=normalized['stdev'], skipped_count=0))
    return summary


def collect(args):
    rng = random.Random(args.seed)
    audit = new_audit()
    raw = []
    for name in args.algorithms:
        width = 64 if name in ('DES', 'TDEA') else 128
        for sample in range(args.samples_per_group):
            plaintext = rng.randbytes(width//8)
            key = new_key(name, rng, audit, sample)
            baseline = encrypt(name, key, plaintext)
            for variant in args.variants:
                if variant == 'plaintext':
                    bit = rng.randrange(width)
                    changed = encrypt(name, key, flip(plaintext, bit))
                else:
                    changed, bit = changed_key(name, key, rng, audit, sample)
                    changed = encrypt(name, changed, plaintext)
                hamming = distance(baseline, changed)
                raw.append(dict(algorithm=name, variant=variant+'_bit_flip', sample_id=sample,
                                block_bits=width, effective_key_bits=len(positions(name)),
                                flipped_bit_index=bit, hamming_distance_bits=hamming,
                                normalized_distance=hamming/width, seed=args.seed, status='accepted', skip_reason=''))
    return raw, audit


def validate():
    report = dict(passed=False, timestamp=datetime.now(timezone.utc).isoformat(), tests=[])
    def check(name, condition):
        report['tests'].append(dict(test=name, passed=bool(condition)))
        if not condition:
            raise ValueError(name)
    try:
        check('Known Hamming distances', distance(b'\x00\xff', b'\xff\x00')==16 and distance(b'a',b'a')==0)
        try:
            distance(b'a', b'aa')
        except ValueError:
            unequal_rejected = True
        else:
            unequal_rejected = False
        check('Unequal lengths rejected', unequal_rejected)
        rng = random.Random(2003)
        audit = new_audit()
        for name in ALGORITHMS:
            key = new_key(name, rng, audit, 0)
            width = 8 if name in ('DES', 'TDEA') else 16
            p = rng.randbytes(width)
            check(name+' key/block length', len(key)==KEY_BYTES[name] and len(encrypt(name,key,p))==width)
            check(name+' every plaintext bit', all(distance(p,flip(p,i))==1 for i in range(width*8)))
            for i in positions(name):
                changed = flip(key,i)
                if name in ('DES','TDEA'):
                    changed = parity(changed)
                    check(name+f' effective bit {i}', i%8!=0 and distance(effective(key),effective(changed))==1 and all(b.bit_count()%2==1 for b in changed))
                else:
                    check(name+f' key bit {i}', distance(key,changed)==1)
        check('TDEA identical components rejected', not audit_record(audit,'injected',bytes(24),0))
        k = bytes.fromhex('0123456789abcdef23456789abcdef01456789abcdef0123')
        check('TDEA K1=K3 rejected', not audit_record(audit,'injected',k[:16]+k[:8],0))
        check('TDEA audit accounting', audit['generated']==audit['accepted']+audit['rejected'])
        args = arguments(['--samples-per-group','2'])
        raw, _ = collect(args)
        check('Seed deterministic', raw==collect(args)[0])
        check('Normalization', all(0<=r['normalized_distance']<=1 and r['normalized_distance']==r['hamming_distance_bits']/r['block_bits'] for r in raw))
        check('Raw columns', set(raw[0])==set('algorithm variant sample_id block_bits effective_key_bits flipped_bit_index hamming_distance_bits normalized_distance seed status skip_reason'.split()))
        check('Quantiles linear interpolation', quantile([0,10],.25)==2.5)
        report['passed'] = True
    except Exception as exc:
        report['error'] = str(exc)
    return report


def method():
    return dict(mode='ECB single block, no padding', aes_backend='software; use_aesni=False',
                bit_numbering='LSB-first within bytes; flipped_bit_index is physical representation index',
                key_policy='DES/TDEA odd parity restored after one effective-bit flip; TDEA requires three distinct effective components',
                sampling='New random key/plaintext per sample; same pair for both variants; uniform bit selection with rejection for invalid TDEA changes',
                quantiles='Linear interpolation at (n-1)*p (type 7)', warning=WARNING)


def write_json(path, obj):
    path.write_text(json.dumps(obj,indent=2,default=str,allow_nan=False)+'\n',encoding='utf-8')


def run(args, validator=validate):
    session = str(uuid.uuid4())
    gate = args.output.resolve()/('avalanche-validation-'+session)
    gate.mkdir(parents=True, exist_ok=False)
    validation = validator()
    validation.update(session_id=session, purpose=args.purpose)
    write_json(gate/'validation.json', validation)
    if validation.get('passed') is not True:
        raise RuntimeError('Validation failed; no statistics exported: '+str(gate))
    raw, audit = collect(args)
    summary = summarize(raw)
    methodology = method()
    methodology['tdea_candidates'] = audit
    directory = save_run('avalanche',args,methodology,raw,summary)
    shutil.copy2(gate/'validation.json',directory/'validation.json')
    snapshot = directory/'source'
    snapshot.mkdir()
    hashes = {}
    for path in (Path(__file__),Path(__file__).with_name('common.py'),Path(__file__).with_name('avalanche_smoke_check.py')):
        shutil.copy2(path,snapshot/path.name)
        hashes[path.name] = hashlib.sha256((snapshot/path.name).read_bytes()).hexdigest()
    meta = json.loads((directory/'metadata.json').read_text())
    meta.update(session_id=session,validation_passed=True,validation_sha256=hashlib.sha256((directory/'validation.json').read_bytes()).hexdigest(),source_sha256=hashes)
    write_json(directory/'metadata.json',meta)
    lines = ['# Avalanche diffusion demonstration','',WARNING,
             'CPU software AES; DES/TDEA odd parity, one effective bit; ECB single block.',
             'Each sample draws a fresh key/plaintext; both variants share that pair.',
             'No timing or security ranking. Percentiles use linear interpolation (n-1)*p.',
             'Raw status is accepted; invalid TDEA proposals are retried and recorded in metadata, not silently skipped.',
             'TDEA audit (initial and changed proposals): '+json.dumps(audit),
             '', '| Algorithm | Variant | Count | Mean bits | Median bits | SD bits | Mean normalized |',
             '|---|---|---:|---:|---:|---:|---:|']
    lines += [f"| {r['algorithm']} | {r['variant']} | {r['count']} | {r['mean']:.4g} | {r['median']:.4g} | {r['stdev']} | {r['mean_normalized']:.4g} |" for r in summary]
    lines += ['', 'An idealized 0.5 center is not evidence of security; finite samples and correlated variants do not establish SAC or independence of output bits.', 'DES/TDEA are legacy algorithms; no recommendation for modern protection. Synthetic seeded keys are not production keys.']
    (directory/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return directory


def arguments(argv=None):
    cli = parser(__doc__)
    cli.set_defaults(purpose=None)
    cli.add_argument('--profile',choices=['smoke','pilot','study'],default='smoke')
    cli.add_argument('--algorithms',nargs='+',choices=ALGORITHMS,default=list(ALGORITHMS))
    cli.add_argument('--variants',nargs='+',choices=['plaintext','key'],default=['plaintext','key'])
    cli.add_argument('--samples-per-group','--trials',dest='samples_per_group',type=positive)
    args = cli.parse_args(argv)
    args.purpose = args.purpose or args.profile
    if args.purpose != args.profile:
        cli.error('Purpose must match profile')
    if args.samples_per_group is None:
        args.samples_per_group = {'smoke':8,'pilot':200,'study':2000}[args.profile]
    if args.samples_per_group > {'smoke':20,'pilot':500,'study':10000}[args.profile]:
        cli.error('Sample count exceeds explicit profile cap')
    if len(set(args.algorithms))!=len(args.algorithms) or len(set(args.variants))!=len(args.variants):
        cli.error('Duplicate algorithms or variants')
    return args


if __name__ == '__main__':
    args = arguments()
    if not print_plan('avalanche',args,method()):
        run(args)
