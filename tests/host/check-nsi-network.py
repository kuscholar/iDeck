#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 125hz
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""The in-process NSI network tables (build/ntdll-unix/nsi_network_ios.c).

iOS ships no nsiproxy.sys, so PE nsi.dll falls back to nsi_unixlib_ios.c. That
unixlib now hands every non-TCP enumerate and every row/field read to
nsiproxy.sys's table dispatcher over Wine's BSD NDIS/IPv4/IPv6 providers.

Compiles the production dispatcher (everything after its includes) and the
32-bit (WoW64) thunks of nsi_unixlib_ios.c, verbatim, together with fake
providers, under AddressSanitizer and UBSan, and checks:
  * routing: the NDIS/IPv4/IPv6 modules reach their own tables; TCP, UDP, an
    unknown table and a table without the requested operation answer
    STATUS_NOT_SUPPORTED (nsi.dll maps that back to the old device error);
  * validation: wrong row sizes, a size with a NULL buffer, a bad param_type
    and an offset/size that overflows are refused before any provider runs;
    zero sizes pass NULL buffers;
  * MADEIRA_NSI_NETWORK_TABLES=0 serves nothing; any other value serves;
  * an identical enumerate within MADEIRA_NSI_CACHE_MS reuses the last rows
    and count (a short buffer still gets STATUS_BUFFER_OVERFLOW, count-only
    and row reads, other arguments and failed reads are kept apart or not
    kept), a change shows after the window, and 0 turns the copy off;
  * [nsi-network] prints 16 lines at most, with module/table/status/count only;
  * unix calls 1 and 2 exist in both tables, in order, and the 32-bit thunks
    convert every embedded pointer (and nothing else) for the reads.
Static checks: build.sh compiles and archives the three new objects,
shims/net/route.h is Madeira's own (no Apple licence text) and declares only
what the providers use, and the Wine-derived files carry Wine's LGPL-2.1
notices. Synthetic data only: no Wine build, iOS SDK or device.
"""
from pathlib import Path
import os, re, shutil, subprocess, sys, tempfile

root = Path(__file__).resolve().parents[2]
unix = root / 'build/ntdll-unix'
network = (unix / 'nsi_network_ios.c').read_text()
unixlib = (unix / 'nsi_unixlib_ios.c').read_text()
build_sh = (unix / 'build.sh').read_text()
route_h = (unix / 'shims/net/route.h').read_text()
ip_c = (unix / 'nsi_ip_ios.c').read_text()
ndis_c = (unix / 'nsi_ndis_ios.c').read_text()
CC = os.environ.get('CC') or shutil.which('cc') or 'cc'
failures = 0


def require(condition, label):
    global failures
    print(('PASS: ' if condition else 'FAIL: ') + label)
    if not condition:
        failures += 1


def first_comment(text):
    return text[:text.index('*/') + 2]


# ------------------------------------------------------------------ static
for src, obj in [('nsi_network_ios.c', 'nsi_network_ios'), ('nsi_ndis_ios.c', 'nsi_ndis'), ('nsi_ip_ios.c', 'nsi_ip')]:
    require(f'compile_one "$BUILD_DIR/{src}" "{obj}"' in build_sh, f'build.sh compiles {src}')
    require(f'"$OBJ_DIR/{obj}.o"' in build_sh[build_sh.index('ar rcs "$OBJ_DIR/libntdll_unix.a"'):],
            f'build.sh archives {obj}.o into libntdll_unix.a')
require('-I"$BUILD_DIR/shims"' in build_sh, 'compile_one searches shims/ (for <net/route.h>)')

require(route_h.startswith('/* SPDX-License-Identifier: GPL-3.0-or-later\n * Copyright 2026 125hz\n'
                           ' * Madeira Converter Exception: see LICENSE-EXCEPTION.md\n'),
        "shims/net/route.h carries Madeira's own notice")
require(not re.search(r'APPLE_LICENSE|Apple Public Source|APSL|Copyright \(c\) [0-9-]+ Apple', route_h),
        'shims/net/route.h has no Apple licence text')
require(sorted(re.findall(r'^#define (RT[AFM]_[A-Z]+)', route_h, re.M)) ==
        sorted(['RTM_GET', 'RTM_IFINFO', 'RTF_GATEWAY', 'RTF_LLINFO', 'RTF_MULTICAST',
                'RTA_DST', 'RTA_GATEWAY', 'RTA_NETMASK', 'RTA_IFP']),
        'shims/net/route.h declares only the constants ndis.c and ip.c use')
require(ndis_c.startswith('/* SPDX-License-Identifier: GPL-3.0-or-later\n * Copyright 2026 125hz\n'),
        "nsi_ndis_ios.c (an include wrapper) carries Madeira's own notice")
require(ndis_c.rstrip().endswith('#include "../../wine/dlls/nsiproxy.sys/ndis.c"'), 'nsi_ndis_ios.c compiles ndis.c unchanged')
require('#include "../../wine/dlls/nsiproxy.sys/ip.c"' in ip_c, 'nsi_ip_ios.c compiles ip.c unchanged')

wine = root / 'wine/dlls/nsiproxy.sys'
for text, name, source in [(network, 'nsi_network_ios.c', 'nsi.c'), (ip_c, 'nsi_ip_ios.c', 'tcp.c')]:
    head = first_comment(text)
    require('GNU Lesser General Public' in head and 'version 2.1 of the License' in head and 'version 3' not in head
            and 'Huw Davies' in head, f"{name} keeps Wine's LGPL-2.1-or-later notice")
    if (wine / source).exists():
        require(head == first_comment((wine / source).read_text()), f"{name}'s notice is {source}'s, verbatim")
    else:
        print(f'SKIP: {name} vs wine/dlls/nsiproxy.sys/{source} (wine submodule not checked out)')

branch = unixlib[unixlib.index('if (!NmrIsEqualNpiModuleId( params->module, &ios_tcp_moduleid ))'):]
branch = branch[:branch.index('\n    }\n') + 6]
require('status = nsi_enumerate_all_ex( params );' in branch and 'return status;' in branch
        and 'return STATUS_NOT_SUPPORTED' not in branch,
        'nsi_unixlib_ios.c: a non-TCP enumerate goes to the dispatcher and returns its status')
log_calls = re.findall(r'dprintf\( 2, "\[nsi-network\][^;]*;', network, re.S)
require(len(log_calls) == 1 and '%p' not in log_calls[0] and 'addr' not in log_calls[0].lower(),
        '[nsi-network] prints module, table, status and count only')

# ------------------------------------------------------------------ dynamic
dispatcher = network[network.index('static const struct module *modules[] ='):]
funcs64 = unixlib[unixlib.index('const void *nsi_unix_call_funcs[] ='):]
funcs64 = funcs64[:funcs64.index('};') + 2]
thunks = unixlib[unixlib.index('typedef ULONG PTR32;'):]

prelude = r'''
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <time.h>
#include <unistd.h>
typedef int NTSTATUS; typedef unsigned int UINT, ULONG; typedef int BOOL; typedef uintptr_t UINT_PTR;
typedef unsigned char BYTE; typedef unsigned short USHORT;
#define TRUE 1
#define FALSE 0
#define STATUS_SUCCESS ((NTSTATUS)0)
#define STATUS_BUFFER_OVERFLOW ((NTSTATUS)0x80000005)
#define STATUS_INVALID_PARAMETER ((NTSTATUS)0xc000000d)
#define STATUS_NOT_SUPPORTED ((NTSTATUS)0xc00000bb)
#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))
#define WARN(...) do { } while (0)
typedef struct { unsigned int Data1; unsigned short Data2, Data3; unsigned char Data4[8]; } GUID;
typedef struct { USHORT Length; int Type; union { GUID Guid; unsigned long long IfLuid; }; } NPI_MODULEID;
static BOOL NmrIsEqualNpiModuleId( const NPI_MODULEID *a, const NPI_MODULEID *b )
{ return a->Type == b->Type && !memcmp( &a->Guid, &b->Guid, sizeof(GUID) ); }
/* wine/nsi.h */
struct nsi_enumerate_all_ex { void *unknown[2]; const NPI_MODULEID *module; UINT_PTR table; UINT first_arg, second_arg;
    void *key_data; UINT key_size; void *rw_data; UINT rw_size; void *dynamic_data; UINT dynamic_size;
    void *static_data; UINT static_size; UINT_PTR count; };
struct nsi_get_all_parameters_ex { void *unknown[2]; const NPI_MODULEID *module; UINT_PTR table; UINT first_arg, unknown2;
    const void *key; UINT key_size; void *rw_data; UINT rw_size; void *dynamic_data; UINT dynamic_size;
    void *static_data; UINT static_size; };
struct nsi_get_parameter_ex { void *unknown[2]; const NPI_MODULEID *module; UINT_PTR table; UINT first_arg, unknown2;
    const void *key; UINT key_size; UINT_PTR param_type; void *data; UINT data_size; UINT data_offset; };
/* wine/dlls/nsiproxy.sys/unix_private.h */
struct module_table { UINT table; UINT sizes[4];
    NTSTATUS (*enumerate_all)( void *, UINT, void *, UINT, void *, UINT, void *, UINT, UINT_PTR * );
    NTSTATUS (*get_all_parameters)( const void *, UINT, void *, UINT, void *, UINT, void *, UINT );
    NTSTATUS (*get_parameter)( const void *, UINT, UINT, void *, UINT, UINT ); };
struct module { const NPI_MODULEID *module; const struct module_table *tables; };
extern const struct module ndis_module, ipv4_module, ipv6_module;
NTSTATUS nsi_enumerate_all_ex( struct nsi_enumerate_all_ex *params );
NTSTATUS nsi_get_all_parameters_ex( struct nsi_get_all_parameters_ex *params );
NTSTATUS nsi_get_parameter_ex( struct nsi_get_parameter_ex *params );
/* the 32-bit thunks' environment: a guest window and the TCP entry they wrap */
static BYTE guest[1 << 16];
static void *ios_wow_host_ptr( ULONG addr ) { return addr ? guest + addr : NULL; }
static int tcp_entry_calls;
static NTSTATUS ios_nsi_enumerate_all_ex( void *args ) { (void)args; tcp_entry_calls++; return STATUS_SUCCESS; }
'''

harness_main = r'''
#define MOD(d1) { sizeof(NPI_MODULEID), 1, { { d1, 0x9b1a, 0x11d4, { 0x91, 0x23, 0x00, 0x50, 0x04, 0x77, 0x59, 0xbc } } } }
static const NPI_MODULEID ndis_id = MOD(0xeb004a11), ipv4_id = MOD(0xeb004a00), ipv6_id = MOD(0xeb004a01),
                          tcp_id = MOD(0xeb004a03), udp_id = MOD(0xeb004a02);
static int provider_calls, rows = 3;
static NTSTATUS fail_status;
static UINT test_first_arg;
static struct { const void *key; UINT key_size; void *p[4]; UINT s[4]; UINT param_type, data_size, data_offset; } seen;

static NTSTATUS fake_enumerate( void *k, UINT ks, void *rw, UINT rws, void *dyn, UINT ds, void *st, UINT ss, UINT_PTR *count )
{
    UINT i, want = ks || rws || ds || ss;
    provider_calls++;
    seen.p[0] = k; seen.p[1] = rw; seen.p[2] = dyn; seen.p[3] = st;
    if (fail_status) return fail_status;
    for (i = 0; want && i < (UINT)rows && i < *count; i++)
    {
        if (k) memset( (BYTE *)k + i * ks, 0x10 + i, ks );
        if (rw) memset( (BYTE *)rw + i * rws, 0x20 + i, rws );
        if (dyn) memset( (BYTE *)dyn + i * ds, 0x30 + i, ds );
        if (st) memset( (BYTE *)st + i * ss, 0x40 + i, ss );
    }
    if (!want || (UINT_PTR)rows <= *count) { *count = rows; return STATUS_SUCCESS; }
    return STATUS_BUFFER_OVERFLOW;
}
static NTSTATUS fake_get_all( const void *key, UINT ks, void *rw, UINT rws, void *dyn, UINT ds, void *st, UINT ss )
{
    provider_calls++;
    seen.key = key; seen.key_size = ks; seen.p[1] = rw; seen.p[2] = dyn; seen.p[3] = st;
    seen.s[1] = rws; seen.s[2] = ds; seen.s[3] = ss;
    if (rw) memset( rw, 0x5a, rws );
    return STATUS_SUCCESS;
}
static NTSTATUS fake_get( const void *key, UINT ks, UINT type, void *data, UINT size, UINT offset )
{
    provider_calls++;
    seen.key = key; seen.key_size = ks; seen.param_type = type; seen.p[0] = data; seen.data_size = size; seen.data_offset = offset;
    if (data) memset( data, 0x6b, size );
    return STATUS_SUCCESS;
}
static const struct module_table ndis_tables[] =
{
    { 0, { 8, 16, 32, 64 }, fake_enumerate, fake_get_all, fake_get },
    { ~0u },
};
static const struct module_table ipv4_tables[] =
{
    { 10, { 4, 0, 8, 0 }, fake_enumerate, NULL, NULL },
    { ~0u },
};
static const struct module_table ipv6_tables[] =
{
    { 16, { 20, 12, 0, 4 }, fake_enumerate, fake_get_all, fake_get },
    { ~0u },
};
const struct module ndis_module = { &ndis_id, ndis_tables };
const struct module ipv4_module = { &ipv4_id, ipv4_tables };
const struct module ipv6_module = { &ipv6_id, ipv6_tables };

static int check( int ok, const char *label ) { printf( "%s: %s\n", ok ? "PASS" : "FAIL", label ); return !ok; }

static NTSTATUS enumerate( const NPI_MODULEID *m, UINT table, UINT sizes[4], void *bufs[4], UINT_PTR *count )
{
    struct nsi_enumerate_all_ex p;
    NTSTATUS status;
    memset( &p, 0, sizeof(p) );
    p.module = m; p.table = table; p.count = *count; p.first_arg = test_first_arg;
    p.key_data = bufs[0]; p.key_size = sizes[0]; p.rw_data = bufs[1]; p.rw_size = sizes[1];
    p.dynamic_data = bufs[2]; p.dynamic_size = sizes[2]; p.static_data = bufs[3]; p.static_size = sizes[3];
    status = nsi_enumerate_all_ex( &p );
    *count = p.count;
    return status;
}

int main( int argc, char **argv )
{
    int fails = 0, i;
    BYTE a[4 * 64], b[4 * 64], c[4 * 64], d[4 * 64], key[64], out[64];
    UINT sizes[4] = { 8, 16, 32, 64 };
    void *bufs[4] = { a, b, c, d };
    UINT_PTR count;
    NTSTATUS st;
    int before, nocache = argc > 1 && !strcmp( argv[1], "nocache" );

    if (argc > 1 && !strcmp( argv[1], "off" ))   /* MADEIRA_NSI_NETWORK_TABLES=0 run */
    {
        struct nsi_get_all_parameters_ex ga = { { 0 }, &ndis_id, 0, 0, 0, key, 8, b, 16, NULL, 0, NULL, 0 };
        struct nsi_get_parameter_ex gp = { { 0 }, &ndis_id, 0, 0, 0, key, 8, 0, out, 4, 0 };
        count = 4;
        st = enumerate( &ndis_id, 0, sizes, bufs, &count );
        fails += check( st == STATUS_NOT_SUPPORTED && !provider_calls, "switch off: the NDIS table is not served" );
        fails += check( nsi_get_all_parameters_ex( &ga ) == STATUS_NOT_SUPPORTED && nsi_get_parameter_ex( &gp ) == STATUS_NOT_SUPPORTED
                        && !provider_calls, "switch off: row and field reads are not served" );
        return fails;
    }

    count = 4;
    st = enumerate( &ndis_id, 0, sizes, bufs, &count );
    fails += check( st == STATUS_SUCCESS && count == 3 && provider_calls == 1 && a[8] == 0x11 && d[64] == 0x41,
                    "NDIS interfaces: served by the NDIS provider, three rows" );
    {
        UINT s4[4] = { 4, 0, 8, 0 }; void *b4[4] = { a, b, c, d };
        count = 4; before = provider_calls;
        st = enumerate( &ipv4_id, 10, s4, b4, &count );
        fails += check( st == STATUS_SUCCESS && provider_calls == before + 1 && !seen.p[1] && !seen.p[3],
                        "IPv4 table: served; zero sizes pass NULL buffers" );
    }
    {
        UINT s6[4] = { 20, 12, 0, 4 };
        count = 4; before = provider_calls;
        st = enumerate( &ipv6_id, 16, s6, bufs, &count );
        fails += check( st == STATUS_SUCCESS && provider_calls == before + 1, "IPv6 table: served" );
    }
    before = provider_calls;
    count = 4;
    fails += check( enumerate( &tcp_id, 0, sizes, bufs, &count ) == STATUS_NOT_SUPPORTED
                    && enumerate( &udp_id, 0, sizes, bufs, &count ) == STATUS_NOT_SUPPORTED
                    && enumerate( &ndis_id, 1, sizes, bufs, &count ) == STATUS_NOT_SUPPORTED
                    && enumerate( NULL, 0, sizes, bufs, &count ) == STATUS_NOT_SUPPORTED
                    && provider_calls == before, "TCP, UDP, an unknown table and no module: STATUS_NOT_SUPPORTED" );
    {
        UINT bad[4] = { 8, 16, 33, 64 };
        void *nullbuf[4] = { a, NULL, c, d };
        count = 4;
        fails += check( enumerate( &ndis_id, 0, bad, bufs, &count ) == STATUS_INVALID_PARAMETER
                        && enumerate( &ndis_id, 0, sizes, nullbuf, &count ) == STATUS_INVALID_PARAMETER
                        && provider_calls == before, "wrong row size or a size with a NULL buffer: refused" );
    }
    {
        UINT zero[4] = { 0, 0, 0, 0 };
        count = 0; before = provider_calls;
        st = enumerate( &ndis_id, 0, zero, bufs, &count );
        fails += check( st == STATUS_SUCCESS && count == 3 && provider_calls == before + 1 && !seen.p[0] && !seen.p[3],
                        "count-only read (the check nsi.dll makes before calls 1 and 2): the row count" );
        count = 2;
        st = enumerate( &ndis_id, 0, sizes, bufs, &count );
        fails += check( st == STATUS_BUFFER_OVERFLOW && count == 2, "a short buffer: STATUS_BUFFER_OVERFLOW, count untouched" );
    }

    /* row reads */
    {
        struct nsi_get_all_parameters_ex ga = { { 0 }, &ndis_id, 0, 0, 0, key, 8, b, 16, NULL, 0, d, 64 };
        before = provider_calls;
        st = nsi_get_all_parameters_ex( &ga );
        fails += check( st == STATUS_SUCCESS && provider_calls == before + 1 && seen.key == key && seen.p[1] == b
                        && !seen.p[2] && seen.p[3] == d && b[0] == 0x5a, "row read: served, zero-size parts passed as NULL" );
        ga.key_size = 4;
        fails += check( nsi_get_all_parameters_ex( &ga ) == STATUS_INVALID_PARAMETER, "row read: wrong key size refused" );
        ga.key_size = 8; ga.key = NULL;
        fails += check( nsi_get_all_parameters_ex( &ga ) == STATUS_INVALID_PARAMETER, "row read: NULL key refused" );
        ga.key = key; ga.rw_data = NULL;
        fails += check( nsi_get_all_parameters_ex( &ga ) == STATUS_INVALID_PARAMETER, "row read: size with a NULL buffer refused" );
        ga.rw_data = b; ga.module = &ipv4_id; ga.table = 10;
        fails += check( nsi_get_all_parameters_ex( &ga ) == STATUS_NOT_SUPPORTED, "row read: a table without it answers NOT_SUPPORTED" );
        ga.module = &tcp_id; ga.table = 0;
        fails += check( nsi_get_all_parameters_ex( &ga ) == STATUS_NOT_SUPPORTED && provider_calls == before + 1,
                        "row read: TCP answers NOT_SUPPORTED" );
    }
    /* field reads */
    {
        /* param_type 0/1/2 = rw/dynamic/static part: 16/32/64 bytes here */
        struct nsi_get_parameter_ex gp = { { 0 }, &ndis_id, 0, 0, 0, key, 8, 1, out, 4, 28 };
        before = provider_calls;
        st = nsi_get_parameter_ex( &gp );
        fails += check( st == STATUS_SUCCESS && provider_calls == before + 1 && seen.param_type == 1 && seen.data_offset == 28
                        && seen.data_size == 4 && out[0] == 0x6b, "field read: the last 4 bytes of the dynamic part" );
        gp.data_offset = 30;
        fails += check( nsi_get_parameter_ex( &gp ) == STATUS_INVALID_PARAMETER, "field read past the part: refused" );
        gp.param_type = 2; gp.data_offset = 60;
        fails += check( nsi_get_parameter_ex( &gp ) == STATUS_SUCCESS && provider_calls == before + 2,
                        "field read: the last 4 bytes of the static part" );
        gp.param_type = 1;
        gp.data_offset = 0xfffffff0u; gp.data_size = 0x20;
        fails += check( nsi_get_parameter_ex( &gp ) == STATUS_INVALID_PARAMETER, "field read whose offset + size wraps: refused" );
        gp.data_offset = 0; gp.data_size = 4; gp.param_type = 3;
        fails += check( nsi_get_parameter_ex( &gp ) == STATUS_INVALID_PARAMETER, "param_type 3: refused" );
        gp.param_type = 0; gp.data = NULL;
        fails += check( nsi_get_parameter_ex( &gp ) == STATUS_INVALID_PARAMETER, "size with a NULL buffer: refused" );
        fails += check( provider_calls == before + 2, "no provider ran for a refused read" );
    }

    /* the unix call tables */
    fails += check( ARRAY_SIZE(nsi_unix_call_funcs) == 3 && nsi_unix_call_funcs[1] == (const void *)nsi_get_all_parameters_ex
                    && nsi_unix_call_funcs[2] == (const void *)nsi_get_parameter_ex, "64-bit table: calls 1 and 2 are the reads" );
    fails += check( ARRAY_SIZE(nsi_unix_call_wow64_funcs) == 3 && nsi_unix_call_wow64_funcs[0] == (const void *)ios_wow64_nsi_enumerate_all_ex
                    && nsi_unix_call_wow64_funcs[1] == (const void *)ios_wow64_nsi_get_all_parameters_ex
                    && nsi_unix_call_wow64_funcs[2] == (const void *)ios_wow64_nsi_get_parameter_ex, "32-bit table: the same three, in order" );

    /* the 32-bit reads: i386 layouts, every embedded pointer converted */
    fails += check( sizeof(struct nsi_get_all_parameters_ex32) == 56 && offsetof(struct nsi_get_all_parameters_ex32, key) == 24
                    && offsetof(struct nsi_get_all_parameters_ex32, static_size) == 52
                    && sizeof(struct nsi_get_parameter_ex32) == 48 && offsetof(struct nsi_get_parameter_ex32, param_type) == 32
                    && offsetof(struct nsi_get_parameter_ex32, data_offset) == 44, "32-bit argument blocks have the i386 layout" );
    {
        struct nsi_get_all_parameters_ex32 *ga = (void *)(guest + 0x100);
        memcpy( guest + 0x200, &ndis_id, sizeof(ndis_id) );
        memset( ga, 0, sizeof(*ga) );
        ga->module = 0x200; ga->table = 0; ga->key = 0x300; ga->key_size = 8;
        ga->rw_data = 0x400; ga->rw_size = 16; ga->static_data = 0x800; ga->static_size = 64;
        before = provider_calls;
        st = ((NTSTATUS (*)(void *))nsi_unix_call_wow64_funcs[1])( ga );
        fails += check( st == STATUS_SUCCESS && provider_calls == before + 1 && seen.key == guest + 0x300 && seen.p[1] == guest + 0x400
                        && !seen.p[2] && seen.p[3] == guest + 0x800 && guest[0x400] == 0x5a,
                        "32-bit row read: key, module and buffers are guest addresses; the row lands in the guest" );
    }
    {
        struct nsi_get_parameter_ex32 *gp = (void *)(guest + 0x100);
        memset( gp, 0, sizeof(*gp) );
        gp->module = 0x200; gp->key = 0x300; gp->key_size = 8; gp->param_type = 1; gp->data = 0x900; gp->data_size = 4; gp->data_offset = 12;
        before = provider_calls;
        st = ((NTSTATUS (*)(void *))nsi_unix_call_wow64_funcs[2])( gp );
        fails += check( st == STATUS_SUCCESS && provider_calls == before + 1 && seen.p[0] == guest + 0x900 && seen.param_type == 1
                        && seen.data_offset == 12 && seen.data_size == 4 && guest[0x900] == 0x6b,
                        "32-bit field read: converted, numbers unchanged" );
    }

    /* the short-lived table copy (MADEIRA_NSI_CACHE_MS, 500 ms by default) */
    if (nocache)
    {
        test_first_arg = 7; before = provider_calls;
        count = 4; enumerate( &ndis_id, 0, sizes, bufs, &count );
        count = 4; enumerate( &ndis_id, 0, sizes, bufs, &count );
        fails += check( provider_calls == before + 2, "MADEIRA_NSI_CACHE_MS=0: every read goes to the provider" );
    }
    else
    {
        BYTE kept[4 * 64];
        UINT zero[4] = { 0, 0, 0, 0 };
        NTSTATUS st2;

        test_first_arg = 7; before = provider_calls;
        count = 4; st = enumerate( &ndis_id, 0, sizes, bufs, &count );
        memcpy( kept, d, sizeof(kept) ); memset( a, 0, sizeof(a) ); memset( d, 0, sizeof(d) );
        count = 4; st2 = enumerate( &ndis_id, 0, sizes, bufs, &count );
        fails += check( st == STATUS_SUCCESS && st2 == STATUS_SUCCESS && provider_calls == before + 1 && count == 3
                        && !memcmp( kept, d, 3 * 64 ) && a[8] == 0x11,
                        "an identical read within the window: the same rows and count, one provider read" );
        count = 2;
        fails += check( enumerate( &ndis_id, 0, sizes, bufs, &count ) == STATUS_BUFFER_OVERFLOW && count == 2
                        && provider_calls == before + 1, "a short buffer on a kept table: STATUS_BUFFER_OVERFLOW, count untouched" );
        count = 0; enumerate( &ndis_id, 0, zero, bufs, &count );
        count = 0; st = enumerate( &ndis_id, 0, zero, bufs, &count );
        fails += check( st == STATUS_SUCCESS && count == 3 && provider_calls == before + 2,
                        "a count-only read is kept apart from a read of rows" );
        test_first_arg = 8;
        count = 4; enumerate( &ndis_id, 0, sizes, bufs, &count );
        fails += check( provider_calls == before + 3, "a different argument is a different request" );
        test_first_arg = 9; fail_status = (NTSTATUS)0xc0000001;
        count = 4; st = enumerate( &ndis_id, 0, sizes, bufs, &count );
        count = 4; st2 = enumerate( &ndis_id, 0, sizes, bufs, &count );
        fails += check( st == (NTSTATUS)0xc0000001 && st2 == st && provider_calls == before + 5, "a failed read is not kept" );
        fail_status = 0;
        test_first_arg = 7; rows = 4;
        count = 4; enumerate( &ndis_id, 0, sizes, bufs, &count );
        fails += check( count == 3 && provider_calls == before + 5, "within the window a change is not seen yet" );
        usleep( 700 * 1000 );
        count = 4; st = enumerate( &ndis_id, 0, sizes, bufs, &count );
        fails += check( st == STATUS_SUCCESS && count == 4 && provider_calls == before + 6, "after the window the provider is read again" );
        rows = 3; test_first_arg = 0;
    }

    /* the log stops after 16 enumerates */
    for (i = 0; i < 20; i++) { count = 4; enumerate( &ndis_id, 0, sizes, bufs, &count ); }
    return fails;
}
'''

with tempfile.TemporaryDirectory(prefix='madeira-nsi-network-') as tmp:
    tmp = Path(tmp)
    src = tmp / 'check.c'
    src.write_text(prelude + dispatcher + '\n' + funcs64 + '\n' + thunks + '\n' + harness_main)
    exe = tmp / 'check'
    build = subprocess.run([CC, '-std=gnu11', '-Wall', '-Wno-unused-function', '-Wno-missing-braces',
                            '-fsanitize=address,undefined', '-fno-sanitize-recover=undefined', '-g',
                            '-o', str(exe), str(src), '-lpthread'], capture_output=True, text=True)
    require(build.returncode == 0, 'the production dispatcher and 32-bit thunks compile on the host')
    if build.returncode:
        sys.stdout.write(build.stderr[-4000:])
    else:
        env = dict(os.environ, ASAN_OPTIONS='detect_leaks=0')
        for k in [k for k in env if k.startswith('MADEIRA_NSI_')]:
            env.pop(k)
        run = subprocess.run([str(exe)], env=env, capture_output=True, text=True)
        sys.stdout.write(run.stdout)
        require(run.returncode == 0, 'routing, validation and the 32-bit reads hold')
        logs = [l for l in run.stderr.splitlines() if l.startswith('[nsi-network]')]
        require(len(logs) == 16, f'[nsi-network] stops after 16 lines ({len(logs)})')
        require(all(re.fullmatch(r'\[nsi-network\] module=[0-9a-f]{8} table=\d+ status=[0-9a-f]{8} count=\d+', l) for l in logs),
                'log lines carry module, table, status and count only')
        if run.returncode:
            sys.stdout.write(run.stderr[-3000:])
        run = subprocess.run([str(exe)], env=dict(env, MADEIRA_NSI_NETWORK_TABLES='1'), capture_output=True, text=True)
        require(run.returncode == 0, 'MADEIRA_NSI_NETWORK_TABLES=1 (anything but 0) serves as by default')
        run = subprocess.run([str(exe), 'off'], env=dict(env, MADEIRA_NSI_NETWORK_TABLES='0'), capture_output=True, text=True)
        sys.stdout.write(run.stdout)
        require(run.returncode == 0 and '[nsi-network]' not in run.stderr, 'MADEIRA_NSI_NETWORK_TABLES=0: nothing served')
        run = subprocess.run([str(exe), 'nocache'], env=dict(env, MADEIRA_NSI_CACHE_MS='0'), capture_output=True, text=True)
        sys.stdout.write(''.join(l + '\n' for l in run.stdout.splitlines() if 'MADEIRA_NSI_CACHE_MS' in l or l.startswith('FAIL')))
        require(run.returncode == 0, 'MADEIRA_NSI_CACHE_MS=0: routing, validation and the 32-bit reads hold without the copy')

    # shims/net/route.h compiles on its own; its asserts pin the 92-byte message header
    hdr = tmp / 'route_check.c'
    hdr.write_text('#include <sys/types.h>\n#include "%s"\nint main(void) { return RTM_IFINFO == 0xe ? 0 : 1; }\n'
                   % (unix / 'shims/net/route.h').as_posix())
    build = subprocess.run([CC, '-std=gnu11', '-Wall', '-o', str(tmp / 'route_check'), str(hdr)], capture_output=True, text=True)
    require(build.returncode == 0, "shims/net/route.h compiles and its layout asserts hold")
    if build.returncode:
        sys.stdout.write(build.stderr[-2000:])

if failures:
    print(f'check-nsi-network: {failures} FAILED')
    sys.exit(1)
print('check-nsi-network: PASS')
