#!/usr/bin/env python3
"""Compile actual native hold/transfer code with Mach fixtures and claim races."""
from pathlib import Path
import subprocess
import tempfile

root=Path(__file__).resolve().parents[2]
src=(root/'app/Madeira/JITAllocator.c').read_text()
body=src.split('static unsigned ideck_cef64_held_mask',1)[1].split('/* Explicit read-only timing discriminator.',1)[0]
body='static unsigned ideck_cef64_held_mask'+body
body=body.replace('__attribute__((constructor(99), used)) ', '')
slots=(root/'build/diagnostics/cef64_layout_probe.h').read_text().split('struct ideck_cef64_slot',1)[1].split('#ifndef IDECK_CEF64_TOUCH_PAGE',1)[0]
slots='struct ideck_cef64_slot'+slots
code=r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
typedef uint64_t vm_address_t;
typedef uint64_t vm_size_t;
typedef int kern_return_t;
#define KERN_SUCCESS 0
#define VM_FLAGS_FIXED 0
#define MEMORY_OBJECT_NULL 0
#define FALSE 0
#define VM_PROT_NONE 0
#define VM_PROT_READ 1
#define VM_PROT_WRITE 2
#define VM_PROT_ALL 7
#define VM_INHERIT_NONE 2
static int mode,fail_at,calls,cleans,live;
static uint64_t addresses[20],sizes[20];
static int mach_task_self(void){return 7;}
static int vm_map(int task,vm_address_t *a,vm_size_t size,uint64_t mask,int flags,int object,
                  uint64_t off,int copy,int current,int maximum,int inherit){
 assert(task==7 && !mask && !flags && !object && !off && !copy && !current && inherit==2);
 unsigned index=calls++;assert(index<20 && maximum==(index==3?7:3));
 if(mode==1 && index==(unsigned)fail_at)return 3;
 if(mode==2 && index==(unsigned)fail_at)*a+=UINT64_C(0x100000000000);
 for(unsigned i=0;i<20;i++)if(sizes[i])assert(*a>=addresses[i]+sizes[i] || addresses[i]>=*a+size);
 addresses[index]=*a;sizes[index]=size;live++;return 0;
}
static int vm_deallocate(int task,vm_address_t a,vm_size_t size){
 assert(task==7);unsigned i;for(i=0;i<20;i++)if(sizes[i]&&addresses[i]==a&&sizes[i]==size)break;
 assert(i<20);sizes[i]=0;live--;cleans++;return 0;
}
static char *fake_args[]={(char *)"app",(char *)"madeira-steam64-experiment",0};
static char **args=fake_args;
static int args_count=2;
static char ***_NSGetArgv(void){return &args;}
static int *_NSGetArgc(void){return &args_count;}
static const char *option="1";
static int split;
static const char *fixture_getenv(const char *name){if(!strcmp(name,"MADEIRA_CEF64_SOURCE_LAYOUT"))return option;if(!strcmp(name,"MADEIRA_CEF64_SPLIT_LAYOUT"))return split?"1":0;if(!strcmp(name,"MADEIRA_CEF64_NEAR_CODE"))return split>=2?"1":0;if(!strcmp(name,"MADEIRA_CEF64_CRASH_POOLS"))return split>=3?"1":0;if(!strcmp(name,"MADEIRA_CEF64_MULTI_TABLES"))return split>=4?"1":0;if(!strcmp(name,"MADEIRA_CEF64_WIDE_ARENA"))return split==5||(split==6&&mode==7)?"1":0;if(!strcmp(name,"MADEIRA_CEF64_STANDALONE_LAYOUT"))return split>=6&&mode!=8?"1":0;if(!strcmp(name,"MADEIRA_CEF64_FOUR_TABLES"))return ((split>=7&&mode!=9)||mode==8)?"1":0;if(!strcmp(name,"MADEIRA_CEF64_SIX_TABLES"))return split>=8||mode==9?"1":0;if(!strcmp(name,"MADEIRA_CEF64_TABLES_FROM_ARENA"))return split>=9||mode==10?"1":0;if(!strcmp(name,"MADEIRA_CEF64_SEVENTH_TABLE"))return split>=10||mode==11||mode==12?"1":0;if(!strcmp(name,"MADEIRA_CEF64_EIGHTH_TABLE"))return (split>=11&&mode!=16)||mode==13||mode==14?"1":0;if(!strcmp(name,"MADEIRA_CEF64_TWELVE_TABLES"))return split==14||mode==21?"1":mode==23?"10":0;if(!strcmp(name,"MADEIRA_CEF64_NINTH_TAIL_TABLE"))return split>=13||mode==18||mode==19?"1":mode==20?"10":0;if(!strcmp(name,"MADEIRA_CEF64_COMPACT_SOURCE_POOLS"))return split==12||mode==15?"1":mode==17?"10":0;assert(!strcmp(name,"MADEIRA_CEF64_EXTERNAL_CRASHPAD"));return split>=6&&mode!=6?"1":0;}
#define getenv fixture_getenv
'''+slots+body+r'''
static unsigned winners;
static void *claim_worker(void *unused){(void)unused;if(madeira_cef64_hold_claim(0))__atomic_fetch_add(&winners,1,__ATOMIC_RELAXED);return 0;}
int main(int argc,char **argv){
 assert(argc==4);mode=atoi(argv[1]);fail_at=atoi(argv[2]);split=atoi(argv[3]);unsigned count=split==14?20:split>=12?17:split==11?16:split==10?15:split>=8?14:split==7?12:split==6?11:split>=4?13:split==3?11:split==2?9:split?8:6;
 if(mode==3)option=0;
 if(mode==4)option="10";
 if(mode==5)args_count=1;
 ideck_cef64_boot_holds();
 uint64_t base,size;
 if(mode==21||mode==18||mode==19||mode==15||mode==16||mode==6||mode==7||mode==8||mode==9||mode==10||mode==11||mode==12||mode==13||mode==14){assert(!calls&&!live&&madeira_cef64_hold_state()==-1&&!madeira_cef64_standalone_layout());return 0;}
 if(mode>=3 && mode!=17&&mode!=20&&mode!=23){assert(!calls && !live && madeira_cef64_hold_state()==0);assert(!madeira_cef64_hold_claim(0));return 0;}
 if(mode && mode!=17&&mode!=20&&mode!=23){assert(madeira_cef64_hold_state()==-1 && !live && calls==fail_at+1 && cleans==fail_at+(mode==2));assert(!madeira_cef64_hold_claim(0));return 0;}
 assert(madeira_cef64_hold_state()==1 && calls==(int)count && live==(int)count && !cleans);
 if(split==5){assert(addresses[3]==UINT64_C(0x6000000000));assert(sizes[3]==UINT64_C(0x1000000000));}
 else if(split>=6){assert(addresses[3]==UINT64_C(0x7500000000));assert(sizes[3]==(split==14?UINT64_C(0x1c0000000):split==13?UINT64_C(0x220000000):split>=11?UINT64_C(0x240000000):split==10?UINT64_C(0x260000000):split==9?UINT64_C(0x280000000):split>=7?UINT64_C(0x2c0000000):UINT64_C(0x2ffff0000)));if(split>=7)assert(addresses[11]==UINT64_C(0x77c0000000));assert(madeira_cef64_standalone_layout());}
 else assert(addresses[3]==UINT64_C(0x7400000000));
 if(split==12){assert(addresses[0]==UINT64_C(0x7140000000));assert(addresses[1]==UINT64_C(0x70ffff0000));assert(addresses[8]==UINT64_C(0x7180000000));assert(addresses[16]==UINT64_C(0x71a0000000));}
 if(split>=13){assert(addresses[16]==UINT64_C(0x7720000000));assert(addresses[8]+sizes[8]==UINT64_C(0x7160000000));}
 pthread_t workers[16];for(unsigned i=0;i<16;i++)assert(!pthread_create(&workers[i],0,claim_worker,0));
 for(unsigned i=0;i<16;i++)assert(!pthread_join(workers[i],0));assert(winners==1);
 assert(!madeira_cef64_hold_claim(0));madeira_cef64_hold_unclaim(0);assert(madeira_cef64_hold_claim(0));
 for(unsigned i=1;i<count;i++){assert(madeira_cef64_hold_get(i,&base,&size));assert(base==addresses[i]&&size==sizes[i]);assert(madeira_cef64_hold_claim(i));assert(!madeira_cef64_hold_claim(i));}
 assert(!madeira_cef64_hold_get(count,&base,&size)&&!madeira_cef64_hold_claim(count));
 return 0;
}
'''
code=code.replace('#include <pthread.h>', '#include <pthread.h>\n#include "'+str(root/'build/diagnostics/ideck_runtime_selection.h')+'"\nstatic int madeira_cfg_get(const char *key,char *out,size_t size){(void)key;(void)size;out[0]=0;return 0;}')
with tempfile.TemporaryDirectory() as d:
    p=Path(d);(p/'t.c').write_text(code)
    subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-pthread',str(p/'t.c'),'-o',str(p/'t')],check=True)
    for split in (0,1,2,3,4,5,6,7,8,9,10,11,12,13,14):
        for mode in range(6):
            for index in (range(20 if split==14 else 17 if split>=12 else 16 if split==11 else 15 if split==10 else 14 if split>=8 else 12 if split==7 else 11 if split==6 else 13 if split>=4 else 11 if split==3 else 9 if split==2 else 8 if split else 6) if mode in (1,2) else (0,)):
                subprocess.run([str(p/'t'),str(mode),str(index),str(split)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run([str(p/'t'),'12','0','8'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run([str(p/'t'),'14','0','9'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    for mode,split in [(15,6),(16,12),(17,11),(18,10),(19,12),(20,11),(21,11),(23,13)]:
        subprocess.run([str(p/'t'),str(mode),'0',str(split)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    for mode in (6,7,8,9,10,11,13):
        subprocess.run([str(p/'t'),str(mode),'0','6'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
print('PASS: actual production native boot holds, all-slot rollback, exact option+argument gates and16-thread single-claim race (ASan/UBSan); not device transfer validation')
