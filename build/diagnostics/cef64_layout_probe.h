/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * Simultaneous native capacity test only. Never used to satisfy a guest call.
 */
#ifndef IDECK_CEF64_LAYOUT_PROBE_H
#define IDECK_CEF64_LAYOUT_PROBE_H
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static int ideck_cef64_layout_mode(const char *option, int argc, char **argv)
{
    if (!option || (strcmp(option, "1") && strcmp(option, "backing"))) return 0;
    for (int i = 1; i < argc; ++i)
        if (argv[i] && !strcmp(argv[i], "madeira-cef64-layout-diagnostics"))
            return !strcmp(option, "backing") ? 2 : 1;
    return 0;
}

struct ideck_cef64_slot { uint64_t base, size; const char *name; };
static const struct ideck_cef64_slot ideck_cef64_slots[] = {
    {UINT64_C(0x7100000000), UINT64_C(0x40000000), "source-elf-regular-1GiB"},
    {UINT64_C(0x717fff0000), UINT64_C(0x40010000), "source-elf-BRP-1GiB-plus-guard"},
    {UINT64_C(0x7200000000), UINT64_C(0x200000000), "full-V8-cage-8GiB"},
    {UINT64_C(0x7400000000), UINT64_C(0x3c0000000), "FEX-arena-capacity-15GiB"},
    {UINT64_C(0x77ffff0000), UINT64_C(0x400010000), "CEF-BRP-16GiB-plus-guard"},
    {UINT64_C(0x7c00000000), UINT64_C(0x400000000), "CEF-regular-16GiB"}
};

#ifndef IDECK_CEF64_TOUCH_PAGE
static int ideck_cef64_touch_page(vm_address_t address, uint64_t tag)
{
    volatile uint64_t *p = (volatile uint64_t *)(uintptr_t)address;
    size_t words = vm_page_size / sizeof(*p);
    for (size_t i = 0; i < words; ++i) if (p[i]) return 0;
    p[0] = tag;
    p[words - 1] = ~tag;
    return p[0] == tag && p[words - 1] == ~tag;
}
#define IDECK_CEF64_TOUCH_PAGE ideck_cef64_touch_page
#endif

static int madeira_cef64_layout_probe(FILE *out, int backing)
{
    vm_address_t owned[6];
    unsigned held = 0;
    int result = 0;
    uint64_t total = 0;
    fprintf(out, "cef64-layout v2 simultaneous fixed-no-overwrite=1 backing=%d; own mappings only\n", backing);
    if (!vm_page_size || vm_page_size > 0x10000 || (vm_page_size & (vm_page_size - 1))) return 12;
    for (unsigned i = 0; i < 6; ++i) {
        const struct ideck_cef64_slot *s = &ideck_cef64_slots[i];
        if (!s->size || s->base > UINT64_MAX - s->size) return 10;
        for (unsigned j = 0; j < i; ++j) {
            const struct ideck_cef64_slot *p = &ideck_cef64_slots[j];
            if (s->base < p->base + p->size && p->base < s->base + s->size) return 11;
        }
        total += s->size;
    }
    for (unsigned i = 0; i < 6; ++i) {
        vm_address_t actual = ideck_cef64_slots[i].base;
        kern_return_t kr = vm_map(mach_task_self(), &actual, ideck_cef64_slots[i].size, 0,
            VM_FLAGS_FIXED, MEMORY_OBJECT_NULL, 0, FALSE,
            VM_PROT_NONE, backing ? VM_PROT_READ | VM_PROT_WRITE : VM_PROT_NONE, VM_INHERIT_NONE);
        fprintf(out, "cef64-layout slot=%u name=%s base=0x%llx size=0x%llx kr=%d actual=0x%llx\n",
            i, ideck_cef64_slots[i].name, (unsigned long long)ideck_cef64_slots[i].base,
            (unsigned long long)ideck_cef64_slots[i].size, kr, (unsigned long long)actual);
        if (kr != KERN_SUCCESS) { result = 1; break; }
        owned[held++] = actual;
        if (actual != ideck_cef64_slots[i].base) { result = 2; break; }
    }
    fprintf(out, "cef64-layout simultaneous-held=%u requested-bytes=0x%llx; no guest ownership claim\n", held, (unsigned long long)total);
    if (backing && !result) {
        for (unsigned i = 0; i < 6 && !result; ++i) {
            const vm_address_t pages[] = {
                owned[i] + ((i == 1 || i == 4) ? 0x10000 : 0),
                owned[i] + ideck_cef64_slots[i].size - vm_page_size
            };
            for (unsigned j = 0; j < 2; ++j) {
                kern_return_t kr = vm_protect(mach_task_self(), pages[j], vm_page_size, FALSE, VM_PROT_READ | VM_PROT_WRITE);
                int matched = kr == KERN_SUCCESS && IDECK_CEF64_TOUCH_PAGE(pages[j], UINT64_C(0x4345466400000000) | (i * 2 + j));
                fprintf(out, "cef64-layout backing-slot=%u edge=%u protect-kr=%d zero-write-read-match=%d\n", i, j, kr, matched);
                if (kr != KERN_SUCCESS || !matched) { result = 5; break; }
            }
        }
    }
    while (held) {
        --held;
        kern_return_t kr = vm_deallocate(mach_task_self(), owned[held], ideck_cef64_slots[held].size);
        fprintf(out, "cef64-layout cleanup-slot=%u kr=%d\n", held, kr);
        if (kr != KERN_SUCCESS) result = 3;
    }
    if (ferror(out)) result = 4;
    fprintf(out, "cef64-layout result=%d; not guest runtime or full-range commit validation\n", result);
    return result;
}
#endif
