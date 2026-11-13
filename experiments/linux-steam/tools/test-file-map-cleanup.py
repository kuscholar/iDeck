#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Compile the exact pinned realfs_mmap function with a host-only pt_map stub."""
import argparse,hashlib,json,subprocess,importlib.util
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('artifacts',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
repo=Path(__file__).resolve().parents[3];lab=repo/'experiments/linux-steam';src=repo/'vendor/LinuxRunner';out=a.output.resolve();host=a.artifacts.resolve()/'host'
assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(mode=0o700,parents=True)
spec=importlib.util.spec_from_file_location('map_cleanup',lab/'tools/file-map-cleanup.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
assert subprocess.check_output(['git','-C',src,'rev-parse','HEAD'],text=True).strip()==module.PIN
original=subprocess.check_output(['git','-C',src,'show',module.PIN+':fs/real.c']).decode();assert original==(src/'fs/real.c').read_text()
def extract(body):return body[body.index('int realfs_mmap('):body.index('\nssize_t realfs_readlink(')]
headers='''#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <errno.h>
#include "kernel/memory.h"
#include "kernel/calls.h"
#include "kernel/errno.h"
#include "fs/fd.h"
extern void (*runtime_memory_failure)(const char *,uint64_t,uint64_t,int,int,int);
'''
results=[];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
flags=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DISH_INTERNAL=1','-I'+str(src),'-I'+str(host),'-Wall','-Wextra','-Werror']
for mode,body in [('baseline',original),('fixed',module.patched(original))]:
 unit=out/(mode+'.c');unit.write_text(headers+extract(body));obj=out/(mode+'.o')
 subprocess.run(['xcrun','clang',*flags,'-Dpt_map=ideck_test_pt_map','-c',unit,'-o',obj],check=True)
 binary=out/(mode+'-control');subprocess.run(['xcrun','clang',*flags,lab/'tools/file-map-cleanup-control.c',obj,'-o',binary],check=True)
 with (out/(mode+'.log')).open('x') as log:r=subprocess.run([binary,mode,out],stdout=log,stderr=subprocess.STDOUT,timeout=10)
 assert r.returncode==0,mode
 results.append({'mode':mode,'returncode':r.returncode,'exact_function_sha256':hashlib.sha256(extract(body).encode()).hexdigest(),'log_sha256':sha(out/(mode+'.log'))})
(out/'evidence.json').write_text(json.dumps({'scope':'HOST actual native mmap and self Mach VM region coverage; exact realfs function; only pt_map stubbed to inject metadata failure. Not a full guest/device/fix to original ENOMEM','linuxrunner':module.PIN,'tests':results},indent=2)+'\n')
print('HOST exact realfs function: baseline3 leaked failed transfers reproduced; fixed3 cleaned; both3 successes still owned by caller stub')
