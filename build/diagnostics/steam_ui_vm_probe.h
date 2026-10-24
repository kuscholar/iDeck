/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * Native pre-Wine capability probe. Fixed mappings never overwrite; no memory
 * is touched. Only successful mappings created by this probe are deallocated.
 */
#ifndef MADEIRA_STEAM_UI_VM_PROBE_H
#define MADEIRA_STEAM_UI_VM_PROBE_H
#include <stdint.h>
#include <stdio.h>
#ifndef MADEIRA_VM_PROBE_TEST
#include <mach/mach.h>
#include <mach/vm_map.h>
#include <mach/vm_region.h>
_Static_assert(sizeof(vm_address_t) == 8 && sizeof(vm_size_t) == 8, "64-bit native VM probe required");
#endif

static int madeira_steam_ui_vm_probe(FILE *out)
{
    const uint64_t step = 0x400000000ULL; /* 16 GiB */
    unsigned successes = 0, failures = 0;
    fprintf(out, "native-vm-probe v1 begin=0x%llx end=0x8000000000 step=0x%llx protection=NONE fixed-no-overwrite=1\n",
            (unsigned long long)step, (unsigned long long)step);
    for (uint64_t base = step; base < 0x8000000000ULL; base += step) {
        const vm_size_t sizes[] = { 0x10000, step };
        for (unsigned i = 0; i < 2; ++i) {
            vm_address_t region_base = base;
            vm_size_t region_size = 0;
            vm_region_basic_info_data_64_t info = {0};
            mach_msg_type_number_t count = VM_REGION_BASIC_INFO_COUNT_64;
            mach_port_t object = MACH_PORT_NULL;
            kern_return_t query = vm_region_64(mach_task_self(), &region_base, &region_size,
                VM_REGION_BASIC_INFO_64, (vm_region_info_t)&info, &count, &object);
            kern_return_t port_cleanup = object == MACH_PORT_NULL ? KERN_SUCCESS : mach_port_deallocate(mach_task_self(), object);
            fprintf(out, "native-vm-region request=0x%llx size=0x%llx kr=%d base=0x%llx region_size=0x%llx prot=%d port_cleanup=%d\n",
                (unsigned long long)base, (unsigned long long)sizes[i], query,
                (unsigned long long)region_base, (unsigned long long)region_size,
                query == KERN_SUCCESS ? info.protection : -1, port_cleanup);
            if (port_cleanup != KERN_SUCCESS) return 5;
            vm_address_t actual = base;
            kern_return_t kr = vm_map(mach_task_self(), &actual, sizes[i], 0,
                VM_FLAGS_FIXED, MEMORY_OBJECT_NULL, 0, FALSE,
                VM_PROT_NONE, VM_PROT_NONE, VM_INHERIT_NONE);
            kern_return_t cleanup = KERN_SUCCESS;
            if (kr == KERN_SUCCESS) {
                ++successes;
                cleanup = vm_deallocate(mach_task_self(), actual, sizes[i]);
            } else ++failures;
            fprintf(out, "native-vm-probe base=0x%llx size=0x%llx kr=%d actual=0x%llx cleanup=%d\n",
                    (unsigned long long)base, (unsigned long long)sizes[i], kr,
                    (unsigned long long)actual, cleanup);
            if (cleanup != KERN_SUCCESS) {
                fputs("native-vm-probe STOP: own mapping cleanup failed\n", out);
                return 2;
            }
            if (kr == KERN_SUCCESS && actual != base) {
                fputs("native-vm-probe STOP: unexpected fixed mapping address (own mapping released)\n", out);
                return 3;
            }
        }
    }
    fprintf(out, "native-vm-probe COMPLETE successes=%u failures=%u; individual capabilities only, not simultaneous ownership\n", successes, failures);
    return ferror(out) ? 4 : 0;
}
#endif
