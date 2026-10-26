#!/usr/bin/env python3
"""Production machine-list policy: isolation, capacity, duplicate and identity."""
from pathlib import Path
import subprocess,tempfile,os
root=Path(__file__).resolve().parents[2]
program=r'''
#include <assert.h>
#include <string.h>
#include "steam_ui_machines.h"
int main(void) {
 unsigned short a[8]={0xaa64,0x14c,0x1c4}, original[8];unsigned n=3;
 memcpy(original,a,sizeof(a));
 assert(!ideck_advertise_amd64_guest(a,&n,8,0));
 assert(!ideck_advertise_amd64_guest(a,&n,8,"0"));
 assert(!ideck_advertise_amd64_guest(a,&n,8,"10"));
 assert(n==3&&!memcmp(a,original,sizeof(a)));
 assert(ideck_advertise_amd64_guest(a,&n,8,"1"));
 assert(n==4&&a[0]==0xaa64&&a[1]==0x14c&&a[2]==0x1c4&&a[3]==0x8664);
 assert(!ideck_advertise_amd64_guest(a,&n,8,"1")&&n==4);
 n=3;memcpy(a,original,sizeof(a));assert(!ideck_advertise_amd64_guest(a,&n,3,"1"));
 assert(n==3&&!memcmp(a,original,sizeof(a)));
 n=0;assert(!ideck_advertise_amd64_guest(a,&n,8,"1"));
 n=3;a[0]=0x8664;assert(!ideck_advertise_amd64_guest(a,&n,8,"1"));
 return 0;
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'test.c').write_text(program)
 subprocess.run([os.getenv('CC','clang'),'-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(root/'build/wineserver'),str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
build=(root/'build/wineserver/build.sh').read_text()
assert '"registry_ios:registry_ios.c:registry.o"' in build
assert '"registry_ios.o:registry.o"' in build
print('PASS: isolated AMD64 enumeration, native identity, duplicate/capacity guards and archive replacement')
