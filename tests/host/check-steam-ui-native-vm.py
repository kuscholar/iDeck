#!/usr/bin/env python3
"""Exercise production native sweep with Mach API fixtures, never map host VA."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
fixture=r'''
#define MADEIRA_VM_PROBE_TEST 1
#include <stdint.h>
#include <assert.h>
#include <string.h>
typedef uint64_t vm_size_t;
typedef uint64_t vm_address_t;
typedef int kern_return_t;
#define KERN_SUCCESS 0
#define VM_FLAGS_FIXED 0
#define MEMORY_OBJECT_NULL 0
#define FALSE 0
#define VM_PROT_NONE 0
#define VM_INHERIT_NONE 2
static int mach_task_self(void){return 7;}
typedef unsigned mach_msg_type_number_t;
typedef int mach_port_t;
typedef int *vm_region_info_t;
typedef struct {int protection;} vm_region_basic_info_data_64_t;
#define VM_REGION_BASIC_INFO_COUNT_64 1
#define VM_REGION_BASIC_INFO_64 9
#define MACH_PORT_NULL 0
static unsigned queries,ports;static int port_fail;
static kern_return_t vm_region_64(int task,vm_address_t *addr,vm_size_t *size,int flavor,vm_region_info_t info,mach_msg_type_number_t *count,mach_port_t *object){
    assert(task==7 && flavor==9 && *count==1);*object=(++queries & 1)?9:0;*size=0x1000;*info=0;return 0;
}
static kern_return_t mach_port_deallocate(int task,mach_port_t object){assert(task==7 && object==9);ports++;return port_fail?5:0;}

static unsigned calls,cleans;static uint64_t live,size_live;static int mode;
static kern_return_t vm_map(int task,vm_address_t *a,vm_size_t size,uint64_t mask,int flags,int object,uint64_t off,int copy,int current,int maximum,int inherit){
    assert(!live && task==7 && mask==0 && flags==VM_FLAGS_FIXED && object==0 && off==0 && !copy);
    assert(current==VM_PROT_NONE && maximum==VM_PROT_NONE && inherit==VM_INHERIT_NONE);
    assert(size==0x10000 || size==0x400000000ULL);calls++;
    if(mode || *a>=0x7000000000ULL){if(mode==2)*a+=0x10000;live=*a;size_live=size;return 0;}
    return 3;
}
static kern_return_t vm_deallocate(int task,vm_address_t a,vm_size_t size){
    assert(task==7 && live==a && size_live==size);cleans++;if(mode==1)return 5;live=0;return 0;
}
#include "steam_ui_vm_probe.h"
int main(int argc,char **argv){
    mode=argc>1?argv[1][0]-'0':0;port_fail=mode==3;
    int result=madeira_steam_ui_vm_probe(stdout);
    if(!mode){assert(result==0 && calls==62 && cleans==8 && ports==31 && !live);}
    if(mode==1){assert(result==2 && calls==1 && cleans==1 && ports==1);}
    if(mode==2){assert(result==3 && calls==1 && cleans==1 && ports==1 && !live);}
    if(mode==3){assert(result==5 && calls==0 && cleans==0 && ports==1);}
    return 0;
}
'''
with tempfile.TemporaryDirectory() as td:
    td=Path(td);(td/'test.c').write_text(fixture)
    subprocess.run(['cc','-fsanitize=address,undefined','-I',str(root/'build/diagnostics'),str(td/'test.c'),'-o',str(td/'test')],check=True)
    for mode in ('0','1','2','3'):
        p=subprocess.run([str(td/'test'),mode],capture_output=True,text=True,check=True)
        assert ('COMPLETE' in p.stdout)==(mode=='0')
bridge=(root/'app/Madeira/WineProcessBridge.m').read_text().split('int madeira_steam_ui_vm_probe_run',1)[1]
assert 'hasSuffix:@".steamui"' in bridge and 'madeira-native-vm-diagnostics' in bridge
assert 'jit_check_debugged()' in bridge and 'wine_process_is_running()' in bridge and 'wineserver_is_running()' in bridge
print('PASS: exact production sweep: 62 fixed NONE/NONE no-overwrite requests; only own successful mappings released; early stop on cleanup/address mismatch (ASan/UBSan); lab/JIT/fresh gates present')
