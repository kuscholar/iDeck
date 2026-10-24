/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * Reserve-only diagnostic for a FRESH isolated lab or independent Windows
 * control. Never commits, reads, writes or frees a returned guest interval.
 * End the whole isolated host afterwards; pseudo-process exit may retain VA.
 */
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    static const uintptr_t hints[] = {
        0x400000000000ULL, 0x4fffffff0000ULL,
        0x600000000000ULL, 0x6fffffff0000ULL
    };
    static const SIZE_T sizes[] = {
        0x400000000ULL, 0x400010000ULL,
        0x400000000ULL, 0x400010000ULL
    };
    uintptr_t bases[4] = {0};
    setvbuf(stdout, NULL, _IONBF, 0);
    if (argc != 2 || strcmp(argv[1], "--isolated-reserve-only")) {
        puts("reserve-probe REFUSED: explicit isolated reserve-only argument required");
        return 64;
    }
    puts("reserve-probe begin: 4 calls maximum; no commit/access/free; fresh isolated host required");
    for (unsigned i = 0; i < 4; ++i) {
        MEMORY_BASIC_INFORMATION mbi = {0};
        SetLastError(0);
        void *p = VirtualAlloc((void *)hints[i], sizes[i], MEM_RESERVE, PAGE_NOACCESS);
        DWORD error = p ? 0 : GetLastError();
        printf("reserve-probe call=%u base=%p size=0x%llx error=%lu\n",
               i, p, (unsigned long long)sizes[i], (unsigned long)error);
        if (!p) {
            puts("reserve-probe CAPACITY_GATE: request failed; distinct-ownership result incomplete");
            return 70;
        }
        bases[i] = (uintptr_t)p;
        if (bases[i] > UINTPTR_MAX - sizes[i]) {
            puts("reserve-probe FAIL: returned interval overflow");
            return 41;
        }
        for (unsigned j = 0; j < i; ++j) {
            if (bases[i] < bases[j] + sizes[j] && bases[j] < bases[i] + sizes[i]) {
                printf("reserve-probe FAIL: overlapping live grants earlier=%u later=%u\n", j, i);
                return 40;
            }
        }
        SIZE_T queried = VirtualQuery(p, &mbi, sizeof(mbi));
        printf("reserve-probe query=%u available=%u allocation_base=%p region_size=0x%llx state=0x%lx\n",
               i, queried == sizeof(mbi), mbi.AllocationBase,
               (unsigned long long)mbi.RegionSize, (unsigned long)mbi.State);
    }
    puts("reserve-probe PASS: four reported intervals disjoint; no backing/commit guarantee");
    return 0;
}
