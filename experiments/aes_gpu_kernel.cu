// Research skeleton, NOT an AES implementation or a production crypto library.
// TODO: Implement from FIPS 197; document authorship and all reused code/licenses.
// Do not remove this guard until all three entry points have real implementations.
#error "AES GPU skeleton: implement and validate AES-128 before benchmarking"

// ABI contract for aes_gpu.py:
// - contiguous uint8 buffers; unsigned long long is a 64-bit byte count
// - round_keys holds 11 * 16 bytes in FIPS 197 column-major state order
// - each thread handles one independent 16-byte block; guard index >= ceil(n/16)
// - CTR adds the block index to the FULL 128-bit big-endian initial counter,
//   with carry across every byte; no host-endian reinterpretation
// - ECB accepts only full blocks; CTR also supports a partial last block
// - no padding, overlapping buffers, global mutable keys, or silent truncation

extern "C" __global__ void aes128_expand_key(
    const unsigned char* key, unsigned char* round_keys);

extern "C" __global__ void aes128_ecb(
    const unsigned char* input, unsigned char* output,
    const unsigned char* round_keys, unsigned long long input_bytes);

extern "C" __global__ void aes128_ctr(
    const unsigned char* input, unsigned char* output,
    const unsigned char* round_keys, const unsigned char* initial_counter,
    unsigned long long input_bytes);

// TODO: Start with a readable non-optimized AES-128 encryption implementation.
// TODO: NIST SP 800-38A F.1.1 / F.5.1 tests must pass before any timed execution.
// TODO: Test grid boundaries, partial CTR blocks and multi-byte counter carry.
// TODO: Only after correctness: investigate coalescing, registers, tables,
//       occupancy and thread-block size. AES-192/256 are out of initial scope.
// No claim of constant-time behavior, side-channel resistance, fault resistance,
// or secure key lifetime/erasure on a GPU is made.
