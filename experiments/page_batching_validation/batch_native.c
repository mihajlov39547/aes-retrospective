/* Reuse version/capability probes and clocks, with no change to AES implementation. */
#include "../cpu_baseline_validation/native.c"

API int pagebatch_encrypt(const unsigned char *key, const unsigned char *ivs,
    const unsigned char *in, unsigned char *out, size_t page_bytes,
    unsigned int pages, uint64_t *times) {
    EVP_CIPHER_CTX *contexts[32] = {0};
    EVP_CIPHER *cipher = NULL;
    unsigned int p, q;
    uint64_t t, blocks;
    int ok = 0;
    if (!key || !ivs || !in || !out || !times || !page_bytes ||
        page_bytes > INT_MAX || pages < 1 || pages > 32 || page_bytes > SIZE_MAX/pages) return 0;
    blocks = (page_bytes + 15) / 16;
    for (p=0; p<pages; ++p) {
        const unsigned char *iv = ivs + 16*p;
        uint64_t initial = ((uint64_t)iv[12]<<24) | ((uint64_t)iv[13]<<16) |
                           ((uint64_t)iv[14]<<8) | iv[15];
        if (!initial || initial + blocks - 1 > 0xffffffffULL) return 0;
        for (q=0; q<p; ++q) if (!memcmp(iv, ivs+16*q, 12)) return 0;
    }
    t = now_ns();
    cipher = EVP_CIPHER_fetch(NULL, "AES-128-CTR", "provider=default");
    if (!cipher) goto done;
    for (p=0; p<pages; ++p) {
        contexts[p] = EVP_CIPHER_CTX_new();
        if (!contexts[p] || !EVP_EncryptInit_ex(contexts[p], cipher, NULL, key, ivs+16*p) ||
            !EVP_CIPHER_CTX_set_padding(contexts[p], 0)) goto done;
    }
    times[0] = now_ns() - t;
    t = now_ns();
    /* One contiguous native interval, including sequential loop/call overhead.
       All contexts/keys/counters and output are prepared before this interval. */
    for (p=0; p<pages; ++p) {
        int written=0, final=0;
        size_t offset = p*page_bytes;
        if (!EVP_EncryptUpdate(contexts[p], out+offset, &written, in+offset, (int)page_bytes) ||
            !EVP_EncryptFinal_ex(contexts[p], out+offset+written, &final) ||
            (size_t)(written+final) != page_bytes) goto done;
    }
    times[1] = now_ns() - t;
    ok = 1;
done:
    t = now_ns();
    for (p=0; p<pages; ++p) EVP_CIPHER_CTX_free(contexts[p]);
    EVP_CIPHER_free(cipher);
    times[2] = now_ns() - t;
    return ok;
}
