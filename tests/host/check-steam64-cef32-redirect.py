#!/usr/bin/env python3
"""Production UTF16 path/prefix gate tests; never tests real Steam IPC."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
code = r'''
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include "steam64_cef32_redirect.h"
static uint16_t input[1024], output[1024];
static void check(const char *s, int command, const char *expected) {
 size_t n=strlen(s);for(size_t i=0;i<n;++i)input[i]=(unsigned char)s[i];
 size_t got=steam64_cef32_path(output,1024,input,n,command);
 if(!expected) { assert(!got);return; }
 assert(got==strlen(expected));assert(output[got]==0);
 for(size_t i=0;i<got;++i)assert(output[i]==(unsigned char)expected[i]);
}
int main(void) {
 assert(steam64_cef32_enabled("1","1","/private/Documents/wine-steam64"));
 assert(!steam64_cef32_enabled("1","1","/private/Documents/wine"));
 assert(!steam64_cef32_enabled("1","1","/wine-steam64-other"));
 assert(!steam64_cef32_enabled("0","1","/wine-steam64"));
 assert(!steam64_cef32_enabled("1","0","/wine-steam64"));
 assert(!steam64_cef32_enabled(NULL,"1","/wine-steam64"));
 check("C:\\Program Files\\Steam\\bin\\cef\\cef.win64\\steamwebhelper.exe",0,
       "C:\\Program Files\\Steam\\bin\\cef\\cef.win7\\steamwebhelper.exe");
 check("\\??\\C:\\Program Files\\Steam\\bin\\cef\\cef.win64\\steamwebhelper.exe",0,
       "\\??\\C:\\Program Files\\Steam\\bin\\cef\\cef.win7\\steamwebhelper.exe");
 check("\"C:\\Program Files\\Steam\\bin\\cef\\cef.win64\\steamwebhelper.exe\" --x=\"a b\"",1,
       "\"C:\\Program Files\\Steam\\bin\\cef\\cef.win7\\steamwebhelper.exe\" --x=\"a b\"");
 check("c:/program files/steam/bin/cef/cef.win64/steamwebhelper.exe\t--x=1",1,
       "C:\\Program Files\\Steam\\bin\\cef\\cef.win7\\steamwebhelper.exe\t--x=1");
 check("D:\\Program Files\\Steam\\bin\\cef\\cef.win64\\steamwebhelper.exe",0,NULL);
 check("C:\\Program Files\\Steam\\bin\\cef\\cef.win64\\steamwebhelper.exe.other",0,NULL);
 check("C:\\Program Files\\Steam\\bin\\cef\\cef.win64\\steamwebhelper.exe.other x",1,NULL);
 check("\"C:\\Program Files\\Steam\\bin\\cef\\cef.win64\\steamwebhelper.exe --x",1,NULL);
 check("C:\\foo.exe --other=C:\\Program Files\\Steam\\bin\\cef\\cef.win64\\steamwebhelper.exe",1,NULL);
 const char *p="C:\\Program Files\\Steam\\bin\\cef\\cef.win64\\steamwebhelper.exe";
 size_t n=strlen(p);for(size_t i=0;i<n;++i)input[i]=(unsigned char)p[i];
 assert(!steam64_cef32_path(output,n-1,input,n,0));
 /* A Unicode argument after argv[0] must survive without interpretation. */
 input[n++]=' ';input[n++]=0x4e2d;input[n++]=0x6587;
 size_t got=steam64_cef32_path(output,1024,input,n,1);
 assert(got==n-1 && output[got-2]==0x4e2d && output[got-1]==0x6587);
 puts("PASS exact triple gates, NT/DOS UTF16 paths and lossless argv[0] redirect");
}
'''
with tempfile.TemporaryDirectory() as td:
    src=Path(td)/'test.c'; src.write_text(code)
    exe=Path(td)/'test'
    subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                    '-I',str(root/'build/ntdll-unix'),str(src),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
