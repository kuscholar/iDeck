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
    if (!option || (strcmp(option, "1") && strcmp(option, "backing") && strcmp(option, "split-backing") && strcmp(option, "near-backing") && strcmp(option, "crash-backing") && strcmp(option, "table-backing") && strcmp(option, "wide-backing") && strcmp(option, "standalone-backing") && strcmp(option,"standalone-four-backing") && strcmp(option,"standalone-six-backing") && strcmp(option,"standalone-tail-six-backing") && strcmp(option,"standalone-seven-backing") && strcmp(option,"standalone-eight-backing") && strcmp(option,"standalone-compact-nine-backing") && strcmp(option,"standalone-tail-nine-backing") && strcmp(option,"standalone-tail-twelve-backing"))) return 0;
    for (int i = 1; i < argc; ++i)
        if (argv[i] && !strcmp(argv[i], "madeira-cef64-layout-diagnostics"))
            return !strcmp(option,"standalone-tail-twelve-backing") ? 16 : !strcmp(option,"standalone-tail-nine-backing") ? 15 : !strcmp(option,"standalone-compact-nine-backing") ? 14 : !strcmp(option,"standalone-eight-backing") ? 13 : !strcmp(option,"standalone-seven-backing") ? 12 : !strcmp(option,"standalone-tail-six-backing") ? 11 : !strcmp(option,"standalone-six-backing") ? 10 : !strcmp(option,"standalone-four-backing") ? 9 : !strcmp(option, "standalone-backing") ? 8 : !strcmp(option, "wide-backing") ? 7 : !strcmp(option, "table-backing") ? 6 : !strcmp(option, "crash-backing") ? 5 : !strcmp(option, "near-backing") ? 4 : !strcmp(option, "split-backing") ? 3 : !strcmp(option, "backing") ? 2 : 1;
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

/* Explicit alternative, not the default: the observed FEX high-water address
 * fits8GiB, while real V8 asks for another4GiB and a512MiB table. Capacity
 * and future thread demand still require device tests. Never overlap them. */
static const struct ideck_cef64_slot ideck_cef64_split_slots[] = {
    {UINT64_C(0x7100000000), UINT64_C(0x40000000), "source-elf-regular-1GiB"},
    {UINT64_C(0x717fff0000), UINT64_C(0x40010000), "source-elf-BRP-1GiB-plus-guard"},
    {UINT64_C(0x7200000000), UINT64_C(0x200000000), "full-V8-cage-8GiB"},
    {UINT64_C(0x7400000000), UINT64_C(0x200000000), "FEX-arena-capacity-8GiB"},
    {UINT64_C(0x77ffff0000), UINT64_C(0x400010000), "CEF-BRP-16GiB-plus-guard"},
    {UINT64_C(0x7c00000000), UINT64_C(0x400000000), "CEF-regular-16GiB"},
    {UINT64_C(0x7600000000), UINT64_C(0x100000000), "separate-V8-reservation-4GiB"},
    {UINT64_C(0x7700000000), UINT64_C(0x20000000), "separate-V8-table-512MiB"}
};

/*91: CodeRange requires placement near builtins; table is a distinct hold. */
static const struct ideck_cef64_slot ideck_cef64_near_slots[] = {
    {UINT64_C(0x7100000000), UINT64_C(0x40000000), "source-elf-regular-1GiB"},
    {UINT64_C(0x717fff0000), UINT64_C(0x40010000), "source-elf-BRP-1GiB-plus-guard"},
    {UINT64_C(0x7200000000), UINT64_C(0x200000000), "full-V8-cage-8GiB"},
    {UINT64_C(0x7400000000), UINT64_C(0x200000000), "FEX-arena-capacity-8GiB"},
    {UINT64_C(0x77ffff0000), UINT64_C(0x400010000), "CEF-BRP-16GiB-plus-guard"},
    {UINT64_C(0x7c00000000), UINT64_C(0x400000000), "CEF-regular-16GiB"},
    {UINT64_C(0x7600000000), UINT64_C(0x100000000), "separate-V8-reservation-4GiB"},
    {UINT64_C(0x70a0000000), UINT64_C(0x20000000), "near-V8-code-512MiB"},
    {UINT64_C(0x7700000000), UINT64_C(0x20000000), "separate-V8-table-512MiB"}
};

/*93: independent real support-component pools for the genuine crash child. */
static const struct ideck_cef64_slot ideck_cef64_crash_slots[] = {
    {UINT64_C(0x7100000000), UINT64_C(0x40000000), "source-elf-regular-1GiB"},
    {UINT64_C(0x717fff0000), UINT64_C(0x40010000), "source-elf-BRP-1GiB-plus-guard"},
    {UINT64_C(0x7200000000), UINT64_C(0x200000000), "full-V8-cage-8GiB"},
    {UINT64_C(0x7400000000), UINT64_C(0x200000000), "FEX-arena-capacity-8GiB"},
    {UINT64_C(0x77ffff0000), UINT64_C(0x400010000), "CEF-BRP-16GiB-plus-guard"},
    {UINT64_C(0x7c00000000), UINT64_C(0x400000000), "CEF-regular-16GiB"},
    {UINT64_C(0x7600000000), UINT64_C(0x100000000), "separate-V8-reservation-4GiB"},
    {UINT64_C(0x70a0000000), UINT64_C(0x20000000), "near-V8-code-512MiB"},
    {UINT64_C(0x7700000000), UINT64_C(0x20000000), "separate-V8-table-512MiB"},
    {UINT64_C(0x7780000000), UINT64_C(0x40000000), "crashpad-elf-regular-1GiB"},
    {UINT64_C(0x773fff0000), UINT64_C(0x40010000), "crashpad-elf-BRP-1GiB-plus-guard"}
};

/* A placeholder split keeps the first table reserved. A second table needs
 * different backing, not a recycled or overlapping grant of the first. */
static const struct ideck_cef64_slot ideck_cef64_table_slots[] = {
    {UINT64_C(0x7100000000), UINT64_C(0x40000000), "source-elf-regular-1GiB"},
    {UINT64_C(0x717fff0000), UINT64_C(0x40010000), "source-elf-BRP-1GiB-plus-guard"},
    {UINT64_C(0x7200000000), UINT64_C(0x200000000), "full-V8-cage-8GiB"},
    {UINT64_C(0x7400000000), UINT64_C(0x200000000), "FEX-arena-capacity-8GiB"},
    {UINT64_C(0x77ffff0000), UINT64_C(0x400010000), "CEF-BRP-16GiB-plus-guard"},
    {UINT64_C(0x7c00000000), UINT64_C(0x400000000), "CEF-regular-16GiB"},
    {UINT64_C(0x7600000000), UINT64_C(0x100000000), "separate-V8-reservation-4GiB"},
    {UINT64_C(0x70a0000000), UINT64_C(0x20000000), "near-V8-code-512MiB"},
    {UINT64_C(0x7700000000), UINT64_C(0x20000000), "separate-V8-table-512MiB"},
    {UINT64_C(0x7780000000), UINT64_C(0x40000000), "crashpad-elf-regular-1GiB"},
    {UINT64_C(0x773fff0000), UINT64_C(0x40010000), "crashpad-elf-BRP-1GiB-plus-guard"},
    {UINT64_C(0x71c0000000), UINT64_C(0x20000000), "second-V8-table-512MiB"},
    {UINT64_C(0x71e0000000), UINT64_C(0x20000000), "third-V8-table-512MiB"}
};

/* Explicit102 discriminator after the actual8GiB FEX exhaustion. Keep every
 * guest/CEF lease identical; move only the native-owned FEX arena below the
 * guest furniture floor. Native reservation success, not a free-hole probe,
 * decides whether the complete geometry is admissible. No overwrite/fallback. */
static inline void ideck_cef64_fill_wide_slots(struct ideck_cef64_slot slots[13])
{
    memcpy(slots, ideck_cef64_table_slots, sizeof(ideck_cef64_table_slots));
    slots[3] = (struct ideck_cef64_slot){UINT64_C(0x6000000000), UINT64_C(0x1000000000),
                                     "FEX-arena-capacity-64GiB-disjoint-low"};
}

/*103: genuine standalone Crashpad has no embedded libcef/chrome_elf pools.
 * In this separately identified layout9/10 are tables, not legacy crash pools.
 * Only the explicit standalone launch may select this geometry. */
static const struct ideck_cef64_slot ideck_cef64_standalone_slots[] = {
    {UINT64_C(0x7100000000), UINT64_C(0x40000000), "source-elf-regular-1GiB"},
    {UINT64_C(0x717fff0000), UINT64_C(0x40010000), "source-elf-BRP-1GiB-plus-guard"},
    {UINT64_C(0x7200000000), UINT64_C(0x200000000), "full-V8-cage-8GiB"},
    {UINT64_C(0x7500000000), UINT64_C(0x2ffff0000), "FEX-arena-12GiB-minus-guard-standalone"},
    {UINT64_C(0x77ffff0000), UINT64_C(0x400010000), "CEF-BRP-16GiB-plus-guard"},
    {UINT64_C(0x7c00000000), UINT64_C(0x400000000), "CEF-regular-16GiB"},
    {UINT64_C(0x7400000000), UINT64_C(0x100000000), "separate-V8-reservation-4GiB"},
    {UINT64_C(0x70a0000000), UINT64_C(0x20000000), "near-V8-code-512MiB"},
    {UINT64_C(0x7140000000), UINT64_C(0x20000000), "first-V8-table-512MiB-standalone"},
    {UINT64_C(0x71c0000000), UINT64_C(0x20000000), "second-V8-table-512MiB-standalone"},
    {UINT64_C(0x71e0000000), UINT64_C(0x20000000), "third-V8-table-512MiB-standalone"}
};

/*106: observed fourth V8 table request, not a recycled placeholder. Trade
 * one GiB of the FEX interval for one additional aligned real table; leave
 * all old claims/pool masks unchanged. Capacity/lifetime remain measured gates. */
static void ideck_cef64_fill_four_slots(struct ideck_cef64_slot out[12])
{
    memcpy(out,ideck_cef64_standalone_slots,sizeof(ideck_cef64_standalone_slots));
    out[3]=(struct ideck_cef64_slot){UINT64_C(0x7500000000),UINT64_C(0x2c0000000),"FEX-arena-11GiB-four-tables"};
    out[11]=(struct ideck_cef64_slot){UINT64_C(0x77c0000000),UINT64_C(0x20000000),"fourth-V8-table-512MiB-standalone"};
}
/*108: reserve two tables in an observed free guest band BEFORE guest heaps,
 * rather than shrinking FEX further. The no-overwrite native gate and complete
 * simultaneous backing probe must succeed; this is no promise of game capacity. */
static void ideck_cef64_fill_six_slots(struct ideck_cef64_slot out[14])
{
    ideck_cef64_fill_four_slots(out);
    out[12]=(struct ideck_cef64_slot){UINT64_C(0x7060000000),UINT64_C(0x20000000),"fifth-V8-table-512MiB-guest-band"};
    out[13]=(struct ideck_cef64_slot){UINT64_C(0x7080000000),UINT64_C(0x20000000),"sixth-V8-table-512MiB-guest-band"};
}

/*110 discriminator:108/109 consumed the generic image/heap/stack band before
 * CEF initialized. Move only the two extra tables to the old FEX tail, with a
 * smaller native arena. Nothing overlaps the arena the existing FEX bridge
 * actually receives. Ten GiB may still be insufficient: full runtime tests,
 * rather than this capacity probe, decide whether the tradeoff is useful. */
static void ideck_cef64_fill_tail_six_slots(struct ideck_cef64_slot out[14])
{
    ideck_cef64_fill_six_slots(out);
    out[3]=(struct ideck_cef64_slot){UINT64_C(0x7500000000),UINT64_C(0x280000000),"FEX-arena-10GiB-tail-six-tables"};
    out[12]=(struct ideck_cef64_slot){UINT64_C(0x7780000000),UINT64_C(0x20000000),"fifth-V8-table-512MiB-arena-tail"};
    out[13]=(struct ideck_cef64_slot){UINT64_C(0x77a0000000),UINT64_C(0x20000000),"sixth-V8-table-512MiB-arena-tail"};
}

/*111: actual110 requested a seventh live subspace. Keep the generic guest
 * band free and exchange only another512MiB of the published native arena. */
static void ideck_cef64_fill_seven_slots(struct ideck_cef64_slot out[15])
{
    ideck_cef64_fill_tail_six_slots(out);
    out[3]=(struct ideck_cef64_slot){UINT64_C(0x7500000000),UINT64_C(0x260000000),"FEX-arena-9.5GiB-seven-tables"};
    out[14]=(struct ideck_cef64_slot){UINT64_C(0x7760000000),UINT64_C(0x20000000),"seventh-V8-table-512MiB-arena-tail"};
}

/*112: actual111 needs an eighth simultaneously live table after navigation.
 * All fifteen earlier holds keep their identity except the published FEX end. */
static void ideck_cef64_fill_eight_slots(struct ideck_cef64_slot out[16])
{
    ideck_cef64_fill_seven_slots(out);
    out[3]=(struct ideck_cef64_slot){UINT64_C(0x7500000000),UINT64_C(0x240000000),"FEX-arena-9GiB-eight-tables"};
    out[15]=(struct ideck_cef64_slot){UINT64_C(0x7740000000),UINT64_C(0x20000000),"eighth-V8-table-512MiB-arena-tail"};
}

/*128: actual eight-table game return requested a ninth live subspace. Keep the
 * measured game-image gap intact; compacting the source pools would occupy it.
 * Exchange only the final512MiB of the published native arena. This finite bank
 * remains a capacity experiment, not a recycling/lifetime fix or a GO claim. */
static void ideck_cef64_fill_tail_nine_slots(struct ideck_cef64_slot out[17])
{
    ideck_cef64_fill_eight_slots(out);
    out[3]=(struct ideck_cef64_slot){UINT64_C(0x7500000000),UINT64_C(0x220000000),"FEX-arena-8.5GiB-tail-nine-tables"};
    out[16]=(struct ideck_cef64_slot){UINT64_C(0x7720000000),UINT64_C(0x20000000),"ninth-V8-table-512MiB-arena-tail"};
}

/*129: after one game return, actual128 consumed all nine tables and requested
 * a tenth. Test bounded headroom without moving source pools or game images.
 * All twelve tables are disjoint native leases; FEX gets only the remaining
 * sevenGiB. No preserved placeholder or live claim can be recycled here. */
static void ideck_cef64_fill_tail_twelve_slots(struct ideck_cef64_slot out[20])
{
    ideck_cef64_fill_tail_nine_slots(out);
    out[3]=(struct ideck_cef64_slot){UINT64_C(0x7500000000),UINT64_C(0x1c0000000),"FEX-arena-7GiB-tail-twelve-tables"};
    out[17]=(struct ideck_cef64_slot){UINT64_C(0x7700000000),UINT64_C(0x20000000),"tenth-V8-table-512MiB-arena-tail"};
    out[18]=(struct ideck_cef64_slot){UINT64_C(0x76e0000000),UINT64_C(0x20000000),"eleventh-V8-table-512MiB-arena-tail"};
    out[19]=(struct ideck_cef64_slot){UINT64_C(0x76c0000000),UINT64_C(0x20000000),"twelfth-V8-table-512MiB-arena-tail"};
}

/*113: pack the source-built 1GiB pools in reverse order. Both retain their
 * compiled size/alignment and the BRP guard. One64KiB guard now precedes710;
 * the former interior gap becomes a ninth table without shrinking FEX.
 * Native no-overwrite and real component adoption remain mandatory gates. */
static void ideck_cef64_fill_compact_slots(struct ideck_cef64_slot out[17])
{
    ideck_cef64_fill_eight_slots(out);
    out[0].base=UINT64_C(0x7140000000);
    out[1].base=UINT64_C(0x70ffff0000);
    out[8].base=UINT64_C(0x7180000000);
    out[16]=(struct ideck_cef64_slot){UINT64_C(0x71a0000000),UINT64_C(0x20000000),"ninth-V8-table-512MiB-source-gap"};
}

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

static int madeira_cef64_layout_probe_for(FILE *out, int backing,
                                         const struct ideck_cef64_slot *slots, unsigned count)
{
    vm_address_t owned[20];
    unsigned held = 0;
    int result = 0;
    uint64_t total = 0;
    if (count != 6 && count != 8 && count != 9 && count != 11 && count != 12 && count != 13 && count != 14 && count != 15 && count != 16 && count != 17 && count != 20) return 13;
    fprintf(out, "cef64-layout v3 simultaneous fixed-no-overwrite=1 backing=%d; own mappings only\n", backing);
    if (!vm_page_size || vm_page_size > 0x10000 || (vm_page_size & (vm_page_size - 1))) return 12;
    for (unsigned i = 0; i < count; ++i) {
        const struct ideck_cef64_slot *s = &slots[i];
        if (!s->size || s->base > UINT64_MAX - s->size) return 10;
        for (unsigned j = 0; j < i; ++j) {
            const struct ideck_cef64_slot *p = &slots[j];
            if (s->base < p->base + p->size && p->base < s->base + s->size) return 11;
        }
        total += s->size;
    }
    for (unsigned i = 0; i < count; ++i) {
        vm_address_t actual = slots[i].base;
        kern_return_t kr = vm_map(mach_task_self(), &actual, slots[i].size, 0,
            VM_FLAGS_FIXED, MEMORY_OBJECT_NULL, 0, FALSE,
            VM_PROT_NONE, backing ? VM_PROT_READ | VM_PROT_WRITE : VM_PROT_NONE, VM_INHERIT_NONE);
        fprintf(out, "cef64-layout slot=%u name=%s base=0x%llx size=0x%llx kr=%d actual=0x%llx\n",
            i, slots[i].name, (unsigned long long)slots[i].base,
            (unsigned long long)slots[i].size, kr, (unsigned long long)actual);
        if (kr != KERN_SUCCESS) { result = 1; break; }
        owned[held++] = actual;
        if (actual != slots[i].base) { result = 2; break; }
    }
    fprintf(out, "cef64-layout simultaneous-held=%u requested-bytes=0x%llx; no guest ownership claim\n", held, (unsigned long long)total);
    if (backing && !result) {
        for (unsigned i = 0; i < count && !result; ++i) {
            const vm_address_t pages[] = {
                owned[i] + ((slots[i].size & UINT64_C(0x3fffffff)) == 0x10000 ? 0x10000 : 0),
                owned[i] + slots[i].size - vm_page_size
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
        kern_return_t kr = vm_deallocate(mach_task_self(), owned[held], slots[held].size);
        fprintf(out, "cef64-layout cleanup-slot=%u kr=%d\n", held, kr);
        if (kr != KERN_SUCCESS) result = 3;
    }
    if (ferror(out)) result = 4;
    fprintf(out, "cef64-layout result=%d; not guest runtime or full-range commit validation\n", result);
    return result;
}
static inline int madeira_cef64_layout_probe(FILE *out, int backing)
{
    return madeira_cef64_layout_probe_for(out, backing, ideck_cef64_slots, 6);
}
static inline int madeira_cef64_split_layout_probe(FILE *out, int backing)
{
    return madeira_cef64_layout_probe_for(out, backing, ideck_cef64_split_slots, 8);
}

static inline int madeira_cef64_near_layout_probe(FILE *out, int backing)
{
    return madeira_cef64_layout_probe_for(out, backing, ideck_cef64_near_slots, 9);
}

static inline int madeira_cef64_crash_layout_probe(FILE *out, int backing)
{
    return madeira_cef64_layout_probe_for(out, backing, ideck_cef64_crash_slots, 11);
}

static inline int madeira_cef64_table_layout_probe(FILE *out, int backing)
{
    return madeira_cef64_layout_probe_for(out, backing, ideck_cef64_table_slots, 13);
}

static inline int madeira_cef64_wide_layout_probe(FILE *out, int backing)
{
    struct ideck_cef64_slot slots[13];
    ideck_cef64_fill_wide_slots(slots);
    return madeira_cef64_layout_probe_for(out, backing, slots, 13);
}

static inline int madeira_cef64_standalone_layout_probe(FILE *out, int backing)
{
    return madeira_cef64_layout_probe_for(out, backing, ideck_cef64_standalone_slots, 11);
}
static inline int madeira_cef64_four_layout_probe(FILE *out,int backing)
{
    struct ideck_cef64_slot slots[12];ideck_cef64_fill_four_slots(slots);
    return madeira_cef64_layout_probe_for(out,backing,slots,12);
}
static inline int madeira_cef64_six_layout_probe(FILE *out,int backing)
{
    struct ideck_cef64_slot slots[14];ideck_cef64_fill_six_slots(slots);
    return madeira_cef64_layout_probe_for(out,backing,slots,14);
}

static inline int madeira_cef64_tail_six_layout_probe(FILE *out,int backing)
{
    struct ideck_cef64_slot slots[14];ideck_cef64_fill_tail_six_slots(slots);
    return madeira_cef64_layout_probe_for(out,backing,slots,14);
}

static inline int madeira_cef64_seven_layout_probe(FILE *out,int backing)
{
    struct ideck_cef64_slot slots[15];ideck_cef64_fill_seven_slots(slots);
    return madeira_cef64_layout_probe_for(out,backing,slots,15);
}

static inline int madeira_cef64_eight_layout_probe(FILE *out,int backing)
{
    struct ideck_cef64_slot slots[16];ideck_cef64_fill_eight_slots(slots);
    return madeira_cef64_layout_probe_for(out,backing,slots,16);
}

static inline int madeira_cef64_compact_layout_probe(FILE *out,int backing)
{
    struct ideck_cef64_slot slots[17];ideck_cef64_fill_compact_slots(slots);
    return madeira_cef64_layout_probe_for(out,backing,slots,17);
}

static inline int madeira_cef64_tail_nine_layout_probe(FILE *out,int backing)
{
    struct ideck_cef64_slot slots[17];ideck_cef64_fill_tail_nine_slots(slots);
    return madeira_cef64_layout_probe_for(out,backing,slots,17);
}

static inline int madeira_cef64_tail_twelve_layout_probe(FILE *out,int backing)
{
    struct ideck_cef64_slot slots[20];ideck_cef64_fill_tail_twelve_slots(slots);
    return madeira_cef64_layout_probe_for(out,backing,slots,20);
}

#endif
