#!/usr/bin/env python3
"""Actual bounded PE scanner: writable data only, known values, malformed/read-failure cases."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
c=r'''
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
#include "steam_ui_pool_owner.h"
static unsigned char image[0xa000];static unsigned emitted,deny;
static const uint64_t base=0x100000000ULL;
static int reader(void *ctx,uint64_t addr,void *out,size_t n){
 if(addr<base || n>sizeof(image) || addr-base>sizeof(image)-n)return 0;
 if(deny && addr>=base+0x3000)return 0;
 memcpy(out,image+(addr-base),n);return 1;
}
static void emit(void *ctx,uint32_t a,uint64_t av,uint32_t b,uint64_t bv){
 assert(a>=0x3000 && b>=0x3000 && b-a<=512 && av!=bv);
 assert((av==0x7800000000ULL||av==0x7400000000ULL)&&(bv==0x7800000000ULL||bv==0x7400000000ULL));emitted++;
}
static void u16(size_t o,uint16_t v){memcpy(image+o,&v,2);}
static void u32(size_t o,uint32_t v){memcpy(image+o,&v,4);}
static void u64(size_t o,uint64_t v){memcpy(image+o,&v,8);}
static void setup(void){
 memset(image,0,sizeof(image));image[0]='M';image[1]='Z';u32(60,0x80);
 memcpy(image+0x80,"PE\0\0",4);u16(0x84,0x8664);u16(0x86,2);u16(0x94,0xf0);u16(0x98,0x20b);
 u32(0x188+8,0x1000);u32(0x188+12,0x1000);u32(0x188+36,0x60000020);
 u32(0x1b0+8,0x5000);u32(0x1b0+12,0x3000);u32(0x1b0+36,0xc0000040);
 u64(0x200,0x7800000000ULL);u64(0x208,0x7400000000ULL); /* Headers must not be scanned. */
 u64(0x1000,0x7800000000ULL);u64(0x1008,0x7400000000ULL); /* Executable-only section must not be scanned. */
 u64(0x4000,0x7800000000ULL);u64(0x4008,0x7400000000ULL);
 u64(0x5000,0x7800000000ULL);u64(0x5008,0x7800000000ULL);emitted=deny=0;
}
int main(void){
 const uint64_t legacy[]={0x7800000000ULL,0x73ffff0000ULL};
 const uint64_t corrected[]={0x7800000000ULL,0x73ffff0000ULL,0x7400000000ULL};
 setup();assert(!steam_ui_scan_pool_owner(base,sizeof(image),reader,emit,NULL,legacy,2));
 assert(steam_ui_pool_guarded(0x400010000ULL));assert(!steam_ui_pool_guarded(0x400000000ULL));assert(!steam_ui_pool_guarded(0x800010000ULL));
 assert(steam_ui_scan_pool_owner(base,sizeof(image),reader,emit,NULL,corrected,3)==1 && emitted==1);
 setup();deny=1;assert(!steam_ui_scan_pool_owner(base,sizeof(image),reader,emit,NULL,corrected,3));
 setup();u16(0x86,100);assert(!steam_ui_scan_pool_owner(base,sizeof(image),reader,emit,NULL,corrected,3));
 setup();u32(60,0xfffffff0);assert(!steam_ui_scan_pool_owner(base,sizeof(image),reader,emit,NULL,corrected,3));
 setup();u16(0x84,0xaa64);assert(!steam_ui_scan_pool_owner(base,sizeof(image),reader,emit,NULL,corrected,3));
 setup();memset(image+0x3000,0,0x5000);for(unsigned i=0;i<24;i++)u64(0x4000+i*8,i%2?0x7400000000ULL:0x7800000000ULL);
 assert(steam_ui_scan_pool_owner(base,sizeof(image),reader,emit,NULL,corrected,3)==8 && emitted==8);
 assert(!steam_ui_scan_pool_owner(UINT64_MAX-4095,sizeof(image),reader,emit,NULL,corrected,3));
 puts("PASS: actual scanner: corrected BRP base finds data cluster; headers/text/duplicate-only values ignored; malformed PE/read failure/overflow bounded; output capped (ASan/UBSan)");
}
'''
with tempfile.TemporaryDirectory() as td:
 td=Path(td);(td/'test.c').write_text(c)
 subprocess.run(['cc','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I',str(root/'build/diagnostics'),str(td/'test.c'),'-o',str(td/'test')],check=True)
 subprocess.run([str(td/'test')],check=True)
