#!/usr/bin/env python3
"""Execute production spill-order policy with checked occupied-range fixtures."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
s=(root/'build/ntdll-unix/virtual_ios.c').read_text()
a=s.index('static NTSTATUS ios_steam_ui_steer_allocate(')
f=s[a:s.index('\n}\n',a)+3]
h=r'''
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <assert.h>
typedef uintptr_t ULONG_PTR; typedef size_t SIZE_T; typedef unsigned ULONG,NTSTATUS;
static const ULONG_PTR ios_steer_slot=0x7c00000000ULL,ios_spill_cap=0x7800000000ULL;
static void *host_addr_space_limit=(void*)0x8000000000ULL;
static int calls,occupied_low,occupied_high; static ULONG_PTR seen[2];
static NTSTATUS allocate_virtual_memory(void **p,SIZE_T *sz,ULONG t,ULONG prot,ULONG_PTR lo,ULONG_PTR hi,int a,int b) {
 assert(t==0x2000 && prot==1 && !a && !b); assert(*p==0 && *sz==0x1ffff000);
 assert(hi>lo && *sz<hi-lo); seen[calls++]=lo;
 if((lo==0x7400000000ULL && occupied_low)||(lo==ios_steer_slot && occupied_high)) {
   *p=(void*)0xdead; *sz=0x123; return 0xc0000017;
 }
 *p=(void*)lo; return 0;
}
'''+f+r'''
static void test(const char *session,const char *opt,int low,int high,ULONG_PTR first,ULONG_PTR second) {
 if(session)setenv("MADEIRA_STEAM_UI_SESSION",session,1);else unsetenv("MADEIRA_STEAM_UI_SESSION");
 if(opt)setenv("MADEIRA_STEAM_UI_GUEST_SPILL_FIRST",opt,1);else unsetenv("MADEIRA_STEAM_UI_GUEST_SPILL_FIRST");
 calls=0;occupied_low=low;occupied_high=high;void *p=0;SIZE_T size=0x1ffff000;
 NTSTATUS st=ios_steam_ui_steer_allocate(&p,&size,0x2000,1);
 assert(seen[0]==first);
 if(second){assert(calls==2 && seen[1]==second);}else assert(calls==1);
 if(low && high)assert(st==0xc0000017);else {assert(!st);assert((uintptr_t)p==seen[calls-1]);assert(size==0x1ffff000);}
}
int main(void) {
 test(NULL,NULL,0,0,ios_steer_slot,0);
 test("0",NULL,0,0,ios_steer_slot,0);
 test("true",NULL,0,0,ios_steer_slot,0);
 test("1","0",0,0,ios_steer_slot,0);
 test("1",NULL,0,0,0x7400000000ULL,0);
 test("1",NULL,1,0,0x7400000000ULL,ios_steer_slot);
 test("1",NULL,1,1,0x7400000000ULL,ios_steer_slot);
 test(NULL,NULL,0,1,ios_steer_slot,0x7400000000ULL);
 puts("PASS: production isolated guest-first order, ordinary/opt-out preservation, occupied-range fallback, restored retry inputs, honest failure");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(h)
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
assert s.count('ios_steam_ui_steer_allocate(ret, size_ptr, type, protect)')==2
