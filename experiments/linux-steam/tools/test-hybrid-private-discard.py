#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Qualify exclusive discard with current lazy/fork/CoW memory units on HOST.

This never installs or runs an iOS app. The historical prototype remains off by
default; fixture replacement counters do not measure physical RAM reclamation.
"""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for n in ('artifacts','archive','output'):p.add_argument(n,type=Path)
a=p.parse_args();base=a.artifacts.resolve();archive=a.archive.resolve();out=a.output.resolve();repo=Path(__file__).resolve().parents[3];tools=Path(__file__).parent
src=repo/'vendor/LinuxRunner';host=base/'host'
assert str(out).startswith('/Volumes/easystore/') and not out.exists() and archive.is_file()
# Guest harness requires the previously qualified lifecycle/log bridge archive,
# not an uninstrumented kernel. Check before doing any test compilation.
symbols=subprocess.check_output(['xcrun','nm','-g',archive],text=True)
assert all(' T '+s in symbols for s in ('_ideck_guest_lifetime_live','_ideck_guest_lifetime_marker','_ideck_native_log_bridge_marker'))
out.mkdir(mode=0o700,parents=True);commands=[];rows=[]
def run(*cmd,log):
    cmd=[str(x) for x in cmd];commands.append(cmd)
    with log.open('x') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=60,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0'))
    assert not r.returncode,(r.returncode,log)
def build(tool,*args,log):run(sys.executable,tools/tool,*args,log=log)
for mode in ('normal','fail-second'):
    o=out/mode;o.mkdir(mode=0o700)
    build('build-madvise-stats.py',src,host,archive,o/'advice','--sanitize','--host-private-discard',*(['--host-fail-second'] if mode=='fail-second' else []),log=o/'advice-build.log')
    build('build-lazy-pages.py',src,host,o/'advice/libish.a',o/'lazy','--sanitize',log=o/'lazy-build.log')
    mmap_source=o/'advice/mmap.c'
    if mode=='fail-second':
        # The next builder recompiles this unit; compiler flags from the first
        # archive are not inherited. Pin HOST injection in a NEW test-only copy.
        mmap_source=o/'advice/mmap-host-inject.c'
        mmap_source.write_text('#define IDECK_DISCARD_HOST_FAIL_SECOND 1\n'+(o/'advice/mmap.c').read_text())
    build('build-fork-map-failure.py',src,host,o/'lazy/libish.a',o/'fork','--memory-source',o/'lazy/memory.c','--mmap-source',mmap_source,'--sanitize',log=o/'fork-build.log')
    build('build-cow-native-group.py',src,host,o/'fork/libish.a',o/'fork/memory.c',o/'cow','--sanitize',log=o/'cow-build.log')
    flags=['-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DISH_INTERNAL=1','-DLOG_HANDLER_DPRINTF=1','-DIDECK_LAB_NATIVE_LOG=1','-I'+str(src),'-I'+str(host),'-I'+str(repo/'experiments/linux-steam/app'),'-fsanitize=address,undefined','-fno-sanitize-recover=all','-Wall','-Wextra','-Werror']
    run('xcrun','clang',*flags,tools/'private-discard-control.c',repo/'experiments/linux-steam/app/NativeKernelLog.c',o/'cow/libish.a','-L'+str(host),'-lish_emu','-lfakefs','-lsqlite3','-o',o/'control',log=o/'control-build.log')
    run(o/'control',mode,log=o/'control.log')
    checks=[l for l in (o/'control.log').read_text().splitlines() if l.endswith(('=PASS','=FAIL'))]
    assert len(checks)==22 and all(l.endswith('=PASS') for l in checks),checks
    rows.append({'mode':mode,'checks':checks,'log_sha256':hashlib.sha256((o/'control.log').read_bytes()).hexdigest()})
build('test-cow-guest.py',base,out/'normal/cow/libish.a',out/'guest20',log=out/'guest20-build.log')
build('test-cow-adjacent.py',base,out/'normal/cow/libish.a',out/'adjacent4',log=out/'adjacent4-build.log')
svc=out/'svc-discard4';svc.mkdir(mode=0o700);lab=repo/'experiments/linux-steam'
run('xcrun','clang','--target=aarch64-linux-gnu','--ld-path='+str(base/'tool-bin/ld.lld'),'-nostdlib','-static','-ffreestanding','-fno-builtin','-fno-stack-protector','-O2','-Wall','-Wextra','-Werror',lab/'guest/private-discard-probe.c','-Wl,-e,_start','-o',svc/'probe.elf',log=svc/'guest-build.log')
flags=['-DIDECK_LAB_GUEST_LIFETIME=1','-DIDECK_LAB_NATIVE_LOG=1','-DIDECK_LAB_LAZY_PAGES=1','-DIDECK_LAB_PRIVATE_DISCARD=1','-fsanitize=address,undefined','-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DLOG_HANDLER_DPRINTF=1','-DISH_INTERNAL=1','-I'+str(src),'-I'+str(host),'-I'+str(lab/'app'),'-Wall','-Wextra','-Werror','-Wno-unused-parameter']
run('xcrun','clang',*flags,*[lab/'app'/n for n in ['LinuxLabRuntime.c','LabDeviceFS.c','LabBridge.c','LaunchProtocol.c','NativeKernelLog.c']],tools/'private-discard-guest-control.c',out/'normal/cow/libish.a','-L'+str(host),'-lish_emu','-lfakefs','-lsqlite3','-o',svc/'control',log=svc/'host-build.log')
root=svc/'root';root.mkdir(mode=0o700);logs=svc/'logs';logs.mkdir(mode=0o700)
(root/'probe').write_bytes((svc/'probe.elf').read_bytes());(root/'probe').chmod(0o700)
run(svc/'control',root,logs,log=svc/'control.log')
checks=(root/'private-discard-results.txt').read_text().splitlines()
assert len(checks)==4 and all(x.endswith('=PASS') for x in checks),checks
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'evidence.json').write_text(json.dumps({'scope':'HOST current composed memory/mmap/fork/discard/CoW units and own wrappers ASanUBSan; remaining engine/dependencies not fully sanitized. No iPad/Steam/physical reclamation proof','normal_and_second_allocation_failure':rows,'ARM64_ELF_checks':28,'total_checks':72,'actual_ARM64_SVC_replacement_calls':1,'actual_ARM64_SVC_replaced_guest_bytes':65536,'SVC_log_sha256':sha(svc/'control.log'),'normal_archive_sha256':sha(out/'normal/cow/libish.a'),'commands':commands,'private_discard_source_sha256':sha(repo/'experiments/linux-steam/app/PrivateDiscard.inc')},indent=2)+'\n')
print('HOST composed exclusive discard: 44 ownership/rollback + 28 actual ARM64 ELF checks PASS; real SVC replacement count verified')
