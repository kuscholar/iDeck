#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
from pathlib import Path
import subprocess,json,hashlib
import argparse
p=argparse.ArgumentParser(description='HOST actual native offer contract; backend/OS calls are explicit fixture boundaries, not JIT/UI proof')
p.add_argument('namespace_root',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
repo=Path(__file__).resolve().parents[3];lab=repo/'experiments/linux-steam';src=repo/'vendor/LinuxRunner';ns=a.namespace_root.resolve();out=a.output.resolve()
evidence=json.loads((ns/'evidence.json').read_text());assert evidence['platform']=='host' and evidence.get('native_jit_compiled') is True
assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(mode=0o700,parents=True)
fixture=r'''
#include "LabNativeJIT.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static int adopted,faults,adopt_result,handler_result;
void ideck_native_log_line(const char *line){assert(line&&strlen(line)<160);}
void jit_counters(uint64_t *a,uint64_t *b,uint64_t *c){*a=*b=*c=0;}
int ideck_linux_jit_adopt_debugger_region(void *rx,size_t length){
    adopted++;assert((uintptr_t)rx==0x40000000&&length==IDECK_LAB_DEBUGGER_JIT_BYTES);return adopt_result;
}
int ish_app_native_fault_install(void){faults++;return handler_result;}
int main(int argc,char **argv){
    assert(argc==2);const char *kind=argv[1];int expected=-1,expected_adopt=0,expected_fault=0;
    volatile uint64_t *o=ideck_lab_debugger_jit_offer;
    o[0]=IDECK_LAB_DEBUGGER_JIT_MAGIC;o[1]=(uint64_t)getpid();o[2]=0x40000000;o[3]=IDECK_LAB_DEBUGGER_JIT_BYTES;o[4]=IDECK_LAB_DEBUGGER_JIT_BYTES/16384;
    if(!strcmp(kind,"missing"))o[0]=0;
    else if(!strcmp(kind,"magic"))o[0]^=1;
    else if(!strcmp(kind,"pid"))o[1]++;
    else if(!strcmp(kind,"null"))o[2]=0;
    else if(!strcmp(kind,"alignment"))o[2]++;
    else if(!strcmp(kind,"size"))o[3]-=16384;
    else if(!strcmp(kind,"pages"))o[4]++;
    else if(!strcmp(kind,"overflow"))o[2]=UINT64_MAX-16383;
    else if(!strcmp(kind,"valid")){expected=0;expected_adopt=expected_fault=1;}
    else if(!strcmp(kind,"adopt-failure")){expected=adopt_result=-14;expected_adopt=1;}
    else if(!strcmp(kind,"handler-failure")){expected=-2;expected_adopt=expected_fault=1;handler_result=-1;}
    else if(!strcmp(kind,"classic-disabled")){
        assert(ideck_lab_native_jit_prepare_classic()==-1&&adopted==0&&faults==0);return 0;
    }else abort();
    int result=ideck_lab_native_jit_prepare_debugger();assert(result==expected&&adopted==expected_adopt&&faults==expected_fault&&o[0]==0);
    struct ideck_lab_native_jit_stats before,after;ideck_lab_native_jit_read(&before);
    assert(before.activation_status==(expected==0?1:-1));assert(!before.blocks&&!before.segments&&!before.code_bytes);
    o[0]=IDECK_LAB_DEBUGGER_JIT_MAGIC;
    assert(ideck_lab_native_jit_prepare_debugger()==-1&&adopted==expected_adopt&&faults==expected_fault);
    ideck_lab_native_jit_read(&after);assert(after.activation_status==before.activation_status);
    puts("bounded native-offer contract PASS; backend/OS are fixture boundaries");return 0;
}
'''
(out/'control.c').write_text(fixture)
cmd=['xcrun','clang','-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DISH_JIT=1','-DIDECK_LAB_NATIVE_JIT=1','-DIDECK_LAB_DEBUGGER_PREPARED_JIT=1','-DISH_INTERNAL=1','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(src),'-I'+str(ns/'build'),'-I'+str(lab/'app'),str(out/'control.c'),str(lab/'app/LabNativeJIT.c'),'-o',str(out/'control')]
with (out/'compile.log').open('x') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=60)
assert r.returncode==0
rows=[]
for case in ('missing','magic','pid','null','alignment','size','pages','overflow','valid','adopt-failure','handler-failure','classic-disabled'):
 with (out/(case+'.log')).open('x') as f:r=subprocess.run([out/'control',case],stdout=f,stderr=subprocess.STDOUT,timeout=20)
 assert r.returncode==0,(case,r.returncode)
 rows.append({'case':case,'exit':0})
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'evidence.json').write_text(json.dumps({'scope':'HOST actual native offer parser and single-consumption/failure/activation-state contract ASanUBSan; backend adoption/OS fault installation are explicit fixture boundaries, NOT actual OS region/JIT/UI proof','cases':rows,'command':cmd,'sources_sha256':{n:sha(lab/'app'/n) for n in ['LabNativeJIT.c','LabNativeJIT.h']}},indent=2)+'\n')
print('HOST12offer/refusal/replay/failure/classic-disabled controls PASS')
