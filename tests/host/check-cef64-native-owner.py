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
static uint64_t addresses[6],sizes[6];
static int mach_task_self(void){return 7;}
static int vm_map(int task,vm_address_t *a,vm_size_t size,uint64_t mask,int flags,int object,
                  uint64_t off,int copy,int current,int maximum,int inherit){
 assert(task==7 && !mask && !flags && !object && !off && !copy && !current && inherit==2);
 unsigned index=calls++;assert(index<6 && maximum==(index==3?7:3));
 if(mode==1 && index==(unsigned)fail_at)return 3;
 if(mode==2 && index==(unsigned)fail_at)*a+=0x4000;
 for(unsigned i=0;i<6;i++)if(sizes[i])assert(*a>=addresses[i]+sizes[i] || addresses[i]>=*a+size);
 addresses[index]=*a;sizes[index]=size;live++;return 0;
}
static int vm_deallocate(int task,vm_address_t a,vm_size_t size){
 assert(task==7);unsigned i;for(i=0;i<6;i++)if(sizes[i]&&addresses[i]==a&&sizes[i]==size)break;
 assert(i<6);sizes[i]=0;live--;cleans++;return 0;
}
static char *fake_args[]={(char *)"app",(char *)"madeira-steam64-experiment",0};
static char **args=fake_args;
static int args_count=2;
static char ***_NSGetArgv(void){return &args;}
static int *_NSGetArgc(void){return &args_count;}
static const char *option="1";
static const char *fixture_getenv(const char *name){assert(!strcmp(name,"MADEIRA_CEF64_SOURCE_LAYOUT"));return option;}
#define getenv fixture_getenv
'''+slots+body+r'''
static unsigned winners;
static void *claim_worker(void *unused){(void)unused;if(madeira_cef64_hold_claim(0))__atomic_fetch_add(&winners,1,__ATOMIC_RELAXED);return 0;}
int main(int argc,char **argv){
 assert(argc==3);mode=atoi(argv[1]);fail_at=atoi(argv[2]);
 if(mode==3)option=0;
 if(mode==4)option="10";
 if(mode==5)args_count=1;
 ideck_cef64_boot_holds();
 uint64_t base,size;
 if(mode>=3){assert(!calls && !live && madeira_cef64_hold_state()==0);assert(!madeira_cef64_hold_claim(0));return 0;}
 if(mode){assert(madeira_cef64_hold_state()==-1 && !live && calls==fail_at+1 && cleans==fail_at+(mode==2));assert(!madeira_cef64_hold_claim(0));return 0;}
 assert(madeira_cef64_hold_state()==1 && calls==6 && live==6 && !cleans);
 pthread_t workers[16];for(unsigned i=0;i<16;i++)assert(!pthread_create(&workers[i],0,claim_worker,0));
 for(unsigned i=0;i<16;i++)assert(!pthread_join(workers[i],0));assert(winners==1);
 assert(!madeira_cef64_hold_claim(0));madeira_cef64_hold_unclaim(0);assert(madeira_cef64_hold_claim(0));
 for(unsigned i=1;i<6;i++){assert(madeira_cef64_hold_get(i,&base,&size));assert(base==addresses[i]&&size==sizes[i]);assert(madeira_cef64_hold_claim(i));assert(!madeira_cef64_hold_claim(i));}
 assert(!madeira_cef64_hold_get(6,&base,&size)&&!madeira_cef64_hold_claim(6));
 return 0;
}
'''
with tempfile.TemporaryDirectory() as d:
    p=Path(d);(p/'t.c').write_text(code)
    subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-pthread',str(p/'t.c'),'-o',str(p/'t')],check=True)
    for mode in range(6):
        for index in (range(6) if mode in (1,2) else (0,)):
            subprocess.run([str(p/'t'),str(mode),str(index)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
print('PASS: actual production native boot holds, all-slot rollback, exact option+argument gates and16-thread single-claim race (ASan/UBSan); not device transfer validation')
