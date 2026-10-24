#!/usr/bin/env python3
"""Execute production browser-only software-3D policy with ordinary/A-B cases."""
from pathlib import Path
import subprocess,tempfile
s=(Path(__file__).resolve().parents[2]/'build/ntdll-unix/process_ios.c').read_text()
a=s.index('                const char *software = getenv("MADEIRA_STEAM_UI_NO_SWIFTSHADER");')
b=s.index('                static const char dfs[]',a)
code=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
static void policy(int steam_ui,char *result) {
    const char *sp=" --single-process --js-flags=--jitless";
'''+s[a:b]+r'''
    strcpy(result,sp);
}
int main(void) {
    char result[512];
    unsetenv("MADEIRA_STEAM_UI_NO_SWIFTSHADER");
    policy(0,result);assert(!strstr(result,"disable-software-rasterizer"));
    policy(1,result);assert(!strstr(result,"--disable-software-rasterizer"));
    assert(strstr(result,"--js-flags=--jitless"));
    setenv("MADEIRA_STEAM_UI_NO_SWIFTSHADER","0",1);
    policy(1,result);assert(!strstr(result,"disable-software-rasterizer"));
    setenv("MADEIRA_STEAM_UI_NO_SWIFTSHADER","1",1);
    policy(0,result);assert(!strstr(result,"disable-software-rasterizer"));
    policy(1,result);assert(strstr(result,"--disable-software-rasterizer"));
    puts("PASS: production browser software-3D policy, isolated opt-in, explicit A/B opt-out, ordinary path and existing switches preserved");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(code)
 subprocess.run(['clang','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
