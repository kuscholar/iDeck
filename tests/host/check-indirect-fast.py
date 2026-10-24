#!/usr/bin/env python3
"""ExecuteIndirect fast path (madeira.cfg indirect-fast = 1); no Wine, no Metal.

madeira_d3d12.c replays an ExecuteIndirect record by record through the whole
exec_draw / exec_dispatch. With indirect-fast = 1, record 0 still does, and
records 1..count-1 are encoded 64 to a call as only what differs. This test
cuts mad_indirect_fast_on, exec_indirect_fast_why and exec_indirect_rest out of the file
(exec_indirect_fast_ok below is their verdict), compiles
them on the host against the real winemetal.h with a recording
encodeCommands, and checks:
  - off by default, and refused for one record, any capture / census / fault /
    skip-ps / sync diagnostic, the draw-dump windows, a pending capture,
    geometry emulation, a DXBC pipeline with a tessellation or geometry
    variant, an indexed draw without an index buffer, and a closed encoder;
    DXIL and (build 470) DXBC draws and dispatches qualify;
  - draws: per record, buffer 4 (the converter's draw parameters) bound to the
    args buffer at off + k * stride, then the indirect draw at the same offset
    (indexed: the encoder's topology, index type, buffer and offset), in
    batches of at most 64 records chained in order and NULL-terminated, on the
    render encoder; draws and pass draws counted;
  - dispatches: per record one indirect dispatch at off + k * stride on the
    compute encoder, batched the same way;
and in the source: the replay loop takes the fast path only after record 0
drew (and never for indirect tessellation), then leaves the loop; exec_draw
still binds buffer 4 and the indexed draw the way the fast path repeats them;
the catalog lists indirect-fast, off by default.
The runtime part needs clang (or gcc with C23 enums).
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


start = src.index("static int g_indirect_fast = -1;")
end = src.index("\n}\n", src.index("static void exec_indirect_rest(")) + 3
cut = src[start:end]
check("fast path functions found", "static int mad_indirect_fast_on(" in cut and "static int exec_indirect_fast_why(" in cut
      and "static void exec_indirect_rest(" in cut)
check("switch read once with mad_cfg_int_pe, off by default",
      'g_indirect_fast = mad_cfg_int_pe("indirect-fast", 0) ? 1 : 0;' in cut and "if (g_indirect_fast < 0)" in cut)

loop = src[src.index("case MC_DRAW_INDIRECT: case MC_DRAW_INDEXED_INDIRECT: case MC_DISPATCH_INDIRECT: {"):]
loop = loop[:loop.index("\n            break;\n        }")]
check("replay loop: fast path only after record 0 drew (never for indirect tessellation, where the runtime has it), "
      "then leaves the loop",
      "unsigned drawn = e.draws;" in loop
      and "if (!k && mad_indirect_fast_on()) {" in loop
      and ("int why = tess ? IFR_TESS_IND : e.draws != drawn + 1 ? IFR_NOT_DRAWN : exec_indirect_fast_why(&e, c);" in loop
           or ("int tess" not in loop
               and "int why = e.draws != drawn + 1 ? IFR_NOT_DRAWN : exec_indirect_fast_why(&e, c);" in loop))
      and "mad_ifr_note(why, c->u.ind.count);" in loop
      and "if (why != IFR_USED) mad_ifr_detail(&e, c, why, (int)(e.draws - drawn));" in loop
      and "if (why == IFR_USED) { exec_indirect_rest(&e, c); break; }" in loop
      and loop.index("exec_draw(&e, &t);") < loop.index("exec_indirect_fast_why(&e, c)"))
draw = src[src.index("static void exec_draw(struct mad_exec *e, const struct mad_cmd *c) {"):]
draw = draw[:draw.index("\n}\n")]
check("exec_draw binds the record at buffer 4 as the fast path repeats it",
      "MAD_SETBUF(WMTRenderCommandSetVertexBuffer, c->u.ind.args->buffer, c->u.ind.off, 4);" in draw)
check("exec_draw's indexed indirect draw matches the fast path's fields",
      all(s in draw for s in ("c_dii.primitive_type = mad_prim(e->topo);", "c_dii.index_type = e->ib_type;",
                              "c_dii.index_buffer = e->ib->buffer;", "c_dii.index_buffer_offset = e->ib_off;",
                              "c_dii.indirect_args_buffer = c->u.ind.args->buffer;", "c_dii.indirect_args_offset = c->u.ind.off;")))
disp = src[src.index("static void exec_dispatch(struct mad_exec *e, const struct mad_cmd *c) {"):]
disp = disp[:disp.index("\n}\n")]
check("exec_dispatch binds nothing per record: the indirect dispatch alone differs",
      "c_dispi.indirect_args_offset = c->u.ind.off;" in disp and "c->u.ind.off, 4" not in disp)
cat = (root / "app/Madeira/ConfigCatalog.generated.swift").read_text()
check("catalog lists indirect-fast, off by default",
      re.search(r'key: "indirect-fast".*kind: \.bool, defaultValue: "0"', cat) is not None)

harness = r'''
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdarg.h>
#include "winemetal.h"
typedef uint64_t UINT64; typedef unsigned UINT; typedef long LONG; typedef long long LONG64; typedef unsigned D3D12_PRIMITIVE_TOPOLOGY;
enum mad_ck { MC_DRAW = 1, MC_DRAW_INDIRECT, MC_DRAW_INDEXED_INDIRECT, MC_DISPATCH_INDIRECT };
#define MADEIRA_IR_BACKEND_MSC 0
#define MADEIRA_IR_BACKEND_AIRCONV 1
struct mad_resource { obj_handle_t buffer; };
struct mad_pso { int backend; int gs_emu; obj_handle_t cps; void *tess, *tess_strip; int has_tess; };
struct mad_cmd { enum mad_ck kind; union { struct { struct mad_resource *args; UINT64 off; UINT count; UINT stride; } ind; } u; };
struct mad_exec {
    obj_handle_t renc, cenc; struct mad_pso *pso, *cpso; struct mad_resource *ib; UINT64 ib_off;
    enum WMTIndexType ib_type; D3D12_PRIMITIVE_TOPOLOGY topo; unsigned draws, pass_draws;
    unsigned cap_after; struct mad_resource *cap_after_cs; unsigned ncap_after_buf, ncap_after_tex;
};
static int g_census_on, g_capture_on, g_skip_ps_state = -1, g_sd_state, g_quiet_log;
static volatile LONG g_fault_diag;
static unsigned g_list_seq = 100, g_dump_draws;
static long long cfg_value, cfg_reads;
static long long mad_cfg_int_pe(const char *k, long long d) { cfg_reads++; return strcmp(k, "indirect-fast") ? d : cfg_value; }
static void d3d12_log(const char *fmt, ...) { (void)fmt; }
static LONG InterlockedExchangeAdd(volatile LONG *p, LONG v) { return __atomic_fetch_add(p, v, __ATOMIC_SEQ_CST); }
static LONG64 InterlockedExchangeAdd64(volatile LONG64 *p, LONG64 v) { return __atomic_fetch_add(p, v, __ATOMIC_SEQ_CST); }
static LONG InterlockedIncrement(volatile LONG *p) { return __atomic_add_fetch(p, 1, __ATOMIC_SEQ_CST); }
static enum WMTPrimitiveType mad_prim(D3D12_PRIMITIVE_TOPOLOGY t) { return t == 4 ? WMTPrimitiveTypeTriangle : WMTPrimitiveTypePoint; }

struct rec { int compute; unsigned type; obj_handle_t enc, buf, ib; UINT64 off, iboff; unsigned index, prim, itype; };
static struct rec recs[40000]; static unsigned nrec, ncalls, maxchain;
void MTLRenderCommandEncoder_encodeCommands(obj_handle_t enc, const struct wmtcmd_base *cmd) {
    unsigned n = 0; ncalls++;
    for (; cmd; cmd = (const struct wmtcmd_base *)cmd->next.ptr, n++) {
        struct rec *r = &recs[nrec++]; memset(r, 0, sizeof *r); r->enc = enc; r->type = cmd->type;
        if (cmd->type == WMTRenderCommandSetVertexBuffer) { const struct wmtcmd_render_setbuffer *s = (const void *)cmd; r->buf = s->buffer; r->off = s->offset; r->index = s->index; }
        else if (cmd->type == WMTRenderCommandDrawIndexedIndirect) { const struct wmtcmd_render_draw_indexed_indirect *d = (const void *)cmd;
            r->buf = d->indirect_args_buffer; r->off = d->indirect_args_offset; r->ib = d->index_buffer; r->iboff = d->index_buffer_offset; r->prim = d->primitive_type; r->itype = d->index_type; }
        else if (cmd->type == WMTRenderCommandDrawIndirect) { const struct wmtcmd_render_draw_indirect *d = (const void *)cmd;
            r->buf = d->indirect_args_buffer; r->off = d->indirect_args_offset; r->prim = d->primitive_type; }
    }
    if (n > maxchain) maxchain = n;
}
void MTLComputeCommandEncoder_encodeCommands(obj_handle_t enc, const struct wmtcmd_base *cmd) {
    unsigned n = 0; ncalls++;
    for (; cmd; cmd = (const struct wmtcmd_base *)cmd->next.ptr, n++) {
        struct rec *r = &recs[nrec++]; memset(r, 0, sizeof *r); r->compute = 1; r->enc = enc; r->type = cmd->type;
        if (cmd->type == WMTComputeCommandDispatchIndirect) { const struct wmtcmd_compute_dispatch_indirect *d = (const void *)cmd; r->buf = d->indirect_args_buffer; r->off = d->indirect_args_offset; }
    }
    if (n > maxchain) maxchain = n;
}
''' + cut + r'''
/* the replay loop's verdict for a record 0 that drew */
static int exec_indirect_fast_ok(struct mad_exec *e, const struct mad_cmd *c) {
    return mad_indirect_fast_on() && exec_indirect_fast_why(e, c) == IFR_USED;
}
static int bad;
#define EXPECT(c, what) do { if (!(c)) { printf("FAIL %s\n", what); bad = 1; } } while (0)
static struct mad_resource args = { 0xa0 }, ib = { 0x1b };
static struct mad_pso msc = { MADEIRA_IR_BACKEND_MSC, 0, 0xc5 }, air = { MADEIRA_IR_BACKEND_AIRCONV, 0, 0xc6 }, gs = { MADEIRA_IR_BACKEND_MSC, 1, 0 };
static void fresh(struct mad_exec *e, struct mad_cmd *c, enum mad_ck kind, UINT count) {
    memset(e, 0, sizeof *e); memset(c, 0, sizeof *c);
    e->renc = 0xe1; e->cenc = 0; e->pso = &msc; e->cpso = &msc; e->ib = &ib; e->ib_off = 96; e->ib_type = WMTIndexTypeUInt32; e->topo = 4;
    e->draws = 1; e->pass_draws = 1;
    if (kind == MC_DISPATCH_INDIRECT) { e->renc = 0; e->cenc = 0xc1; }
    c->kind = kind; c->u.ind.args = &args; c->u.ind.off = 4096; c->u.ind.count = count; c->u.ind.stride = 20;
    nrec = ncalls = maxchain = 0;
}
int main(void) {
    struct mad_exec e; struct mad_cmd c; UINT counts[] = { 2, 3, 64, 65, 129, 8192 }; unsigned i, k, j;
    fresh(&e, &c, MC_DRAW_INDEXED_INDIRECT, 10);
    EXPECT(!exec_indirect_fast_ok(&e, &c), "off by default");
    EXPECT(cfg_reads == 1 && !exec_indirect_fast_ok(&e, &c) && cfg_reads == 1, "switch read once");
    g_indirect_fast = -1; cfg_value = 1;
    EXPECT(exec_indirect_fast_ok(&e, &c), "on: an MSC indexed indirect draw qualifies");
    c.u.ind.count = 1; EXPECT(!exec_indirect_fast_ok(&e, &c), "one record: nothing to speed up"); c.u.ind.count = 10;
    g_census_on = 1; EXPECT(!exec_indirect_fast_ok(&e, &c), "census frame refused"); g_census_on = 0;
    g_capture_on = 1; EXPECT(!exec_indirect_fast_ok(&e, &c), "capture refused"); g_capture_on = 0;
    g_fault_diag = 1; EXPECT(!exec_indirect_fast_ok(&e, &c), "fault diagnostics refused"); g_fault_diag = 0;
    g_skip_ps_state = 1; EXPECT(!exec_indirect_fast_ok(&e, &c), "skip-ps refused"); g_skip_ps_state = 0;
    EXPECT(exec_indirect_fast_ok(&e, &c), "skip-ps read and off: allowed");
    g_sd_state = 1; EXPECT(!exec_indirect_fast_ok(&e, &c), "sync diagnostics refused");
    g_sd_state = -1; EXPECT(!exec_indirect_fast_ok(&e, &c), "sync diagnostics not read yet: refused"); g_sd_state = 0;
    g_list_seq = 3; EXPECT(!exec_indirect_fast_ok(&e, &c), "first lists (draw dumps) refused");
    g_list_seq = 12100; EXPECT(!exec_indirect_fast_ok(&e, &c), "mid-run draw-dump window refused");
    g_quiet_log = 1; EXPECT(exec_indirect_fast_ok(&e, &c), "quiet-log: no mid-run draw-dump window, allowed"); g_quiet_log = 0;
    g_dump_draws = 40000; EXPECT(exec_indirect_fast_ok(&e, &c), "dump budget spent: allowed"); g_dump_draws = 0; g_list_seq = 100;
    e.cap_after = 1; EXPECT(!exec_indirect_fast_ok(&e, &c), "pending draw capture refused"); e.cap_after = 0;
    e.ncap_after_buf = 1; EXPECT(!exec_indirect_fast_ok(&e, &c), "pending buffer capture refused"); e.ncap_after_buf = 0;
    e.pso = &air; EXPECT(exec_indirect_fast_ok(&e, &c), "build 470: a DXBC draw qualifies");
    air.tess = &air; EXPECT(!exec_indirect_fast_ok(&e, &c), "DXBC with a tessellation/geometry variant refused"); air.tess = 0;
    air.tess_strip = &air; EXPECT(!exec_indirect_fast_ok(&e, &c), "DXBC with a strip geometry variant refused"); air.tess_strip = 0;
    air.has_tess = 1; EXPECT(!exec_indirect_fast_ok(&e, &c), "DXBC with hull/domain stages refused"); air.has_tess = 0;
    air.backend = 7; EXPECT(!exec_indirect_fast_ok(&e, &c), "an unknown backend refused"); air.backend = MADEIRA_IR_BACKEND_AIRCONV;
    e.pso = &gs; EXPECT(!exec_indirect_fast_ok(&e, &c), "geometry emulation refused"); e.pso = &msc;
    e.ib = NULL; EXPECT(!exec_indirect_fast_ok(&e, &c), "indexed without index buffer refused"); e.ib = &ib;
    e.renc = 0; EXPECT(!exec_indirect_fast_ok(&e, &c), "no render encoder refused"); e.renc = 0xe1;
    c.kind = MC_DRAW_INDIRECT; e.ib = NULL; EXPECT(exec_indirect_fast_ok(&e, &c), "non-indexed needs no index buffer");
    fresh(&e, &c, MC_DISPATCH_INDIRECT, 10);
    EXPECT(exec_indirect_fast_ok(&e, &c), "MSC indirect dispatch qualifies");
    e.cpso = &air; EXPECT(exec_indirect_fast_ok(&e, &c), "build 470: DXBC compute qualifies");
    air.backend = 7; EXPECT(!exec_indirect_fast_ok(&e, &c), "unknown compute backend refused"); air.backend = MADEIRA_IR_BACKEND_AIRCONV; e.cpso = &msc;
    e.cenc = 0; EXPECT(!exec_indirect_fast_ok(&e, &c), "no compute encoder refused");

    for (j = 0; j < 3; j++) {
        enum mad_ck kind = j == 0 ? MC_DRAW_INDEXED_INDIRECT : j == 1 ? MC_DRAW_INDIRECT : MC_DISPATCH_INDIRECT;
        for (i = 0; i < sizeof counts / sizeof counts[0]; i++) {
            UINT n = counts[i], per = kind == MC_DISPATCH_INDIRECT ? 1 : 2, at = 0;
            fresh(&e, &c, kind, n);
            exec_indirect_rest(&e, &c);
            EXPECT(nrec == (n - 1) * per, "every later record encoded once");
            EXPECT(ncalls == (n - 1 + 63) / 64 && maxchain <= 64 * per, "batched 64 records to a call");
            EXPECT(e.draws == n, "draws counted");
            EXPECT(e.pass_draws == (kind == MC_DISPATCH_INDIRECT ? 1 : n), "render pass draws counted for draws only");
            for (k = 1; k < n && at < nrec; k++) {
                UINT64 off = 4096 + (UINT64)k * 20;
                if (kind == MC_DISPATCH_INDIRECT) {
                    struct rec *d = &recs[at++];
                    EXPECT(d->compute && d->enc == 0xc1 && d->type == WMTComputeCommandDispatchIndirect && d->buf == 0xa0 && d->off == off, "dispatch record");
                } else {
                    struct rec *s = &recs[at++], *d = &recs[at++];
                    EXPECT(!s->compute && s->enc == 0xe1 && s->type == WMTRenderCommandSetVertexBuffer && s->buf == 0xa0 && s->off == off && s->index == 4,
                           "buffer 4 = this record");
                    if (kind == MC_DRAW_INDEXED_INDIRECT)
                        EXPECT(d->type == WMTRenderCommandDrawIndexedIndirect && d->buf == 0xa0 && d->off == off && d->ib == 0x1b && d->iboff == 96 &&
                               d->itype == WMTIndexTypeUInt32 && d->prim == WMTPrimitiveTypeTriangle, "indexed indirect draw of this record");
                    else
                        EXPECT(d->type == WMTRenderCommandDrawIndirect && d->buf == 0xa0 && d->off == off && d->prim == WMTPrimitiveTypeTriangle,
                               "indirect draw of this record");
                }
            }
        }
    }
    if (!bad) printf("ok\n");
    return bad;
}
'''
cc = os.environ.get("CC") if os.environ.get("CC") and "clang" in os.environ.get("CC") else shutil.which("clang")
std = "-std=gnu11"
if not cc:
    cc, std = shutil.which("gcc") or shutil.which("cc"), "-std=gnu2x"
if not cc:
    print("note: no host compiler; runtime checks skipped")
else:
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        (t / "h.c").write_text(harness)
        exe = t / "h"
        r = subprocess.run([cc, std, "-Wall", "-Wno-unused-function", "-Wno-fixed-enum-extension", "-Wno-unknown-warning-option",
                            "-DDXMT_NATIVE", "-I%s" % (root / "dxmt/src/winemetal"), "-o", str(exe), str(t / "h.c")],
                           capture_output=True, text=True)
        if r.returncode:
            print(r.stderr[-3000:])
        out = subprocess.run([str(exe)], capture_output=True, text=True).stdout if exe.exists() else ""
        check("fast path runtime (switch, refusals, draw/indexed/dispatch chains, batching, counts)",
              r.returncode == 0 and out.strip() == "ok")
        if out.strip() != "ok":
            print(out[:3000])

print("PASS" if ok else "FAILED")
sys.exit(0 if ok else 1)
