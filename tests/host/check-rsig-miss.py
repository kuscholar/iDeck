#!/usr/bin/env python3
"""Which DXIL bindings no root-signature entry covers (rsig-miss); no Metal.

The converter's code 4 (IRErrorCodeResourceNotReferencedByRootSignature) names
no resource. Horizon Zero Dawn (build 469, log 13:57) lost 116 DXIL vertex and
pixel shaders to it. On that failure madeira_d3d12.c now logs, once per shader,
the bindings of the shader's PSV0 part that no root-signature entry visible to
its stage covers, every binding, and the root signature as the runtime read it.
This test cuts the helpers out of madeira_d3d12.c (between the rsig-miss-test
markers, plus rs_rd), compiles them on the host against the real
madeira_ir_abi.h, feeds them DXBC containers with DXIL and PSV0 parts and
checks:
  - the stage comes from the DXIL program header (PS, VS, CS);
  - a CBV in space 6 and an SRV array t0-t3 inside a table range t0-t7, a
    static sampler, a root CBV and root constants are covered;
  - a binding in another space, outside the range, in a range of another kind,
    or behind a parameter visible to another stage is reported, with its
    registers; compute sees every parameter;
  - an unbounded shader array needs an unbounded range;
  - a pipeline with no root signature reports every binding and is described
    as having none; a container without PSV0, or a truncated one, gives -1
    without reading past the end;
  - the description lists tables, root descriptors, constants and samplers;
and in the source: the log runs only for a DXIL conversion that failed with
code 4, before the bytecode dump, and is limited to 24 shaders.
"""
from pathlib import Path
import re, shutil, struct, subprocess, sys, tempfile

root = Path(__file__).resolve().parents[2]
pe = (root / "madeira-d3d12/src/pe/madeira_d3d12.c").read_text()
ok = True


def check(what, cond):
    global ok
    print(("ok   " if cond else "FAIL ") + what)
    ok &= bool(cond)


begin = pe.index("/* rsig-miss-test:begin */")
end = pe.index("/* rsig-miss-test:end */")
block = pe[begin:end]
rd = pe[pe.index("static UINT32 rs_rd(const unsigned char *b, SIZE_T n, SIZE_T off, int *bad) {"):]
rd = rd[:rd.index("\n}\n") + 3]

fail = pe[pe.index('d3d12_log("[madeira-d3d12] %s conversion failed: %s (%s backend, code %u); %llu bytes, head "'):]
fail = fail[:fail.index("free(buf); free(buf2);")]
check("the log runs only for a DXIL conversion that failed with code 4",
      "if (a.ret_backend != MADEIRA_IR_BACKEND_AIRCONV && a.ret_status == MADEIRA_IR_COMPILE_FAILED && a.ret_error_code == 4)\n"
      "            mad_rsig_miss_log(tag, rs, dxil, dxil_len);" in fail)
log = pe[pe.index("static void mad_rsig_miss_log("):]
log = log[:log.index("\n}\n")]
check("once per shader, 24 shaders at most, under a lock",
      "static UINT64 seen[24];" in log and "nseen >= 24" in log and "AcquireSRWLockExclusive(&lock);" in log
      and log.index("seen[nseen++] = h;") < log.index("ReleaseSRWLockExclusive(&lock);\n    want"))

cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
if not cc:
    print("SKIP harness: no C compiler")
else:
    harness = r'''
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint32_t UINT32; typedef unsigned int UINT; typedef uint64_t UINT64; typedef size_t SIZE_T;
#include "madeira_ir_abi.h"
#define MAD_ROOT_PARAM_MAX 32
struct mad_rootsig {
    struct madeira_ir_root_param params[MAD_ROOT_PARAM_MAX];
    struct madeira_ir_root_range *ranges;
    UINT nparams, nranges;
    struct madeira_ir_static_sampler samplers[32];
    UINT nsamplers;
};
''' + rd + block + r'''
static unsigned char blob[4096];
static size_t build(unsigned kind, const uint32_t *res, unsigned nres, int with_psv, int truncate) {
    size_t off = 0, psv_off, dxil_off; unsigned parts = with_psv ? 2 : 1, i;
    memset(blob, 0, sizeof blob);
    memcpy(blob, "DXBC", 4);
    for (i = 0; i < 16; i++) blob[4 + i] = (unsigned char)(0x11 * (i + 1) + kind);
    blob[20] = 1;
    off = 32 + 4 * parts;
    dxil_off = off;
    memcpy(blob + off, "DXIL", 4); *(uint32_t *)(blob + off + 4) = 8;
    *(uint32_t *)(blob + off + 8) = (kind << 16) | 0x60; *(uint32_t *)(blob + off + 12) = 2;
    off += 16;
    psv_off = off;
    if (with_psv) {
        uint32_t body = 4 + 0x34 + 4 + (nres ? 4 + 24 * nres : 0);
        memcpy(blob + off, "PSV0", 4); *(uint32_t *)(blob + off + 4) = truncate ? body - 8 : body;
        off += 8;
        *(uint32_t *)(blob + off) = 0x34; off += 4 + 0x34;
        *(uint32_t *)(blob + off) = nres; off += 4;
        if (nres) { *(uint32_t *)(blob + off) = 24; off += 4; }
        for (i = 0; i < nres; i++, off += 24) memcpy(blob + off, res + 4 * i, 16);
        if (truncate) off -= 8;
    }
    *(uint32_t *)(blob + 24) = (uint32_t)off;
    *(uint32_t *)(blob + 28) = parts;
    *(uint32_t *)(blob + 32) = (uint32_t)dxil_off;
    if (with_psv) *(uint32_t *)(blob + 36) = (uint32_t)psv_off;
    return off;
}
static void param_table(struct mad_rootsig *rs, uint32_t vis, uint32_t first, uint32_t n) {
    struct madeira_ir_root_param *p = &rs->params[rs->nparams++];
    memset(p, 0, sizeof *p); p->type = MADEIRA_IR_PARAM_TABLE; p->visibility = vis; p->first_range = first; p->num_ranges = n;
}
static void param_root(struct mad_rootsig *rs, uint32_t type, uint32_t reg, uint32_t space, uint32_t vis) {
    struct madeira_ir_root_param *p = &rs->params[rs->nparams++];
    memset(p, 0, sizeof *p); p->type = type; p->shader_register = reg; p->register_space = space; p->visibility = vis; p->num_constants = 4;
}
static struct madeira_ir_root_range ranges[8];
static void range(unsigned i, uint32_t type, uint32_t base, uint32_t num, uint32_t space) {
    memset(&ranges[i], 0, sizeof ranges[i]);
    ranges[i].range_type = type; ranges[i].base_register = base; ranges[i].num_descriptors = num; ranges[i].register_space = space;
}
int main(void) {
    struct mad_rootsig rs; const char *stage; char miss[400], all[400], desc[900]; UINT nb; int m; size_t n;
    /* PSV0 kinds: 1 sampler, 2 CBV, 3 SRV typed, 7 UAV raw */
    uint32_t res[] = { 2, 6, 0, 0,   3, 0, 0, 3,   1, 0, 0, 0,   2, 8, 1, 1,   2, 0, 2, 2 };
    memset(&rs, 0, sizeof rs);
    range(0, MADEIRA_IR_RANGE_CBV, 0, 1, 6);
    range(1, MADEIRA_IR_RANGE_SRV, 0, 8, 0);
    range(2, MADEIRA_IR_RANGE_UAV, 0, 4, 0);
    rs.ranges = ranges; rs.nranges = 3;
    param_table(&rs, MADEIRA_IR_VIS_PIXEL, 0, 1);
    param_table(&rs, MADEIRA_IR_VIS_ALL, 1, 2);
    param_root(&rs, MADEIRA_IR_PARAM_CBV, 1, 8, MADEIRA_IR_VIS_ALL);
    param_root(&rs, MADEIRA_IR_PARAM_CONSTANTS, 2, 0, MADEIRA_IR_VIS_PIXEL);
    rs.nsamplers = 1; rs.samplers[0].shader_register = 0; rs.samplers[0].register_space = 0; rs.samplers[0].visibility = MADEIRA_IR_VIS_ALL;

    n = build(0, res, 5, 1, 0);
    { UINT32 v = mad_dxil_stage_vis(blob, n, &stage); printf("stage %u\n", v); printf("name %s\n", stage); }
    m = mad_rsig_miss(&rs, blob, n, MADEIRA_IR_VIS_PIXEL, miss, sizeof miss, all, sizeof all, &nb);
    printf("covered %d %u [%s] [%s]\n", m, nb, miss, all);

    res[5] = 1;                                    /* SRV t0-t3 now in space 1 */
    res[12 + 2] = 3; res[12 + 3] = 3;              /* root CBV now b3: no root CBV there */
    m = mad_rsig_miss(&rs, blob, build(0, res, 5, 1, 0), MADEIRA_IR_VIS_PIXEL, miss, sizeof miss, all, sizeof all, &nb);
    printf("space %d [%s]\n", m, miss);
    res[5] = 0; res[14] = 1; res[15] = 1;

    m = mad_rsig_miss(&rs, blob, build(1, res, 5, 1, 0), MADEIRA_IR_VIS_VERTEX, miss, sizeof miss, all, sizeof all, &nb);
    printf("vis %d [%s]\n", m, miss);
    n = build(5, res, 5, 1, 0);
    { UINT32 v = mad_dxil_stage_vis(blob, n, &stage); printf("cs %u\n", v); printf("csname %s\n", stage); }
    m = mad_rsig_miss(&rs, blob, n, MADEIRA_IR_VIS_ALL, miss, sizeof miss, all, sizeof all, &nb);
    printf("compute %d [%s]\n", m, miss);

    { uint32_t r2[] = { 3, 0, 4, 9,   7, 6, 0, 0,   3, 0, 6, 0xffffffffu };
      m = mad_rsig_miss(&rs, blob, build(0, r2, 3, 1, 0), MADEIRA_IR_VIS_PIXEL, miss, sizeof miss, all, sizeof all, &nb);
      printf("outside %d [%s]\n", m, miss);
      range(1, MADEIRA_IR_RANGE_SRV, 0, 0xffffffffu, 0);
      m = mad_rsig_miss(&rs, blob, build(0, r2, 3, 1, 0), MADEIRA_IR_VIS_PIXEL, miss, sizeof miss, all, sizeof all, &nb);
      printf("unbounded %d [%s]\n", m, miss);
      range(1, MADEIRA_IR_RANGE_SRV, 0, 8, 0); }

    m = mad_rsig_miss(NULL, blob, build(0, res, 5, 1, 0), MADEIRA_IR_VIS_PIXEL, miss, sizeof miss, all, sizeof all, &nb);
    printf("norsig %d %u\n", m, nb);
    mad_rsig_describe(NULL, desc, sizeof desc); printf("descnull [%s]\n", desc);
    m = mad_rsig_miss(&rs, blob, build(0, res, 5, 0, 0), MADEIRA_IR_VIS_PIXEL, miss, sizeof miss, all, sizeof all, &nb);
    printf("nopsv %d\n", m);
    n = build(0, res, 5, 1, 1);
    m = mad_rsig_miss(&rs, blob, n, MADEIRA_IR_VIS_PIXEL, miss, sizeof miss, all, sizeof all, &nb);
    printf("trunc %d\n", m);
    m = mad_rsig_miss(&rs, blob, 40, MADEIRA_IR_VIS_PIXEL, miss, sizeof miss, all, sizeof all, &nb);
    printf("short %d\n", m);
    mad_rsig_describe(&rs, desc, sizeof desc); printf("desc [%s]\n", desc);
    return 0;
}
'''
    with tempfile.TemporaryDirectory() as t:
        c = Path(t) / "h.c"
        c.write_text(harness)
        exe = Path(t) / "h"
        p = subprocess.run([cc, "-std=c11", "-Wall", "-Wno-unused-function", "-fsanitize=address,undefined",
                            "-I", str(root / "madeira-d3d12/src"), str(c), "-o", str(exe)],
                           capture_output=True, text=True)
        if p.returncode != 0:
            p = subprocess.run([cc, "-std=c11", "-Wall", "-Wno-unused-function",
                                "-I", str(root / "madeira-d3d12/src"), str(c), "-o", str(exe)],
                               capture_output=True, text=True)
        check("harness builds", p.returncode == 0)
        if p.returncode != 0:
            print(p.stderr[:3000])
        else:
            r = subprocess.run([str(exe)], capture_output=True, text=True)
            out = r.stdout
            check("harness runs clean", r.returncode == 0 and "runtime error" not in r.stderr)
            if r.returncode != 0 or r.stderr:
                print(r.stderr[:2000])
            lines = dict(l.split(" ", 1) for l in out.strip().split("\n"))
            check("stage from the program header: PS", lines.get("name") == "PS" and lines.get("stage") == "5")
            check("CBV in space 6, SRV array in a range, static sampler, root CBV and root constants are covered",
                  lines.get("covered") == "0 5 [] [CBV b0 space 6, SRV t0-t3 space 0, sampler s0 space 0, CBV b1 space 8, CBV b2 space 0]")
            check("another space and a root CBV at another register are reported",
                  lines.get("space") == "2 [SRV t0-t3 space 1, CBV b3 space 8]")
            check("a parameter visible to PS only does not cover a VS",
                  lines.get("vis") == "2 [CBV b0 space 6, CBV b2 space 0]")
            check("compute sees every parameter", lines.get("cs") == "0" and lines.get("csname") == "CS"
                  and lines.get("compute") == "0 []")
            check("outside the range, a range of another kind and an unbounded array are reported",
                  lines.get("outside") == "3 [SRV t4-t9 space 0, UAV u0 space 6, SRV t6-unbounded space 0]"
                  or print(lines.get("outside")))
            check("an unbounded range covers the unbounded array and t4-t9",
                  lines.get("unbounded") == "1 [UAV u0 space 6]")
            check("no root signature: every binding missing, described as none",
                  lines.get("norsig") == "5 5" and lines.get("descnull") == "[none (the pipeline has no root signature)]")
            check("no PSV0, a truncated PSV0 or a short container give -1",
                  lines.get("nopsv") == "-1" and lines.get("trunc") == "-1" and lines.get("short") == "-1")
            check("the description lists tables, root descriptors, constants and samplers",
                  lines.get("desc") == "[table{CBV b0 space 6} PS; table{SRV t0-t7 space 0, UAV u0-u3 space 0} all; "
                                       "root CBV b1 space 8 all; 4 constants b2 space 0 PS; 1 static sampler(s)]"
                  or print(lines.get("desc")))

print("PASS" if ok else "FAILED")
sys.exit(0 if ok else 1)
