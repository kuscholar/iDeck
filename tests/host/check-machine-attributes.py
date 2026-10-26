#!/usr/bin/env python3
"""Compile the production Wine API backport; check flags and failure behavior."""
from pathlib import Path
import subprocess,tempfile,re,os,shutil
root=Path(__file__).resolve().parents[2]
p=(root/'build/wine-pe/steam-ui-machine-attributes.patch').read_text()
added='\n'.join(x[1:] for x in p.splitlines() if x.startswith('+') and not x.startswith('+++'))
function=re.search(r'HRESULT WINAPI GetMachineTypeAttributes\(.*?\n}',added,re.S).group(0)
fixture=r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#define WINAPI
#define IMAGE_FILE_MACHINE_AMD64 0x8664
#define IMAGE_FILE_MACHINE_ARM64 0xaa64
#define SystemSupportedProcessorArchitectures 181
#define S_OK 0
#define HRESULT_FROM_NT(s) ((int32_t)((uint32_t)(s)|0x10000000))
typedef void *HANDLE;
typedef uint16_t USHORT;
typedef int32_t NTSTATUS,HRESULT;
typedef unsigned MACHINE_ATTRIBUTES;
enum {UserEnabled=1,KernelEnabled=2,Wow64Container=4};
typedef struct {unsigned Machine:16,KernelMode:1,UserMode:1,Native:1,Process:1,WoW64Container:1,Reserved:11;} SYSTEM_SUPPORTED_PROCESSOR_ARCHITECTURES_INFORMATION;
static NTSTATUS error;
static NTSTATUS NtQuerySystemInformationEx(unsigned cls,void *query,unsigned qlen,void *data,unsigned size,void *ret) {
 (void)ret;assert(cls==181&&query&&qlen==sizeof(HANDLE));assert(size==8*sizeof(SYSTEM_SUPPORTED_PROCESSOR_ARCHITECTURES_INFORMATION));
 if(error)return error;
 SYSTEM_SUPPORTED_PROCESSOR_ARCHITECTURES_INFORMATION entries[8]={{.Machine=0xaa64,.Native=1,.UserMode=1,.KernelMode=1},{.Machine=0x14c,.UserMode=1,.WoW64Container=1},{.Machine=0x8664,.UserMode=1,.WoW64Container=1}};
 memcpy(data,entries,sizeof(entries));return 0;
}
'''
main=r'''
int main(void) {
 MACHINE_ATTRIBUTES a=99;
 assert(!GetMachineTypeAttributes(0xaa64,&a)&&a==3);
 assert(!GetMachineTypeAttributes(0x14c,&a)&&a==5);
 assert(!GetMachineTypeAttributes(0x8664,&a)&&a==1);
 assert(!GetMachineTypeAttributes(0,&a)&&a==0);
 error=(int32_t)0xc0000002;a=99;
 assert(GetMachineTypeAttributes(0x8664,&a)==(int32_t)0xd0000002&&a==99);
 return 0;
}
'''
with tempfile.TemporaryDirectory() as td:
 d=Path(td);(d/'test.c').write_text(fixture+function+main)
 subprocess.run([os.getenv('CC','clang'),'-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(d/'test.c'),'-o',str(d/'test')],check=True)
 subprocess.run([str(d/'test')],check=True)
with tempfile.TemporaryDirectory() as td:
 d=Path(td)
 for name in ['dlls/kernel32/kernel32.spec','dlls/kernelbase/kernelbase.spec','dlls/kernelbase/process.c']:
  dest=d/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/'wine'/name,dest)
 subprocess.run(['git','apply','--check',str(root/'build/wine-pe/steam-ui-machine-attributes.patch')],cwd=d,check=True)
assert '@ stdcall -import GetMachineTypeAttributes(long ptr)' in p
assert '@ stdcall GetMachineTypeAttributes(long ptr)' in p
print('PASS: production machine attributes native/x86/AMD64 flags, unsupported machine and query failure')
