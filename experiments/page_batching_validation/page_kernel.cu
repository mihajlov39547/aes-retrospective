// Appended to the original aes_cuda_baseline.cu; encrypt_block and expand_key are unchanged.
extern "C" __global__ void aes_ctr_pages(const unsigned char* in, unsigned char* out,
    const unsigned char* rk, const unsigned char* ivs,
    unsigned long long page_bytes, unsigned int pages) {
    unsigned long long index = (unsigned long long)blockIdx.x * blockDim.x + threadIdx.x;
    unsigned long long blocks_per_page = (page_bytes + 15) / 16;
    unsigned long long page = index / blocks_per_page;
    if (page >= pages) return;
    unsigned long long within = index % blocks_per_page;
    unsigned long long local_offset = within * 16;
    unsigned long long offset = page * page_bytes + local_offset;
    const unsigned char* initial = ivs + page * 16;
    unsigned char s[16];
    for (int j=0; j<12; ++j) s[j] = initial[j];
    unsigned int ctr = ((unsigned int)initial[12] << 24) |
                       ((unsigned int)initial[13] << 16) |
                       ((unsigned int)initial[14] << 8) | initial[15];
    // Host validation guarantees no wrap into the nonce; within is page-relative.
    ctr += (unsigned int)within;
    for (int j=15; j>=12; --j) { s[j] = (unsigned char)ctr; ctr >>= 8; }
    encrypt_block(s, rk);
    for (int j=0; j<16 && local_offset+j<page_bytes; ++j)
        out[offset+j] = in[offset+j] ^ s[j];
}
