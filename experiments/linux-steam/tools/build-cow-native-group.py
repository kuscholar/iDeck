#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Opt-in anonymous COW grouping in a new copied Linux kernel archive."""
import argparse,hashlib,json,shlex,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ('source','build','archive','memory_source','output'):p.add_argument(name,type=Path)
p.add_argument('--sanitize',action='store_true');p.add_argument('--host-inject',action='store_true')
a=p.parse_args();src,build,archive,prepared,out=[getattr(a,n).resolve() for n in ('source','build','archive','memory_source','output')]
assert str(out).startswith('/Volumes/easystore/') and not out.exists() and archive.is_file() and prepared.is_file()
assert subprocess.check_output(['git','-C',src,'rev-parse','HEAD'],text=True).strip()=='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
assert not subprocess.check_output(['git','-C',src,'status','--porcelain','--untracked-files=no'],text=True).strip()
body=prepared.read_text();anchor='static void *mem_ptr_nofault(struct mem *mem, addr_t addr, int type) {';assert body.count(anchor)==1
helper=Path(__file__).resolve().parents[1]/'app/CowNativeGroup.inc';text=helper.read_text()
if a.host_inject:
 text='extern int ideck_cow_inject_failure;\n'+text
 text=text.replace('void *copy=mmap(', 'void *copy=ideck_cow_inject_failure==1?MAP_FAILED:mmap(')
 text=text.replace('struct data *replacement=malloc(', 'struct data *replacement=ideck_cow_inject_failure==2?NULL:malloc(')
body=body.replace(anchor,text+'\n'+anchor)
old='''            if (entry != NULL && ((entry->flags & P_COW) || type == MEM_WRITE_PTRACE)) {'''
assert body.count(old)==1
body=body.replace(old,'''            int grouped = ideck_cow_native_group(mem,page,type);
            if(grouped<0) failed=true;
            entry = mem_pt(mem,page);
            if (grouped==0 && entry != NULL && ((entry->flags & P_COW) || type == MEM_WRITE_PTRACE)) {''')
out.mkdir(mode=0o700);generated=out/'memory.c';generated.write_text(body)
entry=next(e for e in json.loads((build/'compile_commands.json').read_text()) if e['file'].endswith('/kernel/memory.c'))
cmd=shlex.split(entry['command']);obj=out/Path(cmd[cmd.index('-o')+1]).name
cmd[cmd.index(entry['file'])]=str(generated);cmd[cmd.index('-o')+1]=str(obj)
for key,val in [('-MF',out/'memory.d'),('-MQ',obj)]:
 if key in cmd:cmd[cmd.index(key)+1]=str(val)
if a.host_inject:assert not any('iphoneos' in x.lower() or '-apple-ios' in x.lower() for x in cmd)
if a.sanitize:cmd+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
subprocess.run(cmd,cwd=entry['directory'],check=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before=sha(archive);target=out/'libish.a';shutil.copy2(archive,target)
subprocess.run(['xcrun','ar','r',target,obj],check=True);assert sha(archive)==before
(out/'evidence.json').write_text(json.dumps({'base_archive_sha256':before,'base_unchanged':True,'input_memory_sha256':sha(prepared),'generated_sha256':sha(generated),'helper_sha256':sha(helper),'archive_sha256':sha(target),'host_injection':a.host_inject,'sanitized_memory_unit':a.sanitize,'scope':'Compatible anonymous private CoW groups only; not file/shared/ptrace/limits/physical-RSS/device/game proof','command':cmd},indent=2)+'\n')
print('Copied anonymous CoW grouping archive built; pinned vendor unchanged')
