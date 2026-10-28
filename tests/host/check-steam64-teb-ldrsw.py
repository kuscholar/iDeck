#!/usr/bin/env python3
"""Observed native instruction fixture; exact gate and signed-value semantics."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
header=root/'build/ntdll-unix/steam64_teb_ldrsw.h'
body=r'''
int main(void){
 const char *p="/private/test/wine-steam64";
 const uint32_t observed=0xb9980e48; /* ldrsw x8,[x18,#0x180c] */
 assert(steam64_teb_ldrsw_matches("1",p,observed,0,0x180c));
 assert(!steam64_teb_ldrsw_matches(NULL,p,observed,0,0x180c));
 assert(!steam64_teb_ldrsw_matches("0",p,observed,0,0x180c));
 assert(!steam64_teb_ldrsw_matches("1",NULL,observed,0,0x180c));
 assert(!steam64_teb_ldrsw_matches("1","/private/wine",observed,0,0x180c));
 assert(!steam64_teb_ldrsw_matches("1","/private/wine-steam64-old",observed,0,0x180c));
 assert(!steam64_teb_ldrsw_matches("1",p,observed,0x7900300000,0x180c));
 assert(!steam64_teb_ldrsw_matches("1",p,observed,0,0x1808));
 assert(!steam64_teb_ldrsw_matches("1",p,observed^(1u<<5),0,0x180c));
 assert(!steam64_teb_ldrsw_matches("1",p,observed^(1u<<22),0,0x180c));
 assert(!steam64_teb_ldrsw_matches("1",p,observed^(1u<<10),0,0x180c));
 assert(steam64_teb_ldrsw_value(0x2000)==0x2000);
 assert(steam64_teb_ldrsw_value(-0x2000)==UINT64_C(0xffffffffffffe000));
 assert(steam64_teb_ldrsw_value(INT32_MIN)==UINT64_C(0xffffffff80000000));
 assert(steam64_teb_ldrsw_value(INT32_MAX)==INT32_MAX);
 puts("PASS: observed native LDRSW exact own-field lab gate, negative cases and 64bit sign extension (ASan/UBSan)");
}
'''
with tempfile.TemporaryDirectory() as d:
 d=Path(d);c=d/'main.c';c.write_text('#include <assert.h>\n#include <stdio.h>\n#include "'+str(header)+'"\n'+body)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(c),'-o',str(d/'check')],check=True)
 subprocess.run([str(d/'check')],check=True)
