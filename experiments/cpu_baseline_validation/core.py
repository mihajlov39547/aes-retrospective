"""Deterministic inputs, explicit timing boundaries, and correctness gates."""
import ctypes as ct
import hashlib
import json
import os
from pathlib import Path
from time import perf_counter_ns

ROOT = Path(__file__).resolve().parent
SIZES = [1024, 16384, 1048576, 16777216, 33554432]
SEEDS = list(range(2003, 2008))
IMPLEMENTATIONS = ['pycryptodome', 'openssl_default']


def inputs(seed, size, worker=0):
    # Domain-separated SHAKE avoids dependence on Python RNG implementation/version.
    label = f'aes-phase1-v1:{seed}:{size}:{worker}:'.encode()
    def derive(name, n):
        return hashlib.shake_256(label + name).digest(n)
    # Clear high bit so every supported size is safely below counter exhaustion.
    iv = bytearray(derive(b'counter', 16))
    iv[0] &= 127
    return derive(b'plaintext', size), derive(b'key', 16), bytes(iv)


def check_input(mode, plain, key, iv):
    if mode not in ('ECB', 'CTR') or len(key) != 16 or len(iv) != 16:
        raise ValueError('AES-128, 16-byte counter and ECB/CTR required')
    if not plain or len(plain) > 2147483647:
        raise ValueError('Input length must be in 1..INT_MAX')
    if mode == 'ECB' and len(plain) % 16:
        raise ValueError('ECB requires whole blocks')
    if mode == 'CTR' and int.from_bytes(iv, 'big') + (len(plain) + 15) // 16 > 2**128:
        raise ValueError('Counter would wrap')


def py_cipher(mode, key, iv):
    from Crypto.Cipher import AES
    return AES.new(key, AES.MODE_ECB) if mode == 'ECB' else AES.new(
        key, AES.MODE_CTR, nonce=b'', initial_value=int.from_bytes(iv, 'big'))


class Native:
    def __init__(self):
        self.build = json.loads((ROOT / 'build/build.json').read_text(encoding='utf-8'))
        lib = ROOT / 'build' / ('baseline.dll' if os.name == 'nt' else 'libbaseline.so')
        if hashlib.sha256(lib.read_bytes()).hexdigest() != self.build['library_sha256']:
            raise RuntimeError('Library differs from build manifest; rebuild')
        if hashlib.sha256((ROOT / 'native.c').read_bytes()).hexdigest() != self.build['source_sha256']:
            raise RuntimeError('Native source changed; rebuild')
        self.dll_dir = None
        if os.name == 'nt' and self.build['openssl_root']:
            self.dll_dir = os.add_dll_directory(str(Path(self.build['openssl_root']) / 'bin'))
        self.lib = ct.CDLL(str(lib))
        sig = [ct.c_int, ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p,
               ct.c_size_t, ct.POINTER(ct.c_uint64)]
        for name in ('baseline_encrypt', 'baseline_noop'):
            f = getattr(self.lib, name)
            f.argtypes, f.restype = sig, ct.c_int
        for name in ('baseline_version', 'baseline_build', 'baseline_caps'):
            f = getattr(self.lib, name)
            f.argtypes, f.restype = [], ct.c_char_p
        self.lib.baseline_cpu_aes.argtypes = []
        self.lib.baseline_cpu_aes.restype = ct.c_int

    def metadata(self):
        return dict(openssl_version=self.lib.baseline_version().decode(),
                    openssl_compiler=self.lib.baseline_build().decode(),
                    openssl_cpu_settings=self.lib.baseline_caps().decode(),
                    cpu_aes_available=self.lib.baseline_cpu_aes(), build=self.build,
                    provider='default', instruction_execution='not traced')


def measure(implementation, native, mode, plain, key, iv):
    """Return ciphertext and all raw boundaries. Validation must follow, outside timers."""
    check_input(mode, plain, key, iv)
    # Both paths use zero-initialized bytearray output: equal allocation policy.
    t = perf_counter_ns()
    output = bytearray(len(plain) + 16)  # EVP maximum output allowance; slice view below.
    allocation = perf_counter_ns() - t
    view = memoryview(output)[:len(plain)]
    if implementation == 'pycryptodome':
        t = perf_counter_ns()
        cipher = py_cipher(mode, key, iv)
        setup = perf_counter_ns() - t
        t = perf_counter_ns()
        cipher.encrypt(plain, output=view)
        transform = perf_counter_ns() - t
        t = perf_counter_ns()
        del cipher
        cleanup = perf_counter_ns() - t
        metrics = dict(setup_ns=setup, transform_ns=transform, cleanup_ns=cleanup,
                       native_call_ns=None, ffi_noop_ns=None, ffi_residual_ns=None,
                       buffer_binding_ns=None)
    else:
        t = perf_counter_ns()
        out_ptr = (ct.c_ubyte * len(output)).from_buffer(output)
        key_ptr, iv_ptr, in_ptr = ct.c_char_p(key), ct.c_char_p(iv), ct.c_char_p(plain)
        times = (ct.c_uint64 * 3)()
        args = (int(mode == 'CTR'), key_ptr, iv_ptr, in_ptr, out_ptr, len(plain), times)
        binding = perf_counter_ns() - t
        t = perf_counter_ns()
        native.lib.baseline_noop(*args)
        noop = perf_counter_ns() - t
        t = perf_counter_ns()
        ok = native.lib.baseline_encrypt(*args)
        outer = perf_counter_ns() - t
        if not ok:
            raise RuntimeError('EVP operation failed')
        metrics = dict(setup_ns=times[0], transform_ns=times[1], cleanup_ns=times[2],
                       native_call_ns=outer, ffi_noop_ns=noop,
                       ffi_residual_ns=outer-sum(times), buffer_binding_ns=binding)
    metrics['allocation_ns'] = allocation
    return bytes(view), metrics


PLAIN = bytes.fromhex('6bc1bee22e409f96e93d7e117393172a'
                      'ae2d8a571e03ac9c9eb76fac45af8e51'
                      '30c81c46a35ce411e5fbc1191a0a52ef'
                      'f69f2445df4f9b17ad2b417be66c3710')
KEY = bytes.fromhex('2b7e151628aed2a6abf7158809cf4f3c')
IV = bytes.fromhex('f0f1f2f3f4f5f6f7f8f9fafbfcfdfeff')
EXPECTED = {
    'ECB': '3ad77bb40d7a3660a89ecaf32466ef97'
           'f5d3d58503b9699de785895a96fdbaaf'
           '43b1cd7f598ece23881b00e3ed030688'
           '7b0c785e27e8ad3f8223207104725dd4',
    'CTR': '874d6191b620e3261bef6864990db6ce'
           '9806f66b7970fdff8617187bb9fffdff'
           '5ae4df3edbd5d35e5b4f09020db03eab'
           '1e031dda2fbe03d1792170a0f3009cee'}


def validate(implementation, native):
    cases = []
    def case(name, mode, data, key, iv, expected):
        actual, _ = measure(implementation, native, mode, data, key, iv)
        if actual != expected:
            raise RuntimeError(f'Validation failed: {implementation} {name}')
        cases.append(name)
    for mode in EXPECTED:
        case('NIST SP800-38A F.1.1' if mode == 'ECB' else 'NIST SP800-38A F.5.1',
             mode, PLAIN, KEY, IV, bytes.fromhex(EXPECTED[mode]))
    # Independent counter construction using ECB tests byte order and long carries.
    for bits in (8, 32, 64, 96, 120):
        iv = (2**bits - 1).to_bytes(16, 'big')
        for n in (1, 15, 16, 17, 65):
            data = inputs(2003, n)[0]
            blocks = b''.join((int.from_bytes(iv, 'big') + i).to_bytes(16, 'big')
                              for i in range((n + 15) // 16))
            stream = py_cipher('ECB', KEY, iv).encrypt(blocks)
            expected = bytes(a ^ b for a, b in zip(data, stream))
            case(f'CTR-carry-{bits}-length-{n}', 'CTR', data, KEY, iv, expected)
    for size in SIZES:
        data, key, iv = inputs(2003, size)
        for mode in EXPECTED:
            case(f'equality-{mode}-{size}', mode, data, key, iv,
                 py_cipher(mode, key, iv).encrypt(data))
    return dict(passed=True, cases=cases, source=
                'https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38a.pdf')
