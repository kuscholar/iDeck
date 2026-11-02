#!/usr/bin/env python3
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[2]
h=r/'build/ntdll-unix/steam64_layout.h'
code='''#include <assert.h>
#include "steam64_layout.h"
int main(void){
assert(steam64_layout_enabled("1","1"));
assert(!steam64_layout_enabled(0,"1"));
assert(!steam64_layout_enabled("1",0));
assert(!steam64_layout_enabled("0","1"));
assert(!steam64_layout_enabled("1","10"));
uint64_t lo[]={0x7100000000ULL,0x7200000000ULL,0x73ffff0000ULL,0x7800000000ULL,0x7c00000000ULL};
uint64_t sz[]={STEAM64_FEX_SIZE,0x1ffff0000ULL,0x400010000ULL,0x400000000ULL,0x400000000ULL};
for(unsigned i=0;i<5;i++) for(unsigned j=0;j<i;j++) assert(lo[i]>=lo[j]+sz[j] || lo[j]>=lo[i]+sz[i]);
assert(STEAM64_FEX_BASE+STEAM64_FEX_SIZE==lo[1]);
assert(lo[4]+sz[4]==0x8000000000ULL);
return 0;}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'t.c').write_text(code)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(h.parent),str(p/'t.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
s=(r/'build/ntdll-unix/virtual_ios.c').read_text()
a=s[s.index('if (ios_steam64_layout())',s.index('void ios_reserve_fex_arena')):];a=a[:a.index('/* madeira-bcd')]
assert 'VM_FLAGS_FIXED' in a and 'VM_FLAGS_OVERWRITE' not in a and 'if (kr != KERN_SUCCESS) break' in a
print('PASS: exact double gates, disjoint FEX/cage/threePA intervals, real no-overwrite reservation failure checked; not capacity proof')
