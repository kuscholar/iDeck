#!/usr/bin/env python3
"""Run the production adopter against actual twelve-table native geometry.

Fixtures replace only kernel/view services. No actual host/device VA is mapped.
"""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'build/ntdll-unix/virtual_ios.c').read_text()
start = source.index('static int ios_cef64_adopt_view(')
adopt = source[start:source.index('static NTSTATUS allocate_virtual_memory', start)]
layout = (root / 'build/diagnostics/cef64_layout_probe.h').read_text()
geometry = layout[layout.index('struct ideck_cef64_slot'):layout.index('#ifndef IDECK_CEF64_TOUCH_PAGE')]
fixture = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "cef64_owned_slots.h"
#define ios_cef64_record_lease(...) ((void)0) /* Separate writer test; no host VM changes. */
typedef uint32_t ULONG, NTSTATUS;
typedef uint64_t SIZE_T, ULONG_PTR;
typedef uint16_t WCHAR;
typedef struct { struct { WCHAR *Buffer; uint16_t Length; } ImagePathName, CommandLine; } RTL_USER_PROCESS_PARAMETERS;
typedef struct { RTL_USER_PROCESS_PARAMETERS *ProcessParameters; } PEB;
struct file_view { uint64_t base, size; };
#define STATUS_NO_MEMORY UINT32_C(0xc0000017)
''' + geometry + r'''
static struct ideck_cef64_slot slots[20];
static struct file_view views[20];
static unsigned claims, live, fail_create;
static RTL_USER_PROCESS_PARAMETERS pp;
static PEB peb={&pp};
static int ios_cef64_owned_layout(void){return 1;}
static int madeira_cef64_standalone_layout(void){return 1;}
static PEB *ios_jit_current_peb(void){return &peb;}
static int madeira_cef64_hold_get(unsigned n,uint64_t *b,uint64_t *z){
 assert(n<20);*b=slots[n].base;*z=slots[n].size;return 1;
}
static int madeira_cef64_hold_claim(unsigned n){
 assert(n<20);unsigned bit=1u<<n;if(claims&bit)return 0;claims|=bit;return 1;
}
static void madeira_cef64_hold_unclaim(unsigned n){
 assert(n<20 && (claims&(1u<<n)));claims&=~(1u<<n);
}
static int find_view_range(void *base,SIZE_T size){
 uint64_t b=(uintptr_t)base;
 for(unsigned i=0;i<20;i++)if((live&(1u<<i)) && b<views[i].base+views[i].size && views[i].base<b+size)return 1;
 return 0;
}
static NTSTATUS create_view(struct file_view **out,void *base,SIZE_T size,unsigned protect){
 assert(protect==5);unsigned i;
 for(i=0;i<20;i++)if((uintptr_t)base==slots[i].base)break;
 assert(i<20 && size==slots[i].size && (claims&(1u<<i)));
 if(fail_create)return STATUS_NO_MEMORY;
 views[i]=(struct file_view){(uintptr_t)base,size};live|=1u<<i;*out=&views[i];return 0;
}
''' + adopt + r'''
static void reset(void){
 static WCHAR name[]={'C',':','\\','s','t','e','a','m','w','e','b','h','e','l','p','e','r','.','e','x','e'};
 pp.ImagePathName.Buffer=name;pp.ImagePathName.Length=sizeof(name);
 claims=live=fail_create=0;memset(views,0,sizeof(views));ideck_cef64_fill_tail_twelve_slots(slots);
}
static NTSTATUS allocate(void **base,ULONG_PTR low,ULONG_PTR high,ULONG_PTR alignment){
 struct file_view *view=0;NTSTATUS status=0x1234;
 assert(ios_cef64_adopt_view(&view,base,0x20000000,0x42000,1,5,low,high,alignment,0,&status));
 if(!status)assert(view && (uintptr_t)*base==view->base);
 return status;
}
int main(void){
 reset();
 (void)ideck_cef64_slots;(void)ideck_cef64_split_slots;(void)ideck_cef64_near_slots;(void)ideck_cef64_crash_slots;
 for(unsigned i=0;i<20;i++)for(unsigned j=0;j<i;j++)assert(slots[i].base>=slots[j].base+slots[j].size || slots[j].base>=slots[i].base+slots[i].size);
 assert(slots[3].base+slots[3].size==slots[19].base);
 for(unsigned i=8;i<20;i++){
  void *base=0;assert(!allocate(&base,0,0,0));assert((uintptr_t)base==slots[i].base);
 }
 void *base=0;assert(allocate(&base,0,0,0)==STATUS_NO_MEMORY);
 /* Removing a view alone must never reset the native claim. */
 live=0;base=0;assert(allocate(&base,0,0,0)==STATUS_NO_MEMORY);
 for(unsigned i=8;i<20;i++){
  reset();base=(void*)(uintptr_t)slots[i].base;assert(!allocate(&base,0,0,0));assert((uintptr_t)base==slots[i].base);
 }
 for(unsigned failed=8;failed<20;failed++){
  reset();
  for(unsigned i=8;i<failed;i++){base=0;assert(!allocate(&base,0,0,0));}
  unsigned old=claims;fail_create=1;base=0;assert(allocate(&base,0,0,0)==STATUS_NO_MEMORY && claims==old);
  fail_create=0;assert(!allocate(&base,0,0,0) && (uintptr_t)base==slots[failed].base);
 }
 reset();base=0;assert(allocate(&base,UINT64_C(0x7800000000),0,0)==STATUS_NO_MEMORY && !claims);
 base=0;assert(allocate(&base,0,UINT64_C(0x7000000000),0)==STATUS_NO_MEMORY && !claims);
 puts("PASS actual twelve-table geometry/adopter: disjointness, every fixed hint, exhaustion, retained claims, all-slot create rollback and bounds (ASan/UBSan); no device claim");
}
'''
with tempfile.TemporaryDirectory() as directory:
    p = Path(directory)
    (p / 't.c').write_text(fixture)
    subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                    '-fsanitize=address,undefined', '-I'+str(root/'build/ntdll-unix'),
                    str(p/'t.c'), '-o', str(p/'t')], check=True)
    subprocess.run([str(p/'t')], check=True)
