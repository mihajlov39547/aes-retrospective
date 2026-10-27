/* Phase 1: OpenSSL 3 EVP, no padding, no subprocess in the timed path. */
#ifndef _WIN32
#define _POSIX_C_SOURCE 200809L
#endif
#include <openssl/evp.h>
#include <openssl/crypto.h>
#include <openssl/provider.h>
#include <stdint.h>
#include <stdlib.h>
#include <limits.h>
#include <string.h>
#ifdef _WIN32
#include <windows.h>
#include <intrin.h>
#define API __declspec(dllexport)
#else
#include <time.h>
#define API __attribute__((visibility("default")))
#if defined(__x86_64__)
#include <cpuid.h>
#elif defined(__aarch64__)
#include <sys/auxv.h>
#include <asm/hwcap.h>
#endif
#endif

static uint64_t now_ns(void) {
#ifdef _WIN32
    LARGE_INTEGER t, f;
    QueryPerformanceCounter(&t); QueryPerformanceFrequency(&f);
    return (uint64_t)((t.QuadPart / f.QuadPart) * 1000000000ULL +
        (t.QuadPart % f.QuadPart) * 1000000000ULL / f.QuadPart);
#else
    struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t);
    return (uint64_t)t.tv_sec * 1000000000ULL + (uint64_t)t.tv_nsec;
#endif
}
API const char *baseline_version(void) { return OpenSSL_version(OPENSSL_VERSION); }
API const char *baseline_build(void) { return OpenSSL_version(OPENSSL_CFLAGS); }
API const char *baseline_caps(void) {
    const char *p = OPENSSL_info(OPENSSL_INFO_CPU_SETTINGS);
    return p ? p : "unavailable";
}
/* CPU availability, not evidence that a particular cipher executed AES instructions. */
API int baseline_cpu_aes(void) {
#if defined(_M_X64)
    int r[4]; __cpuid(r, 1); return !!(r[2] & (1 << 25));
#elif defined(__x86_64__)
    unsigned a,b,c,d;
    if (!__get_cpuid(1,&a,&b,&c,&d)) return -1;
    return !!(c & bit_AES);
#elif defined(__linux__) && defined(__aarch64__)
    return !!(getauxval(AT_HWCAP) & HWCAP_AES);
#else
    return -1;
#endif
}
/* Same argument shape as the measured call; diagnostic only, never subtracted. */
API int baseline_noop(int mode, const unsigned char *key, const unsigned char *iv,
    const unsigned char *in, unsigned char *out, size_t n, uint64_t *times) {
    (void)mode; (void)key; (void)iv; (void)in; (void)out; (void)n; (void)times;
    return 1;
}
API int baseline_encrypt(int mode, const unsigned char *key, const unsigned char *iv,
    const unsigned char *in, unsigned char *out, size_t n, uint64_t *times) {
    EVP_CIPHER_CTX *ctx = NULL;
    EVP_CIPHER *cipher = NULL;
    int written = 0, final = 0, ok = 0;
    uint64_t t;
    if (!key || !iv || !in || !out || !times || n > INT_MAX ||
        (mode != 0 && mode != 1) || (mode == 0 && n % 16)) return 0;
    /* Fetch default provider explicitly; excludes third-party provider substitution. */
    t = now_ns();
    cipher = EVP_CIPHER_fetch(NULL, mode ? "AES-128-CTR" : "AES-128-ECB", "provider=default");
    ctx = EVP_CIPHER_CTX_new();
    if (!ctx || !cipher || !EVP_EncryptInit_ex(ctx,cipher,NULL,key,iv) ||
        !EVP_CIPHER_CTX_set_padding(ctx,0)) goto done;
    times[0] = now_ns() - t;
    t = now_ns();
    if (!EVP_EncryptUpdate(ctx,out,&written,in,(int)n) ||
        !EVP_EncryptFinal_ex(ctx,out+written,&final)) goto done;
    times[1] = now_ns() - t;
    ok = (size_t)(written + final) == n;
done:
    t = now_ns();
    EVP_CIPHER_CTX_free(ctx); EVP_CIPHER_free(cipher);
    times[2] = now_ns() - t;
    return ok;
}
