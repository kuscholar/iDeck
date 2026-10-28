#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Read-only CEF126 ARM64 public ABI inventory. Never loads/executes client code.
Recognizes the exact simple literal-table getter shape; rejects unknown code or
pointer encodings. No compatibility hash is modified, bypassed or fabricated.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

class MachO:
    def __init__(self, data):
        self.data=data;self.segments=[]
        if len(data)<32 or struct.unpack_from('<II',data)!=(0xfeedfacf,0x100000c):
            raise ValueError('Expected thin little-endian ARM64 Mach-O')
        count,commands=struct.unpack_from('<II',data,16)
        if commands>len(data)-32 or count>commands//8:raise ValueError('Invalid load-command bounds')
        offset=32
        for _ in range(count):
            if offset+8>32+commands:raise ValueError('Truncated load command')
            command,size=struct.unpack_from('<II',data,offset)
            if size<8 or offset+size>32+commands:raise ValueError('Invalid load command size')
            if command==0x19:
                if size<72:raise ValueError('Truncated segment')
                va,virtual,fo,fs=struct.unpack_from('<QQQQ',data,offset+24)
                if fs>virtual or fo+fs>len(data):raise ValueError('Invalid segment file bounds')
                self.segments.append((va,fo,fs))
            offset+=size
        if offset!=32+commands:raise ValueError('Load command count/size mismatch')
    def read(self,address,size):
        matches=[fo+address-va for va,fo,fs in self.segments if va<=address and size>=0 and address+size<=va+fs]
        if len(matches)!=1:raise ValueError('Unbacked or ambiguous virtual address')
        return self.data[matches[0]:matches[0]+size]

def table_address(image, address, maximum, stride):
    code=struct.unpack('<8I',image.read(address,32))
    expected_prefix=(0x7100001f | maximum<<10,0x54000069,0x52800000 if stride==4 else 0xd2800000,0xd65f03c0)
    if code[:4]!=expected_prefix or code[6]!=(0xb860d900 if stride==4 else 0xf860d900) or code[7]!=0xd65f03c0:
        raise ValueError('Unsupported public getter instruction shape')
    adrp,add=code[4:6]
    if adrp&0x9f00001f!=0x90000008 or add&0xffc003ff!=0x91000108:
        raise ValueError('Unsupported public getter table addressing')
    delta=((adrp>>29)&3)|(((adrp>>5)&0x7ffff)<<2)
    if delta&(1<<20):delta-=1<<21
    return ((address+16)&~4095)+(delta<<12)+((add>>10)&0xfff)

def extract_public_metadata(image, version_address, api_address):
    version=struct.unpack('<8I',image.read(table_address(image,version_address,7,4),32))
    if version[0]!=126:raise ValueError('Only audited CEF126 getters supported')
    pointers=struct.unpack('<3Q',image.read(table_address(image,api_address,2,8),24))
    hashes=[]
    for pointer in pointers:
        text=image.read(pointer,41)
        if not re.fullmatch(b'[a-f0-9]{40}\x00',text):raise ValueError('Unknown API hash pointer/string encoding')
        hashes.append(text[:-1].decode())
    return dict(zip(['cefMajor','cefMinor','cefPatch','cefCommitNumber','chromeMajor','chromeMinor','chromeBuild','chromePatch'],version)),dict(zip(['platform','universal','cefCommit'],hashes))

def exports(path):
    text=subprocess.check_output(['xcrun','llvm-nm','-g',str(path)],text=True)
    return {name:int(address,16) for address,name in re.findall(r'^([0-9a-fA-F]+) [Tt] _(cef_[A-Za-z0-9_]+)$',text,re.M)}

def write_report(path, report):
    if path.is_symlink():raise ValueError('Preserve symlink output; choose a new report path')
    if path.exists():
        try:previous=json.loads(path.read_text())
        except (ValueError,UnicodeError):raise ValueError('Preserve existing non-report output')
        if not isinstance(previous,dict) or previous.get('mode')!='static read-only; CEF not initialized':
            raise ValueError('Preserve existing unrelated output')
    path.write_text(json.dumps(report,indent=2)+'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cef',type=Path,required=True);p.add_argument('--helper',type=Path,required=True)
    p.add_argument('--upstream',type=Path,required=True,help='Pinned upstream source containing include/ and libcef_dll/')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    for protected in [a.cef,a.helper,a.upstream/'include/cef_api_hash.h',a.upstream/'libcef_dll/wrapper/libcef_dll_dylib.cc']:
        if a.output.resolve()==protected.resolve() or (a.output.exists() and a.output.samefile(protected)):
            raise ValueError('Report must never overwrite audited input')
    data=a.cef.read_bytes();symbols=exports(a.cef)
    version,public=extract_public_metadata(MachO(data),symbols['cef_version_info'],symbols['cef_api_hash'])
    header=(a.upstream/'include/cef_api_hash.h').read_text()
    universal=re.search(r'#define CEF_API_HASH_UNIVERSAL "([a-f0-9]{40})"',header).group(1)
    mac=re.search(r'#elif defined\(OS_MAC\)\s+#define CEF_API_HASH_PLATFORM "([a-f0-9]{40})"',header).group(1)
    loader=(a.upstream/'libcef_dll/wrapper/libcef_dll_dylib.cc').read_text()
    upstream=set(re.findall(r'INIT_ENTRY\((cef_[A-Za-z0-9_]+)\)',loader))
    helper=set(exports(a.helper));framework=set(symbols)
    result={'mode':'static read-only; CEF not initialized','cefSHA256':hashlib.sha256(data).hexdigest(),
        'version':version,'publicABIIdentifiers':public,
        'upstreamHeaderSHA256':hashlib.sha256(header.encode()).hexdigest(),
        'upstreamPlatformHash':mac,'upstreamUniversalHash':universal,
        'platformHashMatches':public['platform']==mac,'universalHashMatches':public['universal']==universal,
        'helperAndFrameworkCEFSymbolsNotInUpstreamLoader':sorted((helper&framework)-upstream),
        'limits':['Symbol differences are candidate extensions, not proof every symbol is mandatory.',
                  'Matching hashes/symbols alone would not prove full runtime or struct ABI compatibility.',
                  'Never override cef_api_hash or suppress a compatibility check to use a mismatched build.']}
    write_report(a.output,result)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
