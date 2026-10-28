#!/usr/bin/env python3
"""Compile the production Wine adoption function with ownership/view fixtures."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'build/ntdll-unix/virtual_ios.c').read_text()
adopt = 'static int ios_cef64_adopt_view' + source.split('static int ios_cef64_adopt_view', 1)[1].split('static NTSTATUS allocate_virtual_memory', 1)[0]
code = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "cef64_owned_slots.h"
typedef uint32_t ULONG, NTSTATUS;
typedef uint64_t SIZE_T, ULONG_PTR;
typedef uint16_t WCHAR;
typedef struct { struct { WCHAR *Buffer; uint16_t Length; } ImagePathName; } RTL_USER_PROCESS_PARAMETERS;
typedef struct { RTL_USER_PROCESS_PARAMETERS *ProcessParameters; } PEB;
struct file_view { void *base; };
#define STATUS_NO_MEMORY UINT32_C(0xc0000017)
static int active=1, existing, claimed, create_fails, get_calls, claims, releases;
static uint64_t held=UINT64_C(0x7100000000), held_size=UINT64_C(0x40000000);
static RTL_USER_PROCESS_PARAMETERS params;
static PEB peb={&params}, *owner=&peb;
static int ios_cef64_owned_layout(void){return active;}
static PEB *ios_jit_current_peb(void){return owner;}
static int madeira_cef64_hold_get(unsigned s,uint64_t *b,uint64_t *z){assert(s<6);get_calls++;*b=held;*z=held_size;return 1;}
static int madeira_cef64_hold_claim(unsigned s){assert(s<6);claims++;if(claimed)return 0;claimed=1;return 1;}
static void madeira_cef64_hold_unclaim(unsigned s){assert(s<6&&claimed);releases++;claimed=0;}
static int find_view_range(void *base,SIZE_T size){assert((uintptr_t)base==held&&size==held_size);return existing;}
static NTSTATUS create_view(struct file_view **out,void *base,SIZE_T size,unsigned vprot){
 static struct file_view v;
 assert(claimed&&(uintptr_t)base==held&&size==held_size&&vprot==5);
 if(create_fails)return STATUS_NO_MEMORY;
 v.base=base;*out=&v;return 0;
}
''' + adopt + r'''
static void name(const char *s){static WCHAR n[128];size_t i;for(i=0;s[i];i++)n[i]=(unsigned char)s[i];params.ImagePathName.Buffer=n;params.ImagePathName.Length=(uint16_t)(2*i);}
static NTSTATUS invoke(ULONG_PTR low,ULONG_PTR high,ULONG_PTR align,int expect_handled){
 struct file_view *v=0;void *base=0;NTSTATUS status=0x1234;
 int handled=ios_cef64_adopt_view(&v,&base,held_size,0x2000,1,5,low,high,align,0,&status);
 assert(handled==expect_handled);
 if(handled&&!status)assert((uintptr_t)base==held&&v&&v->base==base);
 else assert(!base&&!v);
 return status;
}
int main(void){
 name("C:\\steam64-cef-load-probe.exe");
 active=0;assert(invoke(0,0,0,0)==0x1234&&!get_calls);active=1;
 owner=0;assert(invoke(0,0,0,0)==0x1234&&!get_calls);owner=&peb;
 name("C:\\steam.exe");assert(invoke(0,0,0,0)==0x1234&&!get_calls);
 name("C:\\steamwebhelper.exe");
 assert(invoke(held+1,0,0,1)==STATUS_NO_MEMORY&&!claims);
 assert(invoke(0,held-1,0,1)==STATUS_NO_MEMORY&&!claims);
 assert(invoke(0,held+held_size-2,0,1)==STATUS_NO_MEMORY&&!claims);
 existing=1;assert(invoke(0,0,0,1)==STATUS_NO_MEMORY&&!claims);existing=0;
 create_fails=1;assert(invoke(0,0,0,1)==STATUS_NO_MEMORY&&!claimed&&releases==1);create_fails=0;
 assert(invoke(held,held+held_size-1,0x10000,1)==0&&claimed);
 assert(invoke(0,0,0,1)==STATUS_NO_MEMORY&&claimed);
 claimed=0;held=UINT64_C(0x717fff0000);held_size=UINT64_C(0x40010000);
 int previous_claims=claims;
 assert(invoke(0,0,UINT64_C(0x40000000),1)==STATUS_NO_MEMORY&&claims==previous_claims);
 assert(invoke(held,held+held_size-1,0x10000,1)==0&&claimed);
 return 0;
}
'''
with tempfile.TemporaryDirectory() as directory:
    temp = Path(directory)
    (temp / 'transfer.c').write_text(code)
    subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                    '-I' + str(root / 'build/ntdll-unix'), str(temp / 'transfer.c'), '-o', str(temp / 'transfer')], check=True)
    subprocess.run([str(temp / 'transfer')], check=True)
print('PASS: actual Wine adoption function checks current owner, inclusive bounds, alignment, live views, duplicate claim and create-view rollback (ASan/UBSan); not a device test')
