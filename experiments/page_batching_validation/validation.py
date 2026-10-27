"""Published NIST/RFC vectors, explicit ECB counter oracle and page-boundary checks."""
import hashlib
from Crypto.Cipher import AES
from engines import phase1
from protocol import BATCHES, material, check


def reference(data, key, ivs, page_bytes):
    check(data, key, ivs, page_bytes)
    return b''.join(AES.new(key, AES.MODE_CTR, nonce=iv[:12],
        initial_value=int.from_bytes(iv[12:], 'big')).encrypt(data[i*page_bytes:(i+1)*page_bytes])
        for i, iv in enumerate(ivs))


def ecb_reference(data, key, ivs, page_bytes):
    check(data, key, ivs, page_bytes)
    result = []
    for p, iv in enumerate(ivs):
        blocks = b''.join(iv[:12] + (int.from_bytes(iv[12:], 'big')+i).to_bytes(4, 'big')
                          for i in range((page_bytes+15)//16))
        stream = AES.new(key, AES.MODE_ECB).encrypt(blocks)
        plain = data[p*page_bytes:(p+1)*page_bytes]
        result.append(bytes(a^b for a,b in zip(plain, stream)))
    return b''.join(result)


def require_equal(actual, expected):
    if actual != expected:
        raise RuntimeError('Ciphertext mismatch; timing rejected')


def validate(cpu, gpu=None):
    report = dict(passed=False, cases=[], references=[
        'https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38a.pdf',
        'https://www.rfc-editor.org/rfc/rfc3686#section-6'])
    def case(name, data, key, ivs, size, expected, layout='pages'):
        require_equal(reference(data, key, ivs, size), expected)
        actual = cpu.encrypt(data, key, ivs, size)
        require_equal(actual, expected)
        if gpu:
            actual = gpu.encrypt(data, key, ivs, size, layout)
            require_equal(actual, expected)
            # Compare EACH page, not just aggregate hash or decryption round-trip.
            for p in range(len(ivs)):
                require_equal(actual[p*size:(p+1)*size], expected[p*size:(p+1)*size])
        report['cases'].append(dict(name=name, layout=layout, segments=len(ivs), segment_bytes=size,
            passed=True, gpu_checked=gpu is not None, ciphertext_sha256=hashlib.sha256(expected).hexdigest()))
    vectors = [
        ('NIST SP800-38A F.5.1', phase1.PLAIN, phase1.KEY, phase1.IV, bytes.fromhex(phase1.EXPECTED['CTR'])),
        ('RFC3686 #1', b'Single block msg', bytes.fromhex('ae6852f8121067cc4bf7a5765577f39e'),
         bytes.fromhex('00000030000000000000000000000001'), bytes.fromhex('e4095d4fb7a7b3792d6175a3261311b8')),
        ('RFC3686 #2', bytes(range(32)), bytes.fromhex('7e24067817fae0d743d6ce1f32539163'),
         bytes.fromhex('006cb6dbc0543b59da48d90b00000001'),
         bytes.fromhex('5104a106168a72d9790d41ee8edad388eb2e1efc46da57c8fce630df9141be28'))]
    for name, data, key, iv, expected in vectors:
        for layout in ('pages', 'continuous'):
            case(name, data, key, [iv], len(data), expected, layout)
    for size in (1, 15, 16, 17, 31, 2048, 2064):
        ivs = [p.to_bytes(12, 'big') + b'\0\0\0\1' for p in range(3)]
        data = hashlib.shake_256(f'page-boundary-{size}'.encode()).digest(3*size)
        case('partial/page/launch boundary', data, bytes(16), ivs, size,
             ecb_reference(data, bytes(16), ivs, size))
    for initial, size in ((255, 65), (65535, 65), (0xfffffffe, 32), (0xffffffff, 16)):
        ivs = [p.to_bytes(12, 'big')+initial.to_bytes(4, 'big') for p in (40, 41)]
        data = bytes(2*size)
        case('counter carry/last legal block', data, bytes(16), ivs, size,
             ecb_reference(data, bytes(16), ivs, size))
    for pages in BATCHES:
        for layout in ('pages', 'continuous'):
            data, key, ivs, size = material(2003, pages, 0, layout)
            case('full workload equality', data, key, ivs, size, reference(data,key,ivs,size), layout)
    report['passed'] = True
    return report
