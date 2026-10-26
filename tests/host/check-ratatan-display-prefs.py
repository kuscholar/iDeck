#!/usr/bin/env python3
"""Exercise production display-only registry mutation and backup failure gates."""
from pathlib import Path
import subprocess,tempfile
r=Path(__file__).resolve().parents[2];s=(r/'build/ideck-control/ideck-control.c').read_text()
a=s.index('static void prepare_ratatan_display(');f=s[a:s.index('\n}\n',a)+3]
h=r'''
#include <stdlib.h>
#include <stdio.h>
#include <wchar.h>
#include <string.h>
#include <stdint.h>
#include <assert.h>
typedef wchar_t WCHAR;typedef unsigned DWORD;typedef int HKEY;typedef long LONG;typedef unsigned char BYTE;
#define HKEY_CURRENT_USER 0
#define KEY_QUERY_VALUE 1
#define KEY_SET_VALUE 2
#define REG_DWORD 4
#define ERROR_FILE_NOT_FOUND 2
static DWORD game[5]={3,1280,656,1280,656},saved[5];static int complete,fail_backup,writes;
static int idx(const WCHAR *name){
 if(wcsstr(name,L"Fullscreen"))return 0;
 if(wcsstr(name,L"Window Width"))return 3;
 if(wcsstr(name,L"Window Height"))return 4;
 return wcsstr(name,L"Width")?1:2;
}
static LONG RegOpenKeyExW(HKEY k,const WCHAR*p,DWORD z,DWORD a,HKEY*out){(void)k;(void)z;(void)a;assert(!wcscmp(p,L"Software\\RatataArts\\Ratatan"));*out=1;return 0;}
static LONG RegCreateKeyExW(HKEY k,const WCHAR*p,DWORD a,void*b,DWORD c,DWORD d,void*e,HKEY*out,void*g){(void)k;(void)a;(void)b;(void)c;(void)d;(void)e;(void)g;assert(!wcscmp(p,L"Software\\iDeck\\Backups\\RatatanDisplayV1"));if(fail_backup)return 5;*out=2;return 0;}
static LONG RegQueryValueExW(HKEY k,const WCHAR*n,void*x,DWORD*t,BYTE*d,DWORD*size){(void)x;*t=REG_DWORD;assert(*size==4);if(k==2&&!wcscmp(n,L"Complete")){if(!complete)return ERROR_FILE_NOT_FOUND;*(DWORD*)d=1;return 0;}*(DWORD*)d=(k==1?game:saved)[idx(n)];return 0;}
static LONG RegSetValueExW(HKEY k,const WCHAR*n,DWORD z,DWORD t,const BYTE*d,DWORD size){(void)z;assert(t==REG_DWORD&&size==4);if(k==2&&!wcscmp(n,L"Complete")){complete=1;return 0;}if(k==2)saved[idx(n)]=*(DWORD*)d;else{game[idx(n)]=*(DWORD*)d;writes++;}return 0;}
static void RegCloseKey(HKEY k){(void)k;}
'''+f+r'''
int main(void){
 setenv("MADEIRA_SCREEN_W","1424",1);setenv("MADEIRA_SCREEN_H","656",1);
 prepare_ratatan_display();assert(writes==0);
 setenv("MADEIRA_STEAM_UI_SESSION","1",1);setenv("MADEIRA_RATATAN_FULLSCREEN","0",1);
 prepare_ratatan_display();assert(writes==0);unsetenv("MADEIRA_RATATAN_FULLSCREEN");
 fail_backup=1;prepare_ratatan_display();assert(writes==0&&game[0]==3);fail_backup=0;
 prepare_ratatan_display();assert(writes==5&&complete&&game[0]==1&&game[1]==1424&&game[2]==656&&saved[0]==3&&saved[1]==1280);
 game[0]=3;prepare_ratatan_display();assert(game[0]==1&&saved[0]==3&&saved[1]==1280);
 puts("PASS: display-only exact key, isolated session, opt-out, backup-before-write, backup failure, repeat keeps original preferences");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(h)
 subprocess.run(['cc','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True,cwd=p)
cs=(r/'app/Madeira/ContentView.swift').read_text();fn=cs[cs.index('private func startSteamUIExperiment('):cs.index('private func prepareSteamLaunch()')]
assert 'setenv("MADEIRA_WGI_HOST_PADS", MadeiraConfig.get("env.MADEIRA_WGI_HOST_PADS") ?? "1", 1)' in fn
assert fn.index('setenv("MADEIRA_WGI_HOST_PADS"')<fn.index('runWineFullSequence(steamUI: true)')
