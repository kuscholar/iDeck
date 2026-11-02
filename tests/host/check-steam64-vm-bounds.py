#!/usr/bin/env python3
"""Run the actual native sampling routine against a constrained Mach fixture."""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
text = (root / 'build/diagnostics/steam_ui_vm_probe.h').read_text()
start = text.index('static int madeira_steam64_vm_bounds(')
code = text[start:text.index('static int madeira_steam_ui_vm_probe(', start)]
fixture = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef uint64_t vm_address_t,vm_size_t;
typedef int kern_return_t;
#define KERN_SUCCESS 0
#define VM_FLAGS_FIXED 0
#define MEMORY_OBJECT_NULL 0
#define FALSE 0
#define VM_PROT_NONE 0
#define VM_INHERIT_NONE 0
static unsigned mode,calls,cleanups,active;
static uint64_t owned,size_owned;
static int mach_task_self(void){return 7;}
static int vm_map(int task,uint64_t *base,uint64_t size,int mask,int flags,int object,
                  int offset,int copy,int prot,int max,int inherit){
 assert(task==7&&!mask&&!flags&&!object&&!offset&&!copy&&!prot&&!max&&!inherit&&!active);
 calls++;uint64_t floor=UINT64_C(0x7000000000),limit=floor+UINT64_C(0x180000000);
 assert(*base>=floor&&*base<floor+UINT64_C(0x200000000));
 assert(size && size<=UINT64_C(0x200000000));
 if(*base>=limit||size>limit-*base)return 1; /* Invalid address, not collision. */
 if(mode==1 && *base<=floor+0x80000 && size>floor+0x80000-*base)return 3;
 if(mode==2)*base+=0x10000;
 active=1;owned=*base;size_owned=size;return 0;
}
static int vm_deallocate(int task,uint64_t base,uint64_t size){
 assert(task==7&&active&&base==owned&&size==size_owned);cleanups++;
 if(mode==3)return 5;
 active=0;return 0;
}
''' + code + r'''
int main(void){
 for(mode=0;mode<4;mode++){
  calls=cleanups=active=0;FILE *f=tmpfile();assert(f);
  int result=madeira_steam64_vm_bounds(f);fflush(f);rewind(f);
  char out[20000];size_t n=fread(out,1,sizeof(out)-1,f);out[n]=0;fclose(f);
  if(mode==0){assert(!result&&calls==64&&cleanups==48&&!active);
   assert(strstr(out,"complete=1 successes=48 largest-tested-prefix=0x180000000"));}
  if(mode==1){assert(!result&&calls==64&&cleanups==24&&!active);
   assert(strstr(out,"kr=3"));assert(strstr(out,"largest-tested-prefix=0x0"));}
  if(mode==2)assert(result==3&&calls==1&&cleanups==1&&!active);
  if(mode==3)assert(result==2&&calls==1&&cleanups==1&&active);
 }
 puts("PASS production native bounds sampler: 64 bounded no-overwrite/no-access calls, exact cleanup, collision/invalid-address distinction, unexpected address and cleanup-failure stop (ASan/UBSan)");
}
'''
with tempfile.TemporaryDirectory(prefix='ideck-vm-bounds-') as td:
    source, binary = Path(td) / 'test.c', Path(td) / 'test'
    source.write_text(fixture)
    subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', str(source), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True, env={**os.environ, 'UBSAN_OPTIONS': 'halt_on_error=1'})
