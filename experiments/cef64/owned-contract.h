/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * Isolated Windows API discriminator, no Valve module or network activity.
 */
#ifndef IDECK_CEF64_OWNED_CONTRACT_H
#define IDECK_CEF64_OWNED_CONTRACT_H
#include <string.h>
static int cef64_owned_contract(void)
{
    const SIZE_T sizes[] = {UINT64_C(0x40000000), UINT64_C(0x40010000),
        UINT64_C(0x400000000), UINT64_C(0x400010000), UINT64_C(0x200000000)};
    const uintptr_t expected[] = {UINT64_C(0x7100000000), UINT64_C(0x717fff0000),
        UINT64_C(0x7c00000000), UINT64_C(0x77ffff0000), UINT64_C(0x7200000000)};
    unsigned char *owned[5] = {0};
    int result = 0;
    setvbuf(stdout, NULL, _IONBF, 0);
    puts("cef64-owned-contract begin; exact reserved ownership, not CEF startup");
    for (unsigned i = 0; i < 5; ++i) {
        MEMORY_BASIC_INFORMATION info;
        owned[i] = VirtualAlloc(NULL, sizes[i], MEM_RESERVE, PAGE_NOACCESS);
        printf("cef64-owned-contract allocation=%u exact=%u error=%lu\n", i,
            (uintptr_t)owned[i] == expected[i], owned[i] ? 0ul : GetLastError());
        if ((uintptr_t)owned[i] != expected[i]) { result = 10 + i; break; }
        if (VirtualQuery(owned[i], &info, sizeof(info)) != sizeof(info) ||
            info.AllocationBase != owned[i] || info.State != MEM_RESERVE || info.RegionSize != sizes[i]) {
            result = 20 + i; break;
        }
        const SIZE_T offsets[] = {(i == 1 || i == 3) ? 0x10000 : 0, sizes[i] - 0x4000};
        for (unsigned edge = 0; edge < 2; ++edge) {
            unsigned char *page = owned[i] + offsets[edge];
            if (VirtualAlloc(page, 0x4000, MEM_COMMIT, PAGE_READWRITE) != page) { result = 30 + i; break; }
            for (unsigned j = 0; j < 0x4000; ++j) if (page[j]) { result = 40 + i; break; }
            if (result) break;
            const unsigned char value = (unsigned char)(0x31 + i * 2 + edge);
            memset(page, value, 0x4000);
            for (unsigned j = 0; j < 0x4000; ++j) if (page[j] != value) { result = 50 + i; break; }
            if (result) break;
            printf("cef64-owned-contract allocation=%u edge=%u committed-zero-write-read=1\n", i, edge);
        }
        if (result) break;
    }
    if (!result) {
        void *duplicate = VirtualAlloc(NULL, sizes[0], MEM_RESERVE, PAGE_NOACCESS);
        printf("cef64-owned-contract duplicate-refused=%u error=%lu\n", !duplicate, duplicate ? 0ul : GetLastError());
        if (duplicate) { VirtualFree(duplicate, 0, MEM_RELEASE); result = 60; }
    }
    for (unsigned i = 0; i < 5; ++i) if (owned[i]) {
        BOOL freed = VirtualFree(owned[i], 0, MEM_RELEASE);
        printf("cef64-owned-contract release=%u result=%u\n", i, !!freed);
        if (!freed && !result) result = 70 + i;
    }
    printf("cef64-owned-contract result=%d; no CEF/login/game claim\n", result);
    return result;
}
#endif
