/* Read-only, fault-safe diagnostics for the guarded Social Club helper.
 * Included only by the iOS signal path, after resolving the exact guest RIP. */
#ifndef IOS_SC_RUNSTATE_DIAG_H
#define IOS_SC_RUNSTATE_DIAG_H

#define IOS_SC_RUN_RING_RVA 0x1d0c40u
#define IOS_SC_RUN_RECORDS 16u

struct ios_sc_run_record
{
    uint64_t sequence;
    uint32_t tid, operation; /* 1: install stack state; 2: restore previous state */
    uint64_t pump, state;
};

struct ios_sc_run_ring
{
    uint64_t counter;
    struct ios_sc_run_record record[IOS_SC_RUN_RECORDS];
};

static int ios_sc_diag_read( uint64_t address, void *out, size_t size )
{
    unsigned char copy[2048];
    mach_vm_size_t got = 0;
    if (!address || size > sizeof(copy) || address > UINT64_MAX - size) return 0;
    if (mach_vm_read_overwrite( mach_task_self(), (mach_vm_address_t)address, size,
                               (mach_vm_address_t)copy, &got ) != KERN_SUCCESS || got != size) return 0;
    memcpy( out, copy, size );
    return 1;
}

static int ios_sc_diag_helper( uint64_t image, uint64_t rip )
{
    unsigned char dos[64], nt[88];
    uint32_t offset, stamp, size;
    uint16_t machine, magic;
    if (!image || rip < image || rip - image >= 0x244000) return 0;
    if (!ios_sc_diag_read( image, dos, sizeof(dos) ) || dos[0] != 'M' || dos[1] != 'Z') return 0;
    memcpy( &offset, dos + 0x3c, sizeof(offset) );
    if (offset < 64 || offset > 0x400 || !ios_sc_diag_read( image + offset, nt, sizeof(nt) )) return 0;
    memcpy( &machine, nt + 4, sizeof(machine) );
    memcpy( &stamp, nt + 8, sizeof(stamp) );
    memcpy( &magic, nt + 24, sizeof(magic) );
    memcpy( &size, nt + 80, sizeof(size) );
    return !memcmp( nt, "PE\0\0", 4 ) && machine == 0x8664 && magic == 0x20b &&
           stamp == 0x6a86d563 && size == 0x244000 &&
           rip - image >= 0x173b90 && rip - image < 0x173cc8;
}

static void ios_sc_diag_ring( const char *tag, uint64_t image )
{
    struct ios_sc_run_ring ring;
    unsigned int i;
    if (!ios_sc_diag_read( image + IOS_SC_RUN_RING_RVA, &ring, sizeof(ring) ))
    {
        dprintf( 2, "[sc-runst] %s ring unreadable\n", tag );
        return;
    }
    dprintf( 2, "[sc-runst] %s ring counter=%llu (last 16 state writes; order by sequence)\n",
             tag, (unsigned long long)ring.counter );
    for (i = 0; i < IOS_SC_RUN_RECORDS; i++)
    {
        struct ios_sc_run_record *r = &ring.record[i];
        uint64_t verify = 0;
        if (!r->sequence || r->sequence > ring.counter || ring.counter - r->sequence >= IOS_SC_RUN_RECORDS ||
            (r->operation != 1 && r->operation != 2)) continue;
        /* A writer clears the sequence, fills the record, then publishes with
         * XCHG. Check it again before printing a potentially racing snapshot. */
        if (!ios_sc_diag_read( image + IOS_SC_RUN_RING_RVA + 8 + i * sizeof(*r), &verify, sizeof(verify) ) ||
            verify != r->sequence) continue;
        dprintf( 2, "[sc-runst] %s seq=%llu tid=%04x %s pump=0x%llx state=0x%llx\n",
                 tag, (unsigned long long)r->sequence, r->tid, r->operation == 1 ? "install" : "restore",
                 (unsigned long long)r->pump, (unsigned long long)r->state );
    }
}

static void ios_sc_diag_loop( const char *tag, uint64_t loop )
{
    uint64_t fields[40];
    if (!ios_sc_diag_read( loop, fields, sizeof(fields) ))
    {
        dprintf( 2, "[sc-runst] %s loop=0x%llx unreadable\n", tag, (unsigned long long)loop );
        return;
    }
    dprintf( 2, "[sc-runst] %s loop=0x%llx type=%u pump=0x%llx loop-state=0x%llx\n",
             tag, (unsigned long long)loop, (unsigned int)fields[1],
             (unsigned long long)fields[0x80 / 8], (unsigned long long)fields[0x128 / 8] );
}

static void ios_sc_runstate_dump( uint64_t image, uint64_t rip, uint64_t pump, uint64_t rsp )
{
    extern void *ios_jit_translate_addr_for_owner( void *, void * );
    extern unsigned long long ios_jit_module_base_for_va( unsigned long long, unsigned long long * );
    static volatile unsigned int dumps;
    uint64_t live, fields[10], state[3], loop = 0, stack[256];
    unsigned int i, found = 0;
    if (!ios_sc_diag_helper( image, rip ) || __sync_fetch_and_add( &dumps, 1 ) >= 4) return;
    live = (uint64_t)(uintptr_t)ios_jit_translate_addr_for_owner( (void *)(uintptr_t)image, NtCurrentTeb()->Peb );
    dprintf( 2, "[sc-runst] fault helper=0x%llx live=0x%llx rva=0x%llx pump=0x%llx rsp=0x%llx\n",
             (unsigned long long)image, (unsigned long long)live, (unsigned long long)(rip - image),
             (unsigned long long)pump, (unsigned long long)rsp );
    if (ios_sc_diag_read( pump, fields, sizeof(fields) ))
    {
        dprintf( 2, "[sc-runst] fault pump vtable=0x%llx state=0x%llx iocp=0x%llx\n",
                 (unsigned long long)fields[0], (unsigned long long)fields[8], (unsigned long long)fields[9] );
        if (ios_sc_diag_read( fields[8], state, sizeof(state) ))
            dprintf( 2, "[sc-runst] pump-state delegate=0x%llx dispatcher=0x%llx quit=%u depth=%u\n",
                     (unsigned long long)state[0], (unsigned long long)state[1],
                     (unsigned int)(state[2] & 0xff), (unsigned int)(state[2] >> 32) );
    }
    else dprintf( 2, "[sc-runst] fault pump unreadable\n" );
    ios_sc_diag_ring( "view", image );
    if (live != image) ios_sc_diag_ring( "pool", live );
    if (ios_sc_diag_read( live + 0x1d0c30, &loop, sizeof(loop) )) ios_sc_diag_loop( "renderer", loop );
    if (ios_sc_diag_read( live + 0x1cea00, &loop, sizeof(loop) )) ios_sc_diag_loop( "main", loop );
    /* Only image addresses are printed. These are return-address candidates,
     * not an unwind: omit stack contents and all guest strings/payloads. */
    if (ios_sc_diag_read( rsp, stack, sizeof(stack) ))
        for (i = 0; i < sizeof(stack) / sizeof(stack[0]) && found < 16; i++)
        {
            unsigned long long size = 0, base = ios_jit_module_base_for_va( stack[i], &size );
            if (!base) continue;
            found++;
            dprintf( 2, "[sc-runst] stack+0x%x image=0x%llx rva=0x%llx\n",
                     i * 8, base, (unsigned long long)(stack[i] - base) );
        }
}

#endif
