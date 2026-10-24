#!/usr/bin/env python3
"""Redundant render state left out of draws (madeira.cfg draw-dedup, default 1);
no Wine, no Metal.

exec_draw handed Metal a draw's whole state every time: pipeline, viewport,
scissor, depth-stencil state and stencil reference, blend colour, rasterizer
state and every buffer binding. With draw-dedup, a set of what the render
encoder already holds is left out, and a buffer bound again at the same index
with a new offset becomes set*BufferOffset. What the encoder holds (struct
mad_dd) is forgotten for a new encoder, at its end, when a chain from anywhere
else reaches it, while a draw's chain is built (a draw that returns early) and
after a draw through the geometry / tessellation emulation.

The runtime part cuts the encode wrappers, the batch and the mad_dd_* helpers
out of madeira_d3d12.c, compiles them on the host against the real winemetal.h
with a Metal stand-in that applies every command to a model render encoder,
and drives a draw builder that calls the helpers the way exec_draw does (the
source checks below pin exec_draw to that shape). Thousands of random draws
(state drawn from small pools, so values repeat), new encoders, chains from
elsewhere (a fence update, an ExecuteIndirect record), early returns and
emulated draws run once with the switch off and once on, with encode-batch on
and off: the encoder state every draw executes with must be the same, and
draw-dedup must send far fewer commands. Offset-only binds go only to an index
that holds a buffer.

In the source: the switch is read once (default 1); exec_draw asks for the
state at tess_go, leaves emulated draws out, turns a held pipeline into a Nop,
guards the viewport, scissor, depth-stencil, blend and rasterizer sets and
every buffer bind with the helpers, and marks the state known only after the
chain was encoded; mad_es_rce forgets the state when a chain from elsewhere
reaches the encoder and mad_es_end when it ends; the catalog lists draw-dedup,
on by default. The runtime part needs clang (or gcc with C23 enums).
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


start = src.index("static volatile LONG64 g_es_enc_t, g_es_open_t;")
end_marker = "#define MTLCommandEncoder_setLabel(e_, s_) mad_es_label((e_), (s_))\n"
cut = src[start:src.index(end_marker) + len(end_marker)]
hstart = src.index("static void mad_dd_reset(struct mad_dd *d) {")
helpers = src[hstart:src.index("static void exec_draw(struct mad_exec *e, const struct mad_cmd *c) {")]
check("draw-dedup helpers found", all(s in helpers for s in (
    "static struct mad_dd *mad_dd_begin(obj_handle_t renc)", "static int mad_dd_pso(", "static int mad_dd_vp(",
    "static int mad_dd_sc(", "static int mad_dd_dss(", "static int mad_dd_blend(", "static int mad_dd_ras(",
    "static struct wmtcmd_base *mad_dd_buf(")))
check("switch read once with mad_cfg_int_pe, on by default",
      "if (g_eb_on < 0 || g_dd_on < 0) {" in cut and 'g_dd_on = mad_cfg_int_pe("draw-dedup", 1) ? 1 : 0;' in cut)
check("mad_es_rce forgets the state when a chain from elsewhere reaches the encoder",
      "if (b->dd.enc == e) b->dd.enc = 0;   /* draw-dedup: a chain from elsewhere" in cut
      and cut.index("if (b->dd.enc == e) b->dd.enc = 0;") < cut.index("mad_eb_push(b, e, MAD_EB_RENDER, c)"))
endfn = cut[cut.index("static void mad_es_end(obj_handle_t e) {"):]
endfn = endfn[:endfn.index("\n}\n")]
check("mad_es_end forgets it when the encoder ends", "if (b->dd.enc == e) b->dd.enc = 0;" in endfn)
check("a replay starts and ends with nothing known (encoder handles are reused across replays)",
      "if (!b->active++) b->dd.enc = 0;" in cut and "if (--b->active > 0) return;\n    b->dd.enc = 0;" in cut)

draw = src[src.index("static void exec_draw(struct mad_exec *e, const struct mad_cmd *c) {"):]
draw = draw[:draw.index("\n}\n")]
need = [
    "tess_go:\n    dd = mad_dd_begin(e->renc);",
    "    if (dd && (tv || gsemu)) dd = NULL;",
    "    if (dd && !mad_dd_pso(dd, c_pso.pso)) c_pso.type = WMTRenderCommandNop;",
    "        if (!dd || mad_dd_vp(dd, &c_vp.viewport)) MAD_APPEND(&c_vp);",
    "            if (!dd || mad_dd_sc(dd, &c_sc.scissor_rect)) MAD_APPEND(&c_sc);",
    "sbn_ = dd ? mad_dd_buf(dd, &sb[nsb], &so[nsb]) : (struct wmtcmd_base *)&sb[nsb]; if (sbn_) MAD_APPEND(sbn_); nsb++;",
    "        if (!dd || mad_dd_dss(dd, c_dss.dsso, c_dss.stencil_ref)) MAD_APPEND(&c_dss);",
    "        if (!dd || mad_dd_blend(dd, e->blend, c_bl.stencil_ref)) MAD_APPEND(&c_bl);",
    "    if (!dd || mad_dd_ras(dd, &c_ras)) MAD_APPEND(&c_ras);",
    "    if (dd) mad_dd_end(dd, e->renc);",
]
for n in need:
    check("exec_draw: %s" % n.strip().split("\n")[-1][:90], draw.count(n) == 1)
order = [draw.index(n) for n in need[2:]]
check("exec_draw builds in the harness's order: pipeline, viewport, scissor, buffers, depth-stencil, blend, rasterizer, then the encode",
      order == sorted(order) and draw.index("tail = (struct wmtcmd_base *)&c_pso;") > draw.index(need[2])
      and draw.index("MTLRenderCommandEncoder_encodeCommands(e->renc, (const struct wmtcmd_base *)&c_pso);") < draw.index(need[-1]))
check("exec_draw appends no state set outside the helpers",
      not re.search(r"(?<!\) )MAD_APPEND\(&c_(vp|sc|dss|bl|ras)\)", draw)
      and "MAD_APPEND(&sb[nsb])" not in draw)
check("the state is asked for after the encoder is chosen and before any set",
      draw.index("if (!exec_begin_render(e)) { MAD_SKIP(e); return; }") < draw.index("dd = mad_dd_begin(e->renc);")
      < draw.index("memset(&c_pso, 0, sizeof c_pso);"))
check("a draw's sb[] has an offset-only twin of the same size",
      "struct wmtcmd_render_setbuffer sb[6 + 16 + 2];" in draw and "struct wmtcmd_render_setbufferoffset so[6 + 16 + 2];" in draw)
cat = (root / "app/Madeira/ConfigCatalog.generated.swift").read_text()
check("catalog lists draw-dedup, on by default",
      re.search(r'key: "draw-dedup".*kind: \.bool, defaultValue: "1"', cat) is not None)

harness = r'''
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdlib.h>
#include "winemetal.h"
typedef uint64_t UINT64; typedef int64_t LONG64; typedef int LONG; typedef unsigned char UINT8; typedef unsigned DWORD; typedef unsigned UINT;
typedef union { long long QuadPart; } LARGE_INTEGER;
#define TLS_OUT_OF_INDEXES 0xffffffffu
static __thread void *fake_tls[64];
#define MAD_EB_SLOT(i) (fake_tls[(i)])
static DWORD TlsAlloc(void) { return 9; }
static int TlsFree(DWORD i) { (void)i; return 1; }
static int TlsSetValue(DWORD i, void *v) { fake_tls[i] = v; return 1; }
static LONG InterlockedExchangeAdd(volatile LONG *p, LONG v) { return __atomic_fetch_add(p, v, __ATOMIC_SEQ_CST); }
static LONG64 InterlockedExchangeAdd64(volatile LONG64 *p, LONG64 v) { return __atomic_fetch_add(p, v, __ATOMIC_SEQ_CST); }
static LONG InterlockedIncrement(volatile LONG *p) { return __atomic_add_fetch(p, 1, __ATOMIC_SEQ_CST); }
static LONG InterlockedCompareExchange(volatile LONG *p, LONG x, LONG cmp) { __atomic_compare_exchange_n(p, &cmp, x, 0, __ATOMIC_SEQ_CST, __ATOMIC_SEQ_CST); return cmp; }
static LONG64 mad_qpc(void) { return 0; }
static void d3d12_log(const char *fmt, ...) { (void)fmt; }
static int QueryPerformanceFrequency(LARGE_INTEGER *f) { f->QuadPart = 1000000; return 1; }

/* The model render encoder: what Metal holds after each command. */
struct model {
    obj_handle_t pso, dss; int has_vp, has_sc, has_dss, has_ref, has_blend, has_ras; struct WMTViewport vp; struct WMTScissorRect sc;
    unsigned ref; float blend[4]; struct wmtcmd_render_setrasterizerstate ras; struct { obj_handle_t buf; UINT64 off; } b[4][40];
};
static struct model enc_state; static obj_handle_t cur_enc; static int bad;
static unsigned long ncmds, nchains;
static struct model shots[20000]; static unsigned nshots;
#define EXPECT(c, what) do { if (!(c)) { printf("FAIL %s\n", what); bad = 1; } } while (0)
static int stage_of(unsigned t, int *off_only) {
    *off_only = 0;
    switch (t) {
    case WMTRenderCommandSetVertexBuffer: return 0;
    case WMTRenderCommandSetFragmentBuffer: return 1;
    case WMTRenderCommandSetObjectBuffer: return 2;
    case WMTRenderCommandSetMeshBuffer: return 3;
    case WMTRenderCommandSetVertexBufferOffset: *off_only = 1; return 0;
    case WMTRenderCommandSetFragmentBufferOffset: *off_only = 1; return 1;
    case WMTRenderCommandSetObjectBufferOffset: *off_only = 1; return 2;
    case WMTRenderCommandSetMeshBufferOffset: *off_only = 1; return 3;
    default: return -1;
    }
}
void MTLRenderCommandEncoder_encodeCommands(obj_handle_t enc, const struct wmtcmd_base *c) {
    int st, oo;
    nchains++;
    if (enc != cur_enc) { printf("FAIL chain for encoder %llx while %llx is open\n", (unsigned long long)enc, (unsigned long long)cur_enc); bad = 1; }
    for (; c; c = (const struct wmtcmd_base *)c->next.ptr) {
        ncmds++;
        switch (c->type) {
        case WMTRenderCommandNop: ncmds--; break;   /* costs no Metal call */
        case WMTRenderCommandSetPSO: enc_state.pso = ((const struct wmtcmd_render_setpso *)c)->pso; break;
        case WMTRenderCommandSetViewport: enc_state.vp = ((const struct wmtcmd_render_setviewport *)c)->viewport; enc_state.has_vp = 1; break;
        case WMTRenderCommandSetScissorRect: enc_state.sc = ((const struct wmtcmd_render_setscissorrect *)c)->scissor_rect; enc_state.has_sc = 1; break;
        case WMTRenderCommandSetDSSO: { const struct wmtcmd_render_setdsso *d = (const void *)c; enc_state.dss = d->dsso; enc_state.has_dss = 1; enc_state.ref = d->stencil_ref; enc_state.has_ref = 1; break; }
        case WMTRenderCommandSetBlendFactorAndStencilRef: { const struct wmtcmd_render_setblendcolor *b = (const void *)c;
            enc_state.blend[0] = b->red; enc_state.blend[1] = b->green; enc_state.blend[2] = b->blue; enc_state.blend[3] = b->alpha;
            enc_state.has_blend = 1; enc_state.ref = b->stencil_ref; enc_state.has_ref = 1; break; }
        case WMTRenderCommandSetRasterizerState: enc_state.ras = *(const struct wmtcmd_render_setrasterizerstate *)c; enc_state.ras.next.ptr = NULL; enc_state.has_ras = 1; break;
        case WMTRenderCommandWaitForFence: case WMTRenderCommandUpdateFence: break;
        case WMTRenderCommandDraw: case WMTRenderCommandDrawIndexedIndirect:
            if (nshots < 20000) shots[nshots++] = enc_state;
            break;
        default:
            st = stage_of(c->type, &oo);
            if (st < 0) { printf("FAIL unexpected command %u\n", c->type); bad = 1; break; }
            if (oo) {
                const struct wmtcmd_render_setbufferoffset *s = (const void *)c;
                if (!enc_state.b[st][s->index].buf) { printf("FAIL offset-only bind at an index with no buffer\n"); bad = 1; }
                enc_state.b[st][s->index].off = s->offset;
            } else {
                const struct wmtcmd_render_setbuffer *s = (const void *)c;
                enc_state.b[st][s->index].buf = s->buffer; enc_state.b[st][s->index].off = s->offset;
            }
        }
    }
}
void MTLComputeCommandEncoder_encodeCommands(obj_handle_t enc, const struct wmtcmd_base *c) { (void)enc; (void)c; }
void MTLBlitCommandEncoder_encodeCommands(obj_handle_t enc, const struct wmtcmd_base *c) { (void)enc; (void)c; }
static obj_handle_t next_handle = 0x1000;
obj_handle_t MTLCommandBuffer_renderCommandEncoder(obj_handle_t cb, struct WMTRenderPassInfo *i) { (void)cb; (void)i; memset(&enc_state, 0, sizeof enc_state); return cur_enc = next_handle++; }
obj_handle_t MTLCommandBuffer_computeCommandEncoder(obj_handle_t cb, bool c) { (void)cb; (void)c; return 0; }
obj_handle_t MTLCommandBuffer_blitCommandEncoder(obj_handle_t cb) { (void)cb; return 0; }
void MTLCommandEncoder_endEncoding(obj_handle_t e) { if (e == cur_enc) cur_enc = 0; }
void NSObject_release(obj_handle_t o) { (void)o; }
void MTLCommandEncoder_setLabel(obj_handle_t e, obj_handle_t s) { (void)e; (void)s; }
''' + cut + helpers + r'''
static long long cfg_dd = 1, cfg_eb = 1;
static long long mad_cfg_int_pe(const char *k, long long d) {
    if (!strcmp(k, "draw-dedup")) return cfg_dd;
    if (!strcmp(k, "encode-batch")) return cfg_eb;
    return d;
}
/* What one draw wants, drawn from small pools so values repeat. */
struct want {
    obj_handle_t pso; int has_vp, has_sc, depth, has_blend, emulated, early; struct WMTViewport vp; struct WMTScissorRect sc;
    obj_handle_t dss; unsigned ref; float blend[4]; struct wmtcmd_render_setrasterizerstate ras;
    unsigned nb; struct { unsigned type; obj_handle_t buf; UINT64 off; unsigned idx; } b[24];
};
static unsigned long rng = 12345;
static unsigned rnd(unsigned n) { rng = rng * 6364136223846793005ull + 1442695040888963407ull; return (unsigned)(rng >> 33) % n; }
static struct want prev; static int have;
static void make(struct want *w) {
    /* Like a game's pass: most of a draw's state is the previous draw's; each part changes now and then. */
    static const unsigned types[4] = { WMTRenderCommandSetVertexBuffer, WMTRenderCommandSetFragmentBuffer, WMTRenderCommandSetObjectBuffer, WMTRenderCommandSetMeshBuffer };
    unsigned k;
    if (!have || !rnd(40)) { memset(&prev, 0, sizeof prev); prev.ras.type = WMTRenderCommandSetRasterizerState; have = 1; }
    *w = prev;
    if (!rnd(4)) w->pso = rnd(6) ? 0x100 + rnd(4) : 0;   /* sometimes no pipeline at all */
    if (!rnd(8)) { w->has_vp = rnd(6) != 0; w->vp.width = 100 + rnd(2); w->vp.height = 50; w->vp.zfar = rnd(3) ? 1.0 : 0.5; }
    if (!rnd(8)) { w->has_sc = rnd(4) != 0; w->sc.width = 10 + rnd(2); w->sc.height = 10; }
    if (!rnd(6)) { w->depth = rnd(4) != 0; w->dss = 0x200 + rnd(2); }
    if (!rnd(6)) w->ref = rnd(3);
    if (!rnd(10)) { w->has_blend = rnd(3) == 0; w->blend[0] = (float)rnd(2); w->blend[3] = 1.0f; }
    if (!rnd(6)) { w->ras.cull_mode = (enum WMTCullMode)rnd(3); w->ras.depth_bias = rnd(5) ? 0.0f : -0.0f; w->ras.winding = (enum WMTWinding)rnd(2); }
    w->emulated = rnd(25) == 0; w->early = rnd(30) == 0;
    /* exec_draw's binds: the argument slot (new offset every draw), heaps, vertex buffers, draw parameters */
    w->nb = 0;
#define B(t, bf, of, ix) do { w->b[w->nb].type = (t); w->b[w->nb].buf = (bf); w->b[w->nb].off = (of); w->b[w->nb].idx = (ix); w->nb++; } while (0)
    {
        UINT64 slot = 1088 * rnd(60); obj_handle_t ring = 0x400 + rnd(9) / 8;   /* a new ring chunk now and then */
        B(types[0], ring, slot, 2); B(types[1], ring, slot, 2);
        B(types[0], prev.nb ? 0x500 : 0x501, 0, 0); B(types[1], 0x500, 0, 0);
        B(types[0], 0x510, 0, 1); B(types[1], 0x510, 0, 1);
        for (k = 0; k < 1 + rnd(3); k++) B(types[0], 0x300 + rnd(3), 64 * rnd(3), 6 + k);
        B(types[0], rnd(10) ? ring : 0x600, slot + 512, 4); B(types[0], ring, slot + 544, 5);
        if (!rnd(10)) B(types[rnd(4)], rnd(12) ? 0x300 + rnd(3) : 0, 64 * rnd(3), rnd(9) ? rnd(8) : 30);   /* odd ones: other stages, no buffer, index 30 */
    }
#undef B
    prev = *w; prev.nb = 1;
}
/* The draw, built the way exec_draw builds it (see the source checks). */
static void do_draw(const struct want *w) {
    struct wmtcmd_render_setpso c_pso; struct wmtcmd_render_setviewport c_vp; struct wmtcmd_render_setscissorrect c_sc;
    struct wmtcmd_render_setbuffer sb[24]; struct wmtcmd_render_setbufferoffset so[24]; struct wmtcmd_render_setdsso c_dss;
    struct wmtcmd_render_setblendcolor c_bl; struct wmtcmd_render_setrasterizerstate c_ras; struct wmtcmd_render_draw c_draw;
    struct wmtcmd_base *tail; struct mad_dd *dd; unsigned nsb = 0, k;
    float blend[4];
    dd = mad_dd_begin(cur_enc);
    if (dd && w->emulated) dd = NULL;
    memset(&c_pso, 0, sizeof c_pso); c_pso.type = WMTRenderCommandSetPSO; c_pso.pso = w->pso;
    if (dd && !mad_dd_pso(dd, c_pso.pso)) c_pso.type = WMTRenderCommandNop;
    tail = (struct wmtcmd_base *)&c_pso;
#define MAD_APPEND(node) do { tail->next.ptr = (node); tail = (struct wmtcmd_base *)(node); } while (0)
    if (w->has_vp) { memset(&c_vp, 0, sizeof c_vp); c_vp.type = WMTRenderCommandSetViewport; c_vp.viewport = w->vp;
                     if (!dd || mad_dd_vp(dd, &c_vp.viewport)) MAD_APPEND(&c_vp); }
    if (w->has_sc) { memset(&c_sc, 0, sizeof c_sc); c_sc.type = WMTRenderCommandSetScissorRect; c_sc.scissor_rect = w->sc;
                     if (!dd || mad_dd_sc(dd, &c_sc.scissor_rect)) MAD_APPEND(&c_sc); }
    memset(sb, 0, sizeof sb);
    for (k = 0; k < w->nb; k++) {
        struct wmtcmd_base *sbn_;
        sb[nsb].type = (enum WMTRenderCommandType)w->b[k].type; sb[nsb].buffer = w->b[k].buf; sb[nsb].offset = w->b[k].off; sb[nsb].index = (uint8_t)w->b[k].idx;
        sbn_ = dd ? mad_dd_buf(dd, &sb[nsb], &so[nsb]) : (struct wmtcmd_base *)&sb[nsb]; if (sbn_) MAD_APPEND(sbn_); nsb++;
        if (w->early && k == w->nb / 2) return;   /* a draw that returns early, its chain never sent */
    }
    if (w->depth) { memset(&c_dss, 0, sizeof c_dss); c_dss.type = WMTRenderCommandSetDSSO; c_dss.dsso = w->dss; c_dss.stencil_ref = (uint8_t)w->ref;
                    if (!dd || mad_dd_dss(dd, c_dss.dsso, c_dss.stencil_ref)) MAD_APPEND(&c_dss); }
    if (w->has_blend) { memset(&c_bl, 0, sizeof c_bl); c_bl.type = WMTRenderCommandSetBlendFactorAndStencilRef;
                        memcpy(blend, w->blend, sizeof blend);
                        c_bl.red = blend[0]; c_bl.green = blend[1]; c_bl.blue = blend[2]; c_bl.alpha = blend[3]; c_bl.stencil_ref = (uint8_t)w->ref;
                        if (!dd || mad_dd_blend(dd, blend, c_bl.stencil_ref)) MAD_APPEND(&c_bl); }
    c_ras = w->ras; c_ras.next.ptr = NULL;
    if (!dd || mad_dd_ras(dd, &c_ras)) MAD_APPEND(&c_ras);
    memset(&c_draw, 0, sizeof c_draw); c_draw.type = WMTRenderCommandDraw; MAD_APPEND(&c_draw);
    tail->next.ptr = NULL;
    MTLRenderCommandEncoder_encodeCommands(cur_enc, (const struct wmtcmd_base *)&c_pso);
    if (dd) mad_dd_end(dd, cur_enc);
#undef MAD_APPEND
}
static void foreign(int kind) {   /* a fence update, or an ExecuteIndirect record (buffer 4 + an indirect draw) */
    if (kind) {
        struct wmtcmd_render_setbuffer s; struct wmtcmd_render_draw_indexed_indirect d;
        memset(&s, 0, sizeof s); memset(&d, 0, sizeof d);
        s.type = WMTRenderCommandSetVertexBuffer; s.buffer = 0x300 + rnd(3); s.offset = 4096 + 20 * rnd(4); s.index = (uint8_t)rnd(8);
        d.type = WMTRenderCommandDrawIndexedIndirect; s.next.ptr = &d;
        MTLRenderCommandEncoder_encodeCommands(cur_enc, (const struct wmtcmd_base *)&s);
    } else {
        struct wmtcmd_render_fence_op f; memset(&f, 0, sizeof f); f.type = WMTRenderCommandUpdateFence; f.fence = 0xfe;
        MTLRenderCommandEncoder_encodeCommands(cur_enc, (const struct wmtcmd_base *)&f);
    }
}
static struct model ref[20000]; static unsigned nref; static unsigned long ref_cmds;
static int same(const struct model *a, const struct model *b) {
    unsigned s, i;
    if (a->pso != b->pso || a->has_vp != b->has_vp || a->has_sc != b->has_sc || a->has_dss != b->has_dss || a->has_ref != b->has_ref ||
        a->has_blend != b->has_blend || a->has_ras != b->has_ras) return 0;
    if (a->has_vp && memcmp(&a->vp, &b->vp, sizeof a->vp)) return 0;
    if (a->has_sc && memcmp(&a->sc, &b->sc, sizeof a->sc)) return 0;
    if (a->has_dss && a->dss != b->dss) return 0;
    if (a->has_ref && a->ref != b->ref) return 0;
    if (a->has_blend && memcmp(a->blend, b->blend, sizeof a->blend)) return 0;
    if (a->has_ras && (a->ras.fill_mode != b->ras.fill_mode || a->ras.cull_mode != b->ras.cull_mode || a->ras.depth_clip_mode != b->ras.depth_clip_mode ||
                       a->ras.winding != b->ras.winding || memcmp(&a->ras.depth_bias, &b->ras.depth_bias, 12))) return 0;
    for (s = 0; s < 4; s++) for (i = 0; i < 31; i++) if (a->b[s][i].buf != b->b[s][i].buf || (a->b[s][i].buf && a->b[s][i].off != b->b[s][i].off)) return 0;
    return 1;
}
static void run(int replays) {
    struct WMTRenderPassInfo rpi; unsigned r, k; memset(&rpi, 0, sizeof rpi);
    rng = 777; nshots = 0; ncmds = 0; nchains = 0; next_handle = 0x1000; have = 0;
    for (r = 0; r < (unsigned)replays; r++) {
        struct mad_eb *b = mad_es_begin();
        obj_handle_t e = MTLCommandBuffer_renderCommandEncoder(0xcb, &rpi);
        for (k = 0; k < 400; k++) {
            unsigned what = rnd(100);
            struct want w;
            if (what < 4) { MTLCommandEncoder_endEncoding(e); e = MTLCommandBuffer_renderCommandEncoder(0xcb, &rpi); }
            else if (what < 6) foreign(0);
            else if (what < 8) foreign(1);
            make(&w); do_draw(&w);
        }
        MTLCommandEncoder_endEncoding(e);
        mad_es_finish(b);
        next_handle = 0x1000;   /* the next replay reuses the same encoder handles */
    }
}
int main(void) {
    unsigned i, eb;
    for (eb = 0; eb < 2; eb++) {
        g_eb_on = -1; g_dd_on = -1; cfg_eb = eb; cfg_dd = 0;
        run(6);
        memcpy(ref, shots, nshots * sizeof shots[0]); nref = nshots; ref_cmds = ncmds;
        EXPECT(g_dd_on == 0, "switched off");
        g_eb_on = -1; g_dd_on = -1; cfg_dd = 1;
        run(6);
        EXPECT(g_dd_on == 1, "switched on");
        EXPECT(nshots == nref && nshots > 1000, "the same draws reach the encoder");
        for (i = 0; i < nshots && i < nref; i++)
            if (!same(&shots[i], &ref[i])) { printf("FAIL draw %u ran with other state than without draw-dedup (encode-batch %u)\n", i, eb); bad = 1; break; }
        EXPECT(ncmds * 10 < ref_cmds * 7, "far fewer commands");
        printf("note: encode-batch %u: %lu commands with draw-dedup vs %lu without; %ld of %ld state sets left out, %ld binds as offsets\n",
               eb, ncmds, ref_cmds, (long)g_dd_elided, (long)g_dd_sets, (long)g_dd_offsets);
        g_dd_elided = g_dd_sets = g_dd_offsets = 0;
    }
    {   /* the helpers on their own */
        struct mad_eb *b = mad_es_begin(); struct mad_dd *d;
        struct wmtcmd_render_setbuffer s; struct wmtcmd_render_setbufferoffset o; struct wmtcmd_base *n;
        cur_enc = 0x55;
        d = mad_dd_begin(0x55);
        EXPECT(d && d->enc == 0, "unknown while a chain is built");
        memset(&s, 0, sizeof s); s.type = WMTRenderCommandSetFragmentBuffer; s.buffer = 0x9; s.offset = 16; s.index = 3;
        n = mad_dd_buf(d, &s, &o); EXPECT(n == (struct wmtcmd_base *)&s, "first bind sent whole");
        n = mad_dd_buf(d, &s, &o); EXPECT(n == NULL, "same bind left out");
        s.offset = 32; n = mad_dd_buf(d, &s, &o);
        EXPECT(n == (struct wmtcmd_base *)&o && o.type == WMTRenderCommandSetFragmentBufferOffset && o.offset == 32 && o.index == 3 && !o.next.ptr,
               "new offset only: set*BufferOffset");
        s.buffer = 0xa; n = mad_dd_buf(d, &s, &o); EXPECT(n == (struct wmtcmd_base *)&s, "another buffer: sent whole");
        mad_dd_end(d, 0x55);
        EXPECT(mad_dd_begin(0x56) && d->pso == 0 && d->b[1][3].buf == 0, "another encoder: forgotten");
        mad_dd_end(d, 0x56); cur_enc = 0x56;
        MTLRenderCommandEncoder_encodeCommands(0x56, NULL);
        EXPECT(d->enc == 0, "a chain from elsewhere: forgotten");
        mad_dd_end(d, 0x56); MTLCommandEncoder_endEncoding(0x56);
        EXPECT(d->enc == 0, "the encoder ended: forgotten");
        mad_es_finish(b);
        g_dd_on = 0; EXPECT(mad_dd_begin(0x55) == NULL, "off: no state");
    }
    if (!bad) printf("ok\n");
    return bad;
}
'''
wm_dir = root / "dxmt/src/winemetal"
cc = os.environ.get("CC") if os.environ.get("CC") and "clang" in os.environ.get("CC") else shutil.which("clang")
std = "-std=gnu11"
if not cc:
    cc, std = shutil.which("gcc") or shutil.which("cc"), "-std=gnu2x"
if not (wm_dir / "winemetal.h").exists():
    print("note: no dxmt sources; runtime checks skipped")
elif not cc:
    print("note: no host compiler; runtime checks skipped")
else:
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        (t / "h.c").write_text(harness)
        exe = t / "h"
        r = subprocess.run([cc, std, "-O1", "-Wall", "-Wno-unused-function", "-Wno-fixed-enum-extension", "-Wno-unknown-warning-option",
                            "-DDXMT_NATIVE", "-I%s" % wm_dir, "-o", str(exe), str(t / "h.c")], capture_output=True, text=True)
        if r.returncode:
            print(r.stderr[-3000:])
        out = subprocess.run([str(exe)], capture_output=True, text=True).stdout if exe.exists() else ""
        print(out.strip())
        check("draw-dedup runtime (every draw runs with the same encoder state, far fewer commands, helper rules)",
              r.returncode == 0 and out.strip().endswith("ok"))

print("PASS" if ok else "FAILED")
sys.exit(0 if ok else 1)
