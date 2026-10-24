#!/usr/bin/env python3
"""clear-rects: ClearRenderTargetView / ClearDepthStencilView rectangles honoured.

madeira-d3d12 cleared the whole view whatever rectangles the game passed (a
Metal load action has no rectangle). Horizon Zero Dawn (build 480, 2026-10-09
20:37) began to pass them with its first gameplay frames and its image was
badly corrupted. With the opt-in switch a clear whose rectangles do not cover
the view becomes a pass of its own: the target loaded and stored, one
full-target triangle per rectangle under a scissor, drawn with clear functions
from the helper library (mad_kernels.metal), as DXMT's D3D11 ClearView does.

Checks: off by default and the old path untouched when off; the rectangles
are clipped and stored at record time (a covering rectangle keeps the
load-action clear, rectangles all outside clear nothing); the replay flushes a
pending whole clear of the view first, waits on the fence chain before the
draws and signals it after them, and falls back to the whole view without the
clear functions; the shaders sit behind MAD_NO_CLEAR_RECTS and the build
retries without them, so the other helper kernels never depend on them. The
record helper is compiled and run against stubs.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
pe = (root / 'madeira-d3d12/src/pe/madeira_d3d12.c').read_text()
metal = (root / 'madeira-d3d12/src/pe/mad_kernels.metal').read_text()
build_sh = root / 'tools/build-madeira-d3d12-dll.sh'   # the fork's CI build script
build = build_sh.read_text() if build_sh.exists() else None
catalog = (root / 'app/Madeira/ConfigCatalog.generated.swift').read_text()
ok = True


def check(what, cond):
    global ok
    print(('ok   ' if cond else 'FAIL ') + what)
    ok &= bool(cond)


def body(sig):
    start = pe.index(sig)
    while pe.index(';', start) < pe.index('{', start):
        start = pe.index(sig, start + 1)
    brace = pe.index('{', start)
    depth = 0
    for i in range(brace, len(pe)):
        if pe[i] == '{':
            depth += 1
        elif pe[i] == '}':
            depth -= 1
            if depth == 0:
                return pe[start:i + 1]
    raise AssertionError('unterminated: ' + sig)


check('off by default: mad_cfg_int_pe("clear-rects", 0)', 'mad_cfg_int_pe("clear-rects", 0)' in pe)
rt = body('static void STDMETHODCALLTYPE list_ClearRenderTargetView(ID3D12GraphicsCommandList *This,')
ds = body('static void STDMETHODCALLTYPE list_ClearDepthStencilView(ID3D12GraphicsCommandList *This,')
for name, f, d in (('render target', rt, '0'), ('depth-stencil', ds, '1')):
    check(name + ': rectangles recorded before the command, nothing recorded when all are outside',
          f.index('nr = mad_clear_rects_record(l, ') < f.index('if (nr < 0) return;') < f.index('c = mad_list_push(l, ') and
          ', n, rects, ' + d + ', &at);' in f)
    check(name + ': the old "ignored" line only with the switch off', 'g_clear_rects != 1' in f)
    check(name + ': only a partial clear carries rectangles',
          'if (nr > 0) { c->u.clear.nrect = (UINT)nr; c->u.clear.rect_at = at; }' in f)
rec = body('static int mad_clear_rects_record(struct mad_list *l, const struct mad_resource *r, const struct mad_rtvp *v,')
check('the record helper asks the switch only when rectangles came',
      'if (!n || !rects || !r || !mad_clear_rects_on()) return 0;' in rec)
ex = body('static void mad_exec_list(struct mad_queue *q, struct mad_list *l, obj_handle_t cb)')
check('replay: rectangles go to exec_clear_rects, everything else to the pending clear as before',
      'if (c->u.clear.nrect) exec_clear_rects(&e, l, c);   /* madeira-bcd clear-rects */\n'
      '            else exec_add_clear(&e, c->u.clear.res, &c->u.clear.v, c->u.clear.rgba, 0.0f, 0, 0, 0);' in ex and
      'if (c->u.clear.nrect) exec_clear_rects(&e, l, c);   /* madeira-bcd clear-rects */\n'
      '            else exec_add_clear(&e, c->u.clear.res, &c->u.clear.v, NULL, c->u.clear.depth, 1, c->u.clear.stencil, c->u.clear.flags);' in ex)
cr = body('static void exec_clear_rects(struct mad_exec *e, const struct mad_list *l, const struct mad_cmd *c)')
check('replay: without clear functions the whole view, as before',
      cr.index('if (!pso || (is_depth && !dss))') < cr.index('exec_add_clear(e, r, v, NULL, c->u.clear.depth, 1,'))
check('replay: a pending whole clear of the view goes first, the open pass ends',
      'if (i >= 0) exec_flush_clear(e, i);   /* an earlier whole clear of this view goes first */\n'
      '    exec_end(e);   /* nothing may stay open while this pass\'s encoder is made */' in cr and
      cr.index('exec_end(e);   /* nothing may stay open') < cr.index('enc = MTLCommandBuffer_renderCommandEncoder(e->cb, &rpi);'))
check('replay: the target is loaded and stored',
      'rpi.depth.load_action = WMTLoadActionLoad; rpi.depth.store_action = WMTStoreActionStore;' in cr and
      'rpi.colors[0].load_action = WMTLoadActionLoad; rpi.colors[0].store_action = WMTStoreActionStore;' in cr and
      'rpi.stencil.load_action = WMTLoadActionLoad; rpi.stencil.store_action = WMTStoreActionStore;' in cr)
check('replay: fence wait before the draws, signal after them, then the encoder ends',
      cr.index('exec_fence_render(e, enc, 0);') < cr.index('MTLRenderCommandEncoder_encodeCommands(enc, (const struct wmtcmd_base *)&c_sc[0]);') <
      cr.index('exec_fence_render(e, enc, 1);') < cr.index('MTLCommandEncoder_endEncoding(enc);'))
check('replay: the pass names its attachment for the fence chain (ml1134)',
      cr.index('e->f6_att[0] = r; e->f6_natt = 1;') < cr.index('exec_fence_render(e, enc, 0);'))
check('replay: one triangle per layer under each rectangle\'s scissor',
      'c_draw[j].vertex_count = 3;' in cr and 'c_draw[j].instance_count = layers;' in cr and
      'c_sc[j].scissor_rect.width = q[2] - q[0]; c_sc[j].scissor_rect.height = q[3] - q[1];' in cr)
dss = body('static obj_handle_t mad_clear_dss(struct mad_device *d, UINT8 flags)')
check('a stencil clear replaces with the reference, a depth clear writes depth always',
      'dsi.depth_compare_function = WMTCompareFunctionAlways;' in dss and
      'dsi.depth_write_enabled = (flags & D3D12_CLEAR_FLAG_DEPTH) != 0;' in dss and
      's.depth_stencil_pass_op = s.stencil_fail_op = s.depth_fail_op = WMTStencilOperationReplace;' in dss and
      'c_dss.stencil_ref = c->u.clear.stencil;' in cr)
pso = body('static obj_handle_t mad_clear_pso(struct mad_device *d, const struct mad_resource *r, int is_depth)')
check('pipelines by format: the depth fragment with the depth (and stencil) format, else by integer kind',
      'rp.fragment_function = d->clr_fs[3];' in pso and 'if (r->has_stencil) rp.stencil_pixel_format = r->tex_pf;' in pso and
      'rp.fragment_function = d->clr_fs[mad_pf_int_kind(r->tex_pf)];' in pso and 'else if (d->nclr_pso < 32)' in pso)
guard = metal[metal.index('#ifndef MAD_NO_CLEAR_RECTS'):]
check('the clear shaders sit behind MAD_NO_CLEAR_RECTS, after the other kernels',
      metal.index('kernel void mad_probe_words') < metal.index('#ifndef MAD_NO_CLEAR_RECTS') and guard.rstrip().endswith('#endif') and
      all(('mad_clear_' + n) in guard for n in ('vs(', 'fs_float(', 'fs_uint(', 'fs_sint(', 'fs_depth(')))
check('the shaders write what the runtime binds: fragment buffer 0, depth(any), a layer per instance',
      guard.count('[[buffer(0)]]') == 4 and '[[depth(any)]]' in guard and '[[render_target_array_index]]' in guard)
if build is not None:
    check('the build compiles the helpers again without them when they do not compile',
          'mad_kernels_metal -DMAD_NO_TEXBUF_PROBE -DMAD_NO_CLEAR_RECTS;' in build and 'mad_kernels_metal ||' in build)
check('in the settings catalog, off by default',
      'key: "clear-rects"' in catalog and 'defaultValue: "0"' in catalog[catalog.index('key: "clear-rects"'):][:300])

kind = body('static int mad_pf_int_kind(enum WMTPixelFormat pf)')
harness = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
typedef uint32_t UINT32; typedef unsigned UINT; typedef long LONG; typedef uint16_t UINT16;
typedef struct { LONG left, top, right, bottom; } D3D12_RECT;
static LONG InterlockedIncrement(volatile LONG *p) { return ++*p; }
static int logs;
static void d3d12_log(const char *fmt, ...) { (void)fmt; logs++; }
static int sw = 1, g_clear_rects = -1;
static volatile LONG g_crect_empty;
static int mad_clear_rects_on(void) { return sw; }
static int mad_grow(void **p, unsigned *cap, unsigned need, size_t sz) {
    if (need <= *cap) return 1;
    *p = realloc(*p, need * sz); *cap = need; return *p != NULL;
}
struct mad_rtvp { UINT16 level, slice, layers, plane; };
struct mad_resource { UINT32 width, height; unsigned serial; };
struct mad_list { UINT32 *cdata; unsigned ncdata, cdcap; };
enum WMTPixelFormat { WMTPixelFormatR8Unorm = 10, WMTPixelFormatR8Uint = 13, WMTPixelFormatR8Sint = 14, WMTPixelFormatR16Uint = 23,
  WMTPixelFormatR16Sint = 24, WMTPixelFormatRG8Uint = 33, WMTPixelFormatRG8Sint = 34, WMTPixelFormatR32Uint = 53,
  WMTPixelFormatR32Sint = 54, WMTPixelFormatRG16Uint = 63, WMTPixelFormatRG16Sint = 64, WMTPixelFormatRGBA8Uint = 73,
  WMTPixelFormatRGBA8Sint = 74, WMTPixelFormatRGB10A2Uint = 91, WMTPixelFormatRG32Uint = 103, WMTPixelFormatRG32Sint = 104,
  WMTPixelFormatRGBA16Uint = 113, WMTPixelFormatRGBA16Sint = 114, WMTPixelFormatRGBA32Uint = 123, WMTPixelFormatRGBA32Sint = 124,
  WMTPixelFormatRGBA16Float = 115, WMTPixelFormatBGRA8Unorm = 80 };
''' + kind + '\n' + rec + r'''
static int bad;
#define EXPECT(c, what) do { if (!(c)) { printf("FAIL %s\n", what); bad = 1; } else printf("ok   %s\n", what); } while (0)
int main(void) {
    struct mad_list l = { 0 };
    struct mad_resource r = { 1408, 648, 7 };
    struct mad_rtvp v0 = { 0, 0, 1, 0 }, v1 = { 1, 0, 1, 0 };
    D3D12_RECT whole = { 0, 0, 1408, 648 }, big = { -5, -5, 5000, 5000 }, part = { 100, 50, 600, 300 };
    D3D12_RECT edge = { 1300, 600, 1600, 900 }, out = { 2000, 2000, 2100, 2100 }, empty = { 10, 10, 10, 20 };
    D3D12_RECT two[2] = { { 0, 0, 704, 648 }, { 704, 0, 1408, 324 } }, mixed[3] = { { 5, 5, 6, 6 }, { 3000, 0, 3001, 1 }, { 0, 0, 0, 0 } };
    UINT at = 99;
    int n;

    EXPECT(mad_clear_rects_record(&l, &r, &v0, 0, NULL, 0, &at) == 0 && l.ncdata == 0, "no rectangles: the whole view");
    EXPECT(mad_clear_rects_record(&l, &r, &v0, 1, &whole, 0, &at) == 0 && l.ncdata == 0, "a rectangle equal to the view: the whole view");
    EXPECT(mad_clear_rects_record(&l, &r, &v0, 1, &big, 1, &at) == 0, "a rectangle larger than the view: the whole view");
    EXPECT(mad_clear_rects_record(&l, &r, &v0, 2, (D3D12_RECT[]){ part, big }, 0, &at) == 0, "any covering rectangle: the whole view");
    n = mad_clear_rects_record(&l, &r, &v0, 1, &part, 1, &at);
    EXPECT(n == 1 && at == 0 && l.ncdata == 4 && l.cdata[0] == 100 && l.cdata[1] == 50 && l.cdata[2] == 600 && l.cdata[3] == 300,
           "a partial rectangle is stored as x0, y0, x1, y1");
    n = mad_clear_rects_record(&l, &r, &v0, 1, &edge, 0, &at);
    EXPECT(n == 1 && at == 4 && l.cdata[4] == 1300 && l.cdata[5] == 600 && l.cdata[6] == 1408 && l.cdata[7] == 648,
           "a rectangle over the edge is clipped to the view");
    n = mad_clear_rects_record(&l, &r, &v1, 1, &part, 0, &at);
    EXPECT(n == 1 && l.cdata[at + 2] == 600 && l.cdata[at + 3] == 300, "inside a level-1 view (704x324) it stays");
    n = mad_clear_rects_record(&l, &r, &v1, 1, &edge, 0, &at);
    EXPECT(n == -1, "outside a level-1 view: nothing to clear");
    n = mad_clear_rects_record(&l, &r, &v0, 2, two, 0, &at);
    EXPECT(n == 2 && l.cdata[at + 4] == 704 && l.cdata[at + 7] == 324, "two halves: both stored (D3D12 clears their union)");
    {
        unsigned before = l.ncdata;
        EXPECT(mad_clear_rects_record(&l, &r, &v0, 1, &out, 0, &at) == -1 && l.ncdata == before, "all outside: nothing stored, nothing cleared");
        EXPECT(mad_clear_rects_record(&l, &r, &v0, 1, &empty, 0, &at) == -1, "an empty rectangle clears nothing");
        n = mad_clear_rects_record(&l, &r, &v0, 3, mixed, 0, &at);
        EXPECT(n == 1 && l.ncdata == before + 4 && l.cdata[at] == 5, "only the rectangles with area are kept");
    }
    EXPECT(g_crect_empty == 3, "clears with nothing inside are counted");
    sw = 0;
    EXPECT(mad_clear_rects_record(&l, &r, &v0, 1, &part, 0, &at) == 0, "switch off: the whole view, as before");
    EXPECT(mad_pf_int_kind(WMTPixelFormatRGBA8Uint) == 1 && mad_pf_int_kind(WMTPixelFormatRGB10A2Uint) == 1 &&
           mad_pf_int_kind(WMTPixelFormatR32Sint) == 2 && mad_pf_int_kind(WMTPixelFormatRGBA16Float) == 0 &&
           mad_pf_int_kind(WMTPixelFormatBGRA8Unorm) == 0, "integer targets take the uint / sint fragment");
    printf("%s\n", bad ? "harness FAILED" : "harness ok");
    return bad;
}
'''

cc = shutil.which('cc') or shutil.which('gcc') or shutil.which('clang')
if not cc:
    check('a host C compiler', False)
else:
    with tempfile.TemporaryDirectory(prefix='madeira-crect-') as tmp:
        src = Path(tmp) / 'crect.c'
        exe = Path(tmp) / 'crect'
        src.write_text(harness)
        b = subprocess.run([cc, '-std=gnu11', '-Wall', '-Wno-unused-function', str(src), '-o', str(exe)], capture_output=True, text=True)
        check('the record helper compiles on the host', b.returncode == 0)
        if b.returncode:
            print(b.stderr[-3000:])
        else:
            run = subprocess.run([str(exe)], capture_output=True, text=True)
            print(run.stdout, end='')
            check('the record helper behaves', run.returncode == 0)

if not ok:
    sys.exit(1)
print('PASS: clear-rects')
