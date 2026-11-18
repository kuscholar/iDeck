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
p.add_argument('--native-jit',action='store_true',help='Explicit optional emitter base with matching Linux adapter layouts; does not activate iOS JIT')
p.add_argument('--debugger-prepared-jit',action='store_true',help='Default-off exact owned120MiB region handoff from authorized native developer debugger; requires native-jit')
p.add_argument('--metal-drain',action='store_true',help='Track real Metal command/main bodies before retained transport completion')
p.add_argument('--shared-library',action='store_true',help='Mount a separate app-private realfs Steam library, preserving default /Steam')
p.add_argument('--capture-launch',action='store_true',help='Capture one checked native request; response remains125, no game execution')
p.add_argument('--dock-storage',action='store_true',help='New physical drive_c library layout and metadata mapping only')
p.add_argument('--register-shared-library',action='store_true',help='Register the shared install location before first Steam guest, retaining prior metadata')
p.add_argument('--retire-empty-probe',action='store_true',help='Retire only the exact empty legacy Control probe directories through Linux VFS')
p.add_argument('--file-map-cleanup',action='store_true',help='Release native file backings only when pt_map rejects ownership; no cap/allocation retry')
p.add_argument('--file-mmap-failure-probe',action='store_true',help='Lab-only shared-file ENOMEM discriminator: at most four immediately unmapped controls, original result unchanged')
p.add_argument('--fork-map-failure',action='store_true',help='Return ENOMEM on failed child page-table/reservation allocation; no capacity/retry changes')
p.add_argument('--cow-native-group',action='store_true',help='Group compatible private anonymous CoW pages inside one native-page range; no file/shared/cap changes')
p.add_argument('--cow-native-pages-per-group',type=int,choices=(1,2),default=1,help='Explicit CoW span experiment: two native pages may reduce backings at extra materialization cost')
p.add_argument('--cow-backing-broker',action='store_true',help='Explicit owned dynamic chunks for private CoW only; no coarser copies, default off')
p.add_argument('--blocked-wait-callers',action='store_true',help='Default-off bounded main-renderer blocked-futex existing ABI/code-only caller metadata; no synchronization changes')
p.add_argument('--checked-frame-snapshot',action='store_true',help='Default-off checked malloc pixel copy adopted by immutable NSData; no Foundation large-copy allocation, allocationNULL stops display')
p.add_argument('--frame-snapshot-pool',action='store_true',help='Default-off four preallocated1280x800 immutable snapshot slots; allocation/exhaustion are explicit failures, no late pixel malloc')
p.add_argument('--pthread-stack-soft-limit',action='store_true',help='Default-off fixed Linux Steam shell soft stack4MiB; preserves hard limit, Darwin and explicit pthread attributes')
p.add_argument('--pthread-stack-cache-off',action='store_true',help='Default-off fixed Linux guest GLIBC_TUNABLES setting releases unused exited-thread stack cache; does not change stack size/RLIMIT or Darwin env')
p.add_argument('--va-headroom-probe',action='store_true',help='Default-off16MiB preguest PROT_NONE reserve/release and one control mapping on shared-file ENOMEM; no guest fallback')
p.add_argument('--map-pte-preflight',action='store_true',help='Default-off ordinary-map page-table allocation preflight with ENOMEM metadata rollback; no cap increase')
p.add_argument('--fiber-hash-growth-guard',action='store_true',help='Default-off preserve initialized translation hash if growth calloc fails; request existing flush, no cap change')
p.add_argument('--exclusive-private-discard',action='store_true',help='Explicit whole-backing private DONTNEED replacement experiment; unsupported mappings retain original path, not a physical-RAM reclamation claim')
p.add_argument('--stage-dock-request',action='store_true',help='Copy a normally drained captured request into Swift metadata slot; NOT Wine/game execution')
p.add_argument('--native-setup-transition',action='store_true',help='Explicit main-thread native setup button after normal drain/staging; disables Linux restart, no automatic game launch')
p.add_argument('--cli-input-controls',action='store_true',help='Development only: nine fixed navigation events through existing RFB; no text or game-launch payload')
p.add_argument('--x11-window-state',action='store_true',help='Explicit Lab-only bounded read-only X11 window/focus observer, no WM/input/pixels')
a=p.parse_args();ns,base,out=(getattr(a,n).resolve() for n in ('namespace_root','artifacts','output'))
assert all(str(x).startswith('/Volumes/easystore/') for x in (ns,base,out)) and not out.exists()
assert not (a.checked_frame_snapshot and a.frame_snapshot_pool),'Select one explicit snapshot policy'
assert not a.debugger_prepared_jit or a.native_jit,'Prepared-region handoff requires optional emitter'
assert not a.capture_launch or (a.shared_library and a.metal_drain),'Capture integration needs explicit shared library and tracked Metal boundary'
assert not a.dock_storage or a.capture_launch,'Dock storage needs explicit capture/shared/Metal integration'
assert not a.register_shared_library or a.dock_storage,'Library registration requires the explicit physical Dock storage layout'
assert not a.retire_empty_probe or a.register_shared_library,'Empty-probe retirement requires explicit shared-library registration'
assert not a.stage_dock_request or a.dock_storage,'Native request staging requires explicit captured Dock storage integration'
assert not a.native_setup_transition or a.stage_dock_request,'Native setup presentation requires explicit request staging'
assert not a.va_headroom_probe or a.file_mmap_failure_probe,'Headroom discriminator requires existing exact failure probe'
assert not a.file_mmap_failure_probe or a.file_map_cleanup,'File-mmap probe requires the copied qualified file-backend source'
assert a.cow_native_pages_per_group==1 or a.cow_native_group,'Coarser CoW span requires explicit anonymous grouping'
assert not a.cow_backing_broker or (a.cow_native_group and a.cow_native_pages_per_group==1),'Broker requires original one-native-page CoW groups'
assert not a.exclusive_private_discard or (a.fork_map_failure and a.cow_native_group and a.cow_native_pages_per_group==1),'Discard comparison requires qualified checked-fork and original-span CoW stack'
repo=Path(__file__).resolve().parents[3];lab=repo/'experiments/linux-steam';src=repo/'vendor/LinuxRunner';build=ns/'build'
assert subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip()=='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
assert not subprocess.check_output(['git','-C',str(src),'status','--porcelain','--untracked-files=no'],text=True).strip()
hashof=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
original=json.loads((ns/'evidence.json').read_text());assert original['platform']=='ios'
assert bool(original.get('native_jit_compiled',False))==a.native_jit, 'Native JIT engine and adapter layouts must be selected together'
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
run('build-madvise-stats.py',src,build,out/'logging/libish.a',out/'advice',*(['--experimental-private-discard'] if a.exclusive_private_discard else []))
run('build-lazy-pages.py',src,build,out/'advice/libish.a',out/'lazy')
kernel=out/'lazy/libish.a'
if a.file_map_cleanup:
    run('build-file-map-cleanup.py',src,build,kernel,out/'file-map-cleanup',*(['--mmap-failure-probe'] if a.file_mmap_failure_probe else []),*(['--va-headroom-probe'] if a.va_headroom_probe else []))
    kernel=out/'file-map-cleanup/libish.a'
if a.fork_map_failure:
    run('build-fork-map-failure.py',src,build,kernel,out/'fork-map-failure',
        '--memory-source',out/'lazy/memory.c','--mmap-source',out/'advice/mmap.c')
    kernel=out/'fork-map-failure/libish.a'
if a.cow_native_group:
    memory=out/'fork-map-failure/memory.c' if a.fork_map_failure else out/'lazy/memory.c'
    run('build-cow-native-group.py',src,build,kernel,memory,out/'cow-native-group',*(['--native-pages-per-group',str(a.cow_native_pages_per_group)] if a.cow_native_pages_per_group!=1 else []),*(['--backing-broker'] if a.cow_backing_broker else []))
    kernel=out/'cow-native-group/libish.a'
if a.map_pte_preflight:
    map_memory=out/('cow-native-group' if a.cow_native_group else 'fork-map-failure' if a.fork_map_failure else 'lazy')/'memory.c'
    run('build-map-pte-guard.py',src,build,kernel,out/'map-pte','--memory-source',map_memory)
    kernel=out/'map-pte/libish.a'
run('build-casp-order.py',src,build,build/'libish_emu.a',out/'engine')
engine=out/'engine/libish_emu.a'
if a.fiber_hash_growth_guard:
    run('build-fiber-hash-guard.py',src,build,engine,out/'hash-growth')
    engine=out/'hash-growth/libish_emu.a'
if a.debugger_prepared_jit:
    run('build-debugger-jit-region.py',src,build,engine,out/'debugger-region')
    engine=out/'debugger-region/libish_emu.a'
runtime=out/'runtime';runtime.mkdir()
for source,name in [(kernel,'libish.a'),(engine,'libish_emu.a'),(build/'libfakefs.a','libfakefs.a')]:shutil.copy2(source,runtime/name)
run('build-rfb-lifetime.py',out/'rfb',*(['--checked-frame-snapshot'] if a.checked_frame_snapshot else []),*(['--frame-snapshot-pool'] if a.frame_snapshot_pool else []))
sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
flags=['-target','arm64-apple-ios26.0','-isysroot',sdk,'-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DLOG_HANDLER_DPRINTF=1','-DISH_INTERNAL=1',
 '-DIDECK_LAB_LINUX_SYMBOL_NAMESPACE=1','-include',str(ns/'LinuxSymbolNamespace.h'),
 '-DIDECK_LAB_STEAM_FRONTEND=1','-DIDECK_LAB_RETAINED_FRONTEND=1','-DIDECK_LAB_RFB_LIFETIME=1','-DIDECK_LAB_CASP_ORDER=1',
 '-DIDECK_LAB_GUEST_LIFETIME=1','-DIDECK_LAB_NATIVE_WORKERS=1','-DIDECK_LAB_NATIVE_LOG=1','-DIDECK_LAB_COMPAT_TOOL=1',
 '-DIDECK_LAB_SHARED_DISPLAY=1','-DIDECK_LAB_CEF_DISABLE_GPU=1','-DIDECK_LAB_MADVISE_STATS=1','-DIDECK_LAB_LAZY_PAGES=1',
 '-DIDECK_LAB_X11_TRACE=0','-DIDECK_LAB_GAME_FILE_POLICY='+str(int(a.capture_launch)),'-DIDECK_LAB_CAPTURE_LAUNCH='+str(int(a.capture_launch)),'-DIDECK_LAB_PRIVATE_DISCARD='+str(int(a.exclusive_private_discard)),
 '-DIDECK_LAB_ROOTFS_SHA256="8afdfb2b9dfa76eef305865ec64994451a7cf953fd1bc2eb3a53fd10d066d84a"',
 '-I',str(src),'-I',str(build),'-I',str(lab/'app'),'-I',str(src/'app/LinuxRunner'),'-I',str(out/'rfb'),
 '-O0','-g','-fvisibility=hidden']
sources=[lab/'app'/name for name in ('LinuxLabRuntime.c','LabDeviceFS.c','LabBridge.c','LaunchProtocol.c','ToolInstall.c','NativeKernelLog.c','NativeSignalLease.c','RetainedFrontend.c','LabRootFS.m','LabSocketPrefix.m','LinuxSteamViewController.m','LabRFBClient.m')]
if a.pthread_stack_soft_limit:flags+=['-DIDECK_LAB_PTHREAD_STACK_SOFT_LIMIT=1']
if a.pthread_stack_cache_off:flags+=['-DIDECK_LAB_PTHREAD_STACK_CACHE_OFF=1']
if a.native_jit:
    flags+=['-DISH_JIT=1','-DIDECK_LAB_NATIVE_JIT=1']
    sources += [lab/'app/LabNativeJIT.c']
if a.debugger_prepared_jit:flags+=['-DIDECK_LAB_DEBUGGER_PREPARED_JIT=1']
sources += [src/'app/LinuxRunner'/'RFBProtocol.c']
if a.checked_frame_snapshot:
    flags+=['-DIDECK_LAB_RFB_CHECKED_SNAPSHOT=1']
    sources += [lab/'app/CheckedFrameSnapshot.m']
if a.frame_snapshot_pool:
    flags+=['-DIDECK_LAB_FRAME_SNAPSHOT_POOL=1']
    sources += [lab/'app/FrameSnapshotPool.m']
if a.fiber_hash_growth_guard:flags+=['-DIDECK_LAB_FIBER_HASH_GUARD=1']
if a.map_pte_preflight:flags+=['-DIDECK_LAB_MAP_PTE_PREFLIGHT=1']
if a.va_headroom_probe:
    flags+=['-DIDECK_LAB_VA_HEADROOM_PROBE=1']
    sources += [lab/'app/VAHeadroomProbe.c']
if a.cow_backing_broker:flags+=['-DIDECK_LAB_COW_BROKER=1']
if a.blocked_wait_callers:
    flags+=['-DIDECK_LAB_BLOCKED_WAIT_CALLERS=1']
    sources += [lab/'app/BlockedWaitCallers.c']
if a.x11_window_state:
    flags+=['-DIDECK_LAB_X11_STATE=1']
    sources += [lab/'app/X11StateInstall.c']
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
 'native_jit_compiled':a.native_jit,'native_jit_device_activation_validated':False,
 'debugger_prepared_jit_enabled':a.debugger_prepared_jit,
 'archives_sha256':{p.name:hashof(p) for p in runtime.iterdir()},'native_adapter_objects':rows,'commands':commands,
 'tracked_Metal_command_boundary_enabled':a.metal_drain,'separate_realfs_library_enabled':a.shared_library,'native_launch_capture_enabled':a.capture_launch,'physical_Dock_storage_enabled':a.dock_storage,'shared_library_registration_enabled':a.register_shared_library,'empty_legacy_probe_retirement_enabled':a.retire_empty_probe,'file_map_failed_transfer_cleanup_enabled':a.file_map_cleanup,'file_mmap_failure_probe_enabled':a.file_mmap_failure_probe,'fork_mapping_failure_checks_enabled':a.fork_map_failure,'anonymous_cow_native_group_enabled':a.cow_native_group,'cow_native_pages_per_group':a.cow_native_pages_per_group,'cow_backing_broker_enabled':a.cow_backing_broker,'blocked_wait_callers_enabled':a.blocked_wait_callers,'checked_frame_snapshot_enabled':a.checked_frame_snapshot,'frame_snapshot_pool_enabled':a.frame_snapshot_pool,'fiber_hash_growth_guard_enabled':a.fiber_hash_growth_guard,'map_pte_preflight_enabled':a.map_pte_preflight,'va_headroom_probe_enabled':a.va_headroom_probe,'guest_pthread_stack_soft_limit':a.pthread_stack_soft_limit,'guest_pthread_stack_cache_off':a.pthread_stack_cache_off,'exclusive_private_discard_enabled':a.exclusive_private_discard,'native_dock_request_staging_enabled':a.stage_dock_request,'native_setup_transition_enabled':a.native_setup_transition,'cli_input_controls_enabled':a.cli_input_controls,'x11_window_state_enabled':a.x11_window_state,'gpu_storage_and_Wine_admission_qualified':False},indent=2)+'\n')
print('Built namespaced Linux frontend+qualified runtime copies; no Wine or device execution')
