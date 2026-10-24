#!/usr/bin/env python3
"""NtProtectVirtualMemory's [exec-req] path leaves the syscall callback; no Wine runs.

The PE ntdll shipped until 7b56800 (app/Madeira/arm64ec-windows/ntdll.dll, built
from the wine fork's dlls/ntdll/signal_arm64ec.c) returned from its ml283
[exec-req] probe without leave_syscall_callback(), so
CHPE_V2_CPU_AREA_INFO::InSyscallCallback stayed set and the next memory
notifications on that thread never reached the emulator (docs/gta5-child-crash.md
section 8). build/ntdll-unix/virtual_ios.c ios_patch_execreq_leave retargets the
probe's three exits in the pool copy (opt-in, MADEIRA_EXECREQ_LEAVE=1). Wine
38aa753f98b (ml1259) fixed the probe in source; the ntdll.dll shipped now already
leaves the callback, and the patcher recognises that layout and writes nothing.

This check compiles the production patch code with a model of the JIT pool (one
RX/RW alias, owner-aware translation, a child copy, x18-patched instructions) and
checks:
  - the SHIPPED ntdll.dll: the old layout is absent and the fixed probe is found
    exactly once; walking it from the probe's syscall result to `ret`, every path
    passes leave_syscall_callback(); MADEIRA_EXECREQ_LEAVE unset/0: one "off"
    line; =1: one "already leaves" line however many copies ask, nothing written
    to the image or to any pool copy; a probe with an exit that skips the clear
    is not taken for the fixed one;
  - a SYNTHETIC old-layout image (a minimal PE holding the round-3 ntdll.dll's
    probe at its VA, 0x1800573b8): unset/0: nothing written; =1: the three
    branches hold the expected words and nothing else changes, the image is
    untouched, a second call is a no-op, a child's copy is patched without
    touching the parent's, a copy that differs from the image is refused, an
    image without the probe is reported; control flow: the UNPATCHED code has a
    path that never reaches the InSyscallCallback clear (the bug), the patched
    code has none;
  - ios_image_section_describe names .text / .data of the shipped image and a
    pool copy, and the [prot-img] / [guest-rip-sec] call sites are in place.
Needs python3 and a C compiler (AddressSanitizer/UBSan when available).
"""
from pathlib import Path
import os
import re
import struct
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
native = (root / 'build/ntdll-unix/virtual_ios.c').read_text()
loader = (root / 'build/ntdll-unix/loader_ios.c').read_text()
signal = (root / 'build/ntdll-unix/signal_arm64_ios.c').read_text()
ntdll = root / 'app/Madeira/arm64ec-windows/ntdll.dll'


def function(source, signature):
    start = source.index(signature)
    return source[start:source.index('\n}', start) + 2] + '\n'


def between(source, first, last):
    start = source.index(first)
    return source[start:source.index(last, start) + len(last)] + '\n'


# Call sites: the session's ntdll (load_ntdll_functions), the EC child ntdll,
# and a pseudo-process child's private copy before it runs.
assert loader.count('ios_patch_execreq_leave( module );') == 2, 'session and EC-child ntdll must be patched'
child = function(loader, 'DECLSPEC_EXPORT void wine_ios_child_main(')
assert child.index('ios_jit_copy_module_for_child(pLdrInitializeThunk, child_peb)') \
    < child.index('ios_patch_execreq_leave_current( pLdrInitializeThunk )') \
    < child.index('server_init_process_done();'), 'the child copy must be patched before the child runs'
protect = function(native, 'NTSTATUS WINAPI NtProtectVirtualMemory( HANDLE process, PVOID *addr_ptr, SIZE_T *size_ptr,')
# build 327: insc= was always 1 inside the syscall (the wrapper sets the flag
# before it on the notified path too), so [prot-img] no longer prints it.
assert '[prot-img] #%d tid=%04x' in protect and 'status=%#x | %s' in protect and 'insc=%d' not in protect
assert protect.index('[prot-img]') < protect.index('server_leave_uninterrupted_section( &virtual_mutex, &sigset );')
assert '[guest-rip-sec] rip=%p' in signal

# The probe as the round-3 ntdll.dll (ef12368, shipped until 7b56800) had it, from
# VA 0x1800573b8 to the epilogue's ret: the layout ios_patch_execreq_leave patches.
OLD_PROBE = [
    0x72001f3f, 0x54000960, 0xf00003c8, 0xf947550b, 0xb4000a6b, 0xb00003c8, 0xf94002c1, 0xf94002a0,  # +0x000
    0xf945c508, 0xb000014a, 0x9126514a, 0xd63f0100, 0x2a1303e2, 0x52800023, 0x2a1a03e4, 0xd63f0160,  # +0x020
    0x14000047, 0xaa1403e0, 0xaa1503e1, 0xaa1603e2, 0x2a1303e3, 0x12001f39, 0x940015ea, 0x2a0003fa,  # +0x040
    0x340004b9, 0xf00003c8, 0xf947550b, 0xb40005ab, 0xf94002c1, 0xf94002a0, 0x3500081b, 0xd35efc28,  # +0x060
    0xb40007c8, 0x900003e8, 0xb94ed109, 0x71004d3f, 0x5400048c, 0xb00003ca, 0x11000529, 0x395ec14a,  # +0x080
    0xb90ed109, 0x360803ea, 0xb00003c8, 0x911ec108, 0x910003e4, 0x900002c9, 0x912ec129, 0xd00002c2,  # +0x0a0
    0x9124c042, 0xa90087e0, 0xd00002c3, 0x91230063, 0x52800020, 0xaa0803e1, 0x52800405, 0xb9001bf3,  # +0x0c0
    0xf90003e9, 0x97fffb9d, 0xf94bc648, 0xb50001e8, 0x1400001b, 0xf94002c3, 0xf94002a2, 0x910003e4,  # +0x0e0
    0x52800048, 0xaa1403e0, 0x528000a1, 0x52800305, 0xb90013fa, 0xb9000bf3, 0xb90003e8, 0x940006ea,  # +0x100
    0xf94bc648, 0xb40001c8, 0x3900051f, 0x1400000c, 0xf94002c3, 0xf94002a2, 0x910003e4, 0x52800048,  # +0x120
    0xaa1403e0, 0x528000a1, 0x52800305, 0xb90013fa, 0xb9000bf3, 0xb90003e8, 0x940006db, 0x2a1a03e0,  # +0x140
    0xa9477bfb, 0xa9466bf9, 0xa9455bf5, 0xa94453f3, 0x910203ff, 0xd65f03c0,                          # +0x160
]


def synthetic_image(path):
    """A minimal PE32+ DLL: .text (R-X) at RVA 0x57000 holds OLD_PROBE at RVA
    0x573b8, where the round-3 build had it; .data (RW-) follows."""
    text = bytearray(0x1000)
    struct.pack_into(f'<{len(OLD_PROBE)}I', text, 0x3b8, *OLD_PROBE)
    data = bytes(0x200)
    lfanew, optsz = 0x78, 0xf0
    head = bytearray(0x400)
    head[0:2] = b'MZ'
    struct.pack_into('<I', head, 0x3c, lfanew)
    head[lfanew:lfanew + 4] = b'PE\0\0'
    # AMD64 machine (as ARM64EC images say), two sections, DLL | LARGE_ADDRESS_AWARE | EXECUTABLE
    struct.pack_into('<HHIIIHH', head, lfanew + 4, 0x8664, 2, 0, 0, 0, optsz, 0x2022)
    opt = lfanew + 24
    struct.pack_into('<H', head, opt, 0x20b)                                  # PE32+
    struct.pack_into('<QII', head, opt + 24, 0x180000000, 0x1000, 0x200)     # ImageBase, alignments
    struct.pack_into('<II', head, opt + 56, 0x59000, len(head))              # SizeOfImage, SizeOfHeaders
    struct.pack_into('<I', head, opt + 108, 16)                              # NumberOfRvaAndSizes
    raw = len(head)
    for i, (name, rva, body, flags) in enumerate([(b'.text', 0x57000, text, 0x60000020),
                                                  (b'.data', 0x58000, data, 0xc0000040)]):
        struct.pack_into('<8sIIIIIIHHI', head, opt + optsz + 40 * i, name, len(body), rva, len(body), raw,
                         0, 0, 0, 0, flags)
        raw += len(body)
    path.write_bytes(bytes(head) + bytes(text) + data)


code = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static void sys_icache_invalidate( void *p, size_t n ) { (void)p; (void)n; }
void *ios_jit_rx_base_global, *ios_jit_rw_base_global;
size_t ios_jit_pool_size_global;
'''
code += between(native, '#define IOS_JIT_MAX_MAPPINGS', '\n};')
code += 'static struct ios_jit_mapping ios_jit_mappings[IOS_JIT_MAX_MAPPINGS];\n'
code += 'static int ios_jit_mapping_count = 0;\n'
code += r'''
static void *cur_peb;
/* owner-aware, as in virtual_ios.c: the current process's copy, else the NULL-owner one */
void *ios_jit_translate_addr( void *addr )
{
    int i, fb = -1;
    uintptr_t a = (uintptr_t)addr;
    for (i = 0; i < ios_jit_mapping_count; i++)
    {
        uintptr_t b = (uintptr_t)ios_jit_mappings[i].pe_base;
        if (a < b || a >= b + ios_jit_mappings[i].size) continue;
        if (ios_jit_mappings[i].owner_peb == cur_peb) { fb = i; break; }
        if (!ios_jit_mappings[i].owner_peb && fb < 0) fb = i;
    }
    if (fb < 0) return addr;
    return (char *)ios_jit_mappings[fb].jit_base + (a - (uintptr_t)ios_jit_mappings[fb].pe_base);
}
'''
code += between(native, '#define IOS_EXECREQ_WORDS 17u', 'snprintf( buf, len, "%soutside every section (rva %#x, %u sections)", where, off, nsec );\n        return 1;\n    }\n    return 0;\n}')
code += r'''
#define PREF 0x180000000ull
#define COPY 0x200000u                           /* the child's copy, after the session's */
#define CHILD_PEB ((void *)0x10999c000ull)
static unsigned char *img, *pool, *orig, *snap;  /* globals: LeakSanitizer sees them reachable */
static uint32_t soi;

static void load_image( const char *path )
{
    FILE *f = fopen( path, "rb" );
    long n; unsigned char *file; uint32_t lfanew, soh; uint16_t nsec, optsz; unsigned i;
    assert( f );
    fseek( f, 0, SEEK_END ); n = ftell( f ); fseek( f, 0, SEEK_SET );
    file = malloc( n ); assert( fread( file, 1, n, f ) == (size_t)n ); fclose( f );
    memcpy( &lfanew, file + 0x3c, 4 );
    memcpy( &nsec, file + lfanew + 6, 2 ); memcpy( &optsz, file + lfanew + 20, 2 );
    memcpy( &soi, file + lfanew + 24 + 56, 4 ); memcpy( &soh, file + lfanew + 24 + 60, 4 );
    assert( soi <= COPY );
    img = aligned_alloc( 0x10000, (soi + 0xffff) & ~0xffffu ); memset( img, 0, soi );
    memcpy( img, file, soh );
    for (i = 0; i < nsec; i++)
    {
        const unsigned char *sh = file + lfanew + 24 + optsz + 40 * i;
        uint32_t vs, va, rs, ro;
        memcpy( &vs, sh + 8, 4 ); memcpy( &va, sh + 12, 4 ); memcpy( &rs, sh + 16, 4 ); memcpy( &ro, sh + 20, 4 );
        memcpy( img + va, file + ro, rs < vs || !vs ? rs : vs );
    }
    free( file );
}

static void dump( const char *tag, const unsigned char *fn )
{
    unsigned i;
    printf( "%s", tag );
    for (i = 0; i < 0x180 / 4; i++) printf( " %08x", ((const uint32_t *)fn)[i] );
    printf( "\n" );
}

/* The x18 patcher turns each `ldr x8, [x18, #0x1788]` into a branch to its
 * trampoline in every copy; the copies as they are then are the reference. */
static void x18_patch( uint32_t rva )
{
    uint32_t i;
    for (i = 0; i < 0x180; i += 4)
        if (*(const uint32_t *)(img + rva + i) == 0xf94bc648)
        {
            *(uint32_t *)(pool + rva + i) = 0x14001234;
            *(uint32_t *)(pool + COPY + rva + i) = 0x14001234;
        }
    memcpy( snap, pool, 2 * COPY );
}

static unsigned changed_words( const unsigned char *a, const unsigned char *b, size_t n )
{
    unsigned c = 0;
    size_t i;
    for (i = 0; i < n; i += 4) c += *(const uint32_t *)(a + i) != *(const uint32_t *)(b + i);
    return c;
}

static int untouched( void )
{
    return !memcmp( img, orig, soi ) && !memcmp( pool, snap, 2 * COPY );
}

int main( int argc, char **argv )
{
    const char *mode = argc > 2 ? argv[2] : "";
    uint32_t rva, want[3], i;
    char buf[160];
    unsigned long long ib = 0;
    void *inside;

    load_image( argv[1] );
    pool = aligned_alloc( 0x10000, 4 * COPY ); memset( pool, 0, 4 * COPY );
    ios_jit_rx_base_global = ios_jit_rw_base_global = pool;
    ios_jit_pool_size_global = 4 * COPY;
    /* the session copy (owner NULL) and a child's private copy */
    memcpy( pool, img, soi );
    memcpy( pool + COPY, img, soi );
    ios_jit_mappings[0].pe_base = img; ios_jit_mappings[0].jit_base = pool; ios_jit_mappings[0].size = soi;
    ios_jit_mappings[1].pe_base = img; ios_jit_mappings[1].jit_base = pool + COPY; ios_jit_mappings[1].size = soi;
    ios_jit_mappings[1].owner_peb = CHILD_PEB;
    ios_jit_mapping_count = 2;
    orig = malloc( soi ); memcpy( orig, img, soi );
    snap = malloc( 2 * COPY );
    inside = img + soi / 2;                  /* any address in the shared image, as pLdrInitializeThunk */
    cur_peb = (void *)0x71ffff0000ull;       /* the session: no copy of its own, so the NULL-owner one */

    if (!strcmp( mode, "off" ))
    {
        /* MADEIRA_EXECREQ_LEAVE unset, 0 or empty: either layout, nothing written */
        if (!(rva = ios_execreq_find( img, 0 ))) rva = ios_execreq_find( img, 1 );
        assert( rva );
        x18_patch( rva );
        assert( ios_patch_execreq_leave( img ) == 0 );
        assert( ios_patch_execreq_leave( img ) == 0 );
        cur_peb = CHILD_PEB;
        assert( ios_patch_execreq_leave_current( inside ) == 0 );
        assert( untouched() );
        printf( "off: nothing written\n" );
        return 0;
    }

    if (!strcmp( mode, "fixed" ))
    {
        /* the shipped ntdll.dll: built with wine 38aa753f98b, nothing to patch */
        assert( !ios_execreq_find( img, 0 ) );
        rva = ios_execreq_find( img, 1 );
        printf( "fixed probe rva %#x va %#llx\n", rva, PREF + rva );
        assert( rva );
        dump( "image", img + rva );
        x18_patch( rva );
        assert( ios_patch_execreq_leave( img ) == 0 );
        assert( ios_patch_execreq_leave( img ) == 0 );
        cur_peb = CHILD_PEB;
        assert( ios_patch_execreq_leave_current( inside ) == 0 );
        assert( untouched() );

        /* an exit that skips the clear is not the fixed probe: the notified exit
         * without its load, the clear without its store, a branch out of the
         * cross-process block */
        {
            uint32_t *w = (uint32_t *)(img + rva);
            const uint32_t clr = ios_a64_imm19_target( 0x10, w[4] ), xp = ios_a64_imm19_target( 0x04, w[1] );
            const uint32_t at[3] = { 0x40, clr + 8, xp + 16 };
            const uint32_t by[3] = { 0xd503201f /* nop */, 0xd503201f, ios_a64_b( xp + 16, clr + 12 ) };

            for (i = 0; i < 3; i++)
            {
                const uint32_t keep = w[at[i] / 4];
                w[at[i] / 4] = by[i];
                assert( !ios_execreq_find( img, 1 ) && ios_patch_execreq_leave( img ) == -1 );
                w[at[i] / 4] = keep;
            }
            assert( ios_execreq_find( img, 1 ) == rva && untouched() );
        }

        /* section names */
        assert( ios_image_section_describe( (uintptr_t)img + rva, buf, sizeof(buf), &ib ) && ib == (uintptr_t)img );
        printf( "text: %s\n", buf );
        assert( strstr( buf, "'.text'" ) && strstr( buf, "(R-X CODE)" ) );
        assert( ios_image_section_describe( (uintptr_t)img + 0xd0010, buf, sizeof(buf), NULL ) );
        printf( "data: %s\n", buf );
        assert( strstr( buf, "'.data'" ) && strstr( buf, "(RW-)" ) );
        assert( !ios_image_section_describe( 0x10000, buf, sizeof(buf), NULL ) );
        /* a pool address is named with its copy and that copy's owner (build 327:
         * the child died in the parent's ntdll copy + 0x87050) */
        ib = 0;
        assert( ios_image_section_describe( (uintptr_t)pool + COPY + 0x87050, buf, sizeof(buf), &ib ) &&
                ib == (uintptr_t)img );
        printf( "pool: %s\n", buf );
        assert( strstr( buf, "POOL copy" ) && strstr( buf, "owner=0x10999c000" ) && strstr( buf, "rva 0x87050" ) );
        printf( "fixed: recognised, said once, nothing written, broken exits refused\n" );
        return 0;
    }

    /* "old": the synthetic image with the round-3 probe, MADEIRA_EXECREQ_LEAVE=1 */
    rva = ios_execreq_find( img, 0 );
    printf( "probe rva %#x va %#llx\n", rva, PREF + rva );
    assert( rva && PREF + rva == 0x1800573b8ull && !ios_execreq_find( img, 1 ) );
    x18_patch( rva );
    dump( "before", pool + rva );

    ios_execreq_patched_words( want );
    printf( "words %08x %08x %08x\n", want[0], want[1], want[2] );
    assert( want[0] == 0x54000780 && want[1] == 0xb400088b && want[2] == 0x14000038 );

    /* session copy: the three branches, nothing else */
    assert( ios_patch_execreq_leave( img ) == 1 );
    assert( ((uint32_t *)(pool + rva))[1] == want[0] );
    assert( ((uint32_t *)(pool + rva))[4] == want[1] );
    assert( ((uint32_t *)(pool + rva))[16] == want[2] );
    assert( changed_words( pool, snap, COPY ) == 3 );
    assert( !memcmp( img, orig, soi ) );                             /* image untouched */
    assert( !memcmp( pool + COPY, snap + COPY, COPY ) );             /* child copy untouched */
    assert( ios_patch_execreq_leave( img ) == 0 );                   /* idempotent */
    dump( "after", pool + rva );

    /* the child's private copy, through the shared image */
    cur_peb = CHILD_PEB;
    assert( ios_patch_execreq_leave_current( inside ) == 1 );
    assert( ((uint32_t *)(pool + COPY + rva))[16] == want[2] );
    assert( changed_words( pool + COPY, snap + COPY, COPY ) == 3 );
    assert( ios_patch_execreq_leave_current( inside ) == 0 );
    assert( ios_patch_execreq_leave_current( (void *)0x10000 ) == -1 );

    /* a copy that differs from the image is left alone */
    memcpy( pool + COPY, img, soi );
    ((uint32_t *)(pool + COPY + rva))[8] ^= 1;
    assert( ios_patch_execreq_leave( img ) == -1 );
    assert( ((uint32_t *)(pool + COPY + rva))[16] == ios_execreq_sig[16] );
    memcpy( pool + COPY, img, soi );
    ((uint32_t *)(pool + COPY + rva + IOS_EXECREQ_CLEAR))[2] = 0xd503201f;   /* clear gone */
    assert( ios_patch_execreq_leave( img ) == -1 );

    /* an image without the probe */
    memset( img + rva, 0, 4 );
    assert( ios_patch_execreq_leave( img ) == -1 );
    printf( "old: patched, idempotent, child copy, refusals\n" );
    return 0;
}
'''


def walk(words, start, clears):
    """Every path from `start` to `ret`: does each one pass a clear (the offset of
    leave_syscall_callback's `ldr x8, [x18, #0x1788]`, which falls through; in a
    pool copy the x18 patcher's branch there returns to the next instruction)?
    words: dict offset->insn (function-relative). Calls (bl/blr) return."""
    bad = []
    seen = set()
    stack = [(start, False)]
    while stack:
        pc, cleared = stack.pop()
        if (pc, cleared) in seen:
            continue
        seen.add((pc, cleared))
        if pc in clears:
            cleared = True
        w = words.get(pc)
        assert w is not None, hex(pc)
        succ = []
        if w == 0xd65f03c0:                                   # ret
            if not cleared:
                bad.append(pc)
            continue
        if pc in clears:                                      # returns to the next insn
            succ = [pc + 4]
        elif (w & 0xfc000000) == 0x14000000:                  # b
            imm = w & 0x03ffffff
            imm -= (1 << 26) if imm & (1 << 25) else 0
            succ = [pc + imm * 4]
        elif (w & 0xff000010) == 0x54000000 or (w & 0x7e000000) == 0x34000000:   # b.cond / cbz / cbnz
            imm = (w >> 5) & 0x7ffff
            imm -= (1 << 19) if imm & (1 << 18) else 0
            succ = [pc + 4, pc + imm * 4]
        elif (w & 0x7e000000) == 0x36000000:                  # tbz / tbnz
            imm = (w >> 5) & 0x3fff
            imm -= (1 << 14) if imm & (1 << 13) else 0
            succ = [pc + 4, pc + imm * 4]
        else:                                                 # anything else, calls included, falls through
            succ = [pc + 4]
        for s in succ:
            stack.append((s, cleared))
    return bad


def words_of(out, tag):
    line = next(l for l in out.splitlines() if l.startswith(tag + ' '))
    return {i * 4: int(x, 16) for i, x in enumerate(line.split()[1:])}


with tempfile.TemporaryDirectory() as directory:
    folder = Path(directory)
    source = folder / 'check.c'
    source.write_text(code)
    executable = folder / 'check'
    cc = os.environ.get('CC', 'cc')
    flags = [cc, '-std=gnu11', '-Wall', '-Wextra', '-Wno-unused-function', '-Wno-unused-parameter',
             '-Werror', '-g', str(source), '-o', str(executable)]
    sanitize = ['-fsanitize=address,undefined', '-fno-sanitize-recover=all']
    if subprocess.run(flags[:1] + sanitize + flags[1:], capture_output=True).returncode == 0:
        print('built with AddressSanitizer/UBSan')
    else:
        subprocess.run(flags, check=True)
        print('built without sanitizers')

    old = folder / 'old-layout.dll'
    synthetic_image(old)
    runs = [(image, value, 'off') for image in (ntdll, old) for value in (None, '0', '')]
    runs += [(ntdll, '1', 'fixed'), (old, '1', 'old')]
    for image, value, mode in runs:
        env = dict(os.environ)
        env.pop('MADEIRA_EXECREQ_LEAVE', None)
        if value is not None:
            env['MADEIRA_EXECREQ_LEAVE'] = value
        result = subprocess.run([str(executable), str(image), mode], env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        out, err = result.stdout, result.stderr
        print(f'{image.name} MADEIRA_EXECREQ_LEAVE={value!r}: ' + out.strip().splitlines()[-1])
        if mode == 'off':
            assert err.count('[execreq-leave]') == 1 and '[execreq-leave] off' in err, err
            continue
        if mode == 'fixed':
            rva = re.search(r'^fixed probe rva (0x[0-9a-f]+) ', out, re.M)[1]
            assert err.count('[execreq-leave]') == 4, err
            assert err.count(f'already leaves the syscall callback (rva {rva}, wine 38aa753f98b) '
                             '-- nothing to patch') == 1, err
            assert err.count('not found exactly once') == 3 and 'now clears' not in err, err
            # every path from the probe's syscall result to `ret` leaves the callback
            words = words_of(out, 'image')
            clears = {o for o, w in words.items() if w == 0xf94bc648}
            leaks = walk(words, 0x0, clears)
            print(f'shipped probe at rva {rva}: {len(clears)} clears, {len(leaks)} path end(s) without one')
            assert len(clears) >= 2 and not leaks, leaks
            continue
        assert err.count('[execreq-leave] ntdll') >= 2 and 'now clears InSyscallCallback (rva 0x573b8' in err, err
        assert 'differs from the image at +0x20' in err and 'the blocks the patch branches to differ' in err, err
        assert 'not found exactly once' in err and 'already leaves' not in err, err

        before, after = words_of(out, 'before'), words_of(out, 'after')
        # the probe's paths start after its own syscall and log line (VA 0x1800573b8 = +0x0)
        bug = walk(before, 0x0, {0x120})
        fixed = walk(after, 0x0, {0x120})
        print(f'unpatched: {len(bug)} path end(s) without the clear; patched: {len(fixed)}')
        assert bug, 'the unpatched probe should reach ret without clearing InSyscallCallback'
        assert not fixed, f'patched probe still reaches ret without the clear: {fixed}'
print('PASS: the shipped ntdll.dll already leaves the syscall callback and is left alone; the old-layout '
      'fix is opt-in, exact, idempotent and per copy, and closes every path')
