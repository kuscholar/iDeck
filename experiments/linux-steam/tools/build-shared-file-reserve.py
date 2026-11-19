#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Compile explicit owned-reserve hooks into a NEW copied Linux archive only."""
import argparse,hashlib,json,shlex,shutil,subprocess,importlib.util
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ('source','build','archive','output'):p.add_argument(name,type=Path)
p.add_argument('--real-source',type=Path,required=True)
p.add_argument('--memory-source',type=Path,required=True)
p.add_argument('--host-inject',action='store_true')
a=p.parse_args();src,build,archive,out=(getattr(a,n).resolve() for n in ('source','build','archive','output'))
assert all(str(x).startswith('/Volumes/easystore/') for x in (build,archive,out,a.real_source.resolve(),a.memory_source.resolve())) and not out.exists()
assert subprocess.check_output(['git','-C',src,'rev-parse','HEAD'],text=True).strip()=='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
assert not subprocess.check_output(['git','-C',src,'status','--porcelain','--untracked-files=no'],text=True).strip()
lab=Path(__file__).resolve().parents[1]
patcher=Path(__file__).with_name('shared_file_reserve_patch.py')
spec=importlib.util.spec_from_file_location('shared_reserve_patch',patcher);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
out.mkdir(mode=0o700);commands=[];objects=[]
entries=json.loads((build/'compile_commands.json').read_text())
for name,source,patch in [('real',a.real_source.resolve(),mod.patch_real),('memory',a.memory_source.resolve(),mod.patch_memory)]:
    generated=patch(source.read_text())
    if a.host_inject:
        generated='#if defined(__ENVIRONMENT_IPHONE_OS_VERSION_MIN_REQUIRED__)\n#error Host allocator injection is forbidden on iOS\n#endif\n'+generated
    target=out/(name+'.c');target.write_text(generated)
    entry=next(e for e in entries if e['file'].endswith('/'+('fs/real.c' if name=='real' else 'kernel/memory.c')))
    cmd=shlex.split(entry['command']);obj=out/Path(cmd[cmd.index('-o')+1]).name
    assert subprocess.check_output(['xcrun','ar','t',archive],text=True).splitlines().count(obj.name)==1
    if a.host_inject:
        assert not any('iphoneos' in x.lower() or '-apple-ios' in x.lower() for x in cmd)
        cmd+=['-fsanitize=address,undefined','-fno-sanitize-recover=all']
        if name=='real':cmd+=['-DIDECK_FILE_RESERVE_REALFS_HOST_INJECTION=1']
        else:cmd+=['-Dmalloc=ideck_reserve_test_malloc','-Dcalloc=ideck_reserve_test_calloc']
    cmd[cmd.index(entry['file'])]=str(target);cmd[cmd.index('-o')+1]=str(obj)
    for key,value in [('-MF',out/(name+'.d')),('-MQ',obj)]:
        if key in cmd:cmd[cmd.index(key)+1]=str(value)
    cmd+=['-I'+str(lab/'app'),'-I'+str(source.parent)]
    commands.append(cmd);subprocess.run(cmd,cwd=entry['directory'],check=True);objects.append(obj)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=sha(archive);target=out/'libish.a';shutil.copy2(archive,target)
subprocess.run(['xcrun','ar','r',str(target),*[str(x) for x in objects]],check=True)
assert sha(archive)==before
(out/'evidence.json').write_text(json.dumps({'scope':'Explicit copied Linux realfs/last-data-ref reserve hooks only; native allocator must be linked/prepared separately. NOT device/UI/fragmentation fix proof','linuxrunner':'d1419782da2e299fe22f1ddb85c70ae3d1e276b1','base_archive_sha256':before,'base_archive_unchanged':True,'inputs_sha256':{'real':sha(a.real_source),'memory':sha(a.memory_source),'patcher':sha(patcher)},'generated_sha256':{n:sha(out/(n+'.c')) for n in ['real','memory']},'objects_sha256':{p.name:sha(p) for p in objects},'archive_sha256':sha(target),'commands':commands,'HOST_ONLY_injection':a.host_inject,'eligible_only_after_original_native_ENOMEM':True,'ordinary_or_unsupported_mapping_paths_preserved':True},indent=2)+'\n')
print('Copied owned-reserve file/last-ref hooks built; no source/vendor/FEX/base archive/device changes')
