#!/usr/bin/env python3
"""Compile the actual fixed-input diagnostic gate, including negative cases."""
from pathlib import Path
import subprocess, tempfile
root=Path(__file__).resolve().parents[2]
s=(root/'build/ideck-control/ideck-control.c').read_text()
gate=s[s.index('static int input_diagnostic_allowed(void)'):s.index('static int menu_navigation(void)')]
key_source=s[s.index('static UINT key('):s.index('static int input_diagnostic_allowed(void)')]
stubs=r'''
typedef unsigned UINT,DWORD;typedef unsigned short WORD;
#define INPUT_KEYBOARD 1
#define MAPVK_VK_TO_VSC_EX 4
#define KEYEVENTF_EXTENDEDKEY 1
#define KEYEVENTF_KEYUP 2
typedef struct {UINT type;struct {WORD wVk,wScan;DWORD dwFlags;} ki;} INPUT;
static INPUT captured;
static UINT MapVirtualKeyW(WORD vk,UINT mode){assert(mode==4);switch(vk){case 0x25:return 0xe04b;case 0x27:return 0xe04d;case 0x0d:return 0x1c;case 0x11:return 0x1d;case '1':return 2;default:return 0;}}
static UINT SendInput(UINT n,const INPUT *p,unsigned size){assert(n==1&&size==sizeof(INPUT));captured=*p;return n;}
'''
main=r'''
int main(void) {
 struct steam64_menu_state nav={0};
 assert(!steam64_menu_step(&nav,0x1000,0,0,0,0,1));
 assert(steam64_menu_step(&nav,0x1000,0,0,1,1,1)==MENU_ACCEPT);
 assert(!steam64_menu_step(&nav,0x1000,0,0,999,1,1));
 assert(!steam64_menu_step(&nav,0,0,0,1000,1,1));
 assert(steam64_menu_step(&nav,4,0,0,1001,1,1)==MENU_LEFT);
 assert(!steam64_menu_step(&nav,4,0,0,1400,1,1));
 assert(steam64_menu_step(&nav,4,0,0,1401,1,1)==MENU_LEFT);
 assert(!steam64_menu_step(&nav,4,0,0,1520,1,1));
 assert(steam64_menu_step(&nav,4,0,0,1521,1,1)==MENU_LEFT);
 assert(!steam64_menu_step(&nav,0,0,0,1600,1,1));
 assert(steam64_menu_step(&nav,0,16001,0,1601,1,1)==MENU_RIGHT);
 assert(!steam64_menu_step(&nav,0x1000,0,0,1700,1,0));
 assert(!steam64_menu_step(&nav,0x1000,0,0,1800,0,1));

 key(0x25,0);assert(captured.ki.wScan==0x4b&&captured.ki.dwFlags==KEYEVENTF_EXTENDEDKEY);
 key(0x27,KEYEVENTF_KEYUP);assert(captured.ki.wScan==0x4d&&captured.ki.dwFlags==(KEYEVENTF_KEYUP|KEYEVENTF_EXTENDEDKEY));
 key(0x0d,0);assert(captured.ki.wScan==0x1c&&captured.ki.dwFlags==0);
 key(0x11,0);assert(captured.ki.wScan==0x1d&&captured.ki.dwFlags==0);
 key('1',KEYEVENTF_KEYUP);assert(captured.ki.wScan==2&&captured.ki.dwFlags==KEYEVENTF_KEYUP);
 unsetenv("MADEIRA_STEAM_UI_SESSION");unsetenv("MADEIRA_STEAM64_INPUT_DIAGNOSTICS");unsetenv("WINEPREFIX");
 assert(!input_diagnostic_allowed());
 setenv("MADEIRA_STEAM_UI_SESSION","1",1);setenv("MADEIRA_STEAM64_INPUT_DIAGNOSTICS","1",1);
 assert(!input_diagnostic_allowed());
 const char *bad[]={"","/wine","/wine-steam64-old","/wine-steam64/","wine-steam64"};
 for(unsigned i=0;i<sizeof(bad)/sizeof(*bad);i++){setenv("WINEPREFIX",bad[i],1);assert(!input_diagnostic_allowed());}
 setenv("WINEPREFIX","/private/test/wine-steam64",1);assert(input_diagnostic_allowed());
 setenv("MADEIRA_STEAM_UI_SESSION","0",1);assert(!input_diagnostic_allowed());
 setenv("MADEIRA_STEAM_UI_SESSION","1",1);setenv("MADEIRA_STEAM64_INPUT_DIAGNOSTICS","0",1);assert(!input_diagnostic_allowed());
 setenv("MADEIRA_STEAM64_MENU_KEYS","1",1);assert(!steam64_menu_keys());
 setenv("MADEIRA_STEAM64_INPUT_DIAGNOSTICS","1",1);assert(steam64_menu_keys());
 unsetenv("MADEIRA_STEAM64_MENU_KEYS");assert(!steam64_menu_keys());
 puts("PASS: actual scan/extended/key-up contract and fixed-input gate require isolated prefix and both explicit flags (ASan/UBSan)");
}
'''
with tempfile.TemporaryDirectory() as d:
 d=Path(d);c=d/'gate.c';c.write_text('#include <stdlib.h>\n#include <string.h>\n#include <stdio.h>\n#include <assert.h>\n'+'#include \"'+str(root/'build/ideck-control/steam64-menu-keys.h')+'\"\n'+stubs+key_source+gate+main)
 subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(c),'-o',str(d/'gate')],check=True)
 subprocess.run([str(d/'gate')],check=True)
