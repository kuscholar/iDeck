#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Build an opt-in copied LinuxRunner engine archive with CASP lock ordering.

Never modify the vendor tree, original engine/archive, Valve/FEX or any device.
Requires exact pinned source and a prepared architecture-specific compile DB.
Only this copied emu/tlb.c is recompiled; keep component license/IOS terms.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
from casp_order_patch import patched_tlb
p=argparse.ArgumentParser(description=__doc__)
for name in ('source','build','archive','output'):p.add_argument(name,type=Path)
a=p.parse_args();src,build,archive,out=(getattr(a,n).resolve() for n in ('source','build','archive','output'))
assert str(out).startswith('/Volumes/easystore/') and not out.exists()
pin='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
assert subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip()==pin
assert not subprocess.check_output(['git','-C',str(src),'status','--porcelain','--untracked-files=no'],text=True).strip()
original=subprocess.check_output(['git','-C',str(src),'show',pin+':emu/tlb.c']);assert original==(src/'emu/tlb.c').read_bytes()
entries=[x for x in json.loads((build/'compile_commands.json').read_text()) if x['file'].endswith('/emu/tlb.c')];assert len(entries)==1
entry=entries[0];cmd=shlex.split(entry['command']);member=Path(cmd[cmd.index('-o')+1]).name
assert subprocess.check_output(['xcrun','ar','t',str(archive)],text=True).splitlines().count(member)==1
out.mkdir(mode=0o700);generated=out/'tlb.c';generated.write_text(patched_tlb(original.decode())+'\n__attribute__((used)) const char ideck_casp_order_marker[]="IDECK_CASP_TRANSLATION_BEFORE_PAIR_LOCK_V1";\n')
obj=out/member;cmd[cmd.index(entry['file'])]=str(generated);cmd[cmd.index('-o')+1]=str(obj)
for option,value in [('-MF',out/'tlb.d'),('-MQ',obj)]:
    if option in cmd:cmd[cmd.index(option)+1]=str(value)
# Put the verified pinned headers before historical source-directory includes.
first_include=next(i for i,arg in enumerate(cmd) if arg.startswith('-I'))
# Cross commands start with "xcrun --sdk iphoneos clang", rather than a
# one-token host compiler. Compiler options must follow that launcher prefix.
cmd[first_include:first_include]=['-I'+str(src),'-I'+str(build)]
subprocess.run(cmd,cwd=entry['directory'],check=True)
hashof=lambda x:hashlib.sha256(x.read_bytes()).hexdigest();before=hashof(archive)
target=out/'libish_emu.a';shutil.copy2(archive,target)
subprocess.run(['xcrun','ar','r',str(target),str(obj)],check=True)
assert before==hashof(archive)
for n in ('LICENSE.md','LICENSE.IOS'):shutil.copy2(src/n,out/n)
(out/'evidence.json').write_text(json.dumps({'scope':'Copied experimental engine archive only; NOT execution/Steam/Air/game proof','linuxrunner':pin,'base_unchanged':True,'base_archive_sha256':before,'archive_sha256':hashof(target),'original_tlb_sha256':hashlib.sha256(original).hexdigest(),'generated_tlb_sha256':hashof(generated),'transform_sha256':hashof(Path(__file__).with_name('casp_order_patch.py')),'build_command':cmd,'member':member,'marker':'IDECK_CASP_TRANSLATION_BEFORE_PAIR_LOCK_V1','limits':['Existing CASP32 misalignment and CASP/STXP interaction remain unqualified','No assertion/permission/fault retry workaround','No original runtime or device modified']},indent=2)+'\n')
print('Built copied CASP translation-before-mutex engine; baseline/vendor unchanged')
