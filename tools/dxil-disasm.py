#!/usr/bin/env python3
"""Disassemble a DXIL shader (a DXBC container with a DXIL part) to LLVM IR.

Used to read the Ghost of Tsushima kernel that hung the GPU: madeira_d3d12
logs a faulting compute shader's bytecode as base64 at the next launch
("[b64 <hash>] ..." lines, see GPU fault attribution in madeira_d3d12.c).

  grep -a "^\[b64 <hash>\]" log.txt | sed 's/^\[b64 [0-9a-f]*\] //' | tr -d '\n' | base64 -d > s.dxil
  pip install llvmlite
  python3 tools/dxil-disasm.py s.dxil > s.ll

DXIL is LLVM 3.7 bitcode; current LLVM reads it except for the data layout
("i8:32" is rejected: "i8 must be 8-bit aligned"). The bitstream is walked to
the MODULE_CODE_DATALAYOUT record and "i8:32"/"i16:32" are rewritten in place
to same-width values ("i8:08", "i16:16"), so no other bit moves.
"""
import struct, sys


def bitcode_of(container):
    assert container[:4] == b'DXBC', 'not a DXBC container'
    n = struct.unpack('<I', container[28:32])[0]
    for o in struct.unpack('<%dI' % n, container[32:32 + 4 * n]):
        if container[o:o + 4] in (b'DXIL', b'ILDB'):
            p = o + 8
            _ver, _size, magic, _dver, boff, bsize = struct.unpack('<IIIIII', container[p:p + 24])
            assert magic == 0x4c495844
            return bytearray(container[p + 8 + boff:p + 8 + boff + bsize])
    raise SystemExit('no DXIL part')


def fix_datalayout(data):
    class R:
        def __init__(s,d): s.d=d; s.pos=0
        def read(s,n):
            v=0
            for i in range(n):
                b=(s.d[(s.pos)>>3]>>((s.pos)&7))&1; v|=b<<i; s.pos+=1
            return v
        def vbr(s,n):
            v=0; sh=0
            while True:
                x=s.read(n); v|=(x&((1<<(n-1))-1))<<sh; sh+=n-1
                if not (x>>(n-1)): return v
        def align32(s): s.pos=(s.pos+31)&~31
    r=R(data); assert r.read(8)==0x42 and r.read(8)==0x43
    r.read(16)
    blockinfo={}
    found=[]
    def read_abbrev_def(r):
        n=r.vbr(5); ops=[]; i=0
        while i<n:
            lit=r.read(1)
            if lit: ops.append(('lit',r.vbr(8)))
            else:
                e=r.read(3)
                if e in (1,2): ops.append((e,r.vbr(5)))
                else: ops.append((e,None))
            i+=1
        return ops
    def read_scalar(r,op):
        k,v=op
        if k=='lit': return v
        if k==1: return r.read(v)
        if k==2: return r.vbr(v)
        if k==4: 
            x=r.read(6); return ord("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._"[x])
        raise Exception('bad op %r'%(op,))
    def read_abbrev_record(r,ops):
        vals=[]; i=0; positions=[]
        while i<len(ops):
            k,v=ops[i]
            if k==3:  # array
                n=r.vbr(6); el=ops[i+1]
                for _ in range(n):
                    positions.append((r.pos,el)); vals.append(read_scalar(r,el))
                i+=2; continue
            if k==5:  # blob
                n=r.vbr(6); r.align32(); positions.append((r.pos,'blob',n)); vals.append(bytes(r.d[r.pos>>3:(r.pos>>3)+n])); r.pos+=n*8; r.align32(); i+=1; continue
            positions.append((r.pos,ops[i])); vals.append(read_scalar(r,ops[i])); i+=1
        return vals,positions
    def parse_block(r,width,bid,depth):
        abbrevs=list(blockinfo.get(bid,[]))
        cur_bi=None
        while r.pos+width <= len(r.d)*8:
            a=r.read(width)
            if a==0: r.align32(); return
            if a==1:
                nb=r.vbr(8); nw=r.vbr(4); r.align32(); ln=r.read(32)
                if nb==0 or nb==8:   # blockinfo, module
                    parse_block(r,nw,nb,depth+1)
                else: r.pos+=ln*32
                continue
            if a==2:
                ops=read_abbrev_def(r)
                if bid==0: blockinfo.setdefault(cur_bi,[]).append(ops)
                else: abbrevs.append(ops)
                continue
            if a==3:
                code=r.vbr(6); n=r.vbr(6); pos=[]; vals=[]
                for _ in range(n): pos.append((r.pos,(2,6))); vals.append(r.vbr(6))
            else:
                ops=abbrevs[a-4]; vals,pos=read_abbrev_record(r,ops); code=vals[0]; vals=vals[1:]; pos=pos[1:]
            if bid==0 and code==1: cur_bi=vals[0]
            if bid==8 and code==3:
                s=''.join(chr(c) for c in vals); found.append((s,pos))
    parse_block(r,2,-1,0)

    for s,pos in found:
        print("datalayout:", s, file=sys.stderr)
        fixes={'i8:32':'i8:08','i16:32':'i16:16'}
        for old,new in fixes.items():
            i=s.find(old)
            if i<0: continue
            for j,(a,b) in enumerate(zip(old,new)):
                if a==b: continue
                p,op=pos[i+j]
                k,w=op
                val=ord(b)
                if k==2:  # vbr(w): same number of chunks
                    def enc(v):
                        out=[]; 
                        while True:
                            c=v&((1<<(w-1))-1); v>>=(w-1)
                            if v: out.append(c|(1<<(w-1)))
                            else: out.append(c); return out
                    ea,eb=enc(ord(a)),enc(val); assert len(ea)==len(eb)
                    val=0
                    for ci,c in enumerate(eb): val|=c<<(ci*w)
                    bits=w*len(eb)
                elif k==1: bits=w
                else: raise SystemExit('unsupported enc %r'%(op,))
                for t in range(bits):
                    bit=(val>>t)&1; byte=(p+t)>>3; sh=(p+t)&7
                    data[byte]=(data[byte]&~(1<<sh))|(bit<<sh)
    return data


def main():
    import llvmlite.binding as llvm
    blob = open(sys.argv[1], 'rb').read()
    bc = fix_datalayout(bitcode_of(blob)) if blob[:4] == b'DXBC' else fix_datalayout(bytearray(blob))
    print(str(llvm.parse_bitcode(bytes(bc))))


if __name__ == '__main__':
    main()
