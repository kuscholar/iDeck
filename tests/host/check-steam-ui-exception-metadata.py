#!/usr/bin/env python3
"""Exercise the production exception-record filter; no guest payload is printed."""
from pathlib import Path
import tempfile,subprocess
s=(Path(__file__).resolve().parents[2]/'build/ntdll-unix/virtual_ios.c').read_text()
a=s.index('static const char *ios_steam_ui_cpp_category(');b=s.index('NTSTATUS WINAPI NtReadVirtualMemory(',a)
code='#include <string.h>\n#include <stddef.h>\n#include <assert.h>\ntypedef size_t SIZE_T;\n'+s[a:b]+r'''
int main(void) {
 unsigned r[20]={0},code=0,pc=0;
 assert(!strcmp(ios_steam_ui_cpp_category(".?AVbad_alloc@std@@"), "bad_alloc"));
 assert(!strcmp(ios_steam_ui_cpp_category(".?AVbad_alloc@__Cr@std@@"), "bad_alloc"));
 assert(!strcmp(ios_steam_ui_cpp_category(".?AVruntime_error@__1@std@@"), "runtime_error"));
 assert(!strcmp(ios_steam_ui_cpp_category(".?AVbad_alloc_user@std@@"), "unknown"));
 assert(!strcmp(ios_steam_ui_cpp_category("private message"), "unknown"));
 assert(!ios_steam_ui_exception32_metadata(r,80,&code,&pc));
 r[0]=0xc0000005U;r[3]=0x12345678;r[4]=2;
 assert(ios_steam_ui_exception32_metadata(r,80,&code,&pc));assert(code==r[0]&&pc==r[3]);
 assert(!ios_steam_ui_exception32_metadata(r,79,&code,&pc));
 assert(!ios_steam_ui_exception32_metadata(r,81,&code,&pc));
 r[4]=16;assert(!ios_steam_ui_exception32_metadata(r,80,&code,&pc));
 r[4]=15;r[0]=0x0517a7ed;
 assert(ios_steam_ui_exception32_metadata(r,80,&code,&pc));
 r[0]=0x41424344;assert(!ios_steam_ui_exception32_metadata(r,80,&code,&pc));
 return 0;
}
'''
with tempfile.TemporaryDirectory() as temp:
 p=Path(temp);(p/'test.c').write_text(code)
 subprocess.run(['clang','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS: production exception metadata filter, exact size, public code allowlist, bounded parameter count (ASan/UBSan)')
