"""Fixed page-batching protocol and collision-free synthetic message identifiers."""
import hashlib
import random

PAGE_BYTES = 1 << 20
BATCHES = [1, 4, 16, 32]
SEEDS = list(range(2003, 2008))
LAYOUTS = ('pages', 'continuous')
JOBS = [(layout, measurement) for layout in LAYOUTS for measurement in ('cpu', 'resident', 'pipeline')]


def check(data, key, ivs, segment_bytes):
    if len(key) != 16 or segment_bytes <= 0 or segment_bytes > 2147483647:
        raise ValueError('AES-128 and positive INT_MAX-bounded segment length required')
    if not 1 <= len(ivs) <= 32 or len(data) != len(ivs) * segment_bytes:
        raise ValueError('Expected 1..32 equal-length segments')
    nonces = []
    for iv in ivs:
        if len(iv) != 16:
            raise ValueError('Expected nonce96 || counter32')
        initial = int.from_bytes(iv[12:], 'big')
        if initial < 1 or initial + (segment_bytes + 15)//16 - 1 > 0xffffffff:
            raise ValueError('32-bit counter would be zero or overflow')
        nonces.append(iv[:12])
    if len(set(nonces)) != len(nonces):
        raise ValueError('Nonce reuse between independent segments')


def counters(seed, pages, repeat, layout):
    if seed not in SEEDS or pages not in BATCHES or not -5 <= repeat < 20 or layout not in LAYOUTS:
        raise ValueError('Outside fixed study domain')
    # Injective 96-bit mapping, not a truncated hash: seed32 || message32 || page32.
    message = (LAYOUTS.index(layout) << 24) | (pages << 16) | (repeat + 5)
    count = pages if layout == 'pages' else 1
    return [seed.to_bytes(4, 'big') + message.to_bytes(4, 'big') + p.to_bytes(4, 'big') + b'\0\0\0\1'
            for p in range(count)]


def material(seed, pages, repeat, layout):
    ivs = counters(seed,pages,repeat,layout)
    key = hashlib.shake_256(f'aes-pages-v1:key:{seed}'.encode()).digest(16)
    # SHAKE prefix property: smaller batches share the prefix of larger batches in a round.
    data = hashlib.shake_256(f'aes-pages-v1:data:{seed}:{repeat}'.encode()).digest(pages*PAGE_BYTES)
    segment_bytes = PAGE_BYTES if layout == 'pages' else pages*PAGE_BYTES
    check(data, key, ivs, segment_bytes)
    return data, key, ivs, segment_bytes


def schedule(seed, warmups, repeats):
    rng = random.Random(seed)
    batches = list(BATCHES)
    rng.shuffle(batches)
    result = []
    for pages in batches:
        for repeat in range(-warmups, repeats):
            jobs = list(JOBS)
            rng.shuffle(jobs)
            for layout, measurement in jobs:
                result.append(dict(pages=pages, bytes=pages*PAGE_BYTES, repeat=repeat,
                    warmup=repeat < 0, layout=layout, measurement=measurement,
                    pair_id=f'{seed}:{pages}:{repeat}:{layout}', execution_index=len(result)))
    return result
