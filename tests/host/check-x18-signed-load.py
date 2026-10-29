#!/usr/bin/env python3
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'t.c').write_text('''#include "x18_signed_load.h"
#include <assert.h>
int main(void){int32_t a[]={0,1,-1,INT32_MIN,INT32_MAX};uint64_t v=0;
for(int i=0;i<5;i++){assert(ios_x18_ldrsw(0xb9980e48,(uintptr_t)&a[i],&v));assert(v==(uint64_t)(int64_t)a[i]);}
assert(ios_x18_ldrsw(0xb9980e5f,(uintptr_t)&a[2],&v));
assert(!ios_x18_ldrsw(0xb9580e48,0,&v));assert(!ios_x18_ldrsw(0xf9980e48,0,&v));}
''');subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I',str(r/'build/ntdll-unix'),str(p/'t.c'),'-o',str(p/'test')],check=True);subprocess.run([str(p/'test')],check=True)
print('PASS exact device LDRSW opcode, signed 32-to-64 semantics, XZR and nonmatching opcode rejection (ASan/UBSan)')
