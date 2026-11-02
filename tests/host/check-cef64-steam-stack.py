#!/usr/bin/env python3
"""Verify existing per-program stack policy leaves Chromium/game stacks alone."""
from pathlib import Path
import tempfile,subprocess
root=Path(__file__).resolve().parents[2]
s=(root/"build/ntdll-unix/virtual_ios.c").read_text();start=s.index("#define IOS_SMALL_STACK_FLOOR");end=s.index("/***********************************************************************",start);actual=s[start:end]
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/"test.c";p.write_text(r'''#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
typedef uint16_t WCHAR;typedef size_t SIZE_T;
struct U{WCHAR *Buffer;unsigned short Length;};typedef struct{struct U ImagePathName;} RTL_USER_PROCESS_PARAMETERS;
typedef struct{RTL_USER_PROCESS_PARAMETERS *ProcessParameters;} PEB;
static const char *list="steam.exe";static RTL_USER_PROCESS_PARAMETERS pp;static PEB peb={&pp},*owner=&peb;
static const char *mockenv(const char *key){assert(!strcmp(key,"MADEIRA_SMALL_STACK_EXES"));return list;}
#define getenv mockenv
static PEB *ios_jit_current_peb(void){return owner;}
'''+actual+r'''
static size_t floor_for(const char *path){WCHAR u[500];size_t n=strlen(path);assert(n<500);for(size_t i=0;i<n;i++)u[i]=(unsigned char)path[i];pp.ImagePathName.Buffer=u;pp.ImagePathName.Length=n*2;return ios_thread_stack_floor();}
int main(void){
 assert(floor_for("C:\\Program Files\\Steam\\steam.exe")==2*1024*1024);
 assert(floor_for("/Steam/STEAM.EXE")==2*1024*1024);
 const char *keep[]={"steamwebhelper.exe","notsteam.exe","steam.exe.bak","hr.exe","Ratatan.exe","explorer.exe","crashpad_handler.exe"};
 for(unsigned i=0;i<sizeof(keep)/sizeof(keep[0]);i++)assert(floor_for(keep[i])==8*1024*1024);
 list=NULL;assert(floor_for("steam.exe")==8*1024*1024);list="";assert(floor_for("steam.exe")==8*1024*1024);
 list="steam.exe";owner=NULL;assert(floor_for("steam.exe")==8*1024*1024);
 puts("PASS actual existing Steam-only2MiB option; CEF/game/ordinary/foreign-owner8MiB unchanged");
}
''');subprocess.run(["clang","-Wall","-Wextra","-Werror","-fsanitize=address,undefined",str(p),"-o",str(Path(td)/"test")],check=True);subprocess.run([str(Path(td)/"test")],check=True)
