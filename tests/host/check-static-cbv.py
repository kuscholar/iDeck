#!/usr/bin/env python3
"""static-cbv (build 491, Horizon Zero Dawn).

NVIDIA's driver, and vkd3d-proton for single-descriptor CBV ranges of a
descriptor table ("hoisting"; all of them with force_static_cbv), read a
constant-buffer descriptor when the draw is recorded. madeira-d3d12 read every
descriptor when the GPU runs. A game that rewrites such a descriptor after the
draw was recorded draws right there and with another object's constants here.
static-cbv latches those descriptors at each draw's record (MC_CBV_LATCH) and
gives the GPU a copy of the table with them.

Checks: off by default and every hook guarded; the root-signature parser keeps
the single-CBV ranges, their VOLATILE flags and the table extent; draws,
dispatches and ExecuteIndirect latch; replay counts descriptors rewritten since
the record; the copy holds the latched CBVs (mode 1: ranges not marked VOLATILE;
mode 2: all), the other descriptors from the heap, sits in the chunk of the
draw's own argument slot and is reused while nothing changes; catalog; Horizon
Zero Dawn's list. The helpers are compiled and run against stubs.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
pe = (root / 'madeira-d3d12/src/pe/madeira_d3d12.c').read_text()
catalog = (root / 'app/Madeira/ConfigCatalog.generated.swift').read_text()
recs = (root / 'app/Madeira/GameRecommendations.swift').read_text()
ok = True


def check(what, cond):
    global ok
    print(('ok   ' if cond else 'FAIL ') + what)
    ok &= bool(cond)


def block(src, start, end):
    i = src.index(start)
    return src[i:src.index(end, i)]


DEF = ('static int exec_arg_slot_for(struct mad_exec *e, const struct mad_rootsig *rs, const UINT64 *root,\n'
       '                             const UINT32 (*consts)[64], obj_handle_t *buf, UINT64 *off, const UINT *ovr, const struct mad_pso *pso) {')
scbv = block(pe, '/* madeira-bcd STATIC-CBV', '/* ---- madeira-bcd: SYNC DIAGNOSTICS')

check('off by default', 'mad_cfg_int_pe("static-cbv", 0)' in scbv and 'g_scbv_on = v >= 1 && v <= 3 ? (int)v : 0;' in scbv)
parse = block(pe, 'UINT32 pos = 0, ext = 0, bounded = 1;', 'r->nranges += nr;')
check('the parser keeps single-CBV ranges, their VOLATILE flag (1.0: volatile) and a bounded extent',
      'D3D12_DESCRIPTOR_RANGE_FLAG_DESCRIPTORS_VOLATILE;   /* 1.0: volatile */' in pe and
      'rg->range_type == MADEIRA_IR_RANGE_CBV && rg->num_descriptors == 1 && r->scbv_n[i] < 8' in parse and
      'r->scbv_vol[i] |= (UINT8)(1u << r->scbv_n[i]);' in parse and
      "r->scbv_ext[i] = bounded && ext && ext <= MAD_SCBV_MAX_EXT ? (UINT16)ext : 0;" in pe)
check('draws, dispatches and ExecuteIndirect latch before they are recorded',
      pe.count('if (g_scbv_on > 0) mad_scbv_latch((struct mad_list *)This, 0);   /* madeira-bcd static-cbv */') == 2 and
      'if (g_scbv_on > 0) mad_scbv_latch((struct mad_list *)This, 1);   /* madeira-bcd static-cbv */' in pe and
      'if (g_scbv_on > 0) mad_scbv_latch((struct mad_list *)This, kind == MC_DISPATCH_INDIRECT ? 1 : 0);' in pe)
check('record state: tables, signatures (which drop the tables), the heap; Reset clears it',
      'if (!resolve && g_scbv_on > 0) l->rec_tab[0][index] = value;' in pe and
      'if (!resolve && g_scbv_on > 0) l->rec_tab[1][index] = value;' in pe and
      'l->rec_rs[0] = (struct mad_rootsig *)rs; memset(l->rec_tab[0], 0, sizeof l->rec_tab[0]);' in pe and
      'l->rec_rs[1] = (struct mad_rootsig *)rs; memset(l->rec_tab[1], 0, sizeof l->rec_tab[1]);' in pe and
      'if (c->u.heaps.srv) l->rec_heap = c->u.heaps.srv;' in pe and
      'l->rec_rs[0] = l->rec_rs[1] = NULL; l->rec_heap = NULL;' in pe)
check('replay: latches remembered, dropped with the signature',
      'case MC_CBV_LATCH: mad_scbv_replay(&e, c); break;' in pe and
      'case MC_ROOTSIG: e.rs = c->u.rootsig; memset(e.lat_va[0], 0, sizeof e.lat_va[0]);' in pe and
      'case MC_CROOTSIG: e.crs = c->u.rootsig; memset(e.lat_va[1], 0, sizeof e.lat_va[1]);' in pe)
slot = block(pe, DEF, '\n}\n')
check('the copies are made right before the argument slot (modes 1 and 2), after the sync diagnostics saw the real tables',
      'const int sc_on = (g_scbv_on == 1 || g_scbv_on == 2) && rs && root && (root == e->root || root == e->croot);' in slot and
      slot.index('root = mad_sd_root(e, rs, root, sd_root, pso);') < slot.index('if (sc_on) root = mad_scbv_root(e, rs, root, sc_root, sc_bp);') <
      slot.index('chunk = l->ring_used / (MAD_ARG_RING_BYTES / MAD_ARG_SLOT_BYTES);'))
check('a report every 300 presents', 'if (g_scbv_on > 0 && s->presents % 300 == 0) mad_scbv_report(s->presents);' in pe)
check('settings catalog', 'ConfigOption(key: "static-cbv"' in catalog)
hzd = block(recs, 'static let horizonZeroDawn = GameRecommendation(', 'avx: false')
check("no game list has it (HZD's v15 dropped it: on 491 it found nothing to latch differently)", 'static-cbv' not in hzd)
configs = [c.split('"""')[0] for c in recs.split('config: """')[1:]]
check('no other game list has it', sum('static-cbv' in c for c in configs) == 0)

harness = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdarg.h>
typedef uint32_t UINT32; typedef unsigned UINT; typedef long LONG; typedef uint64_t UINT64; typedef int64_t LONG64;
typedef uint8_t UINT8; typedef uint16_t UINT16;
typedef unsigned long long obj_handle_t;
static LONG InterlockedIncrement(volatile LONG *p) { return ++*p; }
static char logbuf[8192]; static size_t loglen;
static void d3d12_log(const char *fmt, ...) {
    va_list ap; va_start(ap, fmt);
    loglen += (size_t)vsnprintf(logbuf + loglen, sizeof logbuf - loglen, fmt, ap);
    va_end(ap);
}
static long long cfg;
static long long mad_cfg_int_pe(const char *k, long long d) { return !strcmp(k, "static-cbv") ? cfg : d; }
#define MAD_ROOT_PARAM_MAX 32
#define MAD_SCBV_MAX_EXT 64u
#define MAD_ARG_RING_BYTES (64u * 1024u)
#define MAD_ARG_SLOT_BYTES 1088u
struct mad_descriptor { UINT64 gpu_va, texture_view_id, metadata; };
struct mad_heap { struct mad_descriptor *cpu; UINT64 gpu_address; UINT count; };
struct mad_rootsig { UINT nparams; UINT8 scbv_n[MAD_ROOT_PARAM_MAX], scbv_vol[MAD_ROOT_PARAM_MAX];
                     UINT16 scbv_off[MAD_ROOT_PARAM_MAX][8], scbv_ext[MAD_ROOT_PARAM_MAX]; };
enum mad_ck { MC_DRAW = 1, MC_CBV_LATCH = 40 };
struct mad_cmd { enum mad_ck kind; union { struct { UINT bp, index, data, n; UINT64 va; } latch; } u; };
struct mad_list {
    UINT32 *cdata; unsigned ncdata, cdcap;
    struct mad_rootsig *rec_rs[2]; UINT64 rec_tab[2][MAD_ROOT_PARAM_MAX]; struct mad_heap *rec_heap;
    UINT64 lat_va[2][MAD_ROOT_PARAM_MAX]; unsigned lat_data[2][MAD_ROOT_PARAM_MAX];
    obj_handle_t *rings; void **ring_cpu; UINT64 *ring_gpu; unsigned nrings; unsigned ring_used;
};
struct mad_exec {
    struct mad_list *l; struct mad_heap *srv; struct mad_rootsig *rs, *crs;
    UINT64 root[MAD_ROOT_PARAM_MAX], croot[MAD_ROOT_PARAM_MAX];
    UINT64 lat_va[2][MAD_ROOT_PARAM_MAX]; unsigned lat_data[2][MAD_ROOT_PARAM_MAX], lat_n[2][MAD_ROOT_PARAM_MAX];
    UINT64 sc_src[2][MAD_ROOT_PARAM_MAX], sc_dst[2][MAD_ROOT_PARAM_MAX]; unsigned sc_lat[2][MAD_ROOT_PARAM_MAX], sc_chunk[2][MAD_ROOT_PARAM_MAX];
};
static int mad_grow(void **arr, unsigned *cap, unsigned need, size_t elem) {
    if (need > *cap) { unsigned n = need * 2; void *p = realloc(*arr, n * elem); if (!p) return 0; *arr = p; *cap = n; }
    return 1;
}
static struct mad_cmd cmds[64]; static unsigned ncmds;
static struct mad_cmd *mad_list_push(struct mad_list *l, enum mad_ck kind) {
    (void)l; if (ncmds == 64) return NULL; memset(&cmds[ncmds], 0, sizeof cmds[0]); cmds[ncmds].kind = kind; return &cmds[ncmds++];
}
static int mad_list_ring_grow(struct mad_exec *e) {
    struct mad_list *l = e->l;
    l->rings = realloc(l->rings, (l->nrings + 1) * sizeof *l->rings);
    l->ring_cpu = realloc(l->ring_cpu, (l->nrings + 1) * sizeof *l->ring_cpu);
    l->ring_gpu = realloc(l->ring_gpu, (l->nrings + 1) * sizeof *l->ring_gpu);
    l->rings[l->nrings] = 100 + l->nrings; l->ring_cpu[l->nrings] = calloc(1, MAD_ARG_RING_BYTES);
    l->ring_gpu[l->nrings] = 0x700000000ull + 0x100000ull * l->nrings; l->nrings++;
    return 1;
}
''' + scbv + r'''
static int bad;
#define EXPECT(c, what) do { if (!(c)) { printf("FAIL %s\n", what); bad = 1; } else printf("ok   %s\n", what); } while (0)
int main(void) {
    static struct mad_descriptor heapmem[64];
    struct mad_heap h = { heapmem, 0x500000000ull, 64 };
    static struct mad_rootsig rs; static struct mad_list l; static struct mad_exec e;
    UINT64 tmpbuf[MAD_ROOT_PARAM_MAX]; const UINT64 *t;
    const struct mad_descriptor *cp;
    const unsigned per = MAD_ARG_RING_BYTES / MAD_ARG_SLOT_BYTES;
    unsigned i;
    for (i = 0; i < 64; i++) { heapmem[i].gpu_va = 0x1000 + i; heapmem[i].texture_view_id = i; heapmem[i].metadata = 256; }
    /* p0: CBV at 0 (not volatile) + two SRVs, extent 3; p1: one VOLATILE CBV; p2: a CBV in an unbounded table (not copied) */
    rs.nparams = 3;
    rs.scbv_n[0] = 1; rs.scbv_off[0][0] = 0; rs.scbv_ext[0] = 3;
    rs.scbv_n[1] = 1; rs.scbv_off[1][0] = 0; rs.scbv_ext[1] = 1; rs.scbv_vol[1] = 1;
    rs.scbv_n[2] = 1; rs.scbv_off[2][0] = 0; rs.scbv_ext[2] = 0;
    cfg = 1; EXPECT(mad_scbv_on() == 1 && strstr(logbuf, "static-cbv = 1") != NULL, "static-cbv = 1 read once and logged");
    l.rec_rs[0] = &rs; l.rec_heap = &h;
    l.rec_tab[0][0] = h.gpu_address + 10 * 24; l.rec_tab[0][1] = h.gpu_address + 20 * 24; l.rec_tab[0][2] = h.gpu_address + 30 * 24;
    mad_scbv_latch(&l, 0);
    EXPECT(ncmds == 3 && cmds[0].kind == MC_CBV_LATCH && cmds[0].u.latch.index == 0 && cmds[0].u.latch.va == l.rec_tab[0][0] &&
           cmds[0].u.latch.n == 1 && l.cdata[cmds[0].u.latch.data] == 0x100a && g_scbv_latches == 3,
           "a draw latches the CBV of every bound table that has one");
    mad_scbv_latch(&l, 0);
    EXPECT(ncmds == 3, "the next draw, nothing rewritten: no new latch");
    heapmem[10].gpu_va = 0x9999;   /* the game rewrites the constant buffer after the first draw */
    mad_scbv_latch(&l, 0);
    EXPECT(ncmds == 4 && cmds[3].u.latch.index == 0 && l.cdata[cmds[3].u.latch.data] == 0x9999,
           "rewritten after the draw: the next draw latches the new one");
    l.rec_tab[0][1] = 0; mad_scbv_latch(&l, 0);
    EXPECT(ncmds == 4, "an unbound table latches nothing");
    l.rec_tab[0][1] = h.gpu_address + 70 * 24; mad_scbv_latch(&l, 0);
    EXPECT(ncmds == 4, "a table outside the heap latches nothing");

    /* replay */
    e.l = &l; e.srv = &h; e.rs = &rs;
    mad_scbv_replay(&e, &cmds[0]); mad_scbv_replay(&e, &cmds[1]); mad_scbv_replay(&e, &cmds[2]);
    EXPECT(g_scbv_checked == 2 && g_scbv_changed == 1 && g_scbv_checked_vol == 1 && g_scbv_changed_vol == 0,
           "replay counts a latched descriptor the heap no longer holds (non-VOLATILE and VOLATILE apart)");
    e.root[0] = cmds[0].u.latch.va; e.root[1] = cmds[1].u.latch.va; e.root[2] = cmds[2].u.latch.va;
    t = mad_scbv_root(&e, &rs, e.root, tmpbuf, 0);
    cp = l.nrings ? (const struct mad_descriptor *)l.ring_cpu[0] : NULL;
    EXPECT(t == tmpbuf && l.nrings == 1 && t[0] == l.ring_gpu[0] && t[1] == e.root[1] && t[2] == e.root[2] && l.ring_used == 1 &&
           g_scbv_skipped == 1 && cp && cp[0].gpu_va == 0x100a && cp[1].gpu_va == 0x100b && cp[2].gpu_va == 0x100c,
           "mode 1: the table is copied with the CBV as recorded and the SRVs from the heap; a VOLATILE-only table and an unbounded one are not");
    t = mad_scbv_root(&e, &rs, e.root, tmpbuf, 0);
    EXPECT(t[0] == l.ring_gpu[0] && l.ring_used == 1 && g_scbv_reused == 1 && g_scbv_copies == 1, "the next draw reuses the copy");
    mad_scbv_replay(&e, &cmds[3]);
    t = mad_scbv_root(&e, &rs, e.root, tmpbuf, 0);
    EXPECT(t[0] == l.ring_gpu[0] + MAD_ARG_SLOT_BYTES && l.ring_used == 2 &&
           ((const struct mad_descriptor *)((const char *)l.ring_cpu[0] + MAD_ARG_SLOT_BYTES))->gpu_va == 0x9999,
           "after the next latch: a new copy with the newly latched CBV");
    l.ring_used = per - 1;
    t = mad_scbv_root(&e, &rs, e.root, tmpbuf, 0);
    EXPECT(l.ring_used == per - 1 && t[0] == l.ring_gpu[0] + MAD_ARG_SLOT_BYTES,
           "the slot still fits the chunk that holds the copy: reused");
    memset(e.sc_dst, 0, sizeof e.sc_dst);   /* as if the latch had changed */
    t = mad_scbv_root(&e, &rs, e.root, tmpbuf, 0);
    EXPECT(l.nrings == 2 && t[0] == l.ring_gpu[1] && l.ring_used == per + 1,
           "no room for a new copy and the slot in this chunk: both go to the next one");
    l.ring_used = per - 2;
    t = mad_scbv_root(&e, &rs, e.root, tmpbuf, 0);
    EXPECT(l.ring_used == per - 1 && t[0] == l.ring_gpu[0] + (UINT64)(per - 2) * MAD_ARG_SLOT_BYTES,
           "a copy is not reused from another chunk than the slot's");
    g_scbv_on = 2; l.ring_used = 0;
    t = mad_scbv_root(&e, &rs, e.root, tmpbuf, 0);
    cp = (const struct mad_descriptor *)l.ring_cpu[0];
    EXPECT(t[1] == l.ring_gpu[0] + 3 * 24 && cp[3].gpu_va == 0x1014 && l.ring_used == 1, "mode 2: the VOLATILE table is copied too, packed after the first");
    loglen = 0; mad_scbv_report(300);
    EXPECT(strstr(logbuf, "[static-cbv] present #300: 4 latches") != NULL && strstr(logbuf, "1 of 3 latched descriptors of ranges not marked VOLATILE") != NULL,
           "the report");
    printf("%s\n", bad ? "harness FAILED" : "harness ok");
    if (bad) printf("%s", logbuf);
    return bad;
}
'''

cc = shutil.which('cc') or shutil.which('gcc') or shutil.which('clang')
if not cc:
    check('a host C compiler', False)
else:
    with tempfile.TemporaryDirectory(prefix='madeira-scbv-') as tmp:
        src = Path(tmp) / 'scbv.c'
        exe = Path(tmp) / 'scbv'
        src.write_text(harness)
        b = subprocess.run([cc, '-std=gnu11', '-Wall', '-Wno-unused-function', '-Wno-unused-variable', str(src), '-o', str(exe)],
                           capture_output=True, text=True)
        check('the helpers compile on the host', b.returncode == 0)
        if b.returncode:
            print(b.stderr[-3000:])
        else:
            run = subprocess.run([str(exe)], capture_output=True, text=True)
            print(run.stdout, end='')
            check('the helpers behave', run.returncode == 0)

print('PASS: static-cbv' if ok else 'FAIL: static-cbv')
raise SystemExit(0 if ok else 1)
