#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Build actual macOS ARM64 PartitionAlloc, then retarget our bundle for iOS.

Only three pinned BSD source files are edited in a disposable private copy.
All consumers use the same opt-in dynamic-pool definition. No CEF, Valve file,
runtime mask patch, fake mapping, signing, installation or upstream edit.
"""
import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import re
import shutil
import struct
import subprocess

REPO=Path(__file__).resolve().parents[2]
OWN=REPO/'experiments/mac-arm-steam'
spec=importlib.util.spec_from_file_location('pa_source',Path(__file__).with_name('build-partitionalloc-probe.py'))
pa=importlib.util.module_from_spec(spec);spec.loader.exec_module(pa)
DEFINE='IDECK_MAC_COMPACT_POOLS'


def once(text,old,new):
    if text.count(old)!=1:raise ValueError('Pinned source contract changed')
    return text.replace(old,new,1)


def patched(name,text):
    # Generated source edits retain each Chromium file's original BSD notice.
    # These modifications use the same BSD terms; no upstream submission.
    if name=='partition_alloc_config.h':
        text=once(text,'#if PA_BUILDFLAG(HAS_64_BIT_POINTERS) && BUILDFLAG(IS_IOS)',
            '#if defined(IDECK_MAC_COMPACT_POOLS) && (!BUILDFLAG(IS_MAC) || IDECK_MAC_COMPACT_POOLS != 1)\n#error Invalid compact Mac experiment configuration\n#endif\n'
            '#if PA_BUILDFLAG(HAS_64_BIT_POINTERS) && (BUILDFLAG(IS_IOS) || defined(IDECK_MAC_COMPACT_POOLS))')
    elif name=='partition_address_space.h':
        text=once(text,'#if BUILDFLAG(IS_IOS)',
            '#if BUILDFLAG(IS_IOS) || defined(IDECK_MAC_COMPACT_POOLS)')
        text=once(text,
            '  PA_ALWAYS_INLINE static size_t RegularPoolSize();\n  PA_ALWAYS_INLINE static size_t BRPPoolSize();',
            '#if defined(IDECK_MAC_COMPACT_POOLS)\n'
            '  PA_ALWAYS_INLINE static size_t RegularPoolSize() { return kRegularPoolSizeForIOSTestProcess; }\n'
            '  PA_ALWAYS_INLINE static size_t BRPPoolSize() { return kBRPPoolSizeForIOSTestProcess; }\n'
            '#else\n  PA_ALWAYS_INLINE static size_t RegularPoolSize();\n  PA_ALWAYS_INLINE static size_t BRPPoolSize();\n#endif')
    elif name=='partition_address_space.cc':
        text=once(text,'#if BUILDFLAG(IS_IOS)\n#include <mach-o/dyld.h>',
            '#if BUILDFLAG(IS_IOS) || defined(IDECK_MAC_COMPACT_POOLS)\n#include <mach-o/dyld.h>')
        text=once(text,'#if !BUILDFLAG(IS_IOS)\n#error Dynamic pool size is only supported on iOS.',
            '#if !BUILDFLAG(IS_IOS) && !defined(IDECK_MAC_COMPACT_POOLS)\n#error Dynamic pool size requires iOS or the explicit Mac source experiment.')
        text=once(text,'namespace {\nbool IsIOSTestProcess() {',
            '// Compact Mac selectors are defined inline in the shared header.\n'
            '#if !defined(IDECK_MAC_COMPACT_POOLS)\nnamespace {\nbool IsIOSTestProcess() {')
        text=once(text,'#endif  // PA_CONFIG(DYNAMICALLY_SELECT_POOL_SIZE)\n\nvoid PartitionAddressSpace::Init()',
            '#endif  // !defined(IDECK_MAC_COMPACT_POOLS)\n#endif  // PA_CONFIG(DYNAMICALLY_SELECT_POOL_SIZE)\n\nvoid PartitionAddressSpace::Init()')
    else:raise ValueError('Unexpected source patch target')
    return text


def text_hash(path):
    data=path.read_bytes()
    if len(data)<32 or struct.unpack_from('<II',data)!=(0xfeedfacf,0x100000c):raise ValueError('Expected thin ARM64')
    count,commands=struct.unpack_from('<II',data,16);offset=32;found=[]
    if commands>len(data)-32 or count>commands//8:raise ValueError('Invalid commands')
    for _ in range(count):
        cmd,size=struct.unpack_from('<II',data,offset)
        if size<8 or offset+size>32+commands:raise ValueError('Invalid command bounds')
        if cmd==0x19:
            if size<72:raise ValueError('Invalid segment')
            number=struct.unpack_from('<I',data,offset+64)[0]
            if size!=72+80*number:raise ValueError('Invalid section table')
            for i in range(number):
                name,segment,_,length,file_offset=struct.unpack_from('<16s16sQQI',data,offset+72+i*80)
                if name.rstrip(b'\0')==b'__text' and segment.rstrip(b'\0')==b'__TEXT':
                    if not length or file_offset+length>len(data):raise ValueError('Invalid text backing')
                    found.append(hashlib.sha256(data[file_offset:file_offset+length]).hexdigest())
        offset+=size
    if offset!=32+commands or len(found)!=1:raise ValueError('Expected one code section')
    return found[0]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--glued',action='store_true',help='Exercise adjacent core pools and combined mask')
    args=parser.parse_args();source=args.source.resolve();out=args.output.resolve();private=(REPO.parent/'.madeira-install').resolve()
    if not source.is_relative_to(private) or not out.is_relative_to(private) or out==private or out.exists() or out.is_relative_to(source) or source.is_relative_to(out):
        raise ValueError('Use new disjoint private output and pinned private source')
    pa.verify(source)
    shutil.copytree(source,out/'source')
    own_snapshot=out/'own-source';own_snapshot.mkdir()
    own_inputs={}
    for path in [Path(__file__).resolve(),OWN/'mac-compact-allocator.cc',OWN/'mac-compact-allocator.h',OWN/'mac-allocator-host.mm']:
        data=path.read_bytes();own_inputs[str(path.relative_to(REPO))]=pa.sha(data)
        (own_snapshot/path.name).write_bytes(data)
    copied=out/'source';patches={}
    for name in ['partition_alloc_config.h','partition_address_space.h','partition_address_space.cc']:
        path=copied/'partition_alloc'/name;before=path.read_bytes();after=patched(name,before.decode()).encode();path.write_bytes(after)
        patches[name]={'beforeSHA256':pa.sha(before),'afterSHA256':pa.sha(after)}
    gen=out/'gen';plan=(copied/'partition_alloc/BUILD.gn').read_text();all_flags={};seen=set()
    for name,body in re.findall(r'pa_buildflag_header\("(\w+)"\) \{(.*?)\n\}',plan,re.S):
        flags=re.findall(r'"([A-Z][A-Z_0-9]*)=',body);seen.update(flags)
        values={f:int(f in pa.ONES or (args.glued and f=='GLUE_CORE_POOLS')) for f in flags};all_flags.update(values)
        rel='partition_alloc/'+('partition_alloc_base/debug/' if name=='debugging_buildflags' else '')+name+'.h'
        path=gen/rel;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('#include "partition_alloc/buildflag.h"\n'+''.join(f'#define PA_BUILDFLAG_INTERNAL_{f}() ({v})\n' for f,v in values.items()))
    if not pa.ONES.issubset(seen):raise ValueError('Buildflag contract changed')
    if all_flags.get('GLUE_CORE_POOLS')!=int(args.glued):raise ValueError('Glued pool flag missing')
    def initial(target):
        body=plan.split('component("'+target+'") {',1)[1].split('sources = [',1)[1].split(']',1)[0]
        return re.findall(r'"([^"]+\.(?:cc|mm))"',body)
    sources=initial('allocator_core')+['page_allocator_internals_posix.cc','stack/asm/arm64/push_registers_asm.cc']
    sources+=initial('allocator_base')+['partition_alloc_base/'+s for s in [
        'debug/stack_trace_posix.cc','files/file_util_posix.cc','memory/page_size_posix.cc',
        'posix/safe_strerror.cc','process/process_handle_posix.cc','rand_util_posix.cc',
        'threading/platform_thread_posix.cc','time/time_conversion_posix.cc','debug/stack_trace_mac.cc',
        'time/time_apple.mm','apple/foundation_util.mm','apple/mach_logging.cc','mac/mac_util.mm','system/sys_info_mac.mm']]
    if len(sources)!=62 or len(set(sources))!=62:raise ValueError('Source-list contract changed')
    sdk=subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
    flags=['xcrun','clang++','-target','arm64-apple-macos14.0','-isysroot',sdk,'-std=c++20','-O1','-g',
        '-fno-exceptions','-fno-rtti','-fvisibility=hidden','-DHAVE_DLADDR','-DIS_PARTITION_ALLOC_IMPL=1',
        '-DIS_PARTITION_ALLOC_BASE_IMPL=1','-D'+DEFINE+'=1','-I'+str(gen),'-isystem',str(copied)]
    def compile_one(name):
        obj=out/(name.replace('/','_')+'.o')
        completed=subprocess.run(flags+['-c',str(copied/'partition_alloc'/name),'-o',str(obj)],capture_output=True,text=True)
        if completed.returncode:raise ValueError(name+'\n'+completed.stderr)
        return obj
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:objects=list(executor.map(compile_one,sources))
    own=own_snapshot/'mac-compact-allocator.cc';obj=out/'own.o'
    subprocess.run(flags+['-Wall','-Wextra','-Werror','-c',str(own),'-o',str(obj)],check=True)
    mac=out/'MacCompactAllocator.mac.bundle'
    subprocess.run(flags+['-bundle',*[str(x) for x in [*objects,obj]],'-framework','Foundation','-framework','CoreFoundation','-framework','Security','-o',str(mac)],check=True)
    # Real host execution happens in a separate process to give one allocator lifetime.
    host=out/'control.c';host.write_text('#include <dlfcn.h>\n#include <stdio.h>\n#include "mac-compact-allocator.h"\nint main(int c,char**v){if(c!=2)return 2;void*h=dlopen(v[1],RTLD_NOW|RTLD_LOCAL);if(!h){fputs("host load failed\\n",stderr);return 3;}int(*run)(struct IDeckMacAllocatorResult*,uint64_t)=dlsym(h,"IDeckRunMacAllocator");if(!run)return 4;struct IDeckMacAllocatorResult r={0};if(run(0,sizeof r)!=2 || run(&r,sizeof r-1)!=2)return 5;int result=run(&r,sizeof r);if(result || r.abi!=2 || r.compiled_mac!=1 || r.allocations!=398 || r.frees!=398 || r.failures || r.pool_bytes!=(256u<<20) || !r.disjoint || !r.cleaned || r.glued!='+str(int(args.glued))+')return 6;return run(&r,sizeof r)==3?0:7;}\n')
    subprocess.run(['xcrun','clang','-Wall','-Wextra','-Werror','-I'+str(own_snapshot),str(host),'-o',str(out/'control')],check=True)
    with (out/'host-run.log').open('w') as log:subprocess.run([str(out/'control'),str(mac)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=30)
    app=out/'MacAllocator.app';app.mkdir();bundle=app/'MacCompactAllocator.bundle';shutil.copyfile(mac,bundle)
    before=text_hash(bundle)
    sdk_version=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-version'],text=True).strip()
    temp=out/'retargeted.bundle'
    subprocess.run(['xcrun','vtool','-set-build-version','ios','17.0',sdk_version,'-replace','-output',str(temp),str(bundle)],check=True);temp.replace(bundle)
    deps=subprocess.check_output(['xcrun','otool','-L',str(bundle)],text=True)
    for original,framework,executable in re.findall(r'(/System/Library/Frameworks/(\w+)\.framework/Versions/[A-Z]/(\w+))',deps):
        if framework!=executable or framework not in ['Foundation','CoreFoundation','Security']:raise ValueError('Unexpected Mac framework dependency')
        subprocess.run(['xcrun','install_name_tool','-change',original,'/System/Library/Frameworks/'+framework+'.framework/'+executable,str(bundle)],check=True)
    if text_hash(bundle)!=before:raise ValueError('Retargeting changed instructions')
    ios_sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
    binary=app/'MacAllocatorHost'
    subprocess.run(['xcrun','clang++','-target','arm64-apple-ios17.0','-isysroot',ios_sdk,'-std=c++20','-fobjc-arc','-Wall','-Wextra','-Werror',str(own_snapshot/'mac-allocator-host.mm'),'-framework','UIKit','-framework','Foundation','-o',str(binary)],check=True)
    build=21 if args.glued else 20
    info={'CFBundleIdentifier':'com.kuschqin.ideck.maclab.macprobe','CFBundleName':'iDeck Mac Allocator','CFBundleDisplayName':'iDeck Mac Allocator','CFBundleExecutable':binary.name,'CFBundlePackageType':'APPL','CFBundleVersion':str(build),'CFBundleShortVersionString':'0.0.'+str(build),'IDeckMacAllocatorGlued':args.glued,'MinimumOSVersion':'17.0','UIDeviceFamily':[1,2],'UILaunchScreen':{},'UIRequiresFullScreen':True,'UIApplicationSceneManifest':{'UIApplicationSupportsMultipleScenes':False,'UISceneConfigurations':{'UIWindowSceneSessionRoleApplication':[{'UISceneConfigurationName':'Mac allocator','UISceneDelegateClassName':'IDeckMacAllocatorScene'}]}},'UISupportedInterfaceOrientations':['UIInterfaceOrientationPortrait','UIInterfaceOrientationLandscapeLeft','UIInterfaceOrientationLandscapeRight']}
    (app/'Info.plist').write_bytes(plistlib.dumps(info))
    for name in ['LICENSE','AUTHORS']:shutil.copyfile(source/name,app/('Chromium-'+name+'.txt'))
    for name,digest in own_inputs.items():
        if pa.sha((REPO/name).read_bytes())!=digest:raise ValueError('Own source changed during build')
    receipt={'state':'UNSIGNED, HOST PASS ONLY','sourceTag':pa.TAG,'subtree':pa.TREE,'sourceReceiptSHA256':pa.RECEIPT,'sourceEdits':patches,'allCompileDefinition':DEFINE+'=1','sourceUnits':sources,'buildFlags':all_flags,'moduleCompiledTarget':'arm64-apple-macos14.0','retargetedTextUnchanged':True,'moduleTextSHA256':before,'moduleSHA256':pa.sha(bundle.read_bytes()),'hostSHA256':pa.sha(binary.read_bytes()),'hostTest':'398 alloc/free,4workers,256MiB pools, checks enabled, zero failures','CEFIntegrated':False,'newEntitlements':False,'sourceFingerprints':own_inputs}
    (out/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print('Unsigned Mac-compiled allocator host:',app)


if __name__=='__main__':main()
