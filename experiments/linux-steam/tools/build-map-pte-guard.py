#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""New copied kernel ordinary-map PTE preflight; no vendor/base/FEX edits."""
import argparse,hashlib,json,shlex,shutil,subprocess
from pathlib import Path
from map_pte_patch import patched_memory,function,PIN
p=argparse.ArgumentParser(description=__doc__)
for name in ('source','build','archive','output'):p.add_argument(name,type=Path)
p.add_argument('--memory-source',type=Path);p.add_argument('--host-inject',action='store_true');a=p.parse_args()
src,build,archive,out=(getattr(a,n).resolve() for n in ('source','build','archive','output'))
assert str(out).startswith('/Volumes/easystore/') and not out.exists()
assert subprocess.check_output(['git','-C',src,'rev-parse','HEAD'],text=True).strip()==PIN
assert not subprocess.check_output(['git','-C',src,'status','--porcelain','--untracked-files=no'],text=True).strip()
original=subprocess.check_output(['git','-C',src,'show',PIN+':kernel/memory.c']).decode();assert original==(src/'kernel/memory.c').read_text()
prepared=a.memory_source.resolve() if a.memory_source else src/'kernel/memory.c'
body=prepared.read_text()
if a.memory_source:
 assert str(prepared).startswith('/Volumes/easystore/') and not prepared.is_relative_to(src)
 for sig in ('static struct pt_entry *mem_pt_new(','static int pt_map_accounted('):
  assert function(body,sig)==function(original,sig),'Ordinary-map boundary drift'
body=patched_memory(body)
entry=next(e for e in json.loads((build/'compile_commands.json').read_text()) if e['file'].endswith('/kernel/memory.c'))
cmd=shlex.split(entry['command']);member=Path(cmd[cmd.index('-o')+1]).name
assert subprocess.check_output(['xcrun','ar','t',archive],text=True).splitlines().count(member)==1
if a.host_inject:
 assert not any('iphoneos' in x.lower() or '-apple-ios' in x.lower() for x in cmd)
 body='#if defined(__ENVIRONMENT_IPHONE_OS_VERSION_MIN_REQUIRED__)\n#error HOST allocator injection forbidden on iOS\n#endif\n'+body
 cmd+=['-Dcalloc=ideck_test_calloc','-Dmalloc=ideck_test_malloc','-Dfree=ideck_test_free','-fsanitize=address,undefined','-fno-sanitize-recover=all']
out.mkdir(mode=0o700,parents=True);generated=out/'memory.c';generated.write_text(body);obj=out/member
cmd[cmd.index(entry['file'])]=str(generated);cmd[cmd.index('-o')+1]=str(obj)
for key,value in [('-MF',out/'memory.d'),('-MQ',obj)]:
 if key in cmd:cmd[cmd.index(key)+1]=str(value)
cmd+=['-I'+str(src),'-I'+str(Path(__file__).resolve().parents[1]/'app')]
if a.memory_source:cmd+=['-I'+str(prepared.parent)]
subprocess.run(cmd,cwd=entry['directory'],check=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before=sha(archive);target=out/'libish.a';shutil.copy2(archive,target);subprocess.run(['xcrun','ar','r',target,obj],check=True);assert sha(archive)==before
for name in ('LICENSE.md','LICENSE.IOS'):shutil.copy2(src/name,out/name)
(out/'evidence.json').write_text(json.dumps({'linuxrunner':PIN,'scope':'Ordinary map PTE allocation preflight and empty-metadata rollback only; caller backing/accounting remains owned on failure. NOT initial engine/all allocation/device/CEF/game proof','base_unchanged':True,'base_archive_sha256':before,'archive_sha256':sha(target),'original_sha256':hashlib.sha256(original.encode()).hexdigest(),'input_sha256':sha(prepared),'generated_sha256':sha(generated),'transform_sha256':sha(Path(__file__).with_name('map_pte_patch.py')),'command':cmd,'HOST_ONLY_injection':a.host_inject},indent=2)+'\n')
print('Copied ordinary-map PTE preflight built; base/vendor unchanged')
