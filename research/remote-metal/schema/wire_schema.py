#!/usr/bin/env python3
"""Single source of truth for the remote Metal command wire format.

Generates the record layouts, size/alignment assertions, the guest packer and
the host decoder from one description, because hand-maintaining a wire format
on both sides of a machine boundary drifts -- and drift in a wire format shows
up as corruption at runtime rather than as a compile error.

Started as the 15 render opcodes an ARM64 D3D11 cube emits (measured:
28,800 records over 12,288 batches, zero compute, zero blit. Unobserved
opcodes are deliberately absent; adding one is a new record type, never an ABI
change.

⚠️ The cube's observed maxima are NOT baked in. It used at most 12 bytes of
inline setBytes data, exactly one viewport and exactly one scissor -- but
sidecars stay `offset + length` and arrays stay `offset + count`, so a heavier
title needs new opcode implementations rather than a redesigned ABI.
"""

WIRE_VERSION = 2

# Negotiated ceilings. Generous against the cube's measurements (18 records,
# 12 sidecar bytes) but bounded, so a hostile or corrupt batch cannot make the
# decoder allocate or loop without limit.
LIMITS = dict(
    # ml817: raised from 1MB / 4096 / 64KB. Those were sized against a cube
    # (18 records per batch). A UE4 base pass exceeded 4096 records in one
    # batch and the WHOLE batch was dropped -- every draw in it -- which is
    # what "no graphics" looked like in the first in-game log.
    MAX_BATCH_BYTES   = 8 << 20,
    MAX_RECORDS       = 65536,
    MAX_SIDECAR_BYTES = 1 << 20,
    MAX_ARRAY_COUNT   = 256,
)

U8, U16, U32, U64, F32, F64 = 'u8', 'u16', 'u32', 'u64', 'f32', 'f64'
CTYPE = {U8:'uint8_t', U16:'uint16_t', U32:'uint32_t', U64:'uint64_t',
         F32:'float', F64:'double'}
CSIZE = {U8:1, U16:2, U32:4, U64:8, F32:4, F64:8}

# (opcode, name, [(field, type)], sidecar?)
# Fields are ordered largest-first so every record is naturally aligned with
# no implicit padding -- explicit tail padding is added where needed.
RECORDS = [
    ( 0, 'Nop',                        [], None),
    ( 1, 'UseResource',                [('resource',U64),('usage',U64),('stages',U64)], None),
    ( 2, 'SetVertexBuffer',            [('buffer',U64),('offset',U64),('index',U64)], None),
    ( 3, 'SetVertexBufferOffset',      [('offset',U64),('index',U64)], None),
    ( 4, 'SetFragmentBuffer',          [('buffer',U64),('offset',U64),('index',U64)], None),
    (10, 'SetFragmentTexture',         [('texture',U64),('index',U64)], None),
    (11, 'SetFragmentBytes',           [('index',U64)], 'bytes'),
    (12, 'SetRasterizerState',         [('front_facing',U32),('cull_mode',U32),
                                        ('fill_mode',U32),('depth_clip_mode',U32),
                                        ('depth_bias',F32),('slope_scale',F32),
                                        ('depth_bias_clamp',F32),('pad0',U32)], None),
    (13, 'SetViewports',               [], 'viewports'),
    (14, 'SetScissorRects',            [], 'scissors'),
    (15, 'SetPSO',                     [('pso',U64)], None),
    (16, 'SetDSSO',                    [('dsso',U64),('stencil_ref',U32),('pad0',U32)], None),
    (17, 'SetBlendFactorAndStencilRef',[('r',F32),('g',F32),('b',F32),('a',F32),
                                        ('stencil_ref',U32),('pad0',U32)], None),
    (19, 'Draw',                       [('primitive',U64),('start',U64),('count',U64),
                                        ('instances',U64),('base_instance',U64)], None),
    (20, 'DrawIndexed',                [('primitive',U64),('index_count',U64),
                                        ('index_type',U64),('index_buffer',U64),
                                        ('index_offset',U64),('instances',U64),
                                        ('base_vertex',U64),('base_instance',U64)], None),
    # --- ml7xx: added by hand in the header while the schema went stale. Now
    # carried here so regeneration cannot silently drop them again. ---
    (21, 'SetFragmentBufferOffset',    [('offset',U64),('index',U64)], None),
    (22, 'SetObjectBufferOffset',      [('offset',U64),('index',U64)], None),
    (23, 'SetVisibilityMode',          [('offset',U64),('mode',U32),('pad',U32)], None),
    (24, 'DrawIndexedIndirect',        [('index_buffer',U64),('index_buffer_offset',U64),
                                        ('indirect_args_buffer',U64),('indirect_args_offset',U64),
                                        ('primitive_type',U32),('index_type',U32)], None),
    (25, 'SetMeshBuffer',              [('buffer',U64),('offset',U64),('index',U64)], None),
    (26, 'SetMeshBufferOffset',        [('offset',U64),('index',U64)], None),
    (27, 'SetObjectBuffer',            [('buffer',U64),('offset',U64),('index',U64)], None),
    (28, 'DrawMeshThreadgroups',       [('grid_w',U32),('grid_h',U32),('grid_d',U32),
                                        ('obj_w',U32),('obj_h',U32),('obj_d',U32),
                                        ('mesh_w',U32),('mesh_h',U32),('mesh_d',U32),
                                        ('pad',U32)], None),
    # --- ml817: the draw families a UE4 title actually uses. DXMT's geometry-
    # shader and tessellation emulation are mesh draws and pack as
    # SetObjectBuffer(Offset) + DrawMeshThreadgroups; only the INDIRECT mesh
    # dispatch, plain indirect draw and the render-stage barrier needed new
    # record types. Wire opcode numbers are ours (winemetal's 29+ are its
    # composite commands, which never cross the wire). ---
    (29, 'DrawMeshThreadgroupsIndirect',[('indirect_buffer',U64),('indirect_offset',U64),
                                        ('obj_w',U32),('obj_h',U32),('obj_d',U32),
                                        ('mesh_w',U32),('mesh_h',U32),('mesh_d',U32)], None),
    (30, 'MemoryBarrier',              [('scope',U32),('stages_after',U32),
                                        ('stages_before',U32),('pad0',U32)], None),
    (31, 'DrawIndirect',               [('indirect_buffer',U64),('indirect_offset',U64),
                                        ('primitive',U32),('pad0',U32)], None),
]

# Sidecar element shapes: variable-count arrays referenced by offset + count.
SIDECARS = dict(
    bytes     = ('uint8_t',        1),
    viewports = ('struct wmtw_viewport', 48),
    scissors  = ('struct wmtw_scissor',  32),
)

HDR = """/* GENERATED by schema/wire_schema.py -- do not edit by hand.
 *
 * Wire format for forwarding winemetal render commands across a machine
 * boundary. Regenerate with:  python3 schema/wire_schema.py
 */
#ifndef WMT_WIRE_H
#define WMT_WIRE_H
#include <stdint.h>
#include <string.h>

#define WMTW_VERSION %d
""" % WIRE_VERSION


def gen_header():
    o = [HDR]
    for k, v in LIMITS.items():
        o.append("#define WMTW_%s %du" % (k, v))
    o.append("""
/* Static assertions fire at compile time on BOTH sides, so a layout change
 * that only one side picked up cannot reach the wire. Token-pasting the
 * expression into an identifier does not work -- use _Static_assert. */
#if defined(__cplusplus)
#  define WMTW_ASSERT(c, m) static_assert(c, m)
#else
#  define WMTW_ASSERT(c, m) _Static_assert(c, m)
#endif

enum wmtw_op {""")
    for op, name, _, _ in RECORDS:
        o.append("    WMTW_OP_%-28s = %d," % (name, op))
    o.append("    /* one past the highest opcode -- NOT the number of record types,")
    o.append("       since opcodes are sparse (winemetal's numbering is preserved) */")
    o.append("    WMTW_OP__MAX")
    o.append("};")
    o.append("#define WMTW_OP_COUNT %d   /* record types actually implemented */\n" % len(RECORDS))
    o.append("""/* Every record starts with this. `size` covers the header and body but NOT
 * sidecar data, which lives in a separate region addressed by offset -- so a
 * decoder can walk the stream without understanding any record it does not
 * implement. */
struct wmtw_hdr { uint16_t op; uint16_t version; uint32_t size; };

struct wmtw_viewport { double x, y, width, height, znear, zfar; };
struct wmtw_scissor  { uint64_t x, y, width, height; };

/* Batch prologue. Sidecar data follows the record stream. */
struct wmtw_batch {
    uint32_t magic;          /* 'WMTB' */
    uint16_t version;
    uint16_t encoder_kind;   /* 0 render, 1 compute, 2 blit */
    uint32_t record_bytes;
    uint32_t record_count;
    uint32_t sidecar_bytes;
    uint32_t reserved;
};
#define WMTW_BATCH_MAGIC 0x42544D57u
""")
    for op, name, fields, side in RECORDS:
        o.append("struct wmtw_%s {" % name.lower())
        o.append("    struct wmtw_hdr h;")
        for f, t in fields:
            o.append("    %-9s %s;" % (CTYPE[t], f))
        if side:
            o.append("    uint32_t %s_offset;   /* into the sidecar region */" % side)
            o.append("    uint32_t %s_count;    /* elements, not bytes */" % side)
        o.append("};")
        # size assertion
        sz = 8 + sum(CSIZE[t] for _, t in fields) + (8 if side else 0)
        o.append('WMTW_ASSERT(sizeof(struct wmtw_%s) == %d, "wmtw_%s layout changed on one side only");'
                 % (name.lower(), sz, name.lower()))
        o.append("")
    o.append("#endif")
    return "\n".join(o)


if __name__ == '__main__':
    import os, sys
    out = os.path.join(os.path.dirname(__file__), '..', 'wmt_wire.h')
    open(out, 'w').write(gen_header() + "\n")
    print("wrote", os.path.normpath(out))
    print("records: %d   version: %d" % (len(RECORDS), WIRE_VERSION))
