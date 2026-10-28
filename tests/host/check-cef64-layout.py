#!/usr/bin/env python3
"""Exercise concurrent ownership/cleanup with Mach fixtures; no host VA mapped."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
fixture = r'''
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
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
#define VM_INHERIT_NONE 2
static const uint64_t vm_page_size = 0x4000;
static int mode, fail_at, calls, cleans, live, maximum_live, backing, protections, touches;
static uint64_t addresses[6], sizes[6];
static int mach_task_self(void) { return 7; }
static int vm_map(int task, vm_address_t *a, vm_size_t size, uint64_t mask, int flags, int object,
                  uint64_t off, int copy, int current, int maximum, int inherit) {
 assert(task==7 && !mask && !flags && !object && !off && !copy && !current && maximum==(backing?3:0) && inherit==2);
 int index=calls++;
 assert(index<6);
 if(mode==1 && index==fail_at) return 3;
 if(mode==2 && index==fail_at) *a+=0x4000;
 for(int i=0;i<live;i++) assert(*a>=addresses[i]+sizes[i] || addresses[i]>=*a+size);
 addresses[live]=*a;sizes[live++]=size;
 if(live>maximum_live) maximum_live=live;
 return 0;
}
static int vm_deallocate(int task, vm_address_t a, vm_size_t size) {
 assert(task==7 && live && addresses[live-1]==a && sizes[live-1]==size);
 live--;cleans++;return mode==3 && cleans==1?5:0;
}
static int vm_protect(int task, vm_address_t a, vm_size_t size, int maximum, int protection) {
 assert(task==7 && size==vm_page_size && !maximum && protection==3 && live==6);
 int index=protections++;
 int slot=index/2;assert(a>=addresses[slot] && a+size<=addresses[slot]+sizes[slot]);
 if(slot==1 || slot==4) assert(a>=addresses[slot]+0x10000);
 return mode==4 && index==fail_at?5:0;
}
static int touch_page(vm_address_t a,uint64_t tag) {
 (void)a;assert((tag>>32)==0x43454664);int index=touches++;return !(mode==5 && index==fail_at);
}
#define IDECK_CEF64_TOUCH_PAGE touch_page
#include "cef64_layout_probe.h"
int main(int argc,char **argv) {
 char *ordinary[]={"app",0},*explicit[]={"app","madeira-cef64-layout-diagnostics",0};
 assert(!ideck_cef64_layout_mode("1",1,ordinary));
 assert(!ideck_cef64_layout_mode("backing",1,ordinary));
 assert(!ideck_cef64_layout_mode(0,2,explicit));
 assert(!ideck_cef64_layout_mode("10",2,explicit));
 assert(ideck_cef64_layout_mode("1",2,explicit)==1);
 assert(ideck_cef64_layout_mode("backing",2,explicit)==2);
 assert(argc==4);mode=atoi(argv[1]);fail_at=atoi(argv[2]);backing=atoi(argv[3]);
 int result=madeira_cef64_layout_probe(stdout,backing);
 assert(!live);
 if(!mode) assert(result==0 && maximum_live==6 && calls==6 && cleans==6);
 if(mode==1) assert(result==1 && calls==fail_at+1 && cleans==fail_at);
 if(mode==2) assert(result==2 && calls==fail_at+1 && cleans==fail_at+1);
 if(mode==3) assert(result==3 && cleans==6);
 if(mode==4 || mode==5) assert(result==5 && cleans==6);
 if(!mode && backing) assert(protections==12 && touches==12);
 assert((ideck_cef64_slots[1].base+0x10000)%0x40000000==0);
 assert(ideck_cef64_slots[2].base%0x200000000==0);
 assert((ideck_cef64_slots[4].base+0x10000)%0x400000000==0);
 assert(ideck_cef64_slots[5].base%0x400000000==0);
 return 0;
}
'''
with tempfile.TemporaryDirectory() as d:
    p=Path(d);(p/'t.c').write_text(fixture)
    subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(root/'build/diagnostics'),str(p/'t.c'),'-o',str(p/'t')],check=True)
    for backing in (0,1):
        for mode in range(6 if backing else 4):
            for index in (range(6) if mode in (1,2) else range(12) if mode in (4,5) else (0,)):
                subprocess.run([str(p/'t'),str(mode),str(index),str(backing)],check=True,stdout=subprocess.DEVNULL)
text=(root/'app/Madeira/JITAllocator.c').read_text()
assert '"MADEIRA_CEF64_LAYOUT_PROBE"' in text and 'ideck_cef64_layout_mode(layout, argc, argv)' in text
print('PASS: six simultaneous full-sized disjoint reservations; optional own-page backing preserves guards; all-slot/edge failure/mismatch/cleanup cases (ASan/UBSan); no device claim')
