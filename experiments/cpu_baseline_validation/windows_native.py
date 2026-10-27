"""Verify x64 PE images and the wrapper's resolved libcrypto IAT bindings on Windows."""
import ctypes as ct
import hashlib
from pathlib import Path
import struct


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require_x64_pe(path):
    data = Path(path).read_bytes()
    if data[:2] != b'MZ':
        raise RuntimeError(f'Not a Windows PE image: {path}')
    offset = struct.unpack_from('<I', data, 0x3c)[0]
    if data[offset:offset+4] != b'PE\0\0' or struct.unpack_from('<H', data, offset+4)[0] != 0x8664:
        raise RuntimeError(f'Not a native Windows x86-64 image: {path}')


def verify_bindings(wrapper, expected_path, expected_hash):
    """Read resolved import addresses, not PATH, CLI output or an assumed DLL basename."""
    expected_path = Path(expected_path).resolve(strict=True)
    if sha256(expected_path) != expected_hash:
        raise RuntimeError('Configured libcrypto changed since build; rebuild')
    kernel = ct.WinDLL('kernel32', use_last_error=True)
    kernel.GetModuleHandleExW.argtypes = [ct.c_ulong, ct.c_void_p, ct.POINTER(ct.c_void_p)]
    kernel.GetModuleHandleExW.restype = ct.c_int
    kernel.GetModuleFileNameW.argtypes = [ct.c_void_p, ct.c_wchar_p, ct.c_ulong]
    kernel.GetModuleFileNameW.restype = ct.c_ulong
    base = wrapper._handle
    header = ct.string_at(base, 4096)
    pe = struct.unpack_from('<I', header, 0x3c)[0]
    optional = pe + 24
    if struct.unpack_from('<H', header, optional)[0] != 0x20b:
        raise RuntimeError('Expected PE32+ wrapper')
    image_size = struct.unpack_from('<I', header, optional + 56)[0]
    imports, import_size = struct.unpack_from('<II', header, optional + 112 + 8)

    def read(offset, size):
        if not 0 <= offset <= image_size - size:
            raise RuntimeError('PE import address outside image')
        return ct.string_at(base + offset, size)

    def name(offset):
        return read(offset, min(512, image_size-offset)).split(b'\0', 1)[0].decode('ascii')

    required = {'OpenSSL_version', 'EVP_EncryptUpdate', 'EVP_CIPHER_fetch'}
    evidence = {}
    for offset in range(imports, imports + import_size, 20):
        lookup, _, _, dll_name, iat = struct.unpack('<IIIII', read(offset, 20))
        if not dll_name:
            break
        dll = name(dll_name)
        if 'libcrypto' not in dll.lower():
            continue
        if not lookup:
            raise RuntimeError('Cannot inspect original import names')
        for index in range(image_size // 8):
            entry = struct.unpack('<Q', read(lookup + index*8, 8))[0]
            if not entry:
                break
            if entry & (1 << 63):
                continue
            symbol = name(entry + 2)
            if symbol not in required:
                continue
            address = struct.unpack('<Q', read(iat + index*8, 8))[0]
            module = ct.c_void_p()
            # FROM_ADDRESS | UNCHANGED_REFCOUNT
            if not kernel.GetModuleHandleExW(6, address, ct.byref(module)):
                raise ct.WinError(ct.get_last_error())
            buffer = ct.create_unicode_buffer(32768)
            length = kernel.GetModuleFileNameW(module, buffer, len(buffer))
            if not length or length >= len(buffer):
                raise RuntimeError('Cannot resolve imported function module')
            actual = Path(buffer.value).resolve(strict=True)
            if actual != expected_path or sha256(actual) != expected_hash:
                raise RuntimeError(f'Unintended libcrypto binding: {symbol} -> {actual}; expected {expected_path}')
            evidence[symbol] = dict(import_name=dll, resolved_path=str(actual), sha256=expected_hash)
    if evidence.keys() != required:
        raise RuntimeError('Required dynamic EVP/libcrypto bindings could not be verified')
    return evidence
