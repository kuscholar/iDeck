#!/usr/bin/env python3
"""Run the actual guest probe logic against disjoint/alias/failure API fixtures.
This validates reporting and bounds, not any OS virtual-memory implementation.
"""
from pathlib import Path
import os,subprocess,tempfile
root=Path(__file__).resolve().parents[2]
header=r'''
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
typedef size_t SIZE_T;
typedef unsigned long DWORD;
typedef struct {void *AllocationBase;size_t RegionSize;unsigned long State;} MEMORY_BASIC_INFORMATION;
#define MEM_RESERVE 0x2000
#define PAGE_NOACCESS 1
static unsigned calls;
static void SetLastError(DWORD e){}
static DWORD GetLastError(void){return 8;}
static void *VirtualAlloc(void *hint,SIZE_T size,DWORD type,DWORD prot){
    const char *mode=getenv("RESERVE_FIXTURE");
    if(type!=MEM_RESERVE||prot!=PAGE_NOACCESS||++calls>4)abort();
    if(mode[0]=='f' && calls==3)return NULL;
    if(mode[0]=='o' && calls==3)return (void*)0x7800000000ULL;
    if(mode[0]=='w')return (void*)(UINTPTR_MAX-7);
    return (void*)(0x7000000000ULL+(uintptr_t)calls*0x800000000ULL);
}
static SIZE_T VirtualQuery(void *p,MEMORY_BASIC_INFORMATION *m,SIZE_T n){
    m->AllocationBase=p;m->RegionSize=0x400000000ULL;m->State=MEM_RESERVE;return n;
}
'''
with tempfile.TemporaryDirectory() as td:
    td=Path(td);(td/'windows.h').write_text(header)
    exe=td/'probe'
    subprocess.run(['cc','-fsanitize=address,undefined','-I',str(td),str(root/'tests/steam-ui/reservation-ownership.c'),'-o',str(exe)],check=True)
    for mode,code,label in [('disjoint',0,'PASS'),('overlap',40,'FAIL: overlapping'),('failure',70,'CAPACITY_GATE'),('wrap',41,'interval overflow')]:
        env=dict(os.environ,RESERVE_FIXTURE=mode)
        p=subprocess.run([str(exe),'--isolated-reserve-only'],env=env,capture_output=True,text=True)
        assert p.returncode==code,(mode,p.returncode,p.stdout,p.stderr)
        assert label in p.stdout
    p=subprocess.run([str(exe)],capture_output=True,text=True)
    assert p.returncode==64 and 'REFUSED' in p.stdout
print('PASS: actual PE logic reports alias vs capacity vs disjoint; finite reserve-only calls; overflow and explicit opt-in checked (ASan/UBSan)')
