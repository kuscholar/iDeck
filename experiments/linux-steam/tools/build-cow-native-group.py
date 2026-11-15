#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Opt-in anonymous COW grouping in a new copied Linux kernel archive."""
import argparse,hashlib,json,shlex,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ('source','build','archive','memory_source','output'):p.add_argument(name,type=Path)
p.add_argument('--sanitize',action='store_true');p.add_argument('--host-inject',action='store_true')
p.add_argument('--backing-broker',action='store_true',help='Explicit real owned native-page slots for eligible CoW only; default unchanged')
p.add_argument('--native-pages-per-group',type=int,choices=(1,2),default=1,help='Explicit coarse private-anonymous CoW experiment; may materialize extra pages')
a=p.parse_args();src,build,archive,prepared,out=[getattr(a,n).resolve() for n in ('source','build','archive','memory_source','output')]
assert str(out).startswith('/Volumes/easystore/') and not out.exists() and archive.is_file() and prepared.is_file()
assert subprocess.check_output(['git','-C',src,'rev-parse','HEAD'],text=True).strip()=='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
assert not subprocess.check_output(['git','-C',src,'status','--porcelain','--untracked-files=no'],text=True).strip()
body=prepared.read_text();anchor='static void *mem_ptr_nofault(struct mem *mem, addr_t addr, int type) {';assert body.count(anchor)==1
assert not a.backing_broker or a.native_pages_per_group==1,'Broker requires original one-native-page CoW span'
helper=Path(__file__).resolve().parents[1]/'app/CowNativeGroup.inc';text=helper.read_text()
if a.native_pages_per_group!=1:text='#define IDECK_LAB_COW_NATIVE_PAGES '+str(a.native_pages_per_group)+'\n'+text
if a.host_inject:
 text='extern int ideck_cow_inject_failure;\n'+text
 text=text.replace('void *copy=mmap(', 'void *copy=ideck_cow_inject_failure==1?MAP_FAILED:mmap(')
 text=text.replace('struct data *replacement=malloc(', 'struct data *replacement=ideck_cow_inject_failure==2?NULL:malloc(')
if a.backing_broker:
 allocation='mmap(NULL,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,0,0)'
 assert text.count(allocation)==1
 text=text.replace(allocation,'ideck_cow_broker_allocate(bytes)')
 rollback='if(!replacement){munmap(copy,bytes);return _ENOMEM;}'
 assert text.count(rollback)==1
 text=text.replace(rollback,'if(!replacement){if(ideck_cow_broker_release_owned(copy,bytes)!=1)abort();return _ENOMEM;}')
 old_release='        if (data->data != vdso_data) munmap(data->data, data->size);'
 assert body.count(old_release)==1
 body='#include "CowBackingBroker.h"\n'+body.replace(old_release,'''        if (data->data != vdso_data) {
            int owned = ideck_cow_broker_release_owned(data->data, data->size);
            if (owned < 0) abort();
            if (!owned) munmap(data->data, data->size);
        }''')
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
if a.backing_broker:cmd+=['-I'+str(helper.parent)]
subprocess.run(cmd,cwd=entry['directory'],check=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before=sha(archive);target=out/'libish.a';shutil.copy2(archive,target)
subprocess.run(['xcrun','ar','r',target,obj],check=True);assert sha(archive)==before
broker_evidence=None
if a.backing_broker:
 broker=helper.parent/'CowBackingBroker.c';broker_obj=out/'CowBackingBroker.o'
 broker_cmd=cmd.copy();broker_cmd[broker_cmd.index(str(generated))]=str(broker);broker_cmd[broker_cmd.index('-o')+1]=str(broker_obj)
 for key,val in [('-MF',out/'broker.d'),('-MQ',broker_obj)]:
  if key in broker_cmd:broker_cmd[broker_cmd.index(key)+1]=str(val)
 subprocess.run(broker_cmd,cwd=entry['directory'],check=True)
 subprocess.run(['xcrun','ar','r',target,broker_obj],check=True)
 broker_evidence={'source_sha256':sha(broker),'header_sha256':sha(helper.parent/'CowBackingBroker.h'),'command':broker_cmd,'host_capacity_override':False}
(out/'evidence.json').write_text(json.dumps({'base_archive_sha256':before,'base_unchanged':True,'input_memory_sha256':sha(prepared),'generated_sha256':sha(generated),'helper_sha256':sha(helper),'archive_sha256':sha(target),'backing_broker':broker_evidence,'native_pages_per_group':a.native_pages_per_group,'host_injection':a.host_inject,'sanitized_memory_unit':a.sanitize,'scope':'Compatible anonymous private CoW groups only; not file/shared/ptrace/limits/physical-RSS/device/game proof','command':cmd},indent=2)+'\n')
print('Copied anonymous CoW grouping archive built; pinned vendor unchanged')
