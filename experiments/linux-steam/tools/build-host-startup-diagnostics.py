#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Copy ONLY own frontend sources to diagnose display bootstrap/cleanup.

No timeout expansion, connect workaround, Steam/guest/credential change, or
device action. Use an existing exact joined host archive in a fresh private out.
The diagnostic shell writes fixed stages/numeric child IDs to its private fd3;
native exit hooks emit only allowlisted executable roles and numeric statuses.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

p=argparse.ArgumentParser(description=__doc__)
for name in ('artifacts','archive','output'):p.add_argument(name,type=Path)
p.add_argument('--engine',type=Path,help='Explicit copied experimental engine; default original prepared engine')
a=p.parse_args();base,archive,out=(getattr(a,n).resolve() for n in ('artifacts','archive','output'))
assert all(str(x).startswith('/Volumes/easystore/') for x in (base,archive,out))
assert archive.is_file() and not out.exists()
repo=Path(__file__).resolve().parents[3];lab=repo/'experiments/linux-steam';src=repo/'vendor/LinuxRunner';host=base/'host'
engine=(a.engine or host/'libish_emu.a').resolve();assert engine.is_file() and str(engine).startswith('/Volumes/easystore/')
assert subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip()=='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
assert not subprocess.check_output(['git','-C',str(src),'status','--porcelain','--untracked-files=no'],text=True).strip()
out.mkdir(mode=0o700)
hashof=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
before=hashof(archive)
engine_before=hashof(engine)
header=(lab/'app/LinuxSteamSession.h').read_text()
def replace(body,old,new):
    assert body.count(old)==1,(old,body.count(old))
    return body.replace(old,new)
header=replace(header,'"set -eu; umask 077; "',
    '"set -eu; umask 077; exec 3> /tmp/ideck-startup-diagnostics.txt; echo session-enter >&3; "')
header=replace(header,'& xpid=$!; ', '& xpid=$!; echo xvfb-start=$xpid >&3; ')
header=replace(header,'cleanup() { test', 'cleanup() { saved=$?; echo cleanup-enter=$saved >&3; test')
header=replace(header,'kill \\"$xpid\\" 2>/dev/null || :; wait || :; };',
    'echo cleanup-kill-xvfb=$xpid >&3; kill \\"$xpid\\" 2>/dev/null || :; wait || :; echo cleanup-wait-returned >&3; };')
header=replace(header,'& vpid=$!; ', '& vpid=$!; echo vnc-start=$vpid >&3; ')
header=replace(header,'echo ready > /tmp/ideck-display-ready; ',
    'echo display-ready >&3; echo ready > /tmp/ideck-display-ready; ')
header=replace(header,'& spid=$!; ', '& spid=$!; echo steam-start=$spid >&3; ')
# Add stages without printing shell args/environment/passwords. Preserve the
# original count limit, delay, failed test status and EXIT cleanup contract.
token='n=$((n+1)); test \\"$n\\" -lt 100; sleep .1;'
assert header.count(token)==2
header=header.replace(token,'n=$((n+1)); echo display-wait=$n >&3; test \\"$n\\" -lt 100; sleep .1;')
(out/'LinuxSteamSession.h').write_text(header)
role='''
static void ideck_startup_exit(struct task *task,int status) {
    const char *role=!strcmp(task->comm,"Xvfb")?"xvfb":!strcmp(task->comm,"x11vnc")?"x11vnc":NULL;
    if(!role)return;
    char line[160];snprintf(line,sizeof line,"DISPLAY_ROLE_EXIT role=%s tid=%d tgid=%d status=%d",role,task->pid,task->tgid,status);
    ideck_native_log_line(line);
}
'''
runtime=(lab/'app/LinuxLabRuntime.c').read_text()
runtime=replace(runtime,'static void observe_exit(struct task *task, int status) {',
    role+'\nstatic void observe_exit(struct task *task, int status) {\n    ideck_startup_exit(task,status);')
(out/'LinuxLabRuntime.c').write_text(runtime)
backend=(lab/'app/RetainedFrontend.c').read_text()
backend=replace(backend,'static void observe(struct task *task,int status){',
    role+'\nstatic void observe(struct task *task,int status){ideck_startup_exit(task,status);')
# The copied backend needs declarations that the original backend never used.
backend='#include "NativeKernelLog.h"\n#include <stdio.h>\n'+backend
(out/'RetainedFrontend.c').write_text(backend)
flags=['-DIDECK_LAB_RETAINED_FRONTEND=1','-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DLOG_HANDLER_DPRINTF=1','-DISH_INTERNAL=1',
       '-DIDECK_HOST_SHUTDOWN_PROFILE=0','-DIDECK_LAB_STEAM_FRONTEND=1','-DIDECK_LAB_COMPAT_TOOL=1',
       '-DIDECK_LAB_GUEST_LIFETIME=1','-DIDECK_LAB_NATIVE_WORKERS=1','-DIDECK_LAB_NATIVE_LOG=1',
       '-DIDECK_LAB_LAZY_PAGES=1','-DIDECK_LAB_MADVISE_STATS=1','-DIDECK_LAB_CEF_DISABLE_GPU=1','-DIDECK_LAB_SHARED_DISPLAY=1']
sources=[out/'LinuxLabRuntime.c',*[lab/'app'/n for n in ('LabDeviceFS.c','LabBridge.c','LaunchProtocol.c','ToolInstall.c','NativeKernelLog.c','NativeSignalLease.c')],out/'RetainedFrontend.c',lab/'tools/retained-backend-control.c']
command=['xcrun','clang',*flags,'-I',str(src),'-I',str(host),'-I',str(lab/'app'),'-Wall','-Wextra','-Werror','-Wno-unused-parameter',*[str(x) for x in sources],str(archive),str(engine),'-L',str(host),'-lfakefs','-lsqlite3','-o',str(out/'control')]
subprocess.run(command,check=True)
assert hashof(archive)==before and hashof(engine)==engine_before
(out/'evidence.json').write_text(json.dumps({'scope':'HOST copied own-source startup diagnostic; selected engine separately recorded; no device/UI/game claim','archive_sha256':before,'archive_unchanged':True,'engine_sha256':engine_before,'explicit_engine':bool(a.engine),'source_sha256':{str(x.relative_to(repo)):hashof(x) for x in (lab/'app/LinuxSteamSession.h',lab/'app/LinuxLabRuntime.c',lab/'app/RetainedFrontend.c',lab/'tools/retained-backend-control.c')},'generated_sha256':{n:hashof(out/n) for n in ('LinuxSteamSession.h','LinuxLabRuntime.c','RetainedFrontend.c')},'control_sha256':hashof(out/'control'),'build_command':command},indent=2)+'\n')
print('Built copied host display-stage/allowlisted-exit diagnostic; no guest runtime workaround')
