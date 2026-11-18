#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Build a copied pinned engine allocation guard; never edit vendor or FEX."""
import argparse,hashlib,json,shlex,shutil,subprocess
from pathlib import Path
from fiber_hash_patch import patched_engine
p=argparse.ArgumentParser(description=__doc__)
for name in ('source','build','archive','output'):p.add_argument(name,type=Path)
p.add_argument('--host-inject',action='store_true',help='HOST ONLY externally supplied one-shot growth allocator; forbidden for iOS')
a=p.parse_args();src,build,archive,out=(getattr(a,n).resolve() for n in ('source','build','archive','output'))
assert str(out).startswith('/Volumes/easystore/') and not out.exists()
pin='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
assert subprocess.check_output(['git','-C',src,'rev-parse','HEAD'],text=True).strip()==pin
assert not subprocess.check_output(['git','-C',src,'status','--porcelain','--untracked-files=no'],text=True).strip()
original=subprocess.check_output(['git','-C',src,'show',pin+':asbestos/asbestos.c']);assert original==(src/'asbestos/asbestos.c').read_bytes()
entries=[e for e in json.loads((build/'compile_commands.json').read_text()) if e['file'].endswith('/asbestos/asbestos.c')];assert len(entries)==1
entry=entries[0];cmd=shlex.split(entry['command']);member=Path(cmd[cmd.index('-o')+1]).name
assert subprocess.check_output(['xcrun','ar','t',archive],text=True).splitlines().count(member)==1
body=patched_engine(original.decode())
if a.host_inject:
    assert not any('iphoneos' in x.lower() or '-apple-ios' in x.lower() for x in cmd),'HOST allocation injection forbidden on iOS'
    body='''#if defined(__ENVIRONMENT_IPHONE_OS_VERSION_MIN_REQUIRED__)
#error HOST allocation injection forbidden on iOS
#endif
#include <stddef.h>
extern void *ideck_hash_test_calloc(size_t,size_t);
'''+body.replace('struct list *new_hash = calloc(new_size, sizeof(struct list));','struct list *new_hash = ideck_hash_test_calloc(new_size, sizeof(struct list));')
    cmd+=['-fsanitize=address,undefined','-fno-sanitize-recover=all']
out.mkdir(mode=0o700,parents=True);generated=out/'asbestos.c';generated.write_text(body);obj=out/member
cmd[cmd.index(entry['file'])]=str(generated);cmd[cmd.index('-o')+1]=str(obj)
for key,value in [('-MF',out/'asbestos.d'),('-MQ',obj)]:
    if key in cmd:cmd[cmd.index(key)+1]=str(value)
first=next(i for i,v in enumerate(cmd) if v.startswith('-I'));cmd[first:first]=['-I'+str(src),'-I'+str(build)]
subprocess.run(cmd,cwd=entry['directory'],check=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before=sha(archive);target=out/'libish_emu.a';shutil.copy2(archive,target)
subprocess.run(['xcrun','ar','r',target,obj],check=True);assert sha(archive)==before
for name in ('LICENSE.md','LICENSE.IOS'):shutil.copy2(src/name,out/name)
(out/'evidence.json').write_text(json.dumps({'scope':'Copied engine existing-table growth failure guard only; no initial engine/other allocations or CEF/UI/Air/game proof','linuxrunner':pin,'base_unchanged':True,'base_archive_sha256':before,'archive_sha256':sha(target),'original_sha256':hashlib.sha256(original).hexdigest(),'generated_sha256':sha(generated),'transform_sha256':sha(Path(__file__).with_name('fiber_hash_patch.py')),'build_command':cmd,'member':member,'cap_change':False,'host_injection':a.host_inject},indent=2)+'\n')
print('Copied engine hash growth guard built; pinned source/base/FEX unchanged')
