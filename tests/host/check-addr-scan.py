#!/usr/bin/env python3
"""GPU-address lookups stop where nothing earlier can reach (madeira.cfg
addr-scan, default 1); no Wine, no Metal.

mad_resolve_address finds the resource behind a GPU address (every
IASetVertexBuffers, IASetIndexBuffer and root descriptor a game records): a
binary search in the address index, then a walk back over the entries that
could still contain the address. That walk went over every entry that started
less than the LARGEST resource size below the address. Each entry now carries
pmax, the highest end of itself and every entry before it, and the walk stops
at the first entry whose pmax is at or below the address.

The runtime part cuts the index code (mad_aidx_begin .. the locked lookup) out
of madeira_d3d12.c and compiles it on the host with stand-ins, then tracks and
untracks thousands of resources -- packed buffers as Metal lays them out, a few
huge ones, aliasing placed resources, forced rebuilds -- and checks after every
change that pmax is the running maximum of the ends, and that every lookup
(inside resources, at their first and last byte, one past the end, in gaps)
returns what a brute-force search returns (the newest live resource holding the
address) and the same as the old walk (addr-scan = 0). It also prints how much
faster the lookups got.

In the source: pmax is kept by insert, remove and rebuild inside the aidx_ver
bracket; both walks (lock-free and locked) use it; the switch is read once,
before any lock; the catalog lists addr-scan, on by default.
"""
from pathlib import Path
import os, re, shutil, subprocess, sys, tempfile

root = Path(__file__).resolve().parents[2]
src = (root / "madeira-d3d12/src/pe/madeira_d3d12.c").read_text()
ok = True


def check(what, cond):
    global ok
    print(("ok   " if cond else "FAIL ") + what)
    ok &= bool(cond)


start = src.index("static void mad_aidx_begin(struct mad_device *d) {")
lk = src.index("static struct mad_resource *mad_resolve_address_locked(struct mad_device *d, UINT64 addr, UINT64 *off) {")
cut = src[start:src.index("\n}\n", lk) + 3]
entry = re.search(r"struct mad_addr_entry \{[^}]*\}", src).group(0)
grow = src[src.index("static int mad_grow(void **arr, unsigned *cap, unsigned need, size_t elem) {"):]
grow = grow[:grow.index("\n}\n") + 3]
check("index code found", "static void mad_aidx_pmax(struct mad_device *d, unsigned from)" in cut and "static struct mad_resource *mad_resolve_address(" in cut)
check("entries carry pmax", "UINT64 pmax;" in entry)
def body(name):
    b = cut[cut.index(name):]
    return b[:b.index("\n}\n")]
ins, rem, reb = body("static void mad_addr_index_insert("), body("static void mad_addr_index_remove("), body("static void mad_addr_index_rebuild(")
check("insert, remove and rebuild keep pmax inside the aidx_ver bracket",
      ins.index("mad_aidx_begin(d);") < ins.index("mad_aidx_pmax(d, lo);") < ins.rindex("mad_aidx_end(d);")
      and rem.index("mad_aidx_begin(d);") < rem.index("mad_aidx_pmax(d, i);") < rem.rindex("mad_aidx_end(d);")
      and reb.index("qsort(") < reb.index("mad_aidx_pmax(d, 0);") < reb.rindex("mad_aidx_end(d);"))
look, lock = body("static struct mad_resource *mad_resolve_address(struct mad_device *d"), body("static struct mad_resource *mad_resolve_address_locked(struct mad_device *d, UINT64 addr, UINT64 *off) {")
check("both walks stop on pmax (the old bound kept for addr-scan = 0)",
      "(pm ? MAD_LD(ax[i].pmax) > addr : MAD_LD(ax[i].lo) + maxsz > addr)" in look
      and "(g_addr_scan > 0 ? d->aidx[i].pmax > addr : d->aidx[i].lo + d->aidx_maxsize > addr)" in lock)
check("switch read once with mad_cfg_int_pe, on by default, before any lock",
      'g_addr_scan = mad_cfg_int_pe("addr-scan", 1) ? 1 : 0;' in cut
      and look.index("pm = mad_addr_scan_on();") < look.index("mad_resolve_address_locked(d, addr, off)"))
cat = (root / "app/Madeira/ConfigCatalog.generated.swift").read_text()
check("catalog lists addr-scan, on by default", re.search(r'key: "addr-scan".*kind: \.bool, defaultValue: "1"', cat) is not None)

harness = r'''
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdlib.h>
#include <time.h>
typedef uint64_t UINT64; typedef int64_t LONG64; typedef int LONG;
typedef struct { int x; } CRITICAL_SECTION;
static void EnterCriticalSection(CRITICAL_SECTION *c) { (void)c; }
static void LeaveCriticalSection(CRITICAL_SECTION *c) { (void)c; }
static LONG InterlockedIncrement(volatile LONG *p) { return ++*p; }
struct mad_resource { UINT64 gpu_address, size; unsigned track_seq; int live; };
struct mad_device {
    struct mad_resource **live; unsigned nlive, live_cap;
    ''' + entry + r''' *aidx;
    unsigned naidx, aidx_cap; int aidx_dirty; UINT64 aidx_maxsize; unsigned aidx_seq;
    CRITICAL_SECTION live_lock; volatile LONG64 aidx_ver;
};
static LONG g_resolve_locked, g_resolve_miss;
static long long mad_cfg_int_pe(const char *k, long long d) { (void)k; return d; }
''' + grow + cut + r'''
#define NRES 6000
static struct mad_resource res[NRES]; static unsigned nres;
static struct mad_device dev; static int bad;
#define EXPECT(c, what) do { if (!(c)) { printf("FAIL %s\n", what); bad = 1; } } while (0)
static unsigned long long rng = 99;
static unsigned rnd(unsigned n) { rng = rng * 6364136223846793005ull + 1442695040888963407ull; return (unsigned)(rng >> 33) % n; }
static struct mad_resource *brute(UINT64 a) {
    struct mad_resource *f = NULL; unsigned i;
    for (i = 0; i < nres; i++) if (res[i].live && a >= res[i].gpu_address && a < res[i].gpu_address + res[i].size && (!f || res[i].track_seq > f->track_seq)) f = &res[i];
    return f;
}
static void check_pmax(void) {
    UINT64 m = 0; unsigned i;
    if (dev.aidx_dirty) return;
    for (i = 0; i < dev.naidx; i++) {
        if (dev.aidx[i].hi > m) m = dev.aidx[i].hi;
        if (dev.aidx[i].pmax != m) { printf("FAIL pmax at %u of %u\n", i, dev.naidx); bad = 1; return; }
    }
}
static UINT64 probe(void) {   /* an address: inside a resource, at its first / last byte, one past, or anywhere */
    struct mad_resource *r = &res[rnd(nres)];
    switch (rnd(5)) {
    case 0: return r->gpu_address;
    case 1: return r->gpu_address + r->size - 1;
    case 2: return r->gpu_address + r->size;
    case 3: return r->gpu_address + (r->size > 1 ? rnd((unsigned)(r->size < 0x7fffffff ? r->size : 0x7fffffff)) : 0);
    default: return 0x100000000ull + (UINT64)rnd(0x7fffffff) * 4;
    }
}
int main(void) {
    UINT64 va = 0x100000000ull; unsigned i, step, lookups = 0;
    for (i = 0; i < NRES; i++) {   /* the layout: packed buffers, every 300th a huge one, every 7th aliasing an earlier one */
        struct mad_resource *r = &res[i];
        if (i % 7 == 3 && i > 10) {
            struct mad_resource *o = &res[i - 1 - rnd(i < 40 ? i - 1 : 40)];
            r->gpu_address = o->gpu_address + (o->size > 16 ? rnd((unsigned)(o->size / 2 < 0x7fffffff ? o->size / 2 : 0x7fffffff)) & ~15ull : 0);
            r->size = 16 + rnd(1 << 16);
        } else {
            r->size = i % 300 == 150 ? (UINT64)(124u << 20) : (UINT64)(256 + rnd(1 << 20));
            r->gpu_address = va; va += (r->size + 0xffff) & ~0xffffull;
        }
    }
    nres = NRES;
    for (step = 0; step < 20000; step++) {
        struct mad_resource *r = &res[rnd(nres)];
        unsigned k;
        if (!r->live) { mad_track(&dev, r); r->live = 1; } else if (rnd(3) == 0) { mad_untrack(&dev, r); r->live = 0; }
        if (rnd(500) == 0) dev.aidx_dirty = 1;   /* a lost insert: the next miss rebuilds */
        check_pmax();
        for (k = 0; k < 8; k++) {
            UINT64 a = probe(), off = 0, off0 = 0;
            struct mad_resource *want = brute(a), *got, *old;
            g_addr_scan = 1; got = mad_resolve_address(&dev, a, &off);
            g_addr_scan = 0; old = mad_resolve_address(&dev, a, &off0);
            g_addr_scan = 1;
            lookups++;
            if (got != want || old != want || (got && off != a - got->gpu_address)) {
                printf("FAIL lookup of %llx: got %p, old walk %p, brute force %p\n", (unsigned long long)a, (void *)got, (void *)old, (void *)want);
                bad = 1; step = 20000; break;
            }
        }
    }
    {   /* speed: all live, every lookup hits */
        struct timespec t0, t1, t2; double fast, slow; UINT64 sink = 0; unsigned n;
        for (i = 0; i < nres; i++) if (!res[i].live) { mad_track(&dev, &res[i]); res[i].live = 1; }
        mad_resolve_address(&dev, 1, NULL);   /* a miss: rebuilds if dirty */
        check_pmax();
        clock_gettime(CLOCK_MONOTONIC, &t0);
        g_addr_scan = 1; for (n = 0; n < 200000; n++) { struct mad_resource *r = &res[(n * 7919u) % nres]; sink += (UINT64)(uintptr_t)mad_resolve_address(&dev, r->gpu_address + r->size / 2, NULL); }
        clock_gettime(CLOCK_MONOTONIC, &t1);
        g_addr_scan = 0; for (n = 0; n < 200000; n++) { struct mad_resource *r = &res[(n * 7919u) % nres]; sink += (UINT64)(uintptr_t)mad_resolve_address(&dev, r->gpu_address + r->size / 2, NULL); }
        clock_gettime(CLOCK_MONOTONIC, &t2);
        fast = (t1.tv_sec - t0.tv_sec) * 1e9 + (t1.tv_nsec - t0.tv_nsec); slow = (t2.tv_sec - t1.tv_sec) * 1e9 + (t2.tv_nsec - t1.tv_nsec);
        printf("note: %u lookups checked; on this host a lookup takes %.0f ns with addr-scan, %.0f ns with the old walk (%u entries, largest 124 MB) %s\n",
               lookups, fast / 200000, slow / 200000, dev.naidx, sink ? "" : " ");
        EXPECT(fast < slow, "faster than the old walk");
    }
    if (!bad) printf("ok\n");
    return bad;
}
'''
cc = shutil.which("clang") or shutil.which("gcc") or shutil.which("cc")
if not cc:
    print("note: no host compiler; runtime checks skipped")
else:
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        (t / "h.c").write_text(harness)
        exe = t / "h"
        r = subprocess.run([cc, "-std=gnu11", "-O2", "-Wall", "-Wno-unused-function", "-o", str(exe), str(t / "h.c")], capture_output=True, text=True)
        if r.returncode:
            print(r.stderr[-3000:])
        out = subprocess.run([str(exe)], capture_output=True, text=True).stdout if exe.exists() else ""
        print(out.strip())
        check("lookups equal brute force and the old walk; pmax is the running maximum after every change",
              r.returncode == 0 and out.strip().endswith("ok"))

print("PASS" if ok else "FAILED")
sys.exit(0 if ok else 1)
