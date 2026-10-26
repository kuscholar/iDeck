#!/usr/bin/env python3
"""Compile production path/override/size policy; no game or device needed."""
from pathlib import Path
import subprocess,tempfile
s=(Path(__file__).resolve().parents[2]/'build/ntdll-unix/process_ios.c').read_text()
a=s.index('static int ios_ratatan_fullscreen_args(');f=s[a:s.index('\n}\n',a)+3]
h=r'''
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
typedef uint16_t WCHAR;
'''+f+r'''
static void wide(WCHAR *out,const char *s) {while(*s)*out++=(unsigned char)*s++;*out=0;}
int main(void) {
 WCHAR image[256],cmd[256];char out[160];
 wide(image,"C:\\Steam32BundleLab\\steamapps\\common\\Ratatan\\game.exe");wide(cmd,"game.exe -job-worker-count 2");
 assert(ios_ratatan_fullscreen_args("1",image,strlen("C:\\Steam32BundleLab\\steamapps\\common\\Ratatan\\game.exe"),cmd,strlen("game.exe -job-worker-count 2"),1424,656,out,sizeof(out)));
 assert(!strcmp(out,"-screen-fullscreen 1 -window-mode borderless -popupwindow -screen-width 1424 -screen-height 656"));
 int len=0;while(image[len])len++;
 assert(!ios_ratatan_fullscreen_args(NULL,image,len,cmd,28,1424,656,out,sizeof(out)));
 assert(!ios_ratatan_fullscreen_args("0",image,len,cmd,28,1424,656,out,sizeof(out)));
 assert(!ios_ratatan_fullscreen_args("1",image,len,cmd,28,1,656,out,sizeof(out)));
 assert(!ios_ratatan_fullscreen_args("1",image,len,cmd,28,1424,656,out,4));
 wide(cmd,"game.exe -SCREEN-FULLSCREEN 0");int cl=0;while(cmd[cl])cl++;
 assert(!ios_ratatan_fullscreen_args("1",image,len,cmd,cl,1424,656,out,sizeof(out)));
 wide(image,"C:/Steam32BundleLab/steamapps/common/RATATAN/game.exe");len=0;while(image[len])len++;
 assert(ios_ratatan_fullscreen_args("1",image,len,NULL,0,1424,656,out,sizeof(out)));
 wide(image,"C:\\OtherGame\\game.exe");len=0;while(image[len])len++;
 assert(!ios_ratatan_fullscreen_args("1",image,len,NULL,0,1424,656,out,sizeof(out)));
 wide(image,"C:\\steamapps\\common\\NotRatatan\\game.exe");len=0;while(image[len])len++;
 assert(!ios_ratatan_fullscreen_args("1",image,len,NULL,0,1424,656,out,sizeof(out)));
 puts("PASS: isolated exact Steam Ratatan suffix, user override, current desktop bounds, slash/case handling, other games unchanged");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(h)
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
assert s.index('if (!extra && ios_ratatan_fullscreen_args(')>s.index('const char *extra = child_extra_args(')
