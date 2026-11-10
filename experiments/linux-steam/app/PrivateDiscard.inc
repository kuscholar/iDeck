/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Explicit experimental flag only, included in the copied pinned mmap unit.
 * Replace ONLY whole, exclusively owned private anonymous backing objects.
 * No MAP_FIXED, mprotect, shared/COW/file changes or cap changes.
 */
#include <sys/mman.h>
#include "asbestos/asbestos.h"

#if defined(IDECK_DISCARD_HOST_FAIL_SECOND) && defined(__ENVIRONMENT_IPHONE_OS_VERSION_MIN_REQUIRED__)
#error Host allocation failure injection must never target iOS
#endif

static _Atomic uint64_t ideck_private_discard_calls, ideck_private_discard_bytes;
struct ideck_discard_block {
    struct data *old, *replacement;
    page_t first;
    pages_t pages;
};

static int ideck_try_private_discard(struct mem *mem, addr_t address, dword_t length) {
    /* Bounded preflight. Any partial backing, hole, alias, retained futex key,
     * protection boundary or unsupported mapping uses the ORIGINAL syscall.
     * All replacements are allocated before any PTE/backing is changed.
     */
    if (!mem || !length || PGOFFSET(address) || PGOFFSET(length) ||
            length > 64u * 1024 * 1024 || address > (USER_ADDR_MAX_PAGE + 1) * PAGE_SIZE - length)
        return 0;
    page_t first = PAGE(address), end = first + PAGE(length), cursor = first;
    size_t count = 0, capacity = (size_t)PAGE(length);
    struct ideck_discard_block *blocks = calloc(capacity, sizeof *blocks);
    if (!blocks) return 0;
    int complete = 0;
    /* Optimization must not wait behind guest execution/readers. Contention
     * retains the pinned syscall, rather than adding a new writer wait. */
    if (!write_wrtrylock(&mem->lock)) { free(blocks); return 0; }
    while (cursor < end) {
        struct pt_entry *pt = mem_pt(mem, cursor);
        if (!pt || !pt->data || pt->offset) goto done;
        struct data *data = pt->data;
        if (data->fd || data->memfd_maywrite || data->mapping_offset ||
                !data->size || PGOFFSET(data->size) ||
                (uintptr_t)data->data % real_page_size)
            goto done;
        pages_t pages = PAGE(data->size);
        if (pages > end - cursor || atomic_load(&data->refcount) != pages)
            goto done;
        for (pages_t i = 0; i < pages; i++) {
            struct pt_entry *entry = mem_pt(mem, cursor + i);
            if (!entry || entry->data != data || entry->offset != i * PAGE_SIZE ||
                    !(entry->flags & P_ANONYMOUS) || !(entry->flags & P_WRITE) ||
                    (entry->flags & (P_SHARED | P_COW | P_EXEC)))
                goto done;
        }
        blocks[count++] = (struct ideck_discard_block){.old=data, .first=cursor, .pages=pages};
        cursor += pages;
    }
    for (size_t i = 0; i < count; i++) {
        struct data *old = blocks[i].old;
        struct data *fresh = malloc(sizeof *fresh);
        if (!fresh) goto done;
        void *mapping = MAP_FAILED;
#if defined(IDECK_DISCARD_HOST_FAIL_SECOND)
        if (i != 1)
#endif
            mapping = mmap(NULL, old->size, PROT_READ | PROT_WRITE,
                MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        if (mapping == MAP_FAILED) { free(fresh); goto done; }
        /* No file/shared backing. The name is borrowed in the pinned object;
         * data_release does not own or free it. New anonymous code cache=0.
         */
        *fresh = (struct data){.data=mapping, .size=old->size, .name=old->name};
        atomic_init(&fresh->refcount, (unsigned)blocks[i].pages);
        blocks[i].replacement = fresh;
    }
    asbestos_invalidate_range(mem->mmu.asbestos, first, end);
    for (size_t i = 0; i < count; i++) {
        struct ideck_discard_block *block = &blocks[i];
        for (pages_t j = 0; j < block->pages; j++) {
            /* PTE, offset, permissions, logical accounting and lazy reservation
             * remain intact. Only the owned backing reference changes.
             */
            mem_pt(mem, block->first + j)->data = block->replacement;
            data_release(block->old);
        }
        block->replacement = NULL; /* ownership is now in the existing PTEs */
    }
    mem_changed_pub(mem);
    atomic_fetch_add_explicit(&ideck_private_discard_calls, 1, memory_order_relaxed);
    atomic_fetch_add_explicit(&ideck_private_discard_bytes, length, memory_order_relaxed);
    complete = 1;
done:
    for (size_t i = 0; i < count; i++) {
        struct data *fresh = blocks[i].replacement;
        if (fresh) { munmap(fresh->data, fresh->size); free(fresh); }
    }
    write_wrunlock(&mem->lock);
    free(blocks);
    return complete;
}
const char *ideck_private_discard_marker(void) { return "IDECK_EXCLUSIVE_DISCARD_V1"; }
uint64_t ideck_private_discard_count(void) { return atomic_load(&ideck_private_discard_calls); }
uint64_t ideck_private_discard_replaced_bytes(void) { return atomic_load(&ideck_private_discard_bytes); }
