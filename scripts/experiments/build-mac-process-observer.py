#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Stage an exact-version, read-only CreateSimpleProcess observer in a private copy.
Only dependency load commands change in client consumers. Instruction bytes and
original tier0 remain unchanged. No signing, device operations or authentication.
Any failure must stop the outer signing/deployment pipeline.
"""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import struct
import subprocess
import tempfile
REPO=Path(__file__).resolve().parents[2]
OWN=REPO/'experiments/mac-arm-steam'
TIER0_SHA='9647d38d088833c31aa685d5e558932f2c582125871bdf1157d257fac1f80b06'
PROXY='@rpath/libShim_Tier0.dylib'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def inspect(path):
    b=path.read_bytes()
    if b[:8]!=struct.pack('<II',0xfeedfacf,0x100000c):return None
    n,size=struct.unpack_from('<II',b,16);end=32+size;off=32;texts=[];deps=[]
    if end>len(b) or n>size//8:raise ValueError('Invalid Mach-O commands')
    for _ in range(n):
        if off+8>end:raise ValueError('Truncated command')
        cmd,cs=struct.unpack_from('<II',b,off)
        if cs<8 or off+cs>end:raise ValueError('Invalid command')
        if cmd in (0xc,0x80000018,0x8000001f,0x80000023):
            if cs<24:raise ValueError('Short dylib command')
            pos=struct.unpack_from('<I',b,off+8)[0]
            if pos<24 or pos>=cs:raise ValueError('Invalid dependency offset')
            name=b[off+pos:off+cs].split(b'\0',1)[0].decode()
            deps.append(name)
        if cmd==0x19:
            if cs<72:raise ValueError('Short segment')
            ns=struct.unpack_from('<I',b,off+64)[0]
            if 72+80*ns>cs:raise ValueError('Invalid sections')
            for j in range(ns):
                p=off+72+80*j
                if b[p:p+16].rstrip(b'\0')==b'__text' and b[p+16:p+32].rstrip(b'\0')==b'__TEXT':
                    length=struct.unpack_from('<Q',b,p+40)[0];fo=struct.unpack_from('<I',b,p+48)[0]
                    if fo+length>len(b):raise ValueError('Invalid text bounds')
                    texts.append(hashlib.sha256(b[fo:fo+length]).hexdigest())
        off+=cs
    if off!=end or len(texts)!=1:raise ValueError('Expected exactly one text section')
    return {'textSha256':texts[0],'dependencies':deps}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--converted',type=Path,required=True);a=p.parse_args()
    converted=a.converted.resolve();app=converted/'Steam-iOS.app'
    if converted.is_relative_to(REPO):raise ValueError('Proprietary output must stay outside source repo')
    info=plistlib.loads((app/'Info.plist').read_bytes())
    if info.get('CFBundleIdentifier')!='com.kuschqin.ideck.maclab.macprobe' or info.get('SHIMMacRoot')!='Mac':raise ValueError('Isolated app only')
    tier=app/'Mac/Contents/MacOS/libtier0_s.dylib'
    if sha(tier)!=TIER0_SHA:raise ValueError('Unknown tier0 ABI/signature; audit first')
    proxy=app/'Frameworks/libShim_Tier0.dylib';receipt=converted/'ideck-process-observer.json'
    if proxy.exists():raise ValueError('Existing proxy preserved; inspect prior build before replacement')
    receipt.unlink(missing_ok=True)
    candidates=[]
    for path in sorted(app.rglob('*')):
        if path.is_symlink() or not path.is_file() or path==tier:continue
        # Avoid reading large resources, retaining only thin ARM64 Mach-O files.
        with path.open('rb') as f:magic=f.read(8)
        if magic!=struct.pack('<II',0xfeedfacf,0x100000c):continue
        before=inspect(path);deps=[d for d in before['dependencies'] if d.endswith('/libtier0_s.dylib')]
        if deps:candidates.append((path,before,deps))
    if not candidates:raise ValueError('No original tier0 consumers')
    with tempfile.TemporaryDirectory(prefix='.ideck-tier0-',dir=converted) as temporary:
        temp=Path(temporary);out=temp/'libShim_Tier0.dylib'
        subprocess.run(['xcrun','--sdk','iphoneos','clang','-target','arm64-apple-ios17.0','-Wall','-Wextra','-Werror','-dynamiclib','-install_name',PROXY,'-Wl,-reexport_library,'+str(tier),str(OWN/'tier0-process-observer.c'),str(OWN/'launch-summary.c'),'-o',str(out)],check=True)
        subprocess.run(['xcrun','install_name_tool','-change','@loader_path/libtier0_s.dylib','@loader_path/../Mac/Contents/MacOS/libtier0_s.dylib',str(out)],check=True)
        if '@loader_path/../Mac/Contents/MacOS/libtier0_s.dylib' not in inspect(out)['dependencies']:raise ValueError('Proxy re-export missing')
        staged=[]
        for i,(path,before,deps) in enumerate(candidates):
            copy=temp/str(i);shutil.copy2(path,copy)
            for dependency in deps:subprocess.run(['xcrun','install_name_tool','-change',dependency,PROXY,str(copy)],check=True)
            after=inspect(copy)
            if before['textSha256']!=after['textSha256'] or PROXY not in after['dependencies']:raise ValueError('Instruction change or missing proxy')
            staged.append((path,copy,{'path':str(path.relative_to(app)),'textSha256Unchanged':before['textSha256'],'originalSha256':sha(path),'unsignedSha256':sha(copy)}))
        # All compilation/metadata validation completed before replacing outputs.
        for path,copy,_ in staged:shutil.copy2(copy,path)
        shutil.copy2(out,proxy)
        receipt.write_text(json.dumps({'mode':'read-only process observer; no emulation','sourceRevision':subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),'uncommittedInputs':{str(f.relative_to(REPO)):sha(f) for f in [Path(__file__).resolve(),OWN/'tier0-process-observer.c',OWN/'launch-summary.c',OWN/'launch-summary.h']},'tier0Sha256Unchanged':sha(tier),'proxyUnsignedSha256':sha(proxy),'consumers':[v for _,_,v in staged]},indent=2)+'\n')
    print('Process observer staged:',len(candidates),'consumers; text unchanged; re-sign required')
if __name__=='__main__':main()
