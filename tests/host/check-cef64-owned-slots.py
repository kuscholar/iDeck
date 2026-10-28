#!/usr/bin/env python3
"""Exercise production request routing, not a simulated Steam success."""
from pathlib import Path
import subprocess
import tempfile

root=Path(__file__).resolve().parents[2]
code=r'''
#include <assert.h>
#include "cef64_owned_slots.h"
static int name(const char *s){uint16_t path[128];unsigned n=0;for(;s[n];n++)path[n]=(unsigned char)s[n];return cef64_owned_caller(path,n);}
int main(void){
assert(name("C:\\Steam\\bin\\cef\\cef.win64\\SteamWebHelper.EXE"));
assert(name("C:\\steam64-cef-load-probe.exe"));
assert(!name("C:\\steam.exe"));assert(!name("C:\\notsteamwebhelper.exe"));
assert(!name("C:\\steamwebhelper.exe.bak"));assert(!cef64_owned_caller(0,7));
const uint64_t size[]={0x40000000ULL,0x40010000ULL,0x200000000ULL,0x400010000ULL,0x400000000ULL};
const int slots[]={0,1,2,4,5};
for(unsigned i=0;i<5;i++){
assert(cef64_owned_slot(0,size[i],0x2000,1,0,0,0,0)==slots[i]);
assert(cef64_owned_slot(0,size[i],0x102000,1,0,0,0,0)==slots[i]);
assert(cef64_owned_slot(0,size[i],0x3000,1,0,0,0,0)<0);
assert(cef64_owned_slot(0,size[i],0x2000,4,0,0,0,0)<0);
assert(cef64_owned_slot(0,size[i],0x2000,1,0,0,0,1)<0);
assert(cef64_owned_slot(0,size[i]-4096,0x2000,1,0,0,0,0)<0);
}
assert(cef64_owned_slot(0x42ffff0000ULL,0x40010000ULL,0x2000,1,0,0,0,0)==1);
assert(cef64_owned_slot(0x77ffff0000ULL,0x400010000ULL,0x2000,1,0,0,0,0)==4);
assert(cef64_owned_slot(0x7800000000ULL,0x400010000ULL,0x2000,1,0,0,0,0)<0);
assert(cef64_owned_slot(0x7100010000ULL,0x40000000ULL,0x2000,1,0,0,0,0)<0);
return 0;
}
'''
with tempfile.TemporaryDirectory() as d:
    p=Path(d);(p/'t.c').write_text(code)
    subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(root/'build/ntdll-unix'),str(p/'t.c'),'-o',str(p/'t')],check=True)
    subprocess.run([str(p/'t')],check=True)
src=(root/'build/ntdll-unix/virtual_ios.c').read_text()
adopt=src.split('static int ios_cef64_adopt_view',1)[1].split('static NTSTATUS allocate_virtual_memory',1)[0]
assert 'find_view_range' in adopt and 'held_size != size' in adopt and 'create_view' in adopt
assert 'madeira_cef64_hold_claim' in adopt and 'madeira_cef64_hold_unclaim' in adopt
assert 'mmap(' not in adopt and 'munmap(' not in adopt and 'mprotect(' not in adopt
assert 'no-overwrite' not in adopt or 'OVERWRITE' not in adopt
assert '!sc_helper && !ios_cef64_owned_layout()' in src
print('PASS: exact browser/probe identity, reserve-only protection/type/size/guard shape; checked real-view adoption integration and soft-fallback refusal (ASan/UBSan); no runtime proof')
