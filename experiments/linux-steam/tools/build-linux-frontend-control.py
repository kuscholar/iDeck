#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""PRIVATE Linux-only link control using the SAME qualified hybrid runtime.

One discriminator for full-app initializers/linkage; NOT a replacement for the
Madeira architecture or proof of a game handoff. No rootfs/account/game copy,
signing, installation, library rebuild, FEX/vendor or ordinary-project edit.
"""
import argparse,hashlib,json,plistlib,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for n in ('linux_runtime','artifacts','template_app','output'):p.add_argument(n,type=Path)
p.add_argument('--build-number',type=int,required=True)
a=p.parse_args();linux,base,template,out=[getattr(a,n).resolve() for n in ('linux_runtime','artifacts','template_app','output')]
assert all(str(x).startswith('/Volumes/easystore/') for x in (linux,base,template,out)) and not out.exists()
assert 1<=a.build_number<=999999
repo=Path(__file__).resolve().parents[3];lab=repo/'experiments/linux-steam';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
e=json.loads((linux/'evidence.json').read_text());runtime=linux/'runtime'
for name,digest in e['archives_sha256'].items():assert sha(runtime/name)==digest,name
root_pins={x.split('=',1)[1].strip('"') for command in e['commands'] for x in command if x.startswith('-DIDECK_LAB_ROOTFS_SHA256=')}
assert len(root_pins)==1
info=plistlib.load(open(template/'Info.plist','rb'));assert info['LinuxLabRootFSSHA256']==next(iter(root_pins))
assert info['CFBundleDisplayName']=='iDeck Linux Lab'
assert info['UIApplicationSceneManifest']['UISceneConfigurations']['UIWindowSceneSessionRoleApplication'][0]['UISceneDelegateClassName']=='LinuxLabSceneDelegate'
out.mkdir(mode=0o700);app=out/'Madeira.app';app.mkdir()
info['CFBundleVersion']=str(a.build_number);info['CFBundleExecutable']='Madeira';info['CFBundleIdentifier']='com.kuschqin.ideck.linuxlab'
with (app/'Info.plist').open('wb') as f:plistlib.dump(info,f)
resources=['Assets.car','LabCompatibility','PlugIns',*[x.name for x in template.glob('AppIcon*.png')]]
for name in resources:
 source=template/name;target=app/name
 if source.is_dir():shutil.copytree(source,target,symlinks=True)
 else:shutil.copy2(source,target)
main=out/'main.m';shutil.copy2(lab/'app/main.m',main)
sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
flags=['-target','arm64-apple-ios17.0','-isysroot',sdk,'-fobjc-arc','-fblocks','-O0','-g','-I'+str(lab/'app'),
 '-DIDECK_LAB_MADEIRA_SETUP=0','-DIDECK_LAB_STEAM_FRONTEND=1','-DIDECK_LAB_RETAINED_FRONTEND=1',
 '-DIDECK_LAB_RFB_LIFETIME=1','-DIDECK_LAB_CASP_ORDER=1','-DIDECK_LAB_COMPAT_TOOL=1',
 '-DIDECK_LAB_GUEST_LIFETIME=1','-DIDECK_LAB_NATIVE_WORKERS=1','-DIDECK_LAB_NATIVE_LOG=1']
archives=[runtime/name for name in ('libish.a','libish_emu.a','libfakefs.a')]
frontend=runtime/'libideck_linux_frontend.a';rootfs=[base/'ios-libarchive-v2/liblabrootfs.a',base/'ios-libarchive-v2/libarchive/libarchive.a']
cmd=['xcrun','clang',*flags,main,'-Wl,-force_load,'+str(frontend),*archives,*rootfs,'-lsqlite3','-lz',
 '-framework','Foundation','-framework','UIKit','-framework','Metal','-framework','MetalKit','-framework','ImageIO','-framework','CoreGraphics',
 '-Wl,-dead_strip','-Wl,-rpath,@executable_path/Frameworks','-o',app/'Madeira']
with (out/'link.log').open('x') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
record={'scope':'Private Linux-only link CONTROL, same kernel/frontend/resources; NOT combined Madeira/game execution or device success',
 'source_parent':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
 'main_source_sha256':sha(main),'runtime_receipt_sha256':sha(linux/'evidence.json'),'runtime_archives_sha256':e['archives_sha256'],
 'rootfs_pin':next(iter(root_pins)),'cold_Madeira_setup_enabled':False,'Windows_runtime_linked':False,'build':a.build_number,
 'link_command':[str(x) for x in cmd],'link_exit':r.returncode,'signed':False,'installed':False}
if not r.returncode:
 symbols=subprocess.check_output(['xcrun','nm',app/'Madeira'],text=True)
 assert '_ideck_retained_frontend_run' in symbols and '_ideck_linux_current' in symbols
 assert '_madeira_early_va_claim' not in symbols and '_madeira_cef64_hold_state' not in symbols
 record['macho_sha256']=sha(app/'Madeira');record['binary_bytes']=(app/'Madeira').stat().st_size
 record['actual_symbol_gates_pass']=True
assert all(sha(runtime/name)==digest for name,digest in e['archives_sha256'].items())
(out/'evidence.json').write_text(json.dumps(record,indent=2)+'\n')
raise SystemExit(r.returncode)
