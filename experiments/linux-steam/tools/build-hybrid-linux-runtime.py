#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Assemble the qualified Linux components on a separately namespaced iOS base.

Native Linux-only adapters are compiled with the same forced TLS declaration.
NEVER apply these flags to Wine/FEX sources. All outputs are private/new; no
original archive, vendor source, app installation, account or game is changed.
This prepares link inputs, not proof that Wine can start or return safely.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
p=argparse.ArgumentParser(description=__doc__)
for name in ('namespace_root','artifacts','output'):p.add_argument(name,type=Path)
p.add_argument('--ninja',required=True)
p.add_argument('--metal-drain',action='store_true',help='Track real Metal command/main bodies before retained transport completion')
p.add_argument('--shared-library',action='store_true',help='Mount a separate app-private realfs Steam library, preserving default /Steam')
p.add_argument('--capture-launch',action='store_true',help='Capture one checked native request; response remains125, no game execution')
p.add_argument('--dock-storage',action='store_true',help='New physical drive_c library layout and metadata mapping only')
p.add_argument('--register-shared-library',action='store_true',help='Register the shared install location before first Steam guest, retaining prior metadata')
p.add_argument('--retire-empty-probe',action='store_true',help='Retire only the exact empty legacy Control probe directories through Linux VFS')
p.add_argument('--file-map-cleanup',action='store_true',help='Release native file backings only when pt_map rejects ownership; no cap/allocation retry')
p.add_argument('--fork-map-failure',action='store_true',help='Return ENOMEM on failed child page-table/reservation allocation; no capacity/retry changes')
p.add_argument('--cow-native-group',action='store_true',help='Group compatible private anonymous CoW pages inside one native-page range; no file/shared/cap changes')
p.add_argument('--stage-dock-request',action='store_true',help='Copy a normally drained captured request into Swift metadata slot; NOT Wine/game execution')
p.add_argument('--native-setup-transition',action='store_true',help='Explicit main-thread native setup button after normal drain/staging; disables Linux restart, no automatic game launch')
p.add_argument('--cli-input-controls',action='store_true',help='Development only: nine fixed navigation events through existing RFB; no text or game-launch payload')
a=p.parse_args();ns,base,out=(getattr(a,n).resolve() for n in ('namespace_root','artifacts','output'))
assert all(str(x).startswith('/Volumes/easystore/') for x in (ns,base,out)) and not out.exists()
assert not a.capture_launch or (a.shared_library and a.metal_drain),'Capture integration needs explicit shared library and tracked Metal boundary'
assert not a.dock_storage or a.capture_launch,'Dock storage needs explicit capture/shared/Metal integration'
assert not a.register_shared_library or a.dock_storage,'Library registration requires the explicit physical Dock storage layout'
assert not a.retire_empty_probe or a.register_shared_library,'Empty-probe retirement requires explicit shared-library registration'
assert not a.stage_dock_request or a.dock_storage,'Native request staging requires explicit captured Dock storage integration'
assert not a.native_setup_transition or a.stage_dock_request,'Native setup presentation requires explicit request staging'
repo=Path(__file__).resolve().parents[3];lab=repo/'experiments/linux-steam';src=repo/'vendor/LinuxRunner';build=ns/'build'
assert subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip()=='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
assert not subprocess.check_output(['git','-C',str(src),'status','--porcelain','--untracked-files=no'],text=True).strip()
hashof=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
original=json.loads((ns/'evidence.json').read_text());assert original['platform']=='ios'
for name,data in original['archives'].items():assert hashof(build/name)==data['sha256'],name
assert hashof(ns/'LinuxSymbolNamespace.h')==original['namespace_header_sha256']==hashof(lab/'app/LinuxSymbolNamespace.h')
entries=json.loads((build/'compile_commands.json').read_text())
assert all('-DIDECK_LAB_LINUX_SYMBOL_NAMESPACE=1' in e['command'] for e in entries)
out.mkdir(mode=0o700);commands=[]
def run(tool,*args):
    cmd=[sys.executable,str(lab/'tools'/tool),*[str(x) for x in args]];commands.append(cmd);subprocess.run(cmd,check=True)
run('build-pipe-observer.py',src,build,a.ninja,out/'packet','--packet-pipes','--archive-only')
run('build-tcp-view.py',src,build,out/'packet/libish.a',a.ninja,out/'tcp','--archive-only')
run('build-guest-lifetime.py',src,build,out/'tcp/libish.a',out/'guests','--join-guests','--guest-waves')
run('build-native-workers.py',src,build,out/'guests/libish.a',out/'workers','--join-workers','--stop-profile','--worker-waves')
run('build-native-logging.py',src,build,out/'workers/libish.a',out/'logging')
run('build-madvise-stats.py',src,build,out/'logging/libish.a',out/'advice')
run('build-lazy-pages.py',src,build,out/'advice/libish.a',out/'lazy')
kernel=out/'lazy/libish.a'
if a.file_map_cleanup:
    run('build-file-map-cleanup.py',src,build,kernel,out/'file-map-cleanup')
    kernel=out/'file-map-cleanup/libish.a'
if a.fork_map_failure:
    run('build-fork-map-failure.py',src,build,kernel,out/'fork-map-failure',
        '--memory-source',out/'lazy/memory.c','--mmap-source',out/'advice/mmap.c')
    kernel=out/'fork-map-failure/libish.a'
if a.cow_native_group:
    memory=out/'fork-map-failure/memory.c' if a.fork_map_failure else out/'lazy/memory.c'
    run('build-cow-native-group.py',src,build,kernel,memory,out/'cow-native-group')
    kernel=out/'cow-native-group/libish.a'
run('build-casp-order.py',src,build,build/'libish_emu.a',out/'engine')
runtime=out/'runtime';runtime.mkdir()
for source,name in [(kernel,'libish.a'),(out/'engine/libish_emu.a','libish_emu.a'),(build/'libfakefs.a','libfakefs.a')]:shutil.copy2(source,runtime/name)
run('build-rfb-lifetime.py',out/'rfb')
sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
flags=['-target','arm64-apple-ios26.0','-isysroot',sdk,'-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DLOG_HANDLER_DPRINTF=1','-DISH_INTERNAL=1',
 '-DIDECK_LAB_LINUX_SYMBOL_NAMESPACE=1','-include',str(ns/'LinuxSymbolNamespace.h'),
 '-DIDECK_LAB_STEAM_FRONTEND=1','-DIDECK_LAB_RETAINED_FRONTEND=1','-DIDECK_LAB_RFB_LIFETIME=1','-DIDECK_LAB_CASP_ORDER=1',
 '-DIDECK_LAB_GUEST_LIFETIME=1','-DIDECK_LAB_NATIVE_WORKERS=1','-DIDECK_LAB_NATIVE_LOG=1','-DIDECK_LAB_COMPAT_TOOL=1',
 '-DIDECK_LAB_SHARED_DISPLAY=1','-DIDECK_LAB_CEF_DISABLE_GPU=1','-DIDECK_LAB_MADVISE_STATS=1','-DIDECK_LAB_LAZY_PAGES=1',
 '-DIDECK_LAB_X11_TRACE=0','-DIDECK_LAB_GAME_FILE_POLICY='+str(int(a.capture_launch)),'-DIDECK_LAB_CAPTURE_LAUNCH='+str(int(a.capture_launch)),'-DIDECK_LAB_PRIVATE_DISCARD=0',
 '-DIDECK_LAB_ROOTFS_SHA256="8afdfb2b9dfa76eef305865ec64994451a7cf953fd1bc2eb3a53fd10d066d84a"',
 '-I',str(src),'-I',str(build),'-I',str(lab/'app'),'-I',str(src/'app/LinuxRunner'),'-I',str(out/'rfb'),
 '-O0','-g','-fvisibility=hidden']
sources=[lab/'app'/name for name in ('LinuxLabRuntime.c','LabDeviceFS.c','LabBridge.c','LaunchProtocol.c','ToolInstall.c','NativeKernelLog.c','NativeSignalLease.c','RetainedFrontend.c','LabRootFS.m','LabSocketPrefix.m','LinuxSteamViewController.m','LabRFBClient.m')]
sources += [src/'app/LinuxRunner'/'RFBProtocol.c']
if a.capture_launch:sources += [lab/'app/GameFilePolicy.c',lab/'app/GameFiles.c']
if a.dock_storage:
    import re
    value=re.search(r'static let relativeRoot = "([^"\n]+)"',(repo/'app/Madeira/SteamRuntime.swift').read_text())
    assert value,'Pinned SteamRuntimeFiles.relativeRoot must be an explicit constant'
    flags+=['-DIDECK_LAB_DOCK_STORAGE=1','-DIDECK_LAB_STEAM_WINDOWS_ROOT="'+value.group(1)+'"']
    sources += [lab/'app/WindowsLaunchMap.c',lab/'app/LabWindowsLibrary.m']
if a.shared_library:
    flags+=['-DIDECK_LAB_SHARED_LIBRARY=1']
    sources += [lab/'app/SharedSteamLibrary.c']
if a.register_shared_library:
    flags+=['-DIDECK_LAB_REGISTER_SHARED_LIBRARY=1']
    sources += [lab/'app/SharedLibraryConfig.c',lab/'app/SharedLibraryRegister.c']
if a.retire_empty_probe:flags+=['-DIDECK_LAB_RETIRE_EMPTY_PROBE=1']
if a.metal_drain:
    run('build-metal-drain.py',out/'metal')
    flags+=['-DIDECK_LAB_METAL_DRAIN=1']
    sources += [lab/'app/LabMetalDrain.m',out/'metal/MetalFramebufferView.m']
else:
    sources += [src/'app/LinuxRunner/MetalFramebufferView.m']
objects=[];rows=[];objdir=out/'adapters';objdir.mkdir()
if a.stage_dock_request:flags+=['-DIDECK_LAB_STAGE_DOCK_REQUEST=1']
if a.native_setup_transition:flags+=['-DIDECK_LAB_NATIVE_SETUP_TRANSITION=1']
if a.cli_input_controls:flags+=['-DIDECK_LAB_CLI_INPUT=1']
for source in sources:
    assert source.is_file(),source
    obj=objdir/(source.stem+'.o');cmd=['xcrun','clang',*flags]
    if source.suffix=='.m':cmd+=['-fobjc-arc','-fblocks']
    cmd+=['-c',str(source),'-o',str(obj)];commands.append(cmd);subprocess.run(cmd,check=True)
    symbols=subprocess.check_output(['nm','-m',str(obj)],text=True)
    assert not any(line.rstrip().endswith('external _current') for line in symbols.splitlines()),source
    rows.append({'source':str(source.relative_to(repo)) if source.is_relative_to(repo) else str(source),'source_sha256':hashof(source),'object_sha256':hashof(obj),
                 'linux_TLS_rows':[l for l in symbols.splitlines() if l.rstrip().endswith('external _ideck_linux_current')]})
    objects.append(str(obj))
frontend=runtime/'libideck_linux_frontend.a';subprocess.run(['xcrun','ar','rcs',str(frontend),*objects],check=True)
for name in ('libish.a','libish_emu.a','libfakefs.a','libideck_linux_frontend.a'):
    symbols=subprocess.check_output(['nm','-m','-g',str(runtime/name)],text=True,stderr=subprocess.DEVNULL)
    assert not any(l.rstrip().endswith('external _current') for l in symbols.splitlines()),name
for name,data in original['archives'].items():assert hashof(build/name)==data['sha256'],name
(out/'evidence.json').write_text(json.dumps({'scope':'Qualified copied NAMESPACED Linux kernel/engine/frontend link inputs ONLY; NOT combined app/Wine execution/device/game proof',
 'linuxrunner':original['linuxrunner'],'namespace_base_evidence_sha256':hashof(ns/'evidence.json'),
 'namespace_header_sha256':hashof(ns/'LinuxSymbolNamespace.h'),'base_archives_unchanged':True,
 'archives_sha256':{p.name:hashof(p) for p in runtime.iterdir()},'native_adapter_objects':rows,'commands':commands,
 'tracked_Metal_command_boundary_enabled':a.metal_drain,'separate_realfs_library_enabled':a.shared_library,'native_launch_capture_enabled':a.capture_launch,'physical_Dock_storage_enabled':a.dock_storage,'shared_library_registration_enabled':a.register_shared_library,'empty_legacy_probe_retirement_enabled':a.retire_empty_probe,'file_map_failed_transfer_cleanup_enabled':a.file_map_cleanup,'fork_mapping_failure_checks_enabled':a.fork_map_failure,'anonymous_cow_native_group_enabled':a.cow_native_group,'native_dock_request_staging_enabled':a.stage_dock_request,'native_setup_transition_enabled':a.native_setup_transition,'cli_input_controls_enabled':a.cli_input_controls,'gpu_storage_and_Wine_admission_qualified':False},indent=2)+'\n')
print('Built namespaced Linux frontend+qualified runtime copies; no Wine or device execution')
