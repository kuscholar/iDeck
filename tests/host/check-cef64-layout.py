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
static int count, mode, fail_at, calls, cleans, live, maximum_live, backing, protections, touches;
static uint64_t addresses[20], sizes[20];
static int mach_task_self(void) { return 7; }
static int vm_map(int task, vm_address_t *a, vm_size_t size, uint64_t mask, int flags, int object,
                  uint64_t off, int copy, int current, int maximum, int inherit) {
 assert(task==7 && !mask && !flags && !object && !off && !copy && !current && maximum==(backing?3:0) && inherit==2);
 int index=calls++;
 assert(index<count);
 if(mode==1 && index==fail_at) return 3;
 if(mode==2 && index==fail_at) *a+=UINT64_C(0x100000000000);
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
 assert(task==7 && size==vm_page_size && !maximum && protection==3 && live==count);
 int index=protections++;
 int slot=index/2;assert(a>=addresses[slot] && a+size<=addresses[slot]+sizes[slot]);
 if((sizes[slot]&UINT64_C(0x3fffffff))==0x10000) assert(a>=addresses[slot]+0x10000);
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
 assert(argc==5);mode=atoi(argv[1]);fail_at=atoi(argv[2]);backing=atoi(argv[3]);int split=atoi(argv[4]);count=split==14?20:split>=12?17:split==11?16:split==10?15:split>=8?14:split==7?12:split==6?11:split>=4?13:split==3?11:split==2?9:split?8:6;
 assert(ideck_cef64_layout_mode("split-backing",2,explicit)==3);
 assert(ideck_cef64_layout_mode("table-backing",2,explicit)==6);
 assert(ideck_cef64_layout_mode("wide-backing",2,explicit)==7);
 assert(ideck_cef64_layout_mode("standalone-backing",2,explicit)==8);
 struct ideck_cef64_slot wide[13];ideck_cef64_fill_wide_slots(wide);
 for(unsigned i=0;i<13;i++){if(i==3){assert(wide[i].base==UINT64_C(0x6000000000)&&wide[i].size==UINT64_C(0x1000000000));}else assert(wide[i].base==ideck_cef64_table_slots[i].base&&wide[i].size==ideck_cef64_table_slots[i].size);}
 assert(ideck_cef64_layout_mode("standalone-four-backing",2,explicit)==9);
 assert(ideck_cef64_layout_mode("standalone-six-backing",2,explicit)==10);
 struct ideck_cef64_slot tail[14];ideck_cef64_fill_tail_six_slots(tail);
 assert(tail[3].size==UINT64_C(0x280000000));
 assert(tail[3].base+tail[3].size==tail[12].base && tail[12].base+tail[12].size==tail[13].base);
 assert(tail[13].base+tail[13].size==tail[11].base);
 for(unsigned i=0;i<14;i++)assert(tail[i].base>=UINT64_C(0x7100000000)||i==7);
 assert(ideck_cef64_layout_mode("standalone-tail-six-backing",2,explicit)==11);
 struct ideck_cef64_slot seven[15];ideck_cef64_fill_seven_slots(seven);
 assert(seven[3].size==UINT64_C(0x260000000));
 assert(seven[3].base+seven[3].size==seven[14].base && seven[14].base+seven[14].size==seven[12].base);
 assert(ideck_cef64_layout_mode("standalone-seven-backing",2,explicit)==12);
 struct ideck_cef64_slot eight[16];ideck_cef64_fill_eight_slots(eight);
 assert(eight[3].size==UINT64_C(0x240000000));
 assert(eight[3].base+eight[3].size==eight[15].base && eight[15].base+eight[15].size==eight[14].base);
 assert(ideck_cef64_layout_mode("standalone-eight-backing",2,explicit)==13);
 struct ideck_cef64_slot compact[17];ideck_cef64_fill_compact_slots(compact);
 assert(ideck_cef64_layout_mode("standalone-compact-nine-backing",2,explicit)==14);
 assert(!ideck_cef64_layout_mode("standalone-compact-nine-backing",1,ordinary));
 assert(compact[3].base==eight[3].base && compact[3].size==eight[3].size);
 assert(compact[0].base%compact[0].size==0 && (compact[1].base+0x10000)%0x40000000==0);
 assert(compact[1].base+compact[1].size==compact[0].base);
 assert(compact[0].base+compact[0].size==compact[8].base);
 assert(compact[8].base+compact[8].size==compact[16].base);
 assert(compact[16].base+compact[16].size==compact[9].base);
 for(unsigned i=0;i<16;i++)if(i!=0 && i!=1 && i!=8)assert(compact[i].base==eight[i].base&&compact[i].size==eight[i].size);
 struct ideck_cef64_slot nine[17];ideck_cef64_fill_tail_nine_slots(nine);
 assert(ideck_cef64_layout_mode("standalone-tail-nine-backing",2,explicit)==15);
 assert(!ideck_cef64_layout_mode("standalone-tail-nine-backing",1,ordinary));
 assert(nine[3].base+ nine[3].size==nine[16].base && nine[16].base+nine[16].size==nine[15].base);
 for(unsigned i=0;i<16;i++)if(i!=3)assert(nine[i].base==eight[i].base&&nine[i].size==eight[i].size);
 assert(nine[8].base+nine[8].size==UINT64_C(0x7160000000) && nine[1].base==UINT64_C(0x717fff0000));
 struct ideck_cef64_slot twelve[20];ideck_cef64_fill_tail_twelve_slots(twelve);
 assert(ideck_cef64_layout_mode("standalone-tail-twelve-backing",2,explicit)==16);
 assert(!ideck_cef64_layout_mode("standalone-tail-twelve-backing",1,ordinary));
 assert(twelve[3].base+twelve[3].size==twelve[19].base);
 for(unsigned i=0;i<17;i++)if(i!=3)assert(twelve[i].base==nine[i].base&&twelve[i].size==nine[i].size);
 int result=split==14?madeira_cef64_tail_twelve_layout_probe(stdout,backing):split==13?madeira_cef64_tail_nine_layout_probe(stdout,backing):split==12?madeira_cef64_compact_layout_probe(stdout,backing):split==11?madeira_cef64_eight_layout_probe(stdout,backing):split==10?madeira_cef64_seven_layout_probe(stdout,backing):split==9?madeira_cef64_tail_six_layout_probe(stdout,backing):split==8?madeira_cef64_six_layout_probe(stdout,backing):split==7?madeira_cef64_four_layout_probe(stdout,backing):split==6?madeira_cef64_standalone_layout_probe(stdout,backing):split==5?madeira_cef64_wide_layout_probe(stdout,backing):split==4?madeira_cef64_table_layout_probe(stdout,backing):split==3?madeira_cef64_crash_layout_probe(stdout,backing):split==2?madeira_cef64_near_layout_probe(stdout,backing):split?madeira_cef64_split_layout_probe(stdout,backing):madeira_cef64_layout_probe(stdout,backing);
 assert(!live);
 if(!mode) assert(result==0 && maximum_live==count && calls==count && cleans==count);
 if(mode==1) assert(result==1 && calls==fail_at+1 && cleans==fail_at);
 if(mode==2) assert(result==2 && calls==fail_at+1 && cleans==fail_at+1);
 if(mode==3) assert(result==3 && cleans==count);
 if(mode==4 || mode==5) assert(result==5 && cleans==count);
 if(!mode && backing) assert(protections==count*2 && touches==count*2);
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
    for split in (0,1,2,3,4,5,6,7,8,9,10,11,12,13,14):
        count=20 if split==14 else 17 if split>=12 else 16 if split==11 else 15 if split==10 else 14 if split>=8 else 12 if split==7 else 11 if split==6 else 13 if split>=4 else 11 if split==3 else 9 if split==2 else 8 if split else 6
        for backing in (0,1):
            for mode in range(6 if backing else 4):
                for index in (range(count) if mode in (1,2) else range(count*2) if mode in (4,5) else (0,)):
                    subprocess.run([str(p/'t'),str(mode),str(index),str(backing),str(split)],check=True,stdout=subprocess.DEVNULL)
text=(root/'app/Madeira/JITAllocator.c').read_text()
assert '"MADEIRA_CEF64_LAYOUT_PROBE"' in text and 'ideck_cef64_layout_mode(layout, argc, argv)' in text
print('PASS: original6, split8, near9, crash11 and three-table13/wide-FEX13 simultaneous disjoint reservations; optional page backing; all-slot/edge failure/mismatch/cleanup (ASan/UBSan); no device claim')
