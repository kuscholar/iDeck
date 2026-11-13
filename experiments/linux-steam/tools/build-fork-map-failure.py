#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Overlay checked fork PTE copying on NEW archives; never mutate vendor/base.

Memory/mmap inputs can be already qualified lazy-page/madvise generated copies.
Host allocation injection is explicit and prohibited for an iOS compilation.
"""
import argparse,hashlib,importlib.util,json,shlex,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ('source','build','archive','output'):p.add_argument(name,type=Path)
p.add_argument('--memory-source',type=Path);p.add_argument('--mmap-source',type=Path)
p.add_argument('--sanitize',action='store_true');p.add_argument('--host-inject',action='store_true')
a=p.parse_args();src,build,archive,out=[getattr(a,n).resolve() for n in ('source','build','archive','output')]
assert str(out).startswith('/Volumes/easystore/') and not out.exists()
assert archive.is_file() and (build/'compile_commands.json').is_file()
spec=importlib.util.spec_from_file_location('fork_patch',Path(__file__).with_name('fork-map-failure.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
assert subprocess.check_output(['git','-C',src,'rev-parse','HEAD'],text=True).strip()==module.PIN
assert not subprocess.check_output(['git','-C',src,'status','--porcelain','--untracked-files=no'],text=True).strip()
out.mkdir(mode=0o700,parents=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
entries=json.loads((build/'compile_commands.json').read_text());rows=[];objects=[]
for name,transform,prepared in [('memory',module.memory,a.memory_source),('mmap',module.mmap,a.mmap_source),('fork',module.fork,None)]:
 original=subprocess.check_output(['git','-C',src,'show',module.PIN+':kernel/'+name+'.c'])
 assert original==(src/'kernel'/f'{name}.c').read_bytes()
 inp=prepared.resolve() if prepared else src/'kernel'/f'{name}.c'
 body=inp.read_text()
 if prepared:
  assert str(inp).startswith('/Volumes/easystore/') and not inp.is_relative_to(src)
  signature={'memory':'int pt_copy_on_write(', 'mmap':'struct mm *mm_copy('}[name]
  assert module.function(body,signature)==module.function(original.decode(),signature)
 generated=out/f'{name}.c';generated.write_text(transform(body))
 entry=next(e for e in entries if e['file'].endswith('/kernel/'+name+'.c'))
 cmd=shlex.split(entry['command']);obj=out/Path(cmd[cmd.index('-o')+1]).name
 cmd[cmd.index(entry['file'])]=str(generated);cmd[cmd.index('-o')+1]=str(obj)
 if prepared:cmd+=['-I',str(inp.parent)]
 for key,value in [('-MF',out/f'{name}.d'),('-MQ',obj)]:
  if key in cmd:cmd[cmd.index(key)+1]=str(value)
 if a.sanitize:cmd+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
 if a.host_inject:
  assert not any('iphoneos' in x.lower() or '-apple-ios' in x.lower() for x in cmd)
  if name=='memory':cmd+=['-Dcalloc=ideck_test_calloc','-Dmalloc=ideck_test_malloc']
 subprocess.run(cmd,cwd=entry['directory'],check=True);objects.append(obj)
 rows.append({'unit':name,'original_sha256':hashlib.sha256(original).hexdigest(),'input_sha256':sha(inp),'generated_sha256':sha(generated),'object_sha256':sha(obj),'command':cmd})
before=sha(archive);target=out/'libish.a';shutil.copy2(archive,target)
subprocess.run(['xcrun','ar','r',target,*objects],check=True);assert sha(archive)==before
(out/'evidence.json').write_text(json.dumps({'linuxrunner':module.PIN,'base_archive_sha256':before,'base_unchanged':True,'units':rows,'archive_sha256':sha(target),'sanitized_units':a.sanitize,'HOST_ONLY_injection':a.host_inject,'scope':'Fork PTE/reservation failures and partial-child release only; unchecked engine/ordinary-map allocations remain; not capacity/device/game proof'},indent=2)+'\n')
print('Copied fork allocation failure archive built; vendor/base unchanged')
