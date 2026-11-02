/* SPDX-License-Identifier: LGPL-2.1-or-later */
#ifndef IDECK_CEF64_IMAGE_SPILL_H
#define IDECK_CEF64_IMAGE_SPILL_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>

struct cef64_image_interval { uint64_t base, size; };

/* Match a path component, not a title/command line; never log its contents. */
static int cef64_game_image_owner(const uint16_t *path, size_t length)
{
    static const char component[] = "\\steamapps\\common\\";
    if (!path || !length || length > 32767) return 0;
    for (size_t k = 0; k + sizeof(component) - 1 < length; k++)
    {
        size_t j;
        for (j = 0; component[j]; j++)
        {
            uint16_t c = path[k + j];
            if (c == '/') c = '\\';
            if (c >= 'A' && c <= 'Z') c += 'a' - 'A';
            if (c != (uint16_t)component[j]) break;
        }
        if (!component[j]) return 1;
    }
    return 0;
}

/* Advisory fallback only for the measured non-compact source layout. The
 * gap is NOT a recycled CEF/FEX lease. Existing kernel mappings and Wine
 * views in it remain authoritative; the normal no-replace mapper picks a
 * free subrange. Explicit caller limits and non-relocatable images stay put. */
static int cef64_image_spill_range(const char *enabled, const char *source,
    int owned, int game_owner, uint32_t prior, uint16_t machine,
    uint16_t characteristics, uint32_t flags, uint64_t size,
    uint64_t low, uint64_t high, uint32_t alloc,
    const struct cef64_image_interval slots[20], uint64_t *out_low, uint64_t *out_high)
{
    uint64_t start, end;
    if (!enabled || strcmp(enabled,"1") || !source || strcmp(source,"1") ||
        !owned || !game_owner || prior != UINT32_C(0xc0000017) ||
        (machine != 0x8664 && machine != 0xa641 && machine != 0xaa64) ||
        !(characteristics & 0x2000) || (characteristics & 1) || !(flags & 4) ||
        !size || size > UINT64_C(0x4000000) || high || (alloc & ~UINT32_C(0x100000)) ||
        !slots || !out_low || !out_high)
        return 0;
    if (slots[0].base != UINT64_C(0x7100000000) || slots[0].size != UINT64_C(0x40000000) ||
        slots[1].base != UINT64_C(0x717fff0000) || slots[1].size != UINT64_C(0x40010000) ||
        slots[8].base != UINT64_C(0x7140000000) || slots[8].size != UINT64_C(0x20000000))
        return 0;
    start = slots[8].base + slots[8].size;
    end = slots[1].base;
    if (low > start || end <= start || size > end - start) return 0;
    for (unsigned i = 0; i < 20; i++)
    {
        uint64_t b = slots[i].base, n = slots[i].size;
        if (!n) continue;
        if (n > UINT64_MAX - b || (b < end && b + n > start)) return 0;
    }
    *out_low = start;
    *out_high = end - 1; /* map_view takes an inclusive high address. */
    return 1;
}
#endif
