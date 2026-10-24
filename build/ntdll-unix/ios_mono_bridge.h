/* iOS-Madeira ml648 — shared contract between the native Mach fault handler and
 * FEX for the Mono backpatcher bridge.
 *
 * WHY THIS EXISTS
 * ---------------
 * FEX already knows how to kill Mono's write storm: HandleRWXAccessViolation()
 * calls DetectMonoBackpatcherBlock(), which recognises Mono's XCHG patcher and
 * recompiles that block so the store becomes a call to MonoBackpatcherWrite() —
 * a direct store plus an explicit invalidation, with no fault at all.
 *
 * On iOS that optimisation has never once fired ([mono-cfg] says HOOKS ARMED,
 * "Detected mono backpatcher" appears zero times), because our Mach handler
 * emulates the SWPAL first and FEX never sees a fault. The cost is measured:
 * 40,639 Mach exceptions/sec mean, 88,064/sec peak, which is more than a whole
 * core spent faulting and is what collapses combat to under 10 FPS.
 *
 * ⛔ THIS IS NOT THE Module.S TRANSLATION TABLE. IosAliasEntries means
 * "PE address -> executable JIT-pool address" and ios_ffs_xlate_loop walks
 * EVERY entry to rewrite control-flow targets. Putting a
 * "Mono guest RX -> RW alias" pair in there would rewrite call targets into the
 * NON-EXECUTABLE RW mapping. Hence a separate table, read by exactly one
 * consumer: MonoBackpatcherWrite.
 *
 * ⛔ The Mach handler may not call ARM64EC code (ml613 crashed every launch
 * doing that), must not allocate, format or lock (ml620 died on its own log
 * text), and must not trust any pointer it reads out of guest/JIT memory.
 * So it records raw facts only; ALL interpretation happens at the FEX safe
 * point, where the full host-PC -> guest-RIP machinery already exists. */

#ifndef IOS_MONO_BRIDGE_H
#define IOS_MONO_BRIDGE_H

#include <stdint.h>

#define IOS_MONO_MAX_ALIASES 4096
#define IOS_MONO_MAX_CONTEXTS 64

/* One anonymous JIT alias: the guest's executable view and the writable view of
 * the same physical pages. `generation` retires entries without a hole in the
 * array — a reader that sees a stale generation must miss, not write. */
struct ios_mono_alias {
    uint64_t guest_rx;
    uint64_t host_rw;
    uint64_t size;
    uint32_t generation;   /* odd = live, even = retired */
    uint32_t _pad;
};

/* Per-context pending event. Keyed by context because pseudo-processes share
 * one address space: a single process-global slot would let one process's fault
 * mark another's block. */
struct ios_mono_pending {
    uint64_t context;        /* PEB, 0 = slot free */
    uint64_t block_begin;    /* CpuStateFrame+0, the InlineJITBlockHeader */
    uint64_t host_pc;
    uint64_t fault_addr;
    uint32_t state;          /* 0 empty, 1 published, 2 consumed (one-shot) */
    uint32_t _pad;
};

struct ios_mono_bridge {
    uint32_t abi_version;
    uint32_t diag_enabled;   /* ml649: runtime diagnostic switch, also read by FEX */

    /* Published by FEX so the native side never hardcodes a struct layout. A
     * silent CPUState reshuffle would otherwise turn the capture into a wild
     * read inside a fault handler. Zero means "not published yet" => capture
     * is disabled, which is the safe default. */
    uint32_t off_inline_jit_block_header;   /* within CpuStateFrame */
    uint32_t off_block_tail;                /* within JITCodeHeader */
    uint32_t off_tail_rip;                  /* within JITCodeTail */

    /* Mono module bounds, published by FEX at MarkMonoDetected time. */
    uint64_t mono_base;
    uint64_t mono_end;

    /* FEX code range, so the native side can reject a BlockBegin that is not
     * plausibly a JIT block before dereferencing it. */
    uint64_t code_lo;
    uint64_t code_hi;

    struct ios_mono_pending pending[IOS_MONO_MAX_CONTEXTS];

    uint32_t alias_count;
    struct ios_mono_alias aliases[IOS_MONO_MAX_ALIASES];

    /* Counters only — never per-write logging. */
    uint64_t n_captured;      /* events published by the Mach handler */
    uint64_t n_activated;     /* blocks actually marked by FEX */
    uint64_t n_helper_calls;  /* MonoBackpatcherWrite invocations */
    uint64_t n_alias_miss;    /* helper could not resolve to an RW alias */
    uint64_t n_residual_swp;  /* SWPAL faults still arriving after activation */
    /* Capture declined, split by REASON. One shared counter could only prove
     * that "some" rejection happened, which is useless here: an unreadable
     * block header and a block outside the published code range point at
     * completely different defects. Counts, not a bitmask — a single stray
     * rejection and a four-million-strong storm need telling apart too. */
    uint64_t n_reject_unarmed;      /* mono_base not published yet — ORDERING */
    uint64_t n_reject_no_frame;     /* x28 was 0 — STATE, not ordering. FEX zeroes
                                     * x28 across EC calls (Dispatcher.cpp:108) and
                                     * task #44 already recorded x28=0 faults as a
                                     * real recurring condition, so folding this in
                                     * with 'unarmed' would have buried a live
                                     * signal under a startup one. */
    uint64_t n_reject_bad_block;    /* header unreadable or null */
    uint64_t n_reject_outside_code; /* block_begin outside FEX's code range */
};

#endif /* IOS_MONO_BRIDGE_H */
