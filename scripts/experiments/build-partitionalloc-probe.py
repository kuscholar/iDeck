#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Build an unsigned standalone Chromium126 iOS allocator probe, not Steam/CEF.

Uses unmodified pinned BSD Chromium sources. No GN installation, malloc shim,
runtime patch, signing, device action or entitlement changes. --fetch downloads
only the ~3MB allocator subtree and two build headers, with pinned hash checks.
"""
import argparse, concurrent.futures, hashlib, json, pathlib, plistlib, re
import subprocess, urllib.request

REPO = pathlib.Path(__file__).resolve().parents[2]
TAG = '126.0.6478.183'
TREE = '3e6d40abe3803b5f785a0adbd1030740cf1e8071'
RECEIPT = '53d7a70a8f494e90f9206395bde038ac8db79ba147611cc2f572f8d2ce0b7471'
HEADERS = {
    'build/build_config.h': '29cd44f8f573426ff11ab1f73fdd2af6ad45aebd4afab6f2aea9971239635543',
    'build/buildflag.h': '40538acaa9b39d0f68e895503752bde340f8ea1cdb67a87bfaee865dba54c5cd',
}
LICENSE_SHA = '368cca1106be99d39ecd32a38d8305585d802a475effb66380b91ffc9bcf709b'
# Deliberately explicit standalone configuration, NOT a recreation of Valve's
# CEF GN args. BRP, its slow checks, ordinary and expensive DCHECKs remain on.
# Optional malloc replacement, thread cache, StarScan/MTE/pkeys are not tested.
ONES = set('HAS_64_BIT_POINTERS USE_PARTITION_ALLOC ENABLE_BACKUP_REF_PTR_SUPPORT '
           'ENABLE_BACKUP_REF_PTR_SLOW_CHECKS ENABLE_GWP_ASAN_SUPPORT '
           'STACK_SCAN_SUPPORTED PA_DCHECK_IS_ON PA_EXPENSIVE_DCHECKS_ARE_ON '
           'PA_CAN_UNWIND_WITH_FRAME_POINTERS'.split())

def sha(data): return hashlib.sha256(data).hexdigest()
def download(url): return urllib.request.urlopen(url, timeout=30).read()

def fetch(root):
    base = f'https://raw.githubusercontent.com/chromium/chromium/{TAG}/'
    tree = json.loads(download(f'https://api.github.com/repos/chromium/chromium/git/trees/{TREE}?recursive=1'))
    if tree.get('sha') != TREE or tree.get('truncated'): raise ValueError('Unexpected source tree')
    files = [x for x in tree['tree'] if x['type'] == 'blob']
    if len(files) != 362 or sum(x['size'] for x in files) > 4*1024*1024: raise ValueError('Unexpected source size')
    def one(x):
        rel = pathlib.PurePosixPath(x['path'])
        if rel.is_absolute() or '..' in rel.parts: raise ValueError('Unsafe source path')
        path = root / rel
        if path.is_symlink() or not path.resolve().is_relative_to(root): raise ValueError('Unsafe existing source path')
        data = path.read_bytes() if path.exists() else download(base+'base/allocator/partition_allocator/src/'+str(rel))
        git_blob = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if git_blob != x['sha']: raise ValueError('Source blob mismatch: '+str(rel))
        path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        return {'path':str(rel), 'gitBlob':git_blob, 'sha256':sha(data)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex: entries = list(ex.map(one, files))
    receipt = (json.dumps({'tag':TAG, 'subtree':TREE, 'files':entries}, indent=2)+'\n').encode()
    if sha(receipt) != RECEIPT: raise ValueError('Pinned source receipt mismatch')
    (root/'source-receipt.json').write_bytes(receipt)
    for name in [*HEADERS, 'LICENSE', 'AUTHORS']:
        dest = root/name
        if dest.is_symlink() or not dest.resolve().is_relative_to(root): raise ValueError('Unsafe dependency path')
        data = download(base+name)
        if name in HEADERS and sha(data) != HEADERS[name]: raise ValueError('Build header mismatch')
        dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(data)

def verify(root):
    root = root.resolve()
    receipt = (root/'source-receipt.json').read_bytes()
    if sha(receipt) != RECEIPT: raise ValueError('Wrong source receipt')
    entries = json.loads(receipt)['files']
    for entry in entries:
        path = root/entry['path']
        if path.is_symlink() or not path.resolve().is_relative_to(root): raise ValueError('Unsafe source')
        if sha(path.read_bytes()) != entry['sha256']: raise ValueError('Modified Chromium source: '+entry['path'])
    for name, expected in HEADERS.items():
        if (root/name).is_symlink() or not (root/name).resolve().is_relative_to(root): raise ValueError('Unsafe build header')
        if sha((root/name).read_bytes()) != expected: raise ValueError('Modified build header')
    if sha((root/'LICENSE').read_bytes()) != LICENSE_SHA: raise ValueError('Modified Chromium license')

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=pathlib.Path, required=True)
    p.add_argument('--output', type=pathlib.Path, required=True, help='New private output directory')
    p.add_argument('--fetch', action='store_true')
    a = p.parse_args(); root = a.source.resolve(); output = a.output.resolve()
    private = (REPO.parent/'.madeira-install').resolve()
    if not root.is_relative_to(private) or not output.is_relative_to(private) or output==private:
        raise ValueError('Source/build must remain in private .madeira-install subdirectories')
    if output.exists() or output.is_relative_to(root) or root.is_relative_to(output): raise ValueError('Use new disjoint output')
    root.mkdir(parents=True, exist_ok=True)
    if a.fetch: fetch(root)
    verify(root)
    output.mkdir()
    gen = output/'gen'; plan = (root/'partition_alloc/BUILD.gn').read_text()
    # Reproduce this fixed version's generated headers without a global GN install.
    seen = set(); all_flags = {}
    for name, body in re.findall(r'pa_buildflag_header\("(\w+)"\) \{(.*?)\n\}', plan, re.S):
        flags = re.findall(r'"([A-Z][A-Z_0-9]*)=', body); seen.update(flags)
        values = {f:int(f in ONES) for f in flags}; all_flags.update(values)
        rel = 'partition_alloc/'+('partition_alloc_base/debug/' if name=='debugging_buildflags' else '')+name+'.h'
        dest = gen/rel; dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text('#include "partition_alloc/buildflag.h"\n'+''.join(f'#define PA_BUILDFLAG_INTERNAL_{f}() ({v})\n' for f,v in values.items()))
    if not ONES.issubset(seen): raise ValueError('Buildflag contract changed')
    def initial(target):
        body = plan.split('component("'+target+'") {',1)[1].split('sources = [',1)[1].split(']',1)[0]
        return re.findall(r'"([^"]+\.(?:cc|mm))"',body)
    sources = initial('allocator_core')+['page_allocator_internals_posix.cc','stack/asm/arm64/push_registers_asm.cc']
    sources += initial('allocator_base')+['partition_alloc_base/'+s for s in [
        'debug/stack_trace_posix.cc','files/file_util_posix.cc','memory/page_size_posix.cc',
        'posix/safe_strerror.cc','process/process_handle_posix.cc','rand_util_posix.cc',
        'threading/platform_thread_posix.cc','time/time_conversion_posix.cc','debug/stack_trace_mac.cc',
        'time/time_apple.mm','apple/foundation_util.mm','apple/mach_logging.cc','ios/ios_util.mm','system/sys_info_ios.mm']]
    if len(sources)!=62 or len(set(sources))!=62: raise ValueError('Source-list contract changed')
    sdk = subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
    flags = ['xcrun','clang++','-target','arm64-apple-ios17.0','-isysroot',sdk,'-std=c++20','-O1','-g',
             '-fno-exceptions','-fno-rtti','-DHAVE_DLADDR','-DIS_PARTITION_ALLOC_IMPL=1','-DIS_PARTITION_ALLOC_BASE_IMPL=1',
             '-I'+str(gen),'-isystem',str(root)]
    def compile_one(source):
        dest = output/(source.replace('/','_')+'.o')
        result = subprocess.run(flags+['-c',str(root/'partition_alloc'/source),'-o',str(dest)],capture_output=True,text=True)
        if result.returncode: raise ValueError(source+'\n'+result.stderr)
        return dest
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex: objects = list(ex.map(compile_one,sources))
    probe = REPO/'experiments/mac-arm-steam/partitionalloc-probe.mm'
    own_object = output/'probe.o'
    subprocess.run(flags+['-fobjc-arc','-Wall','-Wextra','-Werror','-c',str(probe),'-o',str(own_object)],check=True)
    app = output/'PartitionAlloc.app'; app.mkdir()
    binary = app/'PartitionAllocRunner'  # Upstream iOS test selector suffix.
    subprocess.run(flags+[str(x) for x in [*objects,own_object]]+['-framework','UIKit','-framework','Foundation',
                   '-framework','CoreFoundation','-o',str(binary)],check=True)
    plist = {'CFBundleIdentifier':'com.kuschqin.ideck.maclab.macprobe','CFBundleName':'iDeck PA Lab',
             'CFBundleDisplayName':'iDeck PA Lab','CFBundleExecutable':binary.name,'CFBundlePackageType':'APPL',
             'CFBundleVersion':'14','CFBundleShortVersionString':'0.0.14','MinimumOSVersion':'17.0',
             'UIDeviceFamily':[1,2],'UILaunchScreen':{},'UIRequiresFullScreen':True,
             'UISupportedInterfaceOrientations':['UIInterfaceOrientationPortrait','UIInterfaceOrientationLandscapeLeft','UIInterfaceOrientationLandscapeRight']}
    (app/'Info.plist').write_bytes(plistlib.dumps(plist)); (app/'Chromium-LICENSE.txt').write_bytes((root/'LICENSE').read_bytes())
    (app/'Chromium-AUTHORS.txt').write_bytes((root/'AUTHORS').read_bytes())
    (output/'build-receipt.json').write_text(json.dumps({'state':'UNSIGNED','sourceTag':TAG,'subtree':TREE,
        'sourceReceiptSHA256':RECEIPT,'flags':all_flags,'sources':sources,'probeSHA256':sha(probe.read_bytes()),
        'scriptSHA256':sha(pathlib.Path(__file__).read_bytes()),'binarySHA256':sha(binary.read_bytes()),
        'CEFIntegrated':False,'entitlementChanges':False},indent=2)+'\n')
    print('UNSIGNED standalone probe:',app)

if __name__=='__main__': main()
