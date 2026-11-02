#!/usr/bin/env python3
"""Exercise the exact-version read-only CEF DelayLoadInfo decoder."""
from pathlib import Path
import subprocess,tempfile,os
root=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/"test.c"
 p.write_text(r'''#include <assert.h>
#include <stdio.h>
#include "cef64_delayload_probe.h"
static unsigned char memory[0x10000];
static int bad;
static int read_mem(uint64_t address,void *out,size_t size){
 if(bad||address<0x10000||address-0x10000>sizeof(memory)||size>sizeof(memory)-(address-0x10000))return 0;
 memcpy(out,memory+(address-0x10000),size);return 1;
}
static int read_fixture(uint64_t address,void *out,size_t size){
 const uint64_t base=0x10000000;
 /* Only the known code bytes occupy a second sparse test range. */
 if(address==base+0x59efb90&&size==9){const unsigned char code[]={0xe8,0xcb,0x1a,0xb1,0xfd,0xcc,0xcc,0x0f,0x0b};memcpy(out,code,size);return !bad;}
 if(address==base)return read_mem(0x10000,out,size);
 if(address==base+0x80)return read_mem(0x10080,out,size);
 return read_mem(address,out,size);
}
static void put32(unsigned off,uint32_t n){memcpy(memory+off,&n,4);}
static void put64(unsigned off,uint64_t n){memcpy(memory+off,&n,8);}
int main(void){
 memory[0]='M';memory[1]='Z';put32(60,0x80);
 put32(0x80,0x4550);memory[0x84]=0x64;memory[0x85]=0x86;put32(0x88,0x66956fee);put32(0xd0,0xd3ca000);
 put32(0x1158,3);put64(0x1160,0x12000);put32(0x2000,72);put64(0x2018,0x13000);put32(0x2020,1);put64(0x2028,0x14000);put32(0x2040,126);
 strcpy((char*)memory+0x3000,"system.dll");strcpy((char*)memory+0x4000,"MissingExport");
 struct ideck_cef_delay_failure out={0};
 assert(ideck_cef_delay_probe(0x159efb96,0x11000,read_fixture,&out));
 assert(out.reason==3&&out.error==126&&!strcmp(out.module,"system.dll")&&!strcmp(out.symbol,"MissingExport"));
 strcpy((char*)memory+0x3000,"NDFAPI.DLL");assert(ideck_cef_delay_probe(0x159efb96,0x11000,read_fixture,&out));
 put32(0x2020,0);put32(0x2028,45);put32(0x1158,4);put32(0x2040,127);
 assert(ideck_cef_delay_probe(0x159efb96,0x11000,read_fixture,&out)&&out.ordinal==45&&out.reason==4&&out.error==127);
 put32(0x2000,71);assert(!ideck_cef_delay_probe(0x159efb96,0x11000,read_fixture,&out));put32(0x2000,72);
 put32(0x88,0);assert(!ideck_cef_delay_probe(0x159efb96,0x11000,read_fixture,&out));put32(0x88,0x66956fee);
 strcpy((char*)memory+0x3000,"private/path.dll");assert(!ideck_cef_delay_probe(0x159efb96,0x11000,read_fixture,&out));
 strcpy((char*)memory+0x3000,"account-value");assert(!ideck_cef_delay_probe(0x159efb96,0x11000,read_fixture,&out));
 strcpy((char*)memory+0x3000,"system.dll");put32(0x1158,2);assert(!ideck_cef_delay_probe(0x159efb96,0x11000,read_fixture,&out));
 put32(0x1158,3);bad=1;assert(!ideck_cef_delay_probe(0x159efb96,0x11000,read_fixture,&out));bad=0;
 assert(!ideck_cef_delay_probe(0x159efb97,0x11000,read_fixture,&out));
 assert(!ideck_cef_delay_probe(1,0x11000,read_fixture,&out));assert(!ideck_cef_delay_probe(0x159efb96,UINT64_MAX,read_fixture,&out));
 puts("PASS exact CEF headers/code/structure, module-symbol-only sanitization, ordinal/name, unreadable and overflow refusal");
}
''')
 subprocess.run(["clang","-std=c11","-Wall","-Wextra","-Werror","-fsanitize=address,undefined","-I",str(root/"build/diagnostics"),str(p),"-o",str(Path(td)/"test")],check=True)
 subprocess.run([str(Path(td)/"test")],check=True,env={**os.environ,"UBSAN_OPTIONS":"halt_on_error=1"})
