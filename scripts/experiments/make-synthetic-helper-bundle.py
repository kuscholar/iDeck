#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Metadata-only synthetic executable-to-bundle discriminator.
ONLY accepts the caller-supplied exact hash of an iDeck-authored fixture with
its unique marker. Never use this tool on Steam/CEF/third-party binaries.
No signing, entry call, injection or device operation. Re-sign before loading.
"""
import argparse,hashlib,json,struct
from pathlib import Path
MARKER=b'IDeckSyntheticHelperFixture-v1'
REPO=Path(__file__).resolve().parents[2]
def transform(data,expected):
 if hashlib.sha256(data).hexdigest()!=expected or MARKER not in data:raise ValueError('Only exact known synthetic fixture accepted')
 if len(data)<32 or struct.unpack_from('<II',data)!=(0xfeedfacf,0x100000c):raise ValueError('Thin ARM64 fixture required')
 if struct.unpack_from('<I',data,12)[0]!=2:raise ValueError('MH_EXECUTE fixture required')
 count,size=struct.unpack_from('<II',data,16);end=32+size;off=32;kept=[];removed=[];text=None
 if end>len(data) or count>size//8:raise ValueError('Invalid command bounds')
 for _ in range(count):
  if off+8>end:raise ValueError('Truncated command')
  cmd,n=struct.unpack_from('<II',data,off)
  if n<8 or n%8 or off+n>end:raise ValueError('Invalid command size')
  raw=data[off:off+n];drop=cmd in (0xe,0x80000028)
  if cmd==0x19:
   if n<72:raise ValueError('Short segment')
   name=raw[8:24].rstrip(b'\0');fo,fs=struct.unpack_from('<QQ',raw,40);ns=struct.unpack_from('<I',raw,64)[0]
   if fo+fs>len(data) or 72+80*ns>n:raise ValueError('Invalid segment')
   if name==b'__PAGEZERO':
    if fo or fs or ns:raise ValueError('Unexpected PAGEZERO payload')
    # Preserve segment ordinal used by LC_DYLD_CHAINED_FIXUPS; an empty
    # zero-protection PAGEZERO keeps the index without reserving 4GiB.
    raw=bytearray(raw);struct.pack_into('<Q',raw,32,0);raw=bytes(raw)
   for j in range(ns):
    p=72+80*j;length=struct.unpack_from('<Q',raw,p+40)[0];position=struct.unpack_from('<I',raw,p+48)[0]
    flags=struct.unpack_from('<I',raw,p+64)[0]
    if flags&0xff not in (1,0x12):
     if position<end or position+length>len(data):raise ValueError('File section overlaps commands or invalid bounds')
    if raw[p:p+16].rstrip(b'\0')==b'__text' and raw[p+16:p+32].rstrip(b'\0')==b'__TEXT':
     if text is not None:raise ValueError('Duplicate text')
     text=(position,length)
  if drop:removed.append(cmd)
  else:kept.append(raw)
  off+=n
 if off!=end or text is None or 0x80000028 not in removed:raise ValueError('Missing fixture entry/text')
 out=bytearray(data);commands=b''.join(kept);out[32:end]=commands+b'\0'*(size-len(commands));struct.pack_into('<III',out,12,8,len(kept),len(commands));flags=struct.unpack_from('<I',out,24)[0];struct.pack_into('<I',out,24,flags&~0x200000)
 position,length=text;assert out[position:position+length]==data[position:position+length]
 return bytes(out),{'kind':'iDeck synthetic fixture only','removedCommandTypes':removed,'textSha256Unchanged':hashlib.sha256(data[position:position+length]).hexdigest(),'metadataOnly':True,'unsigned':True}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--expected-sha256',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 source=a.input.resolve();out=a.output
 if source.is_relative_to(REPO) or out.resolve().is_relative_to(REPO):raise ValueError('Fixture binaries must stay outside source repo')
 if out.exists() or out.is_symlink() or out.with_suffix(out.suffix+'.json').exists() or source==out.resolve():raise ValueError('Preserve existing outputs/input')
 data,report=transform(source.read_bytes(),a.expected_sha256)
 with out.open('xb') as f:f.write(data)
 report.update({'inputSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'outputUnsignedSha256':hashlib.sha256(data).hexdigest()});out.with_suffix(out.suffix+'.json').write_text(json.dumps(report,indent=2)+'\n');print('Synthetic bundle prepared; instruction bytes unchanged; re-sign required')
if __name__=='__main__':main()
