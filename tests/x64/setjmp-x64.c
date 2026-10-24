/*
 * setjmp-x64.c — regression test for the x64 <-> ARM64EC setjmp/longjmp seam.
 *
 * Reproduces exactly the route Qt5Gui's bundled libjpeg takes:
 *     x64 guest -> VCRUNTIME140!__intrinsic_setjmp / longjmp
 *  -> ucrtbase thunks -> ntdll!_setjmp / ntdll!longjmp
 *  -> NTDLL__setjmpex / NTDLL_longjmp
 *
 * The ml703 bug: do_setjmpex() called unwind_one_frame() with a JIT-POOL pc,
 * RtlLookupFunctionEntry found no unwind info, the frame was treated as a leaf,
 * a zero return address was popped, and the resulting all-zero context was
 * copied over a perfectly good jump buffer.  longjmp then unwound to RIP 0 and
 * the guest branched to address zero.
 *
 * Resolved through GetProcAddress rather than the CRT's own setjmp so the test
 * provably exercises VCRUNTIME140's exports.  Everything observed across the
 * longjmp is volatile, because the compiler cannot see that a call through a
 * function pointer can return twice.
 */
#include <windows.h>
#include <stdio.h>
#include <string.h>

typedef int  (*setjmp_fn )( void *buf );
typedef void (*longjmp_fn)( void *buf, int val );

/* x64 _JUMP_BUFFER field offsets */
#define JB_FRAME 0x00
#define JB_RBX   0x08
#define JB_RSP   0x10
#define JB_RBP   0x18
#define JB_RSI   0x20
#define JB_RDI   0x28
#define JB_RIP   0x50

static unsigned char jbuf[512] __attribute__((aligned(16)));
static volatile int stage;
static volatile int sj_ret;
static volatile int failures;

static unsigned long long fld( unsigned off )
{
    unsigned long long v;
    memcpy( &v, jbuf + off, sizeof(v) );
    return v;
}

static void dump( const char *when )
{
    printf( "[sjtest] %-14s Frame=%016llx Rbx=%016llx Rsp=%016llx Rbp=%016llx Rsi=%016llx Rdi=%016llx Rip=%016llx\n",
            when, fld(JB_FRAME), fld(JB_RBX), fld(JB_RSP), fld(JB_RBP),
            fld(JB_RSI), fld(JB_RDI), fld(JB_RIP) );
    fflush( stdout );
}

static void check( int ok, const char *what )
{
    printf( "[sjtest] %-4s %s\n", ok ? "PASS" : "FAIL", what );
    if (!ok) failures++;
    fflush( stdout );
}

int main( void )
{
    volatile unsigned long long canary = 0x5EAF00DDEADBEEFull;
    volatile int  loops = 0;
    HMODULE h;
    setjmp_fn  sj;
    longjmp_fn lj;

    printf( "[sjtest] rev=ml703 x64 setjmp/longjmp via VCRUNTIME140\n" );

    if (!(h = LoadLibraryA( "VCRUNTIME140.dll" )))
    { printf( "[sjtest] FAIL: LoadLibrary(VCRUNTIME140) err=%lu\n", GetLastError() ); return 2; }

    sj = (setjmp_fn) (void *)GetProcAddress( h, "__intrinsic_setjmp" );
    lj = (longjmp_fn)(void *)GetProcAddress( h, "longjmp" );
    printf( "[sjtest] __intrinsic_setjmp=%p longjmp=%p\n", (void *)sj, (void *)lj );
    if (!sj || !lj) { printf( "[sjtest] FAIL: missing export\n" ); return 2; }

    memset( jbuf, 0, sizeof(jbuf) );
    stage = 0; sj_ret = -1;

    sj_ret = sj( jbuf );
    loops++;
    printf( "[sjtest] setjmp returned %d (stage=%d, loops=%d)\n", sj_ret, stage, loops );
    dump( stage == 0 ? "after-setjmp" : "after-longjmp" );

    if (stage == 0)
    {
        check( sj_ret == 0, "first setjmp() returns 0" );
        /* A buffer whose Rip is zero is the ml703 signature: longjmp would
         * unwind to RIP 0 and the process would branch to address zero. */
        check( fld(JB_RIP) != 0, "jump buffer Rip is non-zero" );
        check( fld(JB_RSP) != 0, "jump buffer Rsp is non-zero" );
        if (!fld(JB_RIP))
        {
            printf( "[sjtest] FAIL: Rip==0 — not calling longjmp, it would kill the process\n" );
            return 1;
        }
        stage = 1;
        lj( jbuf, 1 );
        printf( "[sjtest] FAIL: longjmp() returned to its caller\n" );
        return 1;
    }

    check( sj_ret == 1, "setjmp() returns longjmp's value (1)" );
    check( canary == 0x5EAF00DDEADBEEFull, "stack local survived the longjmp" );
    check( loops == 2, "control really passed through setjmp twice" );

    printf( "[sjtest] %s (%d failure%s)\n", failures ? "OVERALL FAIL" : "OVERALL PASS",
            failures, failures == 1 ? "" : "s" );
    return failures ? 1 : 0;
}
