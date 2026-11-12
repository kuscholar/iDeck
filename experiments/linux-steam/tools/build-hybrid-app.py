#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Prepare/build a PRIVATE isolated full Madeira + real Linux frontend app.

Tracked app/build sources come from this experiment, never a different worktree.
Only explicit prepared build payloads supplement that source; no account, game,
prefix/data migration, provisioning, install or FEX source edit. The normal app
project stays untouched. The private copy uses Linux Lab's actual entry point;
Wine/FEX/DXMT remain compiled/linked but are NOT automatically started here.
This is private research, not permission to redistribute a combined binary.
"""
import argparse
import hashlib
import json
import os
import plistlib
import re
from pathlib import Path
import shutil
import subprocess

p=argparse.ArgumentParser(description=__doc__)
for name in ('prepared','linux_runtime','artifacts','output'):p.add_argument(name,type=Path)
p.add_argument('--llvm-mingw',type=Path,required=True)
p.add_argument('--dependency-root',type=Path,help='Pinned read-only Wine/FEX headers/libraries when payload checkout lacks submodules')
p.add_argument('--build',action='store_true')
p.add_argument('--build-number',type=int,default=35)
p.add_argument('--madeira-setup',action='store_true',help='Explicit cold native setup mode, mutually exclusive with Linux experiments')
a=p.parse_args();prepared,linux,base,out=(getattr(a,n).resolve() for n in ('prepared','linux_runtime','artifacts','output'))
assert all(str(x).startswith('/Volumes/easystore/') for x in (prepared,linux,base,out)) and not out.exists()
assert 1 <= a.build_number <= 2147483647
repo=Path(__file__).resolve().parents[3];lab=repo/'experiments/linux-steam';hashof=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
deps=(a.dependency_root or prepared).resolve();assert str(deps).startswith('/Volumes/easystore/')
assert (deps/'FEX/.git').exists() and (deps/'wine/.git').exists(),'Dependency checkout must be initialized; do not mistake parent Git HEAD for submodule'
assert subprocess.check_output(['git','-C',str(deps/'FEX'),'rev-parse','HEAD'],text=True).strip()=='f59cab95659e8add0c88f0c76ec1cf483c536dbf'
assert subprocess.check_output(['git','-C',str(deps/'wine'),'rev-parse','HEAD'],text=True).strip()=='9129e9684daaeae70da9435e7c6060e59392634e'
runtime=linux/'runtime';e=json.loads((linux/'evidence.json').read_text())
assert not a.madeira_setup or e.get('physical_Dock_storage_enabled') is True,'Cold setup requires qualified physical Dock storage'
for name,h in e['archives_sha256'].items():assert hashof(runtime/name)==h,name
compiler=a.llvm_mingw.resolve()/'bin/x86_64-w64-mingw32-clang';assert compiler.is_file()
root_pins={x.split('=',1)[1].strip('"') for command in e.get('commands',[]) for x in command if x.startswith('-DIDECK_LAB_ROOTFS_SHA256=')}
assert len(root_pins)==1 and re.fullmatch('[0-9a-f]{64}',next(iter(root_pins))),'Qualified Linux artifact must record its actual compiled rootfs pin'
root_pin=next(iter(root_pins));ld_lld=base/'tool-bin/ld.lld';assert ld_lld.is_file()
out.mkdir(mode=0o700);stage=out/'source';stage.mkdir();copied=[];payload=[]
files=subprocess.check_output(['git','ls-files','-z','--','app','build','COPYING','LICENSE','LICENSE-EXCEPTION.md','LICENSES'],cwd=repo).split(b'\0')
for raw in files:
    if not raw:continue
    name=raw.decode();source=repo/name
    if not source.is_file():continue
    target=stage/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    copied.append({'source':name,'sha256':hashof(source)})
def supplement(source,target):
    assert source.exists(),source
    if source.is_dir():
        target.mkdir(parents=True,exist_ok=True)
        for child in source.iterdir():supplement(child,target/child.name)
    elif not target.exists():
        # Materialize a prepared file's bytes, never leave an output symlink
        # that a later bundle-copy/sign phase could write through.
        assert source.is_file(),source
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        payload.append({'source':str(source.relative_to(prepared)),'sha256':hashof(source),'bytes':source.stat().st_size})
    else:
        # Preserve all tracked source/notice files. Only supplement missing
        # private build inputs, never overwrite this branch with other source.
        assert target.is_file(),target
native=stage/'app/Madeira';origin=prepared/'app/Madeira'
libraries=('libwineserver.a','libntdll_unix.a','libwin32u_unix.a','libmadeira_rppairing.a','libdxmt_combined.a','libgnutls.a','libnettle.a','libhogweed.a','libgmp.a','libavformat.a','libavcodec.a','libswresample.a','libavutil.a')
for name in libraries:supplement(origin/name,native/name)
for name in ('nls','aarch64-windows','arm64ec-windows','i386-windows','x86_64-vcruntime','d3d12','licenses','legal','Steam64Compatibility'):
    supplement(origin/name,native/name)
supplement(origin/'prefix-template.tar.gz',native/'prefix-template.tar.gz')
supplement(prepared/'app/Frameworks/StikJIT.xcframework',stage/'app/Frameworks/StikJIT.xcframework')
# Optional Mono is copied only from its explicit build package, never an app
# prefix/account. Its inherited bundler modifies only the new output bundle.
mono=prepared/'build/wine-mono/wine-mono-11.0.0'
if mono.is_dir():supplement(mono,stage/'build/wine-mono/wine-mono-11.0.0')
swift=native/'MadeiraApp.swift';text=swift.read_text();assert text.count('\n@main\n')==1
swift.write_text(text.replace('\n@main\n','\n// Alternate entry exists only in this private Linux Lab build.\n'))
entry=native/'HybridLinuxMain.m';entry.write_bytes((lab/'app/main.m').read_bytes())
info=native/'Info.plist';metadata=plistlib.loads(info.read_bytes());metadata['CFBundleDisplayName']='iDeck Linux Lab';metadata['LinuxLabRootFSSHA256']=root_pin
cold_callback='ideck-linux-lab' if a.madeira_setup else None
if cold_callback:
    # A manually signed Lab may have another bundle ID. Its JIT callback must
    # still return to this Lab, never the installed working iDeck/Madeira app.
    metadata['CFBundleURLTypes']=[{'CFBundleURLName':'iDeck Linux Lab callback','CFBundleURLSchemes':[cold_callback]}]
info.write_bytes(plistlib.dumps(metadata))
# These are OWN guest compatibility-tool resources, never Valve/rootfs/auth data.
compat=native/'LabCompatibility';compat.mkdir()
resource_cmd=['xcrun','clang','--target=aarch64-linux-gnu','--ld-path='+str(ld_lld),'-nostdlib','-static','-ffreestanding','-fno-builtin','-fno-stack-protector','-O2','-Wall','-Wextra','-Werror',str(lab/'guest/compatibility.c'),str(lab/'guest/compat-start.S'),'-Wl,-e,_start','-o',str(compat/'ideck-madeira')]
subprocess.run(resource_cmd,check=True)
for name in ('compatibilitytool.vdf','toolmanifest.vdf'):shutil.copy2(lab/name,compat/name)
resource_hashes={x.name:hashof(x) for x in compat.iterdir()}
project=stage/'app/Madeira.xcodeproj/project.pbxproj';text=project.read_text()
# These are read-only compiler/archive inputs. No source/build command runs in
# the prepared FEX checkout; never change its contribution-restricted code.
text=text.replace('$(SRCROOT)/../FEX',str(deps/'FEX'))
text=text.replace('../../FEX/',str(deps/'FEX')+'/')
flags=['-I'+str(lab/'app'),
 '-DIDECK_LAB_STEAM_FRONTEND=1','-DIDECK_LAB_RETAINED_FRONTEND=1','-DIDECK_LAB_RFB_LIFETIME=1','-DIDECK_LAB_CASP_ORDER=1',
 '-DIDECK_LAB_COMPAT_TOOL=1','-DIDECK_LAB_GUEST_LIFETIME=1','-DIDECK_LAB_NATIVE_WORKERS=1','-DIDECK_LAB_NATIVE_LOG=1',
 '-DIDECK_LAB_LAZY_PAGES=1','-DIDECK_LAB_MADVISE_STATS=1']
if a.madeira_setup:flags+=['-DIDECK_LAB_MADEIRA_SETUP=1']
assert 'C0E100000000000000000001' not in text
text=text.replace('/* End PBXBuildFile section */','\t\tC0E100000000000000000001 /* HybridLinuxMain.m in Sources */ = {isa = PBXBuildFile; fileRef = C0E100000000000000000002; settings = {COMPILER_FLAGS = '+json.dumps(' '.join(flags))+'; }; };\n/* End PBXBuildFile section */')
text=text.replace('/* End PBXFileReference section */','\t\tC0E100000000000000000002 /* HybridLinuxMain.m */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.c.objc; path = '+json.dumps(str(entry))+'; sourceTree = "<absolute>"; };\n/* End PBXFileReference section */')
anchor='A3000002 /* Sources */ = {\n\t\t\tisa = PBXSourcesBuildPhase;\n\t\t\tbuildActionMask = 2147483647;\n\t\t\tfiles = ('
assert text.count(anchor)==1;text=text.replace(anchor,anchor+'\n\t\t\t\tC0E100000000000000000001 /* HybridLinuxMain.m in Sources */,')
cold_sources={}
if a.madeira_setup:
    for stem,kind,extension,build_id,ref_id in [
        ('LabStartupMode','sourcecode.c.c','.c','C0E100000000000000000007','C0E100000000000000000008'),
        ('LabMadeiraSetup','sourcecode.swift','.swift','C0E100000000000000000009','C0E10000000000000000000A'),
        ('LabMadeiraPrefix','sourcecode.swift','.swift','C0E10000000000000000000B','C0E10000000000000000000C')]:
        target=native/(stem+extension);target.write_bytes((lab/'app'/(stem+extension)).read_bytes())
        cold_sources['experiments/linux-steam/app/'+target.name]=hashof(target)
        text=text.replace('/* End PBXBuildFile section */','\t\t'+build_id+' = {isa = PBXBuildFile; fileRef = '+ref_id+'; };\n/* End PBXBuildFile section */')
        text=text.replace('/* End PBXFileReference section */','\t\t'+ref_id+' = {isa = PBXFileReference; lastKnownFileType = '+kind+'; path = '+json.dumps(str(target))+'; sourceTree = "<absolute>"; };\n/* End PBXFileReference section */')
        text=text.replace(anchor,anchor+'\n\t\t\t\t'+build_id+' /* cold setup source */,')
    # Plain C startup policy includes its own header, no Linux/Wine header flags.
    (native/'LabStartupMode.h').write_bytes((lab/'app/LabStartupMode.h').read_bytes())
    cold_sources['experiments/linux-steam/app/LabStartupMode.h']=hashof(native/'LabStartupMode.h')
    # Adapt only this Lab's known prefix binding at its two native entry roots.
    # Keep all production installer/PE/path checks intact, and ordinary source
    # untouched. Fail preparation if either exact source contract has changed.
    roots={
        'MadeiraDock.swift':'FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!.appendingPathComponent("wine")',
        'SteamUIExperiment.swift':'runtimePrefix(documents: FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0], arguments: ProcessInfo.processInfo.arguments, selectedRuntime: MadeiraConfig.get("steam-runtime"))',
    }
    for name,expression in roots.items():
        file=native/name;source=file.read_text();assert source.count(expression)==1,(name,'native prefix root changed')
        file.write_text(source.replace(expression,'LabMadeiraPrefix.canonical('+expression+')'))
        cold_sources['private-adapted/'+name]=hashof(file)
frontend=runtime/'libideck_linux_frontend.a'
extra='$(inherited) -Wl,-force_load,'+str(frontend)+' '+ ' '.join(str(runtime/n) for n in ('libish.a','libish_emu.a','libfakefs.a'))
extra+=' '+str(base/'ios-libarchive-v2/liblabrootfs.a')+' '+str(base/'ios-libarchive-v2/libarchive/libarchive.a')+' -framework MetalKit -framework ImageIO -lz'
for identifier,name in [('A8000003','Debug'),('A8000004','Release')]:
    anchor=identifier+' /* '+name+' */ = {\n\t\t\tisa = XCBuildConfiguration;\n\t\t\tbuildSettings = {'
    assert text.count(anchor)==1
    text=text.replace(anchor,anchor+'\n\t\t\t\tOTHER_LDFLAGS = '+json.dumps(extra)+';')
text=text.replace('/* End PBXBuildFile section */','\t\tC0E100000000000000000005 /* LabCompatibility in Resources */ = {isa = PBXBuildFile; fileRef = C0E100000000000000000006; };\n/* End PBXBuildFile section */')
text=text.replace('/* End PBXFileReference section */','\t\tC0E100000000000000000006 /* LabCompatibility */ = {isa = PBXFileReference; lastKnownFileType = folder; path = '+json.dumps(str(compat))+'; sourceTree = "<absolute>"; };\n/* End PBXFileReference section */')
resource_anchor='A3000003 /* Resources */ = {\n\t\t\tisa = PBXResourcesBuildPhase;\n\t\t\tbuildActionMask = 2147483647;\n\t\t\tfiles = ('
assert text.count(resource_anchor)==1
text=text.replace(resource_anchor,resource_anchor+'\n\t\t\t\tC0E100000000000000000005 /* LabCompatibility in Resources */,')
project.write_text(text)
cmd=['xcodebuild','-project',str(project.parent),'-scheme','Madeira','-configuration','Debug','-destination','generic/platform=iOS',
 '-derivedDataPath',str(out/'xcode'),'CODE_SIGNING_ALLOWED=NO','ENABLE_DEBUG_DYLIB=NO',
 'MADEIRA_BUNDLE_IDENTIFIER=com.kuschqin.ideck.linuxlab','CURRENT_PROJECT_VERSION='+str(a.build_number),
 'INFOPLIST_KEY_CFBundleDisplayName=iDeck Linux Lab','build']
record={'scope':'Private isolated FULL source app + Linux frontend build inputs; NOT runtime admission/device/game proof',
 'source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
 'dirty_experiment_source_inputs':copied,'prepared_payloads':payload,'linux_input_evidence_sha256':hashof(linux/'evidence.json'),
 'Linux_entry_source_sha256':hashof(lab/'app/main.m'),'private_project_sha256':hashof(project),
 'read_only_dependency_root':str(deps),'Wine_FEX_sources_modified':False,'provisioning_installation_or_auth_action':False,
 'compiled_payload_source_provenance_not_rebuilt_this_run':True,'compiled_rootfs_pin':root_pin,'cold_madeira_setup_enabled':a.madeira_setup,'cold_setup_callback_scheme':cold_callback,'cold_setup_source_hashes':cold_sources,'own_guest_resource_command':resource_cmd,'own_guest_resource_hashes':resource_hashes,'binary_distribution_allowed':False,'build_command':cmd}
(out/'prepare-evidence.json').write_text(json.dumps(record,indent=2)+'\n')
if a.build:
    env=dict(os.environ,LLVM_MINGW=str(a.llvm_mingw.resolve()))
    with (out/'xcode.log').open('xb') as log:result=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
    (out/'build-result.json').write_text(json.dumps({'exit_code':result.returncode,'signed':False,'installed':False})+'\n')
    if not result.returncode:
        product=out/'xcode/Build/Products/Debug-iphoneos/Madeira.app'
        verification=subprocess.check_output([os.sys.executable,str(lab/'tools/verify-hybrid-package.py'),str(product),str(out/'prepare-evidence.json')],text=True)
        (out/'package-validation.json').write_text(verification)
    raise SystemExit(result.returncode)
print('Prepared private combined project, no build/install/runtime action')
