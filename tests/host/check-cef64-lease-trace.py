#!/usr/bin/env python3
"""Compile the actual read-only lease observer, with no mutating APIs available."""
from pathlib import Path
import subprocess,tempfile,os
root=Path(__file__).resolve().parents[2]
s=(root/"build/ntdll-unix/virtual_ios.c").read_text();start=s.index("static void ios_cef64_trace_free_locked(");end=s.index("NTSTATUS WINAPI NtFreeVirtualMemory",start);code=s[start:end]
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/"test.c";p.write_text(r'''#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
typedef size_t SIZE_T;typedef uint32_t ULONG,NTSTATUS;
#define MEM_RELEASE 0x8000
struct file_view{int x;};static struct file_view view;
static int held=1,remaining=1,logs,queries;static const char *trace="1",*session="1";static char last[500];
static const char *mockenv(const char *k){if(!strcmp(k,"MADEIRA_CEF64_LEASE_TRACE"))return trace;assert(!strcmp(k,"MADEIRA_STEAM_UI_SESSION"));return session;}
#define getenv mockenv
static int madeira_cef64_standalone_layout(void){return held;}
static int madeira_cef64_hold_get(unsigned n,uint64_t *b,uint64_t *z){if(n==2){*b=UINT64_C(0x7200000000);*z=UINT64_C(0x200000000);return 1;}if(n!=8)return 0;*b=UINT64_C(0x7140000000);*z=UINT64_C(0x20000000);return 1;}
static struct file_view *find_view_range(void *b,size_t n){assert(((uintptr_t)b==UINT64_C(0x7140000000)&&n==0x20000000)||((uintptr_t)b==UINT64_C(0x7200000000)&&n==UINT64_C(0x200000000)));queries++;return remaining?&view:NULL;}
static void *ios_jit_current_peb(void){return (void*)0x120000000;}
static int record(int fd,const char *fmt,...){assert(fd==2);va_list a;va_start(a,fmt);vsnprintf(last,sizeof(last),fmt,a);va_end(a);logs++;return 0;}
#define dprintf record
#define ios_cef64_record_lease(...) ((void)0) /* Separate bounded writer test. */
'''+code+r'''
int main(void){
 void *b=(void*)UINT64_C(0x7140000000);
 ios_cef64_trace_free_locked(b,0x10000,0x10000,0x8002,0);assert(logs==1&&strstr(last,"remaining=1")&&strstr(last,"type=0x8002"));
 remaining=0;ios_cef64_trace_free_locked(b,0,0x20000000,0x8000,0);assert(logs==2&&strstr(last,"remaining=0"));
 ios_cef64_trace_free_locked(b,0,0,0x8000,0xc0000017);assert(logs==3&&strstr(last,"status=0xc0000017"));
 ios_cef64_trace_free_locked((void*)UINT64_C(0x7200000000),0,UINT64_C(0x200000000),0x8000,0);assert(logs==4&&strstr(last,"slot=2"));
 const char *bad[]={NULL,"0","11","true","1 "};
 for(unsigned i=0;i<5;i++){trace=bad[i];ios_cef64_trace_free_locked(b,0,0,0,0);}trace="1";
 for(unsigned i=0;i<5;i++){session=bad[i];ios_cef64_trace_free_locked(b,0,0,0,0);}session="1";
 held=0;ios_cef64_trace_free_locked(b,0,0,0,0);held=1;
 ios_cef64_trace_free_locked((void*)0,0,0,0,0);ios_cef64_trace_free_locked((void*)UINT64_C(0x7160000000),0,0,0,0);assert(logs==4&&queries==4);
 ios_cef64_trace_free_locked(b,0x10000,0x10000,0x4000,0);assert(logs==4);
 for(unsigned i=0;i<5000;i++)ios_cef64_trace_free_locked(b,0,0,0x8000,0);assert(logs==4096&&queries==4096);
 ios_cef64_trace_free_locked((void*)UINT64_C(0x7200000000),0,UINT64_C(0x200000000),0x8000,0);assert(logs==4096);
 puts("PASS actual observer gates/range/remaining-view/status/budget; no claim or VM mutation API available");
}
''');subprocess.run(["clang","-std=c11","-Wall","-Wextra","-Werror","-fsanitize=address,undefined",str(p),"-o",str(Path(td)/"test")],check=True);subprocess.run([str(Path(td)/"test")],check=True,env={**os.environ,"UBSAN_OPTIONS":"halt_on_error=1"})
