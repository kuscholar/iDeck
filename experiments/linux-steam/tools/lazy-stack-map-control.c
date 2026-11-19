/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Host fixture for the actual pinned Linux guest mmap/mprotect/fork PTE paths. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "fs/fd.h"
#include "fs/real.h"
#include "kernel/calls.h"
#include "kernel/errno.h"
#include "kernel/init.h"
#include "kernel/mm.h"
#include "kernel/task.h"

#if IDECK_LAB_LAZY_STACK
extern _Atomic uint64_t ideck_stack_map_requests, ideck_stack_map_reserved;
extern _Atomic uint64_t ideck_stack_map_no_hole, ideck_stack_map_metadata_failures;
#endif

static const dword_t stack = MMAP_PRIVATE | MMAP_ANONYMOUS | 0x20000;
static const addr_t length = 0x410000;
static const addr_t guard = 0x10000;

static void ordinary(addr_t address, addr_t size, dword_t prot, dword_t flags) {
    addr_t mapping = sys_mmap64(address, size, prot, flags, -1, 0);
    assert((int64_t)mapping > 0);
    assert(mem_pt(current->mem, PAGE(mapping)));
    assert(!mem_find_reservation(current->mem, PAGE(mapping)));
    assert(!sys_munmap(mapping, size));
}

int main(void) {
    assert(!mount_root(&realfs, "/") && !become_first_process());
    struct mem *memory = current->mem;
    addr_t address = sys_mmap64(0, length, 0, stack, -1, 0);
    assert((int64_t)address > 0);
    page_t start = PAGE(address), pages = length / PAGE_SIZE;
    unsigned char byte = 0x4a;
    assert(user_read(address, &byte, 1));
    assert(user_write(address, &byte, 1));
#if IDECK_LAB_LAZY_STACK
    assert(mem_find_reservation(memory, start) && !mem_pt(memory, start));
    long charge = atomic_load(&anon_page_count);
#else
    assert(mem_pt(memory, start) && !mem_find_reservation(memory, start));
#endif
    assert(!sys_mprotect(address + guard, length - guard, P_READ | P_WRITE));
    assert(user_read(address + guard - 1, &byte, 1));
    assert(user_write(address + guard - 1, &byte, 1));
#if IDECK_LAB_LAZY_STACK
    assert(!mem_pt(memory, PAGE(address + guard)));
    assert(atomic_load(&anon_page_count) == charge);
#endif
    assert(!user_read(address + guard, &byte, 1) && byte == 0);
    assert(!user_read(address + length - 1, &byte, 1) && byte == 0);
    byte = 0x55;
    assert(!user_write(address + length - 1, &byte, 1));

    struct mem child;
    mem_init(&child);
    assert(!pt_copy_on_write(memory, &child, start, pages));
    struct pt_entry *tail = mem_pt(&child, start + pages - 1);
    assert(tail && (tail->flags & P_COW));
    assert(((unsigned char *)tail->data->data)[tail->offset + PAGE_SIZE - 1] == 0x55);
    byte = 0xaa;
    assert(!user_write(address + length - 1, &byte, 1));
    assert(((unsigned char *)tail->data->data)[tail->offset + PAGE_SIZE - 1] == 0x55);
    mem_destroy(&child);

    assert(!sys_munmap(address + guard + PAGE_SIZE * 8, PAGE_SIZE));
    assert(user_read(address + guard + PAGE_SIZE * 8, &byte, 1));
    assert(!user_read(address + length - 1, &byte, 1) && byte == 0xaa);
    assert(!sys_munmap(address, length));
    assert(!mem_find_reservation(memory, start) && !mem_pt(memory, start + pages - 1));
    ordinary(0, length, 0, MMAP_PRIVATE | MMAP_ANONYMOUS);
    ordinary(0, length - PAGE_SIZE, 0, stack);
    ordinary(0, length, P_READ | P_WRITE, stack);
    ordinary(0x1800000000ULL, length, 0, stack | MMAP_FIXED);
#if IDECK_LAB_LAZY_STACK
    assert(atomic_load(&anon_page_count) == charge);
    assert(atomic_load(&ideck_stack_map_requests) == 1 && atomic_load(&ideck_stack_map_reserved) == 1);
    assert(!atomic_load(&ideck_stack_map_no_hole) && !atomic_load(&ideck_stack_map_metadata_failures));
#endif
    puts("Linux mmap, guard, demand-zero, fork CoW, unmap and exclusions PASS");
    return 0;
}
