# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Own opt-in transform of pinned LinuxRunner growth allocation boundary.

No change to hashing, block ownership, locks, cache capacity or fault handling.
This only guards growth of an ALREADY initialized table. Initial engine and
page-table allocations remain separate, unqualified failure boundaries.
"""
def patched_engine(source: str) -> str:
    allocation='    struct list *new_hash = calloc(new_size, sizeof(struct list));\n'
    growth='    if (asbestos->num_blocks >= asbestos->hash_size * 2)\n'
    assert source.count(allocation)==source.count(growth)==1
    source=source.replace(allocation,allocation+'''    /* iDeck Lab: allocate BEFORE unlinking any old bucket. A failed growth
     * leaves the original table usable; the existing next-slice policy flushes
     * translations through its ordinary invalidation/lifetime machinery.
     * Do not retry this allocation on each insertion while flush is pending.
     * Initial table allocation is NOT covered by this growth-only experiment. */
    if (!new_hash && asbestos->hash && asbestos->hash_size) {
        atomic_fetch_add_explicit(&ideck_fiber_hash_growth_failures, 1, memory_order_relaxed);
        asbestos->flush_requested = true;
        return;
    }
''',1)
    source=source.replace(growth,'    if (!asbestos->flush_requested && asbestos->num_blocks >= asbestos->hash_size * 2)\n',1)
    anchor='static void fiber_resize_hash(struct asbestos *asbestos, size_t new_size);'
    assert source.count(anchor)==1
    source=source.replace(anchor,anchor+'\n_Atomic uint64_t ideck_fiber_hash_growth_failures;\n',1)
    return source
