#!/usr/bin/env python3
"""Opt-in A/B switches for the Sony ports' corrupted meshes; no Wine runs.

Horizon Zero Dawn (skinned characters collapse every few frames) and Ghost of
Tsushima (objects with another instance's transform for a frame) are the only
games that show it; GTA V Enhanced and RDR2 do not. Each switch is off by
default and changes nothing then:
  - d3d12-wave-ops = 0 (WaveOps FALSE) and d3d12-binding-tier = 3;
  - d3d12-raw-typed-views = 1: raw and structured buffer views also carry a
    texture-buffer view (the format choice is run here), a UAV with a counter
    keeps its counter view;
  - skin-check captures the draw's indices too (kinds 22/23, run here).
Needs python3 and a C compiler (CC, default cc).
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
dsrc = (root / 'madeira-d3d12/src/pe/madeira_d3d12.c').read_text()
fails = []


def check(what, ok):
    print(('PASS: ' if ok else 'FAIL: ') + what)
    if not ok:
        fails.append(what)


def function(src, sig):
    a = src.index(sig)
    return src[a:src.index('\n}\n', a) + 3]


cc = os.environ.get('CC', 'cc')

# ---- capability switches ----
check('d3d12-wave-ops = 0 reports WaveOps FALSE; anything else keeps TRUE',
      'v = mad_cfg_int_pe("d3d12-wave-ops", 1) ? 1 : 0;' in dsrc and 'o->WaveOps = mad_wave_ops_answer();' in dsrc
      and 'o->WaveOps = TRUE;' not in dsrc)
check('d3d12-binding-tier = 3 reports tier 3; anything else keeps tier 2',
      'v = mad_cfg_int_pe("d3d12-binding-tier", 2) == 3 ? 3 : 2;' in dsrc
      and 'return v == 3 ? D3D12_RESOURCE_BINDING_TIER_3 : D3D12_RESOURCE_BINDING_TIER_2;' in dsrc
      and 'o->ResourceBindingTier = mad_binding_tier_answer();' in dsrc
      and 'o->ResourceBindingTier = D3D12_RESOURCE_BINDING_TIER_2;' not in dsrc)

# ---- raw-typed-views ----
sib = function(dsrc, 'static int mad_raw_typed_sibling(struct mad_device *d, struct mad_resource *r, UINT64 first, UINT64 num,')
check('d3d12-raw-typed-views is off by default', 'g_raw_typed = mad_cfg_int_pe("d3d12-raw-typed-views", 0) ? 1 : 0;' in dsrc)
fmt = r'''
#include <stdio.h>
typedef unsigned long long UINT64;
enum { R32 = 42, RG32 = 18, RGBA32 = 3 };
static int pick(UINT64 stride, int uav, UINT64 first, UINT64 num, UINT64 *f_first, UINT64 *f_num)
{
    int fmt = R32; UINT64 f = 4;
    if (!stride || (stride & 3) || !num) return 0;
    if (!uav && !(stride & 15)) { fmt = RGBA32; f = 16; }
    else if (!uav && !(stride & 7)) { fmt = RG32; f = 8; }
    *f_first = first * stride / f; *f_num = num * stride / f;
    return fmt;
}
int main(void)
{
    UINT64 a, b; int bad = 0;
    bad |= pick(4, 0, 10, 100, &a, &b) != R32 || a != 10 || b != 100;          /* raw SRV */
    bad |= pick(16, 0, 3, 5, &a, &b) != RGBA32 || a != 3 || b != 5;           /* structured float4 */
    bad |= pick(32, 0, 3, 5, &a, &b) != RGBA32 || a != 6 || b != 10;
    bad |= pick(8, 0, 3, 5, &a, &b) != RG32 || a != 3 || b != 5;
    bad |= pick(24, 0, 1, 2, &a, &b) != RG32 || a != 3 || b != 6;
    bad |= pick(12, 0, 2, 4, &a, &b) != R32 || a != 6 || b != 12;             /* no 96-bit texel in Metal */
    bad |= pick(20, 0, 1, 1, &a, &b) != R32 || a != 5 || b != 5;
    bad |= pick(16, 1, 1, 1, &a, &b) != R32 || a != 4 || b != 4;              /* every UAV: R32 */
    bad |= pick(6, 0, 1, 1, &a, &b) != 0 || pick(0, 0, 1, 1, &a, &b) != 0 || pick(4, 0, 1, 0, &a, &b) != 0;
    printf(bad ? "FAIL\n" : "ok\n");
    return bad;
}
'''
check('the sibling format follows the stride as in the source (16 -> RGBA32, 8 -> RG32, else R32; UAVs R32)',
      'if (!stride || (stride & 3) || !num) return 0;' in sib
      and 'if (!uav && !(stride & 15)) { fmt = DXGI_FORMAT_R32G32B32A32_UINT; f = 16; }' in sib
      and 'else if (!uav && !(stride & 7)) { fmt = DXGI_FORMAT_R32G32_UINT; f = 8; }' in sib
      and 'mad_typed_buffer_view(d, r, fmt, first * stride / f, num * stride / f, uav, e, &why)' in sib)
with tempfile.TemporaryDirectory(prefix='madeira-rawtyped-') as directory:
    c = Path(directory) / 'f.c'
    exe = Path(directory) / 'f'
    c.write_text(fmt)
    build = subprocess.run([cc, '-std=gnu11', '-Wall', '-Werror', '-o', str(exe), str(c)], capture_output=True, text=True)
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True)
    check('sibling formats and element ranges for raw, structured and UAV strides', run.returncode == 0)
srv = function(dsrc, 'static void STDMETHODCALLTYPE device_CreateShaderResourceView(ID3D12Device *This,')
uav = function(dsrc, 'static void STDMETHODCALLTYPE device_CreateUnorderedAccessView(ID3D12Device *This,')
check('an SRV gets a sibling only for raw or structured buffer views, before the plain descriptor',
      srv.index('(desc->Buffer.StructureByteStride || (desc->Buffer.Flags & D3D12_BUFFER_SRV_FLAG_RAW)) && mad_raw_typed_on() &&')
      < srv.index('mad_set_buffer_descriptor(e, r->gpu_address + first * stride, num * stride);'))
check('a UAV with a counter keeps its counter view; the counter bookkeeping still runs after a sibling',
      'if (!counter && desc && desc->ViewDimension == D3D12_UAV_DIMENSION_BUFFER &&' in uav
      and uav.index('mad_raw_typed_sibling((struct mad_device *)This, r, first, num, stride, 1, e)) ;')
      < uav.index('else mad_set_buffer_descriptor(e, r->gpu_address + first * stride, num * stride);')
      < uav.index('/* remember this view\'s counter (or forget a stale one) */'))

# ---- skin-check index capture ----
draw = function(dsrc, 'static void mad_skin_draw(struct mad_exec *e, const struct mad_cmd *c) {')
check('skin-check captures an indexed draw\'s indices within the per-frame capture budget',
      'if (g_skin_cap_on && c->kind == MC_DRAW_INDEXED && e->ib && e->ib->buffer && c->u.drawi.icount &&' in draw
      and 'InterlockedIncrement(&g_skin_caps_frame) <= 96) {' in draw
      and 'mad_skin_capture(e, lab, e->ib, off, (UINT)len, lead ? 23 : 22, isz | (tail ? 16u : 0u), 0);' in draw)
pr = function(dsrc, 'static void mad_skin_print(const struct mad_skcap *c) {')
blk = pr[pr.index('} else if (c->kind == 22 || c->kind == 23) {'):pr.index('} else {   /* 21: the start of a shader input */')]
body = blk[blk.index('{') + 1:]
ib = r'''
#include <stdio.h>
#include <string.h>
typedef unsigned int UINT; typedef unsigned int UINT32; typedef unsigned short UINT16;
struct cap { UINT len, kind, stride; const char *label; };
static char out[4096];
#define d3d12_log(...) snprintf(out, sizeof out, __VA_ARGS__)
static void pr(const struct cap *c, const unsigned char *p, UINT32 hash) {
    UINT i;
    {''' + body + r'''
    }
}
int main(void)
{
    unsigned short a[] = { 0xdead, 0, 1, 2, 2, 3, 3, 7, 5, 0xbeef };
    struct cap c = { sizeof a, 23, 2 | 16, "L" };   /* 10 u16: a lead and a trailing u16 that are not the draw's, 8 indices */
    pr(&c, (const unsigned char *)a, 0x1234);
    if (!strstr(out, "L: 8 indices captured, min 0 max 7, 1 of 2 triangles degenerate, hash 00001234: 0 1 2 2 3 3")) { printf("%s\nFAIL\n", out); return 1; }
    { unsigned b[] = { 4, 5, 6, 9, 9, 1 }; struct cap d = { sizeof b, 22, 4, "M" };
      pr(&d, (const unsigned char *)b, 1);
      if (!strstr(out, "M: 6 indices captured, min 1 max 9, 1 of 2 triangles degenerate")) { printf("%s\nFAIL\n", out); return 1; } }
    { unsigned short e2[] = { 0x7777, 0 }; struct cap z = { 4, 23, 2 | 16, "Z" };
      pr(&z, (const unsigned char *)e2, 0);
      if (!strstr(out, "Z: 0 indices captured, min 0 max 0, 0 of 0 triangles degenerate")) { printf("%s\nFAIL\n", out); return 1; } }
    printf("ok\n");
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='madeira-skin-ib-') as directory:
    c = Path(directory) / 'i.c'
    exe = Path(directory) / 'i'
    c.write_text(ib)
    build = subprocess.run([cc, '-std=gnu11', '-Wall', '-Werror', '-Wno-unused-variable', '-fsanitize=address,undefined',
                            '-o', str(exe), str(c)], capture_output=True, text=True)
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True)
    print(run.stdout, end='')
    check('the index summary skips the u16s that are not the draw\'s and counts degenerate triangles', run.returncode == 0)

if fails:
    raise SystemExit('FAILED: %d check(s)' % len(fails))
print('ALL PASS')
