/* SPDX-License-Identifier: LGPL-2.1-or-later
 * Exact source-component layout policy; no mapping or synthetic success here.
 */
#ifndef IDECK_CEF64_OWNED_SLOTS_H
#define IDECK_CEF64_OWNED_SLOTS_H
#include <stdint.h>
#include <stddef.h>

static int cef64_owned_caller(const uint16_t *path, size_t length)
{
    static const char browser[] = "steamwebhelper.exe";
    static const char probe[] = "steam64-cef-load-probe.exe";
    const char *names[] = {browser, probe};
    size_t start = 0;
    if (!path || length > 32767) return 0;
    for (size_t i = 0; i < length; ++i) if (path[i] == '\\' || path[i] == '/') start = i + 1;
    for (unsigned n = 0; n < 2; ++n) {
        size_t i;
        for (i = 0; start + i < length && names[n][i]; ++i) {
            uint16_t c = path[start + i];
            if (c >= 'A' && c <= 'Z') c += 'a' - 'A';
            if (c != (uint16_t)names[n][i]) break;
        }
        if (start + i == length && !names[n][i]) return 1;
    }
    return 0;
}

static int cef64_owned_slot(uint64_t hint, uint64_t size, uint32_t type, uint32_t protect,
                            uint64_t low, uint64_t high, uint64_t alignment, uint32_t attributes)
{
    uint64_t pool;
    if ((type != 0x2000 && type != 0x102000) || protect != 1 || attributes) return -1;
    if (size == UINT64_C(0x40000000) || size == UINT64_C(0x400000000)) {
        pool = size;
        if (hint && (hint & (pool - 1))) return -1;
        return pool == UINT64_C(0x40000000) ? 0 : 5;
    }
    if (size == UINT64_C(0x40010000) || size == UINT64_C(0x400010000)) {
        pool = size - 0x10000;
        if (hint && (hint & (pool - 1)) != pool - 0x10000) return -1;
        return pool == UINT64_C(0x40000000) ? 1 : 4;
    }
    if (size == UINT64_C(0x200000000) && (!hint || !(hint & UINT64_C(0xffffffff)))) return 2;
    (void)low; (void)high; (void)alignment; /* Caller validates selected actual interval. */
    return -1;
}

/* Used only when the additional real native holds exist. In-range fixed
 * addresses retain their meaning: only no-hint, impossible high ASLR hints,
 * or the exact owned base can select these auxiliary reservations. */
static inline int cef64_owned_aux_slot(uint64_t hint, uint64_t size, uint32_t type,
                                      uint32_t protect, uint32_t attributes)
{
    uint64_t base;
    int slot;
    if ((type != 0x2000 && type != 0x102000 && type != 0x42000) || protect != 1 || attributes) return -1;
    if (size == UINT64_C(0x100000000)) { base = UINT64_C(0x7600000000); slot = 6; }
    else if (size == UINT64_C(0x20000000)) { base = UINT64_C(0x7700000000); slot = 7; }
    else return -1;
    if (hint && hint < UINT64_C(0x8000000000) && hint != base) return -1;
    return slot;
}
static inline int cef64_owned_near_slot(uint64_t hint, uint64_t size, uint32_t type,
                                       uint32_t protect, uint32_t attributes)
{
    uint64_t base;
    int slot;
    if (size != UINT64_C(0x20000000) || protect != 1 || attributes) return -1;
    if (type == 0x2000 || type == 0x102000) { base = UINT64_C(0x70a0000000); slot = 7; }
    else if (type == 0x42000) { base = UINT64_C(0x7700000000); slot = 8; }
    else return -1;
    if (hint && hint < UINT64_C(0x8000000000) && hint != base) return -1;
    return slot;
}
static inline int cef64_owned_foreign_fixed(uint64_t hint, uint64_t owned_base)
{
    return hint && hint < UINT64_C(0x8000000000) && hint != owned_base;
}

/* Categorical role only. Never emit the command line or inherited pipe/auth
 * arguments. Require exactly one --type token and exact public role value. */
static inline int cef64_owned_crashpad(const uint16_t *cl, size_t len)
{
    static const char prefix[] = "--type=", role[] = "crashpad-handler";
    size_t value=0, found=0;
    for(size_t k=0;cl && k+7<=len;k++) {
        if(k && cl[k-1]!=' ' && cl[k-1]!='\t' && cl[k-1]!='"')continue;
        size_t j=0;for(;j<7;j++)if(cl[k+j]!=(uint16_t)prefix[j])break;
        if(j==7){found++;value=k+7;}
    }
    if(found!=1 || value+sizeof(role)-1>len)return 0;
    size_t j=0;for(;role[j];j++)if(cl[value+j]!=(uint16_t)role[j])return 0;
    return value+j==len || cl[value+j]==' ' || cl[value+j]=='\t' || cl[value+j]=='"';
}

#endif
