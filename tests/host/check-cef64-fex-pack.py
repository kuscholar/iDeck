#!/usr/bin/env python3
"""Test real lab policy and Wine's gap search; this is not device capacity proof."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'build/ntdll-unix/virtual_ios.c').read_text()


def function(signature):
    start = source.index(signature)
    return source[start:source.index('\n}', start) + 2]


policy = function('static int ios_cef64_fex_pack_direction(')
search = function('static void *find_reserved_free_area(')
site = source.index('int packed = ios_cef64_fex_pack_direction(')
assert source.count('int packed = ios_cef64_fex_pack_direction(') == 1
assert source.index('if ((ptr = map_reserved_area( start, end, host_size', site) > site
assert source.index('ptr = map_free_area( start, end, host_size', site) > site
for forbidden in ('mprotect(', 'munmap(', 'malloc(', 'VirtualFree(', '->'):
    assert forbidden not in policy

harness = r'''
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
typedef uintptr_t ULONG_PTR;
static ULONG_PTR ios_fex_arena_base_unix, ios_fex_arena_end_unix;
struct range_entry { void *base, *end; };
static struct range_entry free_ranges[128], *free_ranges_end;
#define ROUND_ADDR(a,mask) ((void *)((uintptr_t)(a) & ~(uintptr_t)(mask)))
static struct range_entry *free_ranges_lower_bound(void *at) {
 for(struct range_entry *r=free_ranges;r<free_ranges_end;r++)
  if((uintptr_t)r->end >= (uintptr_t)at)return r;
 return free_ranges_end;
}
'''

test = r'''
static const size_t MiB=1024*1024;
static void reset_ranges(void) {
 ios_fex_arena_base_unix=0x7500000000ULL;
 ios_fex_arena_end_unix=ios_fex_arena_base_unix+256*MiB;
 free_ranges[0]=(struct range_entry){(void *)ios_fex_arena_base_unix,(void *)ios_fex_arena_end_unix};
 free_ranges_end=free_ranges+1;
}
static void *place(size_t size,size_t alignment,int packed) {
 void *lo=(void *)ios_fex_arena_base_unix,*hi=(void *)ios_fex_arena_end_unix;
 int direction=packed?ios_cef64_fex_pack_direction(lo,hi,size,0):0;
 void *p=find_reserved_free_area(lo,hi,size,direction,alignment-1);
 if(!p)return NULL;
 uintptr_t a=(uintptr_t)p,e=a+size;
 assert(a>=ios_fex_arena_base_unix && e<=ios_fex_arena_end_unix && e>a);
 assert(!(a&(alignment-1)));
 struct range_entry *r=free_ranges_lower_bound(p);
 assert(r<free_ranges_end && a>=(uintptr_t)r->base && e<=(uintptr_t)r->end);
 struct range_entry before=*r;
 if(a==(uintptr_t)r->base && e==(uintptr_t)r->end) {
  memmove(r,r+1,(free_ranges_end-r-1)*sizeof(*r));free_ranges_end--;
 } else if(a==(uintptr_t)r->base)r->base=(void *)e;
 else if(e==(uintptr_t)r->end)r->end=(void *)a;
 else {
  assert(free_ranges_end<free_ranges+127);
  memmove(r+1,r,(free_ranges_end-r)*sizeof(*r));free_ranges_end++;
  r[0]=(struct range_entry){before.base,(void *)a};
  r[1]=(struct range_entry){(void *)e,before.end};
 }
 for(r=free_ranges+1;r<free_ranges_end;r++)assert(r[-1].end<=r->base);
 return p;
}
int main(void) {
 reset_ranges();void *lo=(void *)ios_fex_arena_base_unix,*hi=(void *)ios_fex_arena_end_unix;
 const char *keys[]={"MADEIRA_CEF64_FEX_PACK","MADEIRA_STEAM_UI_SESSION","MADEIRA_CEF64_SOURCE_LAYOUT"};
 for(unsigned k=0;k<3;k++)setenv(keys[k],"1",1);
 assert(ios_cef64_fex_pack_direction(lo,hi,8*MiB,0)==1);
 assert(ios_cef64_fex_pack_direction(lo,hi,16*MiB,1)==0);
 assert(ios_cef64_fex_pack_direction(lo,hi,128*MiB,1)==0);
 const char *bad[]={"","0","true","11"};
 for(unsigned k=0;k<3;k++) {
  for(unsigned v=0;v<4;v++) {
   setenv(keys[k],bad[v],1);
   assert(ios_cef64_fex_pack_direction(lo,hi,8*MiB,0)==0);
   assert(ios_cef64_fex_pack_direction(lo,hi,16*MiB,1)==1);
  }
  unsetenv(keys[k]);assert(ios_cef64_fex_pack_direction(lo,hi,8*MiB,0)==0);
  setenv(keys[k],"1",1);
 }
 assert(ios_cef64_fex_pack_direction((char *)lo+4096,hi,8*MiB,0)==0);
 assert(ios_cef64_fex_pack_direction(lo,(char *)hi-4096,8*MiB,0)==0);
 assert(ios_cef64_fex_pack_direction((char *)lo-4096,hi,8*MiB,0)==0);
 assert(ios_cef64_fex_pack_direction(lo,(char *)hi+4096,8*MiB,0)==0);
 assert(ios_cef64_fex_pack_direction(lo,hi,0,0)==0);
 assert(ios_cef64_fex_pack_direction(lo,hi,257*MiB,0)==0);
 ios_fex_arena_base_unix=0;assert(ios_cef64_fex_pack_direction(lo,hi,8*MiB,0)==0);
 reset_ranges();ios_fex_arena_end_unix=ios_fex_arena_base_unix;
 assert(ios_cef64_fex_pack_direction(lo,hi,8*MiB,0)==0);
 /* Real Wine gap search on identical fixed intervals: demonstrate stranded
    capacity with mixed alignment, not replay of a complete device trace. */
 for(unsigned packed=0;packed<2;packed++) {
  reset_ranges();
  for(unsigned i=0;i<8;i++) {
   assert(place(8*MiB+8192,65536,packed));
   assert(place(16*MiB,16*MiB,packed));
  }
  size_t free_bytes=0;
  for(struct range_entry *r=free_ranges;r<free_ranges_end;r++)
   free_bytes+=(uintptr_t)r->end-(uintptr_t)r->base;
  assert(free_bytes==8*(8*MiB-8192));
  void *next=place(16*MiB,16*MiB,packed);
  assert(packed?next!=NULL:next==NULL);
 }
 puts("PASS actual full-arena lab gates and Wine gap search: same footprint, preserved alignment/bounds/non-overlap, stranded-span discriminator (ASan/UBSan); not device proof");
}
'''
with tempfile.TemporaryDirectory() as directory:
    directory = Path(directory)
    c = directory / 'pack.c'
    # The unchanged Wine search mixes ptrdiff_t/size_t under its own build flags.
    c.write_text(harness + policy + '\n#pragma clang diagnostic push\n'
                 '#pragma clang diagnostic ignored "-Wsign-compare"\n' + search +
                 '\n#pragma clang diagnostic pop\n' + test)
    subprocess.run(['clang', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', str(c), '-o', str(directory / 'test')], check=True)
    subprocess.run([str(directory / 'test')], check=True)
