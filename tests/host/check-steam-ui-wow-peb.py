#!/usr/bin/env python3
"""Exercise production current-process PEB32 ownership under foreign legacy state."""
from pathlib import Path
import subprocess,tempfile
s=(Path(__file__).resolve().parents[2]/'build/ntdll-unix/process_ios.c').read_text()
a=s.index('static ULONG_PTR ios_steam_ui_current_wow_peb(');b=s.index('/* end ios_steam_ui_current_wow_peb */',a)
code=r'''
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <assert.h>
#include <pthread.h>
#include <stdatomic.h>
typedef uintptr_t ULONG_PTR;
typedef _Atomic int LONG;
typedef struct { void *Peb; } TEB;
static _Thread_local TEB current;
static _Thread_local int missing_teb;
static int is_win64=1;
static const ULONG_PTR page_size=4096;
static TEB *NtCurrentTeb(void){return missing_teb?NULL:&current;}
static int InterlockedIncrement(LONG *p){return atomic_fetch_add(p,1)+1;}
static ULONG_PTR ios_wow_base_for_peb(void *p){
 if((uintptr_t)p==0x7900310000ULL)return 0x7900000000ULL;
 if((uintptr_t)p==0x7800310000ULL)return 0x7800000000ULL;
 return 0;
}
'''+s[a:b]+r'''
static void *worker(void *id){
 uintptr_t owner=(uintptr_t)id;
 current.Peb=(void *)owner;
 for(int i=0;i<1000;i++){
  uintptr_t legacy=i&1?0:0x7700311000ULL;
  uintptr_t wanted=ios_wow_base_for_peb((void *)owner)?owner+page_size:0;
  assert(ios_steam_ui_current_wow_peb(legacy)==wanted);
 }
 return NULL;
}
int main(void){
 unsetenv("MADEIRA_STEAM_UI_SESSION");current.Peb=(void *)0x7900310000ULL;
 assert(ios_steam_ui_current_wow_peb(123)==123);
 setenv("MADEIRA_STEAM_UI_SESSION","0",1);assert(ios_steam_ui_current_wow_peb(456)==456);
 setenv("MADEIRA_STEAM_UI_SESSION","1",1);
 is_win64=0;assert(ios_steam_ui_current_wow_peb(789)==789);is_win64=1;
 missing_teb=1;assert(ios_steam_ui_current_wow_peb(123)==0);missing_teb=0;
 current.Peb=NULL;assert(ios_steam_ui_current_wow_peb(123)==0);
 pthread_t threads[3];uintptr_t owners[]={0x7900310000ULL,0x7800310000ULL,0x100400000ULL};
 for(int i=0;i<3;i++)assert(!pthread_create(&threads[i],NULL,worker,(void *)owners[i]));
 for(int i=0;i<3;i++)assert(!pthread_join(threads[i],NULL));
 puts("PASS: production lab PEB32 query owner isolation, native-zero, foreign/null legacy, ordinary/old-style gates and concurrent sibling queries (ASan/UBSan)");
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.c').write_text(code)
 subprocess.run(['clang','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True,stderr=subprocess.DEVNULL)
