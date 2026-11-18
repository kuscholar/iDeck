#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Match bounded instruction snapshots to exact ARM64 ELF executable segments.

Reports every candidate (up to16), never invents a function from a nearest
exported symbol or treats a non-unique byte pattern as an established base.
No device access, guest payloads, binary patching or runtime changes.
"""
import argparse,hashlib,json,re,struct
from pathlib import Path

def load(path):
    data=path.read_bytes()
    assert data[:6]==b'\x7fELF\x02\x01' and len(data)>=64
    h=struct.unpack_from('<16sHHIQQQIHHHHHH',data)
    assert h[2]==183 and h[9]>=56 and h[5]+h[9]*h[10]<=len(data)
    spans=[]
    for i in range(h[10]):
        kind,flags,off,va,_,size,_,_=struct.unpack_from('<IIQQQQQQ',data,h[5]+i*h[9])
        if kind==1 and flags&1:
            assert off+size<=len(data)
            spans.append((off,va,size))
    return data,spans

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('log',type=Path);p.add_argument('elf',nargs='+',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    assert a.log.stat().st_size<=8*1024*1024 and not a.output.exists()
    assert str(a.output.resolve()).startswith('/Volumes/easystore/')
    modules=[(f.name,*load(f)) for f in a.elf];rows=[];seen=set()
    regex=r'^LINUX_WAIT_CALLER tid=(\d+) frame=([0-7]) lr=(0x[0-9a-f]+) code_start=(0x[0-9a-f]+) words=([0-9a-f,]+)$'
    for line in a.log.read_text().splitlines():
        m=re.fullmatch(regex,line)
        if not m:continue
        tid,frame=int(m[1]),int(m[2]);lr,start=int(m[3],16),int(m[4],16)
        words=tuple(int(x,16) for x in m[5].split(','));assert len(words)==9 and start+16==lr and not lr%4 and lr<1<<48
        key=(tid,frame,lr,words)
        if key in seen:continue
        seen.add(key);assert len(seen)<=128
        pattern=struct.pack('<9I',*words);candidates=[];count=0
        for name,data,spans in modules:
            for off,va,size in spans:
                at=data.find(pattern,off,off+size)
                while at>=0:
                    elfva=va+at-off;count+=1
                    if len(candidates)<16:
                        c={'module':name,'file_offset':hex(at),'ELF_code_start':hex(elfva),'candidate_load_bias':hex(start-elfva),'ELF_callsite':hex(elfva+12)}
                        if words[3]&0xfc000000==0x94000000:
                            imm=words[3]&0x3ffffff
                            if imm&(1<<25):imm-=1<<26
                            c['direct_BL_target_ELFVA']=hex(elfva+12+imm*4)
                        candidates.append(c)
                    at=data.find(pattern,at+1,off+size)
        rows.append({'tid':tid,'frame':frame,'guest_lr':hex(lr),'exact_candidate_count':count,'unique_in_supplied_modules_only':count==1,'candidates':candidates})
    out={'scope':'Exact code bytes in provided ELF executable segments only; no function-name/root-cause/device-success inference','log_SHA256':hashlib.sha256(a.log.read_bytes()).hexdigest(),'modules':{n:hashlib.sha256(d).hexdigest() for n,d,_ in modules},'records':rows}
    with a.output.open('x') as f:json.dump(out,f,indent=2);f.write('\n')
    print('Code-only records',len(rows),'unique within supplied modules',sum(r['unique_in_supplied_modules_only'] for r in rows))
if __name__=='__main__':main()
