#!/usr/bin/env python3
"""Encode batching (madeira.cfg encode-batch, default 1); no Wine, no Metal.

madeira_d3d12.c handed every draw's command chain, and every encoder's fence
wait and fence update, to Metal in an encodeCommands call of its own. With
encode-batch, the chains a replay thread hands to one encoder are queued in a
per-thread arena and sent as one chain when the encoder ends, before any other
encoder is made or used, before an object is released or an encoder labelled,
when the arena is full, after a pipeline-variant draw, and when the replay ends.

This test cuts the encode wrappers and the batch (from g_es_enc_t to the last
wrapper macro) out of the file and compiles them on the host against the real
winemetal.h, with stand-ins for winemetal that record every call Metal would
see. One scenario -- render, compute and blit encoders, fence operations,
draws whose setBytes / viewport / scissor memory the caller rewrites right
after handing it over, a release and a label in the middle of an encoder, an
unknown command type, chains that overflow the arena, two encoders in a row
without an end between them, the end of the replay and calls after it -- runs
once with the switch off and once on. The calls Metal receives must be the
same commands, with the same contents (setBytes as they were when handed over),
on the same encoders, in the same order, interleaved with the same creations,
ends, releases and labels; on, they must take far fewer encodeCommands calls.
Also: on unless madeira.cfg says encode-batch = 0; a thread-local slot that
cannot be read in place turns batching and draw-dedup off (on ARM64EC the slot
is read through `ldr xT, [x18, #0x30]`, not an add off x18: HZD build 500
died on one); a thread outside a
replay and a switched-off batch send at once; the arena is per thread, nested
replays end with the outermost, and mad_es_finish sends what is left.

In the source: the switch is read once with mad_cfg_int_pe; every
render / compute / blit encoder call, endEncoding, encoder creation, setLabel
and NSObject_release in the file goes through a wrapper; mad_ecl_run begins
the batch before it takes the queue lock and finishes it before it lets go;
exec_draw sends right after a pipeline-variant draw; a thread's arena is
freed at DLL_THREAD_DETACH; every command type of winemetal.h is sized (or
named here as never queued); the catalog lists encode-batch, on by default.
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


start = src.index("static volatile LONG64 g_es_enc_t, g_es_open_t;")
end_marker = "#define MTLCommandEncoder_setLabel(e_, s_) mad_es_label((e_), (s_))\n"
end = src.index(end_marker) + len(end_marker)
cut = src[start:end]
check("encode wrappers and batch found", all(s in cut for s in (
    "static int mad_eb_push(", "static void mad_eb_flush(", "static struct mad_eb *mad_es_begin(void)",
    "static void mad_es_finish(", "static void mad_es_release(", "static void mad_es_label(")))
check("switches read once with mad_cfg_int_pe, on by default",
      "if (g_eb_on < 0 || g_dd_on < 0) {" in cut
      and 'g_eb_on = mad_cfg_int_pe("encode-batch", 1) ? 1 : 0;' in cut and 'g_dd_on = mad_cfg_int_pe("draw-dedup", 1) ? 1 : 0;' in cut)
slot = cut[cut.index("#ifndef MAD_EB_SLOT"):cut.index("static struct mad_eb *mad_eb_cur(void)")]
check("on ARM64EC the thread's slot is read through one load off x18 (TEB Self), which the x18 patcher runs without x18",
      "#ifdef __arm64ec__" in slot and '__asm__ volatile("ldr %0, [x18, #0x30]" : "=r"(teb));' in slot
      and "#define MAD_EB_SLOT(i) (((void *const *)((const char *)mad_teb_self() + 0x1480))[(i)])" in slot
      and slot.index("#ifdef __arm64ec__") < slot.index("mad_teb_self() + 0x1480") < slot.index("#else"))
for name, macro in (("render encodeCommands", "#define MTLRenderCommandEncoder_encodeCommands(e_, c_) mad_es_rce((e_), (c_))"),
                    ("compute encodeCommands", "#define MTLComputeCommandEncoder_encodeCommands(e_, c_) mad_es_cce((e_), (c_))"),
                    ("blit encodeCommands", "#define MTLBlitCommandEncoder_encodeCommands(e_, c_) mad_es_bce((e_), (c_))"),
                    ("render encoder creation", "#define MTLCommandBuffer_renderCommandEncoder(cb_, i_) mad_es_renc((cb_), (i_))"),
                    ("compute encoder creation", "#define MTLCommandBuffer_computeCommandEncoder(cb_, c_) mad_es_cenc((cb_), (c_))"),
                    ("blit encoder creation", "#define MTLCommandBuffer_blitCommandEncoder(cb_) mad_es_benc((cb_))"),
                    ("endEncoding", "#define MTLCommandEncoder_endEncoding(e_) mad_es_end((e_))"),
                    ("release", "#define NSObject_release(o_) mad_es_release((o_))"),
                    ("label", "#define MTLCommandEncoder_setLabel(e_, s_) mad_es_label((e_), (s_))")):
    check("%s goes through its wrapper" % name, macro in cut)
# Nothing in the file may reach an encoder, or release an object, around the
# wrappers: a direct call would overtake what a replay thread has queued.
rest = src[:start] + src[end:]
direct = set(re.findall(r"\b(MTL(?:Render|Compute|Blit)?CommandEncoder_\w+|NSObject_release)\b", rest))
check("no encoder call or release outside the wrappers (a new one must flush first, see mad_eb_flush_cur)",
      not (direct - {"MTLRenderCommandEncoder_encodeCommands", "MTLComputeCommandEncoder_encodeCommands",
                     "MTLBlitCommandEncoder_encodeCommands", "MTLCommandEncoder_endEncoding", "MTLCommandEncoder_setLabel",
                     "NSObject_release"}) and src.index(end_marker) < src.index("NSObject_release(smp)"))
run = src[src.index("static void mad_ecl_run(ID3D12CommandQueue *This"):]
run = run[:run.index("\n}\n")]
check("mad_ecl_run begins the batch before the queue lock and finishes it before letting go",
      run.index("struct mad_eb *eb = mad_es_begin();") < run.index("EnterCriticalSection(&ml1021_q->submit_lock)")
      < run.index("mad_es_finish(eb);") < run.index("LeaveCriticalSection(&ml1021_q->submit_lock)")
      and run.count("mad_es_finish(eb);") == 1 and re.search(r"\breturn\b", run) is None)
draw = src[src.index("static void exec_draw(struct mad_exec *e, const struct mad_cmd *c) {"):]
draw = draw[:draw.index("\n}\n")]
check("exec_draw sends a pipeline-variant draw at once (another thread may evict and release the variant)",
      "if (c_pso.type == WMTRenderCommandSetPSO && !tv && c_pso.pso != e->pso->rps) mad_eb_flush_cur(EBF_VARIANT);" in draw
      and draw.index("mad_eb_flush_cur(EBF_VARIANT)") > draw.index("MTLRenderCommandEncoder_encodeCommands(e->renc, (const struct wmtcmd_base *)&c_pso);"))
check("a thread's arena is freed at DLL_THREAD_DETACH",
      "if (reason == DLL_THREAD_DETACH) mad_es_thread_exit();" in src)

wm_dir = root / "dxmt/src/winemetal"
hdr = (wm_dir / "winemetal.h").read_text() if (wm_dir / "winemetal.h").exists() else ""
if hdr:
    def enum_names(name):
        body = hdr[hdr.index("enum %s : uint16_t {" % name):]
        body = body[:body.index("};")]
        return re.findall(r"^\s*(\w+)\s*(?:=\s*\d+)?\s*,", body, re.M)
    size = cut[cut.index("static size_t mad_eb_size("):]
    size = size[:size.index("\n}\n")]
    missing = [n for k in ("WMTRenderCommandType", "WMTComputeCommandType", "WMTBlitCommandType") for n in enum_names(k)
               if not re.match(r"(Unused\d|WMTRenderCommandReserved\d+|WMTBlitCommandReserved\d+)$", n) and ("case %s:" % n) not in size]
    check("every winemetal command type is sized (reserved / unused ones are never queued)%s" % (": missing " + ", ".join(missing) if missing else ""),
          not missing)
else:
    print("note: no dxmt sources; command-type coverage not checked")
cat = (root / "app/Madeira/ConfigCatalog.generated.swift").read_text()
check("catalog lists encode-batch, on by default",
      re.search(r'key: "encode-batch".*kind: \.bool, defaultValue: "1"', cat) is not None)

harness = r'''
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdlib.h>
#include <pthread.h>
#include "winemetal.h"
typedef uint64_t UINT64; typedef int64_t LONG64; typedef int LONG; typedef unsigned char UINT8; typedef unsigned DWORD; typedef unsigned UINT; typedef uint32_t UINT32;
typedef union { long long QuadPart; } LARGE_INTEGER;
#define TLS_OUT_OF_INDEXES 0xffffffffu
static __thread void *fake_tls[64];
static void *broken_tls[64]; static int probe_broken;   /* a TEB whose slots are not where the runtime reads */
#define MAD_EB_SLOT(i) (*(probe_broken ? &broken_tls[(i)] : &fake_tls[(i)]))
static DWORD tls_next = 7;
static DWORD TlsAlloc(void) { return __atomic_fetch_add(&tls_next, 1, __ATOMIC_SEQ_CST); }
static int TlsFree(DWORD i) { (void)i; return 1; }
static int TlsSetValue(DWORD i, void *v) { fake_tls[i] = v; return 1; }
static LONG InterlockedExchangeAdd(volatile LONG *p, LONG v) { return __atomic_fetch_add(p, v, __ATOMIC_SEQ_CST); }
static LONG64 InterlockedExchangeAdd64(volatile LONG64 *p, LONG64 v) { return __atomic_fetch_add(p, v, __ATOMIC_SEQ_CST); }
static LONG InterlockedIncrement(volatile LONG *p) { return __atomic_add_fetch(p, 1, __ATOMIC_SEQ_CST); }
static LONG InterlockedCompareExchange(volatile LONG *p, LONG x, LONG cmp) { __atomic_compare_exchange_n(p, &cmp, x, 0, __ATOMIC_SEQ_CST, __ATOMIC_SEQ_CST); return cmp; }
static LONG64 mad_qpc(void) { return 0; }
static void d3d12_log(const char *fmt, ...) { (void)fmt; }
static int QueryPerformanceFrequency(LARGE_INTEGER *f) { f->QuadPart = 1000000; return 1; }

/* What Metal would see. */
enum { EV_CMD = 1, EV_OPEN, EV_END, EV_REL, EV_LABEL };
struct ev { int op, kind; obj_handle_t enc; unsigned type; uint64_t f[4]; unsigned char pay[400]; unsigned plen; };
static struct ev evs[60000]; static unsigned nev, ncalls, maxchain;
static obj_handle_t next_handle = 0x1000;
static void ev_add(int op, int kind, obj_handle_t enc, unsigned type) {
    struct ev *v = &evs[nev++]; memset(v, 0, sizeof *v); v->op = op; v->kind = kind; v->enc = enc; v->type = type;
}
static void rec_chain(int kind, obj_handle_t enc, const struct wmtcmd_base *c) {
    unsigned n = 0; ncalls++;
    for (; c; c = (const struct wmtcmd_base *)c->next.ptr, n++) {
        struct ev *v; ev_add(EV_CMD, kind, enc, c->type); v = &evs[nev - 1];
        v->f[3] = c->reserved[0] | (uint64_t)c->reserved[1] << 16 | (uint64_t)c->reserved[2] << 32;
        if (kind == 0) switch (c->type) {
        case WMTRenderCommandSetPSO: v->f[0] = ((const struct wmtcmd_render_setpso *)c)->pso; break;
        case WMTRenderCommandSetVertexBuffer: { const struct wmtcmd_render_setbuffer *s = (const void *)c; v->f[0] = s->buffer; v->f[1] = s->offset; v->f[2] = s->index; break; }
        case WMTRenderCommandDraw: { const struct wmtcmd_render_draw *d = (const void *)c; v->f[0] = d->vertex_count; v->f[1] = d->vertex_start; v->f[2] = d->instance_count; break; }
        case WMTRenderCommandWaitForFence: case WMTRenderCommandUpdateFence: { const struct wmtcmd_render_fence_op *f = (const void *)c; v->f[0] = f->fence; v->f[1] = f->stages; break; }
        case WMTRenderCommandSetFragmentBytes: { const struct wmtcmd_render_setbytes *s = (const void *)c; v->plen = (unsigned)s->length; memcpy(v->pay, s->bytes.ptr, s->length); v->f[2] = s->index; break; }
        case WMTRenderCommandSetViewports: { const struct wmtcmd_render_setviewports *s = (const void *)c; v->plen = s->viewport_count * (unsigned)sizeof(struct WMTViewport); memcpy(v->pay, s->viewports.ptr, v->plen); break; }
        case WMTRenderCommandSetScissorRects: { const struct wmtcmd_render_setscissorrects *s = (const void *)c; v->plen = s->rect_count * (unsigned)sizeof(struct WMTScissorRect); memcpy(v->pay, s->scissor_rects.ptr, v->plen); break; }
        case WMTRenderCommandDrawMeshThreadgroups: { const struct wmtcmd_render_draw_meshthreadgroups *d = (const void *)c; v->f[0] = d->threadgroup_per_grid.width; break; }
        default: break;
        } else if (kind == 1) switch (c->type) {
        case WMTComputeCommandSetBytes: { const struct wmtcmd_compute_setbytes *s = (const void *)c; v->plen = (unsigned)s->length; memcpy(v->pay, s->bytes.ptr, s->length); v->f[2] = s->index; break; }
        case WMTComputeCommandDispatch: { const struct wmtcmd_compute_dispatch *d = (const void *)c; v->f[0] = d->size.width; v->f[1] = d->size.height; break; }
        case WMTComputeCommandSetBuffer: { const struct wmtcmd_compute_setbuffer *s = (const void *)c; v->f[0] = s->buffer; v->f[1] = s->offset; v->f[2] = s->index; break; }
        default: break;
        } else switch (c->type) {
        case WMTBlitCommandCopyFromBufferToBuffer: { const struct wmtcmd_blit_copy_from_buffer_to_buffer *b = (const void *)c; v->f[0] = b->src; v->f[1] = b->dst; v->f[2] = b->copy_length; break; }
        case WMTBlitCommandFillBuffer: { const struct wmtcmd_blit_fillbuffer *b = (const void *)c; v->f[0] = b->buffer; v->f[1] = b->length; v->f[2] = b->value; break; }
        default: break;
        }
    }
    if (n > maxchain) maxchain = n;
}
void MTLRenderCommandEncoder_encodeCommands(obj_handle_t enc, const struct wmtcmd_base *c) { rec_chain(0, enc, c); }
void MTLComputeCommandEncoder_encodeCommands(obj_handle_t enc, const struct wmtcmd_base *c) { rec_chain(1, enc, c); }
void MTLBlitCommandEncoder_encodeCommands(obj_handle_t enc, const struct wmtcmd_base *c) { rec_chain(2, enc, c); }
obj_handle_t MTLCommandBuffer_renderCommandEncoder(obj_handle_t cb, struct WMTRenderPassInfo *i) { (void)cb; (void)i; ev_add(EV_OPEN, 0, next_handle, 0); return next_handle++; }
obj_handle_t MTLCommandBuffer_computeCommandEncoder(obj_handle_t cb, bool c) { (void)cb; (void)c; ev_add(EV_OPEN, 1, next_handle, 0); return next_handle++; }
obj_handle_t MTLCommandBuffer_blitCommandEncoder(obj_handle_t cb) { (void)cb; ev_add(EV_OPEN, 2, next_handle, 0); return next_handle++; }
void MTLCommandEncoder_endEncoding(obj_handle_t e) { ev_add(EV_END, 0, e, 0); }
void NSObject_release(obj_handle_t o) { ev_add(EV_REL, 0, o, 0); }
void MTLCommandEncoder_setLabel(obj_handle_t e, obj_handle_t s) { ev_add(EV_LABEL, 0, e, (unsigned)s); }
''' + cut + r'''
static long long cfg_eb = 1, cfg_dd = 1, cfg_reads;
static long long mad_cfg_int_pe(const char *k, long long d) {
    cfg_reads++;
    if (!strcmp(k, "encode-batch")) return cfg_eb < 0 ? d : cfg_eb;
    if (!strcmp(k, "draw-dedup")) return cfg_dd < 0 ? d : cfg_dd;
    return d;
}
static int bad;
#define EXPECT(c, what) do { if (!(c)) { printf("FAIL %s\n", what); bad = 1; } } while (0)

/* One draw: pipeline, vertex buffer, fragment bytes (the caller's memory), viewports (idem), draw. */
static void draw(obj_handle_t enc, unsigned k, unsigned char *bytes, struct WMTViewport *vps, unsigned nvp) {
    struct wmtcmd_render_setpso p; struct wmtcmd_render_setbuffer b; struct wmtcmd_render_setbytes s;
    struct wmtcmd_render_setviewports v; struct wmtcmd_render_draw d;
    memset(&p, 0, sizeof p); memset(&b, 0, sizeof b); memset(&s, 0, sizeof s); memset(&v, 0, sizeof v); memset(&d, 0, sizeof d);
    p.type = WMTRenderCommandSetPSO; p.pso = 0x500 + k % 3;
    b.type = WMTRenderCommandSetVertexBuffer; b.buffer = 0x600 + k % 5; b.offset = k * 64; b.index = (uint8_t)(6 + k % 4);
    s.type = WMTRenderCommandSetFragmentBytes; s.bytes.ptr = bytes; s.length = 16 + k % 17; s.index = 0;
    v.type = WMTRenderCommandSetViewports; v.viewports.ptr = vps; v.viewport_count = (uint8_t)nvp;
    d.type = WMTRenderCommandDraw; d.vertex_count = 3 * k + 3; d.vertex_start = k; d.instance_count = 1;
    d.reserved[1] = (uint16_t)k;   /* reserved words carry data (b2t aspect, tessellation): they must survive */
    p.next.ptr = &b; b.next.ptr = &s; s.next.ptr = nvp ? (void *)&v : (void *)&d; v.next.ptr = &d;
    MTLRenderCommandEncoder_encodeCommands(enc, (const struct wmtcmd_base *)&p);
}
static void fence(obj_handle_t enc, int update) {
    struct wmtcmd_render_fence_op f; memset(&f, 0, sizeof f);
    f.type = update ? WMTRenderCommandUpdateFence : WMTRenderCommandWaitForFence; f.fence = 0xfe; f.stages = update ? WMTRenderStageFragment : WMTRenderStageVertex;
    MTLRenderCommandEncoder_encodeCommands(enc, (const struct wmtcmd_base *)&f);
}
static void scenario(int with_finish_tail) {
    unsigned char bytes[64]; struct WMTViewport vps[8]; unsigned k, j;
    struct mad_eb *b = mad_es_begin();
    struct WMTRenderPassInfo rpi; memset(&rpi, 0, sizeof rpi);
    obj_handle_t r = MTLCommandBuffer_renderCommandEncoder(0xcb, &rpi), c, bl, r2;
    fence(r, 0);
    for (k = 0; k < 40; k++) {
        for (j = 0; j < sizeof bytes; j++) bytes[j] = (unsigned char)(k * 7 + j);
        for (j = 0; j < 8; j++) { memset(&vps[j], 0, sizeof vps[j]); vps[j].width = k + j; }
        draw(r, k, bytes, vps, k % 3 ? 0 : 1 + k % 8);
        memset(bytes, 0xee, sizeof bytes); memset(vps, 0xdd, sizeof vps);   /* the caller reuses its memory at once */
        if (k == 12) NSObject_release(0x7777);   /* a release mid-encoder: everything before it goes first */
        if (k == 20) { struct wmtcmd_render_nop u; memset(&u, 0, sizeof u); u.type = (enum WMTRenderCommandType)41;   /* an unknown type */
                       MTLRenderCommandEncoder_encodeCommands(r, (const struct wmtcmd_base *)&u); }
        if (k == 30) MTLCommandEncoder_setLabel(r, 0x1abe1);
    }
    for (k = 0; k < 400; k++) {   /* overflows the 64 KB arena several times */
        for (j = 0; j < 8; j++) { memset(&vps[j], 0, sizeof vps[j]); vps[j].originX = k; vps[j].zfar = j; }
        for (j = 0; j < sizeof bytes; j++) bytes[j] = (unsigned char)(k + j);
        draw(r, k, bytes, vps, 8);
    }
    fence(r, 1);
    MTLCommandEncoder_endEncoding(r);
    c = MTLCommandBuffer_computeCommandEncoder(0xcb, false);
    for (k = 0; k < 30; k++) {
        UINT32 n = k * 3; struct wmtcmd_compute_setbuffer sb; struct wmtcmd_compute_setbytes sby; struct wmtcmd_compute_dispatch d;
        memset(&sb, 0, sizeof sb); memset(&sby, 0, sizeof sby); memset(&d, 0, sizeof d);
        sb.type = WMTComputeCommandSetBuffer; sb.buffer = 0x900; sb.offset = k * 1088; sb.index = 2;
        sby.type = WMTComputeCommandSetBytes; sby.bytes.ptr = &n; sby.length = sizeof n; sby.index = 2;
        d.type = WMTComputeCommandDispatch; d.size.width = k + 1; d.size.height = 2; d.size.depth = 1;
        sb.next.ptr = &sby; sby.next.ptr = &d;
        MTLComputeCommandEncoder_encodeCommands(c, (const struct wmtcmd_base *)&sb);
        n = 0xdeadbeef;
    }
    MTLCommandEncoder_endEncoding(c);
    bl = MTLCommandBuffer_blitCommandEncoder(0xcb);
    for (k = 0; k < 20; k++) {
        struct wmtcmd_blit_copy_from_buffer_to_buffer cp; struct wmtcmd_blit_fillbuffer f;
        memset(&cp, 0, sizeof cp); memset(&f, 0, sizeof f);
        cp.type = WMTBlitCommandCopyFromBufferToBuffer; cp.src = 0xa00 + k; cp.dst = 0xb00; cp.copy_length = k * 4;
        f.type = WMTBlitCommandFillBuffer; f.buffer = 0xc00; f.length = k; f.value = (uint8_t)k; cp.next.ptr = &f;
        MTLBlitCommandEncoder_encodeCommands(bl, (const struct wmtcmd_base *)&cp);
    }
    MTLCommandEncoder_endEncoding(bl);
    r2 = MTLCommandBuffer_renderCommandEncoder(0xcb, &rpi);
    for (k = 0; k < 5; k++) { for (j = 0; j < sizeof bytes; j++) bytes[j] = (unsigned char)(3 * k + j); draw(r2, k, bytes, vps, 0); }
    {   /* another encoder's chain before r2 ended: r2's go first */
        struct wmtcmd_compute_dispatch d; memset(&d, 0, sizeof d); d.type = WMTComputeCommandDispatch; d.size.width = 77;
        MTLComputeCommandEncoder_encodeCommands(c, (const struct wmtcmd_base *)&d);
    }
    for (k = 5; k < 9; k++) draw(r2, k, bytes, vps, 0);
    if (with_finish_tail) { mad_es_finish(b); b = NULL; }   /* r2 still open: what is queued goes out now */
    for (k = 9; k < 12; k++) draw(r2, k, bytes, vps, 0);   /* outside the replay: sent at once */
    MTLCommandEncoder_endEncoding(r2);
    if (b) mad_es_finish(b);
}
static struct ev ref[60000]; static unsigned nref, ref_calls;
static int same_log(void) {
    unsigned i;
    if (nev != nref) { printf("event count %u vs %u\n", nev, nref); return 0; }
    for (i = 0; i < nev; i++) {
        const struct ev *a = &evs[i], *b = &ref[i];
        if (a->op != b->op || a->kind != b->kind || a->enc != b->enc || a->type != b->type || memcmp(a->f, b->f, sizeof a->f) ||
            a->plen != b->plen || memcmp(a->pay, b->pay, a->plen)) { printf("first difference at event %u (op %d type %u)\n", i, a->op, a->type); return 0; }
    }
    return 1;
}
static void *other_thread(void *arg) {   /* a thread that never began a replay sends at once */
    (void)arg; unsigned before = ncalls; unsigned char by[64] = { 0 }; struct WMTViewport v[1];
    memset(v, 0, sizeof v);
    draw(0x4242, 1, by, v, 0);
    return (void *)(uintptr_t)(ncalls == before + 1 && mad_eb_cur() == NULL);
}
int main(void) {
    probe_broken = 1;
    EXPECT(mad_es_begin() == NULL && g_eb_on == 0 && g_dd_on == 0 && g_eb_tls < 0,
           "a TLS slot that cannot be read in place turns both off");
    probe_broken = 0; g_eb_on = g_dd_on = -1; cfg_reads = 0;
    /* reference: switch off */
    cfg_eb = 0; scenario(1);
    EXPECT(cfg_reads == 2, "switches read once each");
    memcpy(ref, evs, nev * sizeof evs[0]); nref = nev; ref_calls = ncalls;
    EXPECT(ref_calls > 500, "reference: one call per chain");
    /* batched */
    g_eb_on = -1; g_dd_on = -1; cfg_eb = -1; nev = 0; ncalls = 0; next_handle = 0x1000;
    scenario(1);
    EXPECT(g_eb_on == 1, "on by default (madeira.cfg unset)");
    EXPECT(same_log(), "Metal receives the same commands, contents and order, interleaved the same with opens, ends, releases and labels");
    EXPECT(ncalls * 10 < ref_calls, "far fewer encodeCommands calls");
    printf("note: %u encodeCommands calls batched vs %u one per chain; longest chain %u\n", ncalls, ref_calls, maxchain);
    EXPECT(g_eb_why[EBF_RELEASE] >= 1 && g_eb_why[EBF_FULL] >= 1 && g_eb_why[EBF_END] >= 3 && g_eb_alone >= 1 && g_eb_why[EBF_ENCODER] >= 1,
           "sent at release, arena full, encoder end, another encoder; the unknown type alone");
    /* finish without the tail: the end of a replay flushes too */
    nev = 0; ncalls = 0; next_handle = 0x1000; scenario(0);
    memcpy(ref, evs, nev * sizeof evs[0]); nref = nev;
    g_eb_on = 0; nev = 0; ncalls = 0; next_handle = 0x1000; scenario(0);
    EXPECT(same_log(), "switched off at run time: the same calls, one per chain");
    g_eb_on = 1;
    {   /* the arena is per thread */
        pthread_t t; void *r = 0;
        struct mad_eb *b = mad_es_begin();
        pthread_create(&t, NULL, other_thread, NULL); pthread_join(t, &r);
        EXPECT(r != NULL, "another thread outside a replay sends at once");
        EXPECT(mad_eb_cur() == b && b->active == 1, "this thread's replay unaffected");
        {   /* nesting: only the outermost finish ends the replay */
            struct mad_eb *b2 = mad_es_begin();
            EXPECT(b2 == b && b->active == 2, "nested begin");
            mad_es_finish(b2);
            EXPECT(mad_eb_cur() == b, "still active after an inner finish");
        }
        mad_es_finish(b);
        EXPECT(mad_eb_cur() == NULL, "inactive after the last finish");
        mad_es_thread_exit();
        EXPECT(fake_tls[g_eb_tls] == NULL, "thread exit frees the arena");
    }
    if (!bad) printf("ok\n");
    return bad;
}
'''
cc = os.environ.get("CC") if os.environ.get("CC") and "clang" in os.environ.get("CC") else shutil.which("clang")
std = "-std=gnu11"
if not cc:
    cc, std = shutil.which("gcc") or shutil.which("cc"), "-std=gnu2x"
if not hdr:
    print("note: no dxmt sources; runtime checks skipped")
elif not cc:
    print("note: no host compiler; runtime checks skipped")
else:
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        (t / "h.c").write_text(harness)
        exe = t / "h"
        r = subprocess.run([cc, std, "-O1", "-Wall", "-Wno-unused-function", "-Wno-fixed-enum-extension", "-Wno-unknown-warning-option",
                            "-DDXMT_NATIVE", "-I%s" % wm_dir, "-o", str(exe), str(t / "h.c"), "-lpthread"],
                           capture_output=True, text=True)
        if r.returncode:
            print(r.stderr[-3000:])
        out = subprocess.run([str(exe)], capture_output=True, text=True).stdout if exe.exists() else ""
        print(out.strip())
        check("batch runtime (same Metal calls in the same order, fewer calls, flush points, per-thread state)",
              r.returncode == 0 and out.strip().endswith("ok"))

print("PASS" if ok else "FAILED")
sys.exit(0 if ok else 1)
