#!/usr/bin/env python3
"""Compile production fallback policy and native integration with mock map_view.

No actual game/Metal/device mapping is claimed by this host contract test.
"""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'build/ntdll-unix/virtual_ios.c').read_text()
signature = 'static NTSTATUS ios_cef64_image_spill_map('
start = source.index(signature)
wrapper = source[start:source.index('\n}', start) + 2]
call = 'status = ios_cef64_image_spill_map(&view, image_info, size, limit_low, limit_high, alloc_type, status);'
assert source.count(call) == 1
site = source[source.index(call) - 110:source.index(call) + len(call)]
assert 'if (status == STATUS_NO_MEMORY)' in site
assert source.index(call) < source.index('status = map_image_into_view( view, nt_name')
for forbidden in ('mprotect(', 'munmap(', 'mach_vm_', 'hold_claim(', 'hold_unclaim(', 'map_fixed_area('):
    assert forbidden not in wrapper

harness = r'''
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include "cef64_image_spill.h"
typedef uint16_t WCHAR;
typedef size_t SIZE_T;
typedef uintptr_t ULONG_PTR;
typedef uint32_t ULONG, NTSTATUS;
#define STATUS_NO_MEMORY UINT32_C(0xc0000017)
#define MEM_TOP_DOWN 0x100000
#define SEC_IMAGE 0x1000000
#define SEC_FILE 0x800000
#define VPROT_COMMITTED 0x20
#define VPROT_READ 1
#define VPROT_EXEC 4
#define VPROT_WRITECOPY 8
struct file_view { void *base; };
struct pe_image_info { uint16_t machine,image_charact; uint32_t image_flags; };
typedef struct { struct { WCHAR *Buffer; uint16_t Length; } ImagePathName; } RTL_USER_PROCESS_PARAMETERS;
typedef struct { RTL_USER_PROCESS_PARAMETERS *ProcessParameters; } PEB;
static RTL_USER_PROCESS_PARAMETERS pp;
static PEB peb={&pp},*current=&peb;
static int owned=1,extra=0,calls,occupied;
static NTSTATUS map_status;
static struct cef64_image_interval holds[20];
static PEB *ios_jit_current_peb(void){return current;}
static int ios_cef64_owned_layout(void){return owned;}
static int madeira_cef64_hold_get(unsigned i,uint64_t *b,uint64_t *n) {
 if(i==20)return extra;
 assert(i<20);*b=holds[i].base;*n=holds[i].size;return *n!=0;
}
static NTSTATUS map_view(struct file_view **view,void *base,SIZE_T size,
 unsigned alloc,unsigned vprot,ULONG_PTR low,ULONG_PTR high,SIZE_T align) {
 static struct file_view result;
 assert(base==NULL && alloc==MEM_TOP_DOWN && !align);
 assert(vprot==(SEC_IMAGE|SEC_FILE|VPROT_COMMITTED|VPROT_READ|VPROT_EXEC|VPROT_WRITECOPY));
 assert(low==UINT64_C(0x7160000000) && high==UINT64_C(0x717ffeffff));
 assert(size>0 && size<=0x4000000);
 calls++;if(map_status)return map_status;
 if(occupied)return STATUS_NO_MEMORY;
 result.base=(void *)(uintptr_t)((high-size+1)&~UINT64_C(0xffff));
 assert((uintptr_t)result.base>=low && (uintptr_t)result.base+size-1<=high);
 *view=&result;return 0;
}
static int quiet(int fd,const char *fmt,...){(void)fd;(void)fmt;return 0;}
#define dprintf quiet
'''

tests = r'''
static void owner(const char *s) {
 static WCHAR path[1024];size_t n=strlen(s);assert(n<1024);
 for(size_t i=0;i<n;i++)path[i]=(unsigned char)s[i];
 pp.ImagePathName.Buffer=path;pp.ImagePathName.Length=(uint16_t)(2*n);
}
static void setup(void) {
 memset(holds,0,sizeof(holds));
 holds[0]=(struct cef64_image_interval){UINT64_C(0x7100000000),0x40000000};
 holds[1]=(struct cef64_image_interval){UINT64_C(0x717fff0000),0x40010000};
 holds[2]=(struct cef64_image_interval){UINT64_C(0x7200000000),UINT64_C(0x200000000)};
 holds[3]=(struct cef64_image_interval){UINT64_C(0x7500000000),UINT64_C(0x260000000)};
 holds[8]=(struct cef64_image_interval){UINT64_C(0x7140000000),0x20000000};
 holds[16]=(struct cef64_image_interval){UINT64_C(0x7760000000),0x20000000};
 owner("C:\\Program Files\\Steam\\steamapps\\common\\Hot Roads\\hr.exe");
 setenv("MADEIRA_CEF64_IMAGE_SPILL","1",1);setenv("MADEIRA_CEF64_SOURCE_LAYOUT","1",1);
 current=&peb;peb.ProcessParameters=&pp;owned=1;extra=0;calls=0;occupied=0;map_status=0;
}
static int range(uint32_t status,uint16_t machine,uint16_t chars,uint32_t flags,
 uint64_t size,uint64_t low,uint64_t high,uint32_t alloc,uint64_t *a,uint64_t *b) {
 return cef64_image_spill_range("1","1",1,1,status,machine,chars,flags,size,low,high,alloc,holds,a,b);
}
int main(void) {
 setup();uint64_t low=1,high=2;
 assert(range(STATUS_NO_MEMORY,0xa641,0x2000,4,0x477000,0x10000,0,0,&low,&high));
 assert(low==UINT64_C(0x7160000000)&&high==UINT64_C(0x717ffeffff));
 assert(range(STATUS_NO_MEMORY,0x8664,0x2000,4,0x549000,0,0,0,&low,&high));
 assert(range(STATUS_NO_MEMORY,0xaa64,0x2000,4,0x4000000,0,0,MEM_TOP_DOWN,&low,&high));
 assert(!range(0,0xa641,0x2000,4,0x477000,0,0,0,&low,&high));
 assert(!range(0xc0000018,0xa641,0x2000,4,0x477000,0,0,0,&low,&high));
 assert(!range(STATUS_NO_MEMORY,0x14c,0x2000,4,0x477000,0,0,0,&low,&high));
 assert(!range(STATUS_NO_MEMORY,0xa641,0x2001,4,0x477000,0,0,0,&low,&high));
 assert(!range(STATUS_NO_MEMORY,0xa641,0,4,0x477000,0,0,0,&low,&high));
 assert(!range(STATUS_NO_MEMORY,0xa641,0x2000,0,0x477000,0,0,0,&low,&high));
 assert(!range(STATUS_NO_MEMORY,0xa641,0x2000,4,0,0,0,0,&low,&high));
 assert(!range(STATUS_NO_MEMORY,0xa641,0x2000,4,0x4000001,0,0,0,&low,&high));
 assert(!range(STATUS_NO_MEMORY,0xa641,0x2000,4,0x477000,0,UINT64_C(0x717fffffff),0,&low,&high));
 assert(!range(STATUS_NO_MEMORY,0xa641,0x2000,4,0x477000,UINT64_C(0x7160000001),0,0,&low,&high));
 assert(!range(STATUS_NO_MEMORY,0xa641,0x2000,4,0x477000,0,0,0x4000,&low,&high));
 /* Every native interval is checked; future/corrupt/compact layouts fail closed. */
 for(unsigned i=0;i<20;i++) {
  setup();holds[i]=(struct cef64_image_interval){UINT64_C(0x7161000000),0x10000};
  low=123;high=456;assert(!range(STATUS_NO_MEMORY,0xa641,0x2000,4,0x477000,0,0,0,&low,&high));
  assert(low==123&&high==456);
 }
 setup();holds[16]=(struct cef64_image_interval){UINT64_MAX-4096,8192};
 assert(!range(STATUS_NO_MEMORY,0xa641,0x2000,4,0x477000,0,0,0,&low,&high));
 setup();holds[0].base=UINT64_C(0x7140000000);holds[1].base=UINT64_C(0x70ffff0000);
 assert(!range(STATUS_NO_MEMORY,0xa641,0x2000,4,0x477000,0,0,0,&low,&high));
 setup();struct pe_image_info image={0xa641,0x2000,4};struct file_view *view=NULL;
 assert(ios_cef64_image_spill_map(&view,&image,0x477000,0,0,0,STATUS_NO_MEMORY)==0);
 assert(view&&calls==1);calls=0;
 const char *bad[]={"","0","true","11"};
 for(unsigned i=0;i<4;i++) {
  setenv("MADEIRA_CEF64_IMAGE_SPILL",bad[i],1);
  assert(ios_cef64_image_spill_map(&view,&image,0x477000,0,0,0,STATUS_NO_MEMORY)==STATUS_NO_MEMORY);
 }
 unsetenv("MADEIRA_CEF64_IMAGE_SPILL");
 assert(ios_cef64_image_spill_map(&view,&image,0x477000,0,0,0,STATUS_NO_MEMORY)==STATUS_NO_MEMORY);
 assert(calls==0);setup();owned=0;
 assert(ios_cef64_image_spill_map(&view,&image,0x477000,0,0,0,STATUS_NO_MEMORY)==STATUS_NO_MEMORY);
 owned=1;extra=1;
 assert(ios_cef64_image_spill_map(&view,&image,0x477000,0,0,0,STATUS_NO_MEMORY)==STATUS_NO_MEMORY);
 extra=0;current=NULL;
 assert(ios_cef64_image_spill_map(&view,&image,0x477000,0,0,0,STATUS_NO_MEMORY)==STATUS_NO_MEMORY);
 current=&peb;
 const char *not_games[]={"C:\\Steam\\steam.exe","C:\\Steam\\bin\\steamwebhelper.exe", "C:\\notsteamapps\\common\\hr.exe", "C:\\steamapps\\common", "C:\\steamapps\\common\\"};
 for(unsigned i=0;i<sizeof(not_games)/sizeof(*not_games);i++){
  owner(not_games[i]);assert(ios_cef64_image_spill_map(&view,&image,0x477000,0,0,0,STATUS_NO_MEMORY)==STATUS_NO_MEMORY);
 }
 assert(calls==0);owner("C:/STEAMAPPS/COMMON/Hot Roads/hr.exe");
 assert(ios_cef64_image_spill_map(&view,&image,0x477000,0,0,0,STATUS_NO_MEMORY)==0&&calls==1);
 occupied=1;assert(ios_cef64_image_spill_map(&view,&image,0x477000,0,0,0,STATUS_NO_MEMORY)==STATUS_NO_MEMORY);
 occupied=0;map_status=0xc0000018;
 assert(ios_cef64_image_spill_map(&view,&image,0x477000,0,0,0,STATUS_NO_MEMORY)==STATUS_NO_MEMORY);
 calls=0;
 assert(ios_cef64_image_spill_map(&view,&image,0x477000,0,0,0,0xc0000018)==0xc0000018&&calls==0);
 puts("PASS production 64-bit relocatable game-DLL spill: exact gates/layout, all20lease exclusions, caller constraints, overflow, ordinary/CEF/WoW refusals, mapper failure preservation (ASan/UBSan); no device claim");
}
'''

with tempfile.TemporaryDirectory() as directory:
    directory = Path(directory)
    c = directory / 'spill.c'
    c.write_text(harness + wrapper + tests)
    subprocess.run(['clang', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                    '-I', str(root / 'build/ntdll-unix'), str(c), '-o', str(directory / 'test')], check=True)
    subprocess.run([str(directory / 'test')], check=True)
