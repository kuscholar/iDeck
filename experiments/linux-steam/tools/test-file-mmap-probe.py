#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Host controls of exact pinned realfs_mmap + Lab probe; no device or Steam."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('artifacts',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
repo=Path(__file__).resolve().parents[3];lab=repo/'experiments/linux-steam';src=repo/'vendor/LinuxRunner'
out=a.output.resolve();host=a.artifacts.resolve()/'host'
assert str(out).startswith('/Volumes/easystore/') and not out.exists()
out.mkdir(mode=0o700,parents=True)
def load(name):
    spec=importlib.util.spec_from_file_location(name,lab/'tools'/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
cleanup=load('file-map-cleanup');probe=load('file-mmap-probe')
assert subprocess.check_output(['git','-C',src,'rev-parse','HEAD'],text=True).strip()==cleanup.PIN
original=subprocess.check_output(['git','-C',src,'show',cleanup.PIN+':fs/real.c']).decode()
assert original==(src/'fs/real.c').read_text()
fixed=cleanup.patched(original);on=probe.patched(fixed)
assert on.count(probe.CALL)==1 and on.count(probe.FAILURE)==1
assert on.index('int result = errno_map();') < on.index(probe.CALL)
try:probe.patched(on)
except AssertionError:pass
else:raise AssertionError('Duplicate patch accepted')
headers='''#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <errno.h>
#include "kernel/task.h"
#include "kernel/memory.h"
#include "kernel/calls.h"
#include "kernel/errno.h"
#include "fs/fd.h"
#include "debug.h"
extern void (*runtime_memory_failure)(const char *,uint64_t,uint64_t,int,int,int);
'''
flags=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DISH_INTERNAL=1','-I'+str(src),'-I'+str(host),'-I'+str(lab/'app'),'-Wall','-Wextra','-Werror']
cases=['all-success','all-fail','shared-fail','release-fail','native','private','read-only','offset','too-large','too-small','other-errno','bad-fd','not-regular','shrunk','original-success']
results=[]
for enabled,body in [(0,fixed),(1,on)]:
    function=body[body.index('int realfs_mmap('):body.index('\nssize_t realfs_readlink(')]
    if enabled:headers2=headers+'#define IDECK_LAB_FILE_MMAP_PROBE 1\n#include "FileMmapProbe.inc"\n'
    else:headers2=headers
    unit=out/('real-'+str(enabled)+'.c');unit.write_text(headers2+function);obj=unit.with_suffix('.o')
    subprocess.run(['xcrun','clang',*flags,'-Dmmap=probe_mmap','-Dmunmap=probe_munmap','-Dfstat=probe_fstat','-Dpt_map=ideck_test_pt_map','-c',unit,'-o',obj],check=True)
    binary=out/('control-'+str(enabled))
    subprocess.run(['xcrun','clang',*flags,lab/'tools/file-mmap-probe-control.c',obj,'-o',binary],check=True)
    for case in cases:
        log=out/(str(enabled)+'-'+case+'.log')
        with log.open('x') as stream:
            result=subprocess.run([binary,case,str(enabled),out/(str(enabled)+'-'+case+'-own-file')],stdout=stream,stderr=subprocess.STDOUT,timeout=15)
        assert result.returncode==0,(enabled,case,log)
        results.append({'enabled':bool(enabled),'case':case,'exit':result.returncode,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
(out/'evidence.json').write_text(json.dumps({'scope':'HOST exact realfs_mmap with native API stubs; native case uses real own unlinked file. No Steam/device/capacity diagnosis.', 'linuxrunner':cleanup.PIN,'cases':results,'source_sha256':{str(f.relative_to(repo)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [lab/'app/FileMmapProbe.inc',lab/'tools/file-mmap-probe.py',lab/'tools/file-mmap-probe-control.c',Path(__file__)]}},indent=2)+'\n')
print('PASS30 HOST exact-function ASan/UBSan Werror cases; original error/success preserved, controls never installed, no device claim')
