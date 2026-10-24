#!/usr/bin/env python3
"""ml1107: minimal DXBC (SM4/SM5 token stream) disassembler.

  python3 build/tools/dxbc-disasm.py shader.dxbc

Prints the RDEF resource bindings and constant-buffer variables, the input /
output signatures and the SHEX/SHDR instruction stream in fxc-like syntax.
Unknown opcodes are printed as op<N> with their raw operands, so the output is
always complete even when the mnemonic table is not. Written for reading
captured containers (Documents/capture/shader_<name>.dxbc) on the Mac, where
no fxc/vkd3d tool is installed.
"""
import struct, sys

OPS = {0:'add          ',1:'and          ',2:'break        ',3:'breakc       ',4:'call         ',
 5:'callc        ',6:'case         ',7:'continue     ',8:'continuec    ',9:'cut          ',10:'default      ',
 11:'deriv_rtx    ',12:'deriv_rty    ',13:'discard      ',14:'div          ',15:'dp2          ',
 16:'dp3          ',17:'dp4          ',18:'else         ',19:'emit         ',20:'emitthencut  ',
 21:'endif        ',22:'endloop      ',23:'endswitch    ',24:'eq           ',25:'exp          ',
 26:'frc          ',27:'ftoi         ',28:'ftou         ',29:'ge           ',30:'iadd         ',
 31:'if           ',32:'ieq          ',33:'ige          ',34:'ilt          ',35:'imad         ',
 36:'imax         ',37:'imin         ',38:'imul         ',39:'ine          ',40:'ineg         ',
 41:'ishl         ',42:'ishr         ',43:'itof         ',44:'label        ',45:'ld           ',
 46:'ld_ms        ',47:'log          ',48:'loop         ',49:'lt           ',50:'mad          ',
 51:'min          ',52:'max          ',53:'customdata   ',54:'mov          ',55:'movc         ',
 56:'mul          ',57:'ne           ',58:'nop          ',59:'not          ',60:'or           ',
 61:'resinfo      ',62:'ret          ',63:'retc         ',64:'round_ne     ',65:'round_ni     ',
 66:'round_pi     ',67:'round_z      ',68:'rsq          ',69:'sample       ',70:'sample_c     ',
 71:'sample_c_lz  ',72:'sample_l     ',73:'sample_d     ',74:'sample_b     ',75:'sqrt         ',
 76:'switch       ',77:'sincos       ',78:'udiv         ',79:'ult          ',80:'uge          ',
 81:'umul         ',82:'umad         ',83:'umax         ',84:'umin         ',85:'ushr         ',
 86:'utof         ',87:'xor          ',88:'dcl_resource                     ',
 89:'dcl_constantbuffer              ',90:'dcl_sampler                      ',
 91:'dcl_indexrange                  ',92:'dcl_gs_output_primitive_topology ',
 93:'dcl_gs_input_primitive           ',94:'dcl_max_output_vertex_count      ',
 95:'dcl_input                        ',96:'dcl_input_sgv                    ',
 97:'dcl_input_siv                    ',98:'dcl_input_ps                     ',
 99:'dcl_input_ps_sgv                 ',100:'dcl_input_ps_siv                 ',
 101:'dcl_output                       ',102:'dcl_output_sgv                   ',
 103:'dcl_output_siv                   ',104:'dcl_temps                        ',
 105:'dcl_indexable_temp               ',106:'dcl_globalflags                 ',108:'lod',109:'gather4',
 110:'sample_pos',111:'sample_info',113:'hs_decls                         ',
 114:'hs_control_point_phase           ',115:'hs_fork_phase                    ',
 116:'hs_join_phase                    ',117:'emit_stream                      ',
 118:'cut_stream                       ',119:'emitthencut_stream               ',
 120:'interface_call                   ',121:'bufinfo                          ',
 122:'deriv_rtx_coarse                 ',123:'deriv_rtx_fine                   ',
 124:'deriv_rty_coarse                 ',125:'deriv_rty_fine                   ',
 126:'gather4_c                        ',127:'gather4_po                       ',
 128:'gather4_po_c                     ',129:'rcp                              ',
 130:'f32tof16                         ',131:'f16tof32                         ',
 132:'uaddc                            ',133:'usubb                            ',
 134:'countbits                        ',135:'firstbit_hi                      ',
 136:'firstbit_lo                      ',137:'firstbit_shi                     ',
 138:'ubfe                             ',139:'ibfe                             ',
 140:'bfi                              ',141:'bfrev                            ',
 142:'swapc                            ',143:'dcl_stream                       ',
 144:'dcl_function_body                ',145:'dcl_function_table               ',
 146:'dcl_interface                    ',147:'dcl_input_control_point_count    ',
 148:'dcl_output_control_point_count   ',149:'dcl_tess_domain                  ',
 150:'dcl_tess_partitioning            ',151:'dcl_tess_output_primitive        ',
 152:'dcl_hs_max_tessfactor            ',153:'dcl_hs_fork_phase_instance_count ',
 154:'dcl_hs_join_phase_instance_count ',155:'dcl_thread_group                 ',156:'dcl_uav_typed  ',
 157:'dcl_uav_raw    ',158:'dcl_uav_structured',159:'dcl_tgsm_raw',160:'dcl_tgsm_structured',
 161:'dcl_resource_raw                 ',162:'dcl_resource_structured          ',
 163:'ld_uav_typed                     ',164:'store_uav_typed                  ',
 165:'ld_raw                           ',166:'store_raw                        ',
 167:'ld_structured                    ',168:'store_structured                 ',
 169:'atomic_and                       ',170:'atomic_or                        ',
 171:'atomic_xor                       ',172:'atomic_cmp_store                 ',
 173:'atomic_iadd                      ',174:'atomic_imax                      ',
 175:'atomic_imin                      ',176:'atomic_umax                      ',
 177:'atomic_umin                      ',178:'imm_atomic_alloc                 ',
 179:'imm_atomic_consume               ',180:'imm_atomic_iadd                  ',
 181:'imm_atomic_and                   ',182:'imm_atomic_or                    ',
 183:'imm_atomic_xor                   ',184:'imm_atomic_exch                  ',
 185:'imm_atomic_cmp_exch              ',186:'imm_atomic_imax                  ',
 187:'imm_atomic_imin                  ',188:'imm_atomic_umax                  ',
 189:'imm_atomic_umin                  ',190:'sync                             ',
 191:'dadd                             ',192:'dmax                             ',
 193:'dmin                             ',194:'dmul                             ',
 195:'deq                              ',196:'dge                              ',
 197:'dlt                              ',198:'dne                              ',
 199:'dmov                             ',200:'dmovc                            ',
 201:'dtof                             ',202:'ftod                             ',
 203:'eval_snapped                     ',204:'eval_sample_index                ',
 205:'eval_centroid                    ',206:'dcl_gs_instance_count            ',
 207:'abort                            ',208:'debug_break                      ',210:'ddiv',211:'dfma',
 212:'drcp',213:'msad',214:'dtoi',215:'dtou',216:'itod',217:'utod',
 219:'d3dwddm1_3_sb_opcode_gather4_feedback',220:'d3dwddm1_3_sb_opcode_gather4_c_feedback',
 221:'d3dwddm1_3_sb_opcode_gather4_po_feedback',222:'d3dwddm1_3_sb_opcode_gather4_po_c_feedback',
 223:'d3dwddm1_3_sb_opcode_ld_feedback',224:'d3dwddm1_3_sb_opcode_ld_ms_feedback',
 225:'d3dwddm1_3_sb_opcode_ld_uav_typed_feedback',226:'d3dwddm1_3_sb_opcode_ld_raw_feedback',
 227:'d3dwddm1_3_sb_opcode_ld_structured_feedback',228:'d3dwddm1_3_sb_opcode_sample_l_feedback',
 229:'d3dwddm1_3_sb_opcode_sample_c_lz_feedback',230:'d3dwddm1_3_sb_opcode_sample_clamp_feedback',
 231:'d3dwddm1_3_sb_opcode_sample_b_clamp_feedback',232:'d3dwddm1_3_sb_opcode_sample_d_clamp_feedback',
 233:'d3dwddm1_3_sb_opcode_sample_c_clamp_feedback',234:'d3dwddm1_3_sb_opcode_check_access_fully_mapped'}
OPS = {k: v.strip() for k, v in OPS.items()}
NO_OPERANDS_DCL = {104:'dcl_temps',106:'dcl_globalflags',94:'dcl_max_output_vertex_count',152:'dcl_hs_max_tessfactor',
 147:'dcl_input_control_point_count',148:'dcl_output_control_point_count',153:'dcl_hs_fork_phase_instance_count',
 154:'dcl_hs_join_phase_instance_count',206:'dcl_gs_instance_count'}
OPTYPES = {0:'r',1:'v',2:'o',3:'x',4:'l',5:'d',6:'s',7:'t',8:'cb',9:'icb',10:'label',11:'vPrim',12:'null',
 13:'rasterizer',14:'vCoverage',15:'m',16:'fb',17:'ft',18:'fp',19:'fi',20:'fo',21:'vOutputControlPointID',
 22:'vForkInstanceID',23:'vJoinInstanceID',24:'vicp',25:'vocp',26:'vpc',27:'vDomain',28:'u',29:'g',30:'vThreadID',
 31:'vThreadGroupID',32:'vThreadIDInGroup',33:'oMask',34:'vThreadIDInGroupFlattened',35:'vGSInstanceID',
 36:'oDepthGE',37:'oDepthLE',38:'vCycleCounter',39:'oStencilRef',40:'vInnerCoverage'}
DIMS = {0:'unknown',1:'buffer',2:'texture1d',3:'texture2d',4:'texture2dms',5:'texture3d',6:'texturecube',
 7:'texture1darray',8:'texture2darray',9:'texture2dmsarray',10:'texturecubearray',11:'raw_buffer',12:'structured_buffer'}
RET = {1:'unorm',2:'snorm',3:'sint',4:'uint',5:'float',6:'mixed',7:'double',8:'continued',9:'unused'}
INTERP = {0:'',1:'constant',2:'linear',3:'linear centroid',4:'linear noperspective',5:'linear noperspective centroid',
 6:'linear sample',7:'linear noperspective sample'}
SIV = {0:'',1:'position',2:'clip_distance',3:'cull_distance',4:'rendertarget_array_index',5:'viewport_array_index',
 6:'vertex_id',7:'primitive_id',8:'instance_id',9:'is_front_face',10:'sample_index'}

def f32(u): return struct.unpack('<f', struct.pack('<I', u))[0]

class Reader:
    def __init__(self, toks, pos, end): self.t, self.p, self.end = toks, pos, end
    def next(self):
        v = self.t[self.p]; self.p += 1; return v

def read_operand(r):
    tok = r.next()
    ncomp = tok & 3; sel = (tok >> 2) & 3; ty = (tok >> 12) & 0xff; idim = (tok >> 20) & 3
    reps = [(tok >> 22) & 7, (tok >> 25) & 7, (tok >> 28) & 7]
    ext = tok >> 31
    mod = 0
    while ext:
        e = r.next()
        if (e & 0x3f) == 1: mod = (e >> 6) & 0xff
        ext = e >> 31
    if ty == 4:  # imm32
        vals = [r.next() for _ in range(1 if ncomp == 1 else 4)]
        def fmt(v):
            f = f32(v)
            return ('%g' % f) if (abs(f) > 1e-6 and abs(f) < 1e8 or v == 0) else ('0x%08x' % v)
        s = 'l(' + ', '.join(fmt(v) for v in vals) + ')'
    elif ty == 5:
        vals = [r.next() for _ in range(2 if ncomp == 1 else 4)]
        s = 'd(' + ', '.join('0x%08x' % v for v in vals) + ')'
    else:
        idx = []
        for i in range(idim):
            rep = reps[i]
            if rep == 0: idx.append(str(r.next()))
            elif rep == 1: lo = r.next(); hi = r.next(); idx.append(str(lo | (hi << 32)))
            elif rep == 2: idx.append(read_operand(r))
            elif rep == 3: imm = r.next(); idx.append('%d + %s' % (imm, read_operand(r)))
            elif rep == 4: lo = r.next(); hi = r.next(); idx.append('%d + %s' % (lo | (hi << 32), read_operand(r)))
        name = OPTYPES.get(ty, 'op%d' % ty)
        if ty in (8, 3, 9, 24, 25, 26) and len(idx) >= 2:
            s = '%s%s[%s]' % (name, idx[0], idx[1]) if ty == 8 else '%s%s[%s]' % (name, idx[0], idx[1])
            if len(idx) > 2: s = '%s%s[%s][%s]' % (name, idx[0], idx[1], idx[2])
        elif idx:
            s = name + idx[0] + ''.join('[%s]' % x for x in idx[1:])
        else:
            s = name
        comps = 'xyzw'
        if ncomp == 2:
            if sel == 0:
                m = (tok >> 4) & 0xf
                sw = ''.join(comps[i] for i in range(4) if m & (1 << i))
                if sw != 'xyzw' and sw: s += '.' + sw
            elif sel == 1:
                sw = ''.join(comps[(tok >> (4 + 2 * i)) & 3] for i in range(4))
                if sw != 'xyzw': s += '.' + sw
            elif sel == 2:
                s += '.' + comps[(tok >> 4) & 3]
    if mod == 1: s = '-' + s
    elif mod == 2: s = '|' + s + '|'
    elif mod == 3: s = '-|' + s + '|'
    return s

def disasm_shex(data):
    toks = struct.unpack('<%dI' % (len(data) // 4), data)
    ver = toks[0]; ptype = ver >> 16; major = (ver >> 4) & 0xf; minor = ver & 0xf
    out = ['%s_%d_%d' % ({0:'ps',1:'vs',2:'gs',3:'hs',4:'ds',5:'cs'}.get(ptype, 'st%d' % ptype), major, minor)]
    n = toks[1]
    r = Reader(toks, 2, n)
    indent = 0
    while r.p < n:
        start = r.p
        tok = r.next()
        op = tok & 0x7ff
        length = (tok >> 24) & 0x7f
        if op == 53:  # customdata
            cls = (tok >> 11) & 0x1ffff
            length = r.next()
            body = toks[start + 2:start + length]
            if cls == 0:
                out.append('dcl_immediateConstantBuffer { %d x float4 }' % (len(body) // 4))
                for i in range(0, len(body), 4):
                    out.append('    { ' + ', '.join('%g' % f32(v) for v in body[i:i + 4]) + ' },')
            else:
                out.append('customdata class %d, %d dwords' % (cls, len(body)))
            r.p = start + length
            continue
        name = OPS.get(op, 'op%d' % op)
        end = start + length
        ext = tok >> 31
        exts = []
        while ext:
            e = r.next()
            et = e & 0x3f
            if et == 1:
                def s4(v): return v - 16 if v & 8 else v
                exts.append('aoffimmi(%d,%d,%d)' % (s4((e >> 9) & 0xf), s4((e >> 13) & 0xf), s4((e >> 17) & 0xf)))
            elif et == 2: exts.append('dim=%s stride=%d' % (DIMS.get((e >> 6) & 0x1f, '?'), (e >> 11) & 0xfff))
            elif et == 3: exts.append('ret=(%s,%s,%s,%s)' % tuple(RET.get((e >> (6 + 4 * i)) & 0xf, '?') for i in range(4)))
            ext = e >> 31
        sat = (tok >> 13) & 1
        line = name
        if op in (31, 3, 8, 63, 13):  # if/breakc/continuec/retc/discard test
            line += '_nz' if (tok >> 18) & 1 else '_z'
        if sat: line += '_sat'
        ops = []
        if op in NO_OPERANDS_DCL:
            ops.append(str(r.next()) if r.p < end else '')
            if op == 106:
                fl = (tok >> 11) & 0x1fff
                ops = [', '.join(f for b, f in ((1,'refactoringAllowed'),(2,'enableDoublePrecision'),(4,'forceEarlyDepthStencil'),
                       (8,'enableRawAndStructuredBuffers'),(16,'skipOptimization'),(32,'enableMinPrecision'),
                       (64,'enable11_1DoubleExtensions'),(128,'enable11_1ShaderExtensions')) if fl & b)]
        elif op == 88:  # dcl_resource
            dim = (tok >> 11) & 0x1f
            ops.append(read_operand(r)); ret = r.next()
            line = 'dcl_resource_%s (%s)' % (DIMS.get(dim, '?'), ','.join(RET.get((ret >> (4 * i)) & 0xf, '?') for i in range(4)))
        elif op == 89:
            ops.append(read_operand(r)); line += ', dynamicIndexed' if (tok >> 11) & 1 else ', immediateIndexed'
        elif op == 90:
            ops.append(read_operand(r)); line += ', mode_comparison' if (tok >> 11) & 0xf == 1 else ', mode_default'
        elif op in (98, 100, 99):
            line += ' ' + INTERP.get((tok >> 11) & 0xf, '')
            ops.append(read_operand(r))
            if op in (100, 99, 97, 96, 102, 103): ops.append(SIV.get(r.next(), '?'))
        elif op in (97, 96, 102, 103):
            ops.append(read_operand(r)); ops.append(SIV.get(r.next(), '?'))
        elif op in (162, 158, 160):
            ops.append(read_operand(r)); ops.append('stride %d' % r.next())
            if op == 160: ops.append('count %d' % r.next())
        elif op == 156:
            dim = (tok >> 11) & 0x1f
            ops.append(read_operand(r)); ret = r.next()
            line = 'dcl_uav_typed_%s (%s)' % (DIMS.get(dim, '?'), ','.join(RET.get((ret >> (4 * i)) & 0xf, '?') for i in range(4)))
        elif op == 105:
            ops = ['x%d[%d], %d' % (r.next(), r.next(), r.next())]
        elif op == 155:
            ops = ['%d, %d, %d' % (r.next(), r.next(), r.next())]
        elif op == 159:
            ops.append(read_operand(r)); ops.append('%d bytes' % r.next())
        else:
            while r.p < end:
                ops.append(read_operand(r))
        if op in (18, 21, 22, 23): indent = max(0, indent - 1)
        out.append('    ' * indent + line + (' ' + ', '.join(ops) if ops else '') + (' [%s]' % ' '.join(exts) if exts else ''))
        if op in (31, 48, 76, 18): indent += 1
        r.p = end
    return out

def cstr(data, off):
    e = data.index(b'\0', off); return data[off:e].decode('ascii', 'replace')

def dump_rdef(d):
    out = []
    ncb, cboff, nrb, rboff, ver, ptype, flags, creator = struct.unpack_from('<8I', d, 0)
    major = (ver >> 8) & 0xff; minor = ver & 0xff
    is51 = major == 5 and minor == 1
    out.append('RDEF: shader model %d.%d, %d constant buffers, %d resource bindings, creator "%s"' % (major, minor, ncb, nrb, cstr(d, creator)))
    RTYPE = {0:'cbuffer',1:'tbuffer',2:'texture',3:'sampler',4:'uav_rwtyped',5:'structured',6:'uav_rwstructured',
             7:'byteaddress',8:'uav_rwbyteaddress',9:'uav_append',10:'uav_consume',11:'uav_rwstructured_counter'}
    for i in range(nrb):
        sz = 40 if is51 else 32
        f = struct.unpack_from('<%dI' % (sz // 4), d, rboff + i * sz)
        extra = ' space%d' % f[8] if is51 else ''
        out.append('  %-8s %-24s ret=%s dim=%s bind=%d count=%d flags=0x%x%s' % (RTYPE.get(f[1], 't%d' % f[1]), cstr(d, f[0]),
                   RET.get(f[2], str(f[2])), DIMS.get(f[3], str(f[3])), f[5], f[6], f[7], extra))
    for i in range(ncb):
        name, nvar, varoff, size, cflags, ctype = struct.unpack_from('<6I', d, cboff + i * 24)
        out.append('  cbuffer %s (%d bytes, %d vars)' % (cstr(d, name), size, nvar))
        vsz = 40 if major >= 5 else 24
        for j in range(nvar):
            vn, voff, vsize, vflags, vtype, vdef = struct.unpack_from('<6I', d, varoff + j * vsz)
            cls, ty, rows, cols, elems, members, moff = struct.unpack_from('<4H2HI', d, vtype)
            out.append('      +%-5d %-32s %dx%d%s %s bytes%s' % (voff, cstr(d, vn), rows, cols, ('[%d]' % elems) if elems else '', vsize, '' if vflags & 2 else ' (unused)'))
    return out

def dump_sig(tag, d):
    n, off = struct.unpack_from('<2I', d, 0)
    out = ['%s: %d elements' % (tag, n)]
    for i in range(n):
        name, idx, sv, ct, reg, mask, rw = struct.unpack_from('<5I2B', d, off + i * 24)
        out.append('  %-16s%d  reg=%d mask=%x used=%x sv=%d type=%d' % (cstr(d, name), idx, reg, mask, rw, sv, ct))
    return out

def main():
    data = open(sys.argv[1], 'rb').read()
    assert data[:4] == b'DXBC', 'not a DXBC container'
    nchunks = struct.unpack_from('<I', data, 28)[0]
    offs = struct.unpack_from('<%dI' % nchunks, data, 32)
    for o in offs:
        tag = data[o:o + 4].decode('ascii', 'replace'); size = struct.unpack_from('<I', data, o + 4)[0]
        body = data[o + 8:o + 8 + size]
        if tag == 'RDEF': print('\n'.join(dump_rdef(body)))
        elif tag in ('ISGN', 'OSGN', 'PCSG', 'ISG1', 'OSG1'): print('\n'.join(dump_sig(tag, body)))
        elif tag in ('SHEX', 'SHDR'): print('\n'.join(disasm_shex(body)))
        else: print('%s: %d bytes' % (tag, size))

if __name__ == '__main__':
    main()
