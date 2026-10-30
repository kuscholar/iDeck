#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Exact-version private-copy loader discriminator for the audited Steam Helper.
Only Mach-O loader metadata changes; instruction/remaining payload bytes and
original Helper are preserved. No entry, auth, signing, install or process spoof.
Not a generic converter; mismatched versions/layouts are refused.
"""
import argparse,hashlib,importlib.util,json,plistlib,struct,subprocess,tempfile
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
EXPECTED='76374b69c4cb4d7ca0bb3c60f985eb766e90243ee3bc2d6605cf5cc2a67150c3'
OLD_CEF='@executable_path/../Frameworks/Chromium Embedded Framework.framework/Chromium Embedded Framework'
NEW_CEF='@loader_path/../Frameworks/Chromium Embedded Framework.framework/Chromium Embedded Framework'
def digest(data):return hashlib.sha256(data).hexdigest()
def adapt_metadata(data,expected=EXPECTED):
 if digest(data)!=expected:raise ValueError('Unknown Helper version/signature; audit required')
 if len(data)<32 or struct.unpack_from('<II',data)!=(0xfeedfacf,0x100000c) or struct.unpack_from('<I',data,12)[0]!=2:raise ValueError('Expected audited thin ARM64 MH_EXECUTE')
 count,size=struct.unpack_from('<II',data,16);off=32;end=32+size;commands=[];removed=[];segments=[];has_stream=False;has_chained=False;text=None
 if end>len(data) or count>size//8:raise ValueError('Invalid commands')
 for _ in range(count):
  if off+8>end:raise ValueError('Truncated command')
  c,n=struct.unpack_from('<II',data,off)
  if n<8 or n%8 or off+n>end:raise ValueError('Invalid command bounds')
  raw=data[off:off+n];drop=c in (0xe,0x80000028)
  if c==0x19:
   if n<72:raise ValueError('Truncated segment')
   name=raw[8:24].rstrip(b'\0');va,vs,fo,fs=struct.unpack_from('<QQQQ',raw,24);ns=struct.unpack_from('<I',raw,64)[0]
   if fo+fs>len(data) or 72+80*ns>n:raise ValueError('Invalid segment sections')
   segments.append(name.decode())
   if name==b'__PAGEZERO':
    if fo or fs or ns or va:raise ValueError('Unexpected PAGEZERO payload')
    raw=bytearray(raw);struct.pack_into('<Q',raw,32,0);raw=bytes(raw)
   for j in range(ns):
    p=72+80*j;length=struct.unpack_from('<Q',raw,p+40)[0];pos=struct.unpack_from('<I',raw,p+48)[0];kind=struct.unpack_from('<I',raw,p+64)[0]&255
    if kind not in (1,0x12) and (pos<end or pos+length>len(data)):raise ValueError('Section overlaps commands or invalid file range')
    if raw[p:p+16].rstrip(b'\0')==b'__text' and raw[p+16:p+32].rstrip(b'\0')==b'__TEXT':
     if text:raise ValueError('Duplicate text')
     text=(pos,length)
  if c==0x80000022:
   if n!=48:raise ValueError('Unexpected dyld-info size')
   for start,length in zip(struct.unpack_from('<10I',raw,8)[::2],struct.unpack_from('<10I',raw,8)[1::2]):
    if length and (start<end or start+length>len(data)):raise ValueError('Unbacked bind/rebase/export stream')
   has_stream=True
  if c==0x80000034:has_chained=True
  if c==0x2c and struct.unpack_from('<I',raw,16)[0]:raise ValueError('Encrypted image refused')
  if drop:removed.append(c)
  else:commands.append(raw)
  off+=n
 if off!=end or not text or not has_stream or has_chained or segments!=['__PAGEZERO','__TEXT','__DATA_CONST','__DATA','__LINKEDIT'] or 0x80000028 not in removed:raise ValueError('Unexpected exact Helper segment/fixup/entry contract')
 out=bytearray(data);joined=b''.join(commands);out[32:end]=joined+b'\0'*(size-len(joined));struct.pack_into('<III',out,12,8,len(commands),len(joined));struct.pack_into('<I',out,24,struct.unpack_from('<I',out,24)[0]&~0x200000)
 assert out[end:]==data[end:]
 pos,length=text;return bytes(out),{'segmentsPreserved':segments,'dyldInfoStreamsUnchanged':True,'textSha256Unchanged':digest(data[pos:pos+length]),'postOriginalCommandsSha256Unchanged':digest(data[end:]),'originalCommandEnd':end,'removedCommandTypes':removed}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--converted',type=Path,required=True);a=p.parse_args();root=a.converted.resolve();app=root/'Steam-iOS.app'
 if root.is_relative_to(REPO):raise ValueError('Private converted output required')
 info=plistlib.loads((app/'Info.plist').read_bytes())
 if info.get('CFBundleIdentifier')!='com.kuschqin.ideck.maclab.macprobe' or info.get('SHIMMacRoot')!='Mac':raise ValueError('Isolated native lab only')
 original=app/'Mac/Contents/Frameworks/Steam Helper.app/Contents/MacOS/Steam Helper';dest=app/'Mac/Contents/MacOS/IDeckNativeHelperLoad.bundle';receipt=root/'ideck-native-helper-bundle.json'
 if dest.exists() or dest.is_symlink() or receipt.exists():raise ValueError('Existing candidate/receipt preserved')
 data=original.read_bytes();adapted,report=adapt_metadata(data)
 # Prove the corrected loader-relative CEF path resolves inside this app copy.
 cef=(dest.parent/NEW_CEF[len('@loader_path/'):]).resolve(strict=True)
 if not cef.is_relative_to(app.resolve()):raise ValueError('CEF target escapes app')
 spec=importlib.util.spec_from_file_location('observer',REPO/'scripts/experiments/build-mac-process-observer.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 if mod.inspect(original)['dependencies'].count(OLD_CEF)!=1:raise ValueError('Expected exactly one audited CEF dependency')
 with tempfile.TemporaryDirectory(prefix='.ideck-native-helper-',dir=root) as folder:
  candidate=Path(folder)/dest.name;candidate.write_bytes(adapted)
  subprocess.run(['xcrun','install_name_tool','-change',OLD_CEF,NEW_CEF,str(candidate)],check=True)
  b=candidate.read_bytes();parsed=mod.inspect(candidate)
  if parsed['textSha256']!=report['textSha256Unchanged'] or NEW_CEF not in parsed['dependencies'] or b[report['originalCommandEnd']:]!=data[report['originalCommandEnd']:]:raise ValueError('Instruction/payload change or missing CEF correction')
  if digest(original.read_bytes())!=EXPECTED:raise ValueError('Original unexpectedly changed')
  with dest.open('xb') as f:f.write(b)
 report.update({'state':'unsigned private candidate; no entry called','originalHelperSha256Unchanged':EXPECTED,'candidateUnsignedSha256':digest(dest.read_bytes()),'cefDependency':NEW_CEF,'cefTargetSha256':digest(cef.read_bytes()),'sourceParent':subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip()});receipt.write_text(json.dumps(report,indent=2)+'\n');print('Exact Helper private bundle candidate prepared; original/payload/instructions unchanged; normal signing required')
if __name__=='__main__':main()
