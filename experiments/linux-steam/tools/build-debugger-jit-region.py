#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Copy pinned iOS JIT unit with an explicit developer-prepared RX handoff.

Never changes vendor/base/FEX/Valve sources or device state. Reuses the pinned
RW-alias/self-check/ready publication, without a breakpoint or an assumed grant.
Only the user's native developer debugger may supply this exact fresh region.
"""
import argparse,hashlib,json,shlex,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for n in ('source','build','archive','output'):p.add_argument(n,type=Path)
a=p.parse_args();src,build,archive,out=(getattr(a,n).resolve() for n in ('source','build','archive','output'))
pin='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
assert str(out).startswith('/Volumes/easystore/') and not out.exists()
assert subprocess.check_output(['git','-C',src,'rev-parse','HEAD'],text=True).strip()==pin
original=subprocess.check_output(['git','-C',src,'show',pin+':asbestos/guest-arm64/jit.c']);assert original==(src/'asbestos/guest-arm64/jit.c').read_bytes()
entries=[e for e in json.loads((build/'compile_commands.json').read_text()) if e['file'].endswith('/asbestos/guest-arm64/jit.c')];assert len(entries)==1
entry=entries[0];cmd=shlex.split(entry['command']);assert '-DISH_JIT=1' in cmd and any('arm64-apple-ios' in x for x in cmd),'Exact iOS emitter build required'
anchor='int jit_ios_acquire(bool txm, char *detail, size_t size) {'
assert original.decode().count(anchor)==1
addition=r'''
/* iDeck Lab: explicit native debugger handoff, before first guest. The region
 * was allocated RX and prepared page-by-page by the authorized developer
 * debugger. Never reinterpret an app mmap/mprotect result as that grant. */
static bool ideck_prepared_rx_range(uintptr_t start,size_t length) {
    uintptr_t cursor=start,end=start+length;unsigned regions=0;
    while(cursor<end){
        if(++regions>REGION_SIZE/16384)return false;
        vm_address_t query=cursor;vm_size_t span=0;
        vm_region_basic_info_data_64_t info;mach_msg_type_number_t count=VM_REGION_BASIC_INFO_COUNT_64;
        mach_port_t object=MACH_PORT_NULL;
        kern_return_t status=vm_region_64(mach_task_self(),&query,&span,VM_REGION_BASIC_INFO_64,(vm_region_info_t)&info,&count,&object);
        if(object!=MACH_PORT_NULL)mach_port_deallocate(mach_task_self(),object);
        if(status!=KERN_SUCCESS || query>cursor || !span || query>UINTPTR_MAX-span || query+span<=cursor ||
           (info.protection&(VM_PROT_READ|VM_PROT_EXECUTE))!=(VM_PROT_READ|VM_PROT_EXECUTE) ||
           (info.protection&VM_PROT_WRITE))return false;
        cursor=query+span<end?query+span:end;
    }
    return true;
}
int ideck_linux_jit_adopt_debugger_region(void *rx_pointer,size_t length) {
    uintptr_t start=(uintptr_t)rx_pointer;
    if(!start || (start&16383) || length!=REGION_SIZE || start>UINTPTR_MAX-length ||
       region || jit_on || atomic_load(&ios_region_ready) || atomic_load(&layout_ready))return -10;
    if(!ideck_prepared_rx_range(start,length))return -11;
    vm_address_t rw=0;vm_prot_t current_protection,maximum_protection;
    kern_return_t status=vm_remap(mach_task_self(),&rw,length,0,VM_FLAGS_ANYWHERE,mach_task_self(),
                    start,false,&current_protection,&maximum_protection,VM_INHERIT_NONE);
    if(status!=KERN_SUCCESS)return -12;
    if(mprotect((void *)rw,length,PROT_READ|PROT_WRITE)!=0){munmap((void *)rw,length);return -13;}
    /* Every RX segment must retain X after the separate RW alias is created. */
    if(!ideck_prepared_rx_range(start,length)){munmap((void *)rw,length);return -14;}
    region=(uint8_t *)start;rw_delta=(intptr_t)rw-(intptr_t)start;dual_map=true;
    if(!ios_region_verify())return -15;
    atomic_store(&ios_region_ready,true);
    return 0;
}
__attribute__((used)) const char ideck_linux_prepared_jit_marker[]="IDECK_LINUX_DEBUGGER_PREPARED_RX_V1";

'''
body=original.decode().replace(anchor,addition+anchor)
member=Path(cmd[cmd.index('-o')+1]).name
assert subprocess.check_output(['xcrun','ar','t',archive],text=True).splitlines().count(member)==1
out.mkdir(parents=True,mode=0o700);generated=out/'jit.c';generated.write_text(body);obj=out/member
cmd[cmd.index(entry['file'])]=str(generated);cmd[cmd.index('-o')+1]=str(obj)
for key,value in [('-MF',out/'jit.d'),('-MQ',obj)]:
 if key in cmd:cmd[cmd.index(key)+1]=str(value)
first=next(i for i,x in enumerate(cmd) if x.startswith('-I'));cmd[first:first]=['-I'+str(src),'-I'+str(build)]
subprocess.run(cmd,cwd=entry['directory'],check=True)
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest();before=sha(archive);target=out/'libish_emu.a';shutil.copy2(archive,target);subprocess.run(['xcrun','ar','r',target,obj],check=True);assert sha(archive)==before
for name in ('LICENSE.md','LICENSE.IOS'):shutil.copy2(src/name,out/name)
(out/'evidence.json').write_text(json.dumps({'linuxrunner':pin,'base_unchanged':True,'base_archive_sha256':before,'archive_sha256':sha(target),'original_sha256':hashlib.sha256(original).hexdigest(),'generated_sha256':sha(generated),'builder_sha256':sha(Path(__file__)),'build_command':cmd,'scope':'Copied iOS unit only; region must be allocated/prepared by authorized debugger, exact120MiB RX and post-alias X checks before existing self-check. NOT device/Steam/game/return proof','TXM_breakpoint_requested':False},indent=2)+'\n')
print('Built copied optional developer-prepared region handoff; vendor/base unchanged')
