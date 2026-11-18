#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""New pinned fs.c copy/archive; no vendor/base mutation or device action."""
import argparse,hashlib,json,shlex,shutil,subprocess
from pathlib import Path
from bounded_pread_patch import PIN,patched
p=argparse.ArgumentParser(description=__doc__)
for n in ('source','build','archive','output'):p.add_argument(n,type=Path)
p.add_argument('--enabled',action='store_true');p.add_argument('--host-inject',action='store_true');a=p.parse_args()
src,build,archive,out=(getattr(a,n).resolve() for n in ('source','build','archive','output'));lab=Path(__file__).resolve().parents[1]
assert str(out).startswith('/Volumes/easystore/') and not out.exists()
assert subprocess.check_output(['git','-C',src,'rev-parse','HEAD'],text=True).strip()==PIN
assert not subprocess.check_output(['git','-C',src,'status','--porcelain','--untracked-files=no'],text=True).strip()
original=subprocess.check_output(['git','-C',src,'show',PIN+':kernel/fs.c']);assert original==(src/'kernel/fs.c').read_bytes()
body=patched(original.decode()) if a.enabled else original.decode()
entry=next(e for e in json.loads((build/'compile_commands.json').read_text()) if e['file'].endswith('/kernel/fs.c'));cmd=shlex.split(entry['command']);member=Path(cmd[cmd.index('-o')+1]).name
assert subprocess.check_output(['xcrun','ar','t',archive],text=True).splitlines().count(member)==1
if a.host_inject:
 assert not any('iphoneos' in x.lower() or '-apple-ios' in x.lower() for x in cmd)
 body='#if defined(__ENVIRONMENT_IPHONE_OS_VERSION_MIN_REQUIRED__)\n#error HOST injection is forbidden on iOS\n#endif\n'+body
 cmd+=['-Dmalloc=ideck_test_pread_malloc','-Dfree=ideck_test_pread_free','-Drealfs_pread=ideck_test_pread_backend','-fsanitize=address,undefined','-fno-sanitize-recover=all']
out.mkdir(mode=0o700,parents=True);generated=out/'fs.c';generated.write_text(body);obj=out/member
cmd[cmd.index(entry['file'])]=str(generated);cmd[cmd.index('-o')+1]=str(obj)
for k,v in [('-MF',out/'fs.d'),('-MQ',obj)]:
 if k in cmd:cmd[cmd.index(k)+1]=str(v)
cmd+=['-I'+str(src),'-I'+str(lab/'app')];subprocess.run(cmd,cwd=entry['directory'],check=True)
sha=lambda q:hashlib.sha256(q.read_bytes()).hexdigest();before=sha(archive);target=out/'libish.a';shutil.copy2(archive,target);subprocess.run(['xcrun','ar','r',target,obj],check=True);assert before==sha(archive)
for n in ('LICENSE.md','LICENSE.IOS'):shutil.copy2(src/n,out/n)
(out/'evidence.json').write_text(json.dumps({'linuxrunner':PIN,'enabled':a.enabled,'scope':'Private copied sys_pread regular realfile scratch64KiB only; request>64KiB<=16MiB, no allocation/backend retries. NOTdevice/UIproof','original_sha256':hashlib.sha256(original).hexdigest(),'generated_sha256':sha(generated),'base_archive_sha256':before,'base_unchanged':True,'archive_sha256':sha(target),'HOST_ONLY_injection':a.host_inject,'command':cmd},indent=2)+'\n')
print('Copied regular-pread policy prepared; base/vendor unchanged')
