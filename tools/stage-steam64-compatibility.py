#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Stage ONLY pinned open components/notices. Never stage a Steam/CEF client tree.

The release must accompany this folder with exact source/rebuild material for
Chromium/CEF, Crashpad and mini_chromium, plus the iDeck source commit.
This tool checks bytes, source provenance and notices; it does not certify a
fresh-device Steam boot or license compliance for unexamined dependencies.
"""
import argparse, hashlib, json, pathlib, shutil
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--elf-artifact',type=pathlib.Path,required=True)
p.add_argument('--crashpad-binaries',type=pathlib.Path,required=True)
p.add_argument('--crashpad-source',type=pathlib.Path,required=True)
p.add_argument('--output',type=pathlib.Path,required=True)
p.add_argument('--toolchain',type=pathlib.Path,required=True,help='Matching LLVM-MinGW toolchain runtime notices')
a=p.parse_args(); root=pathlib.Path(__file__).resolve().parents[1]
assert not a.output.exists(),'Refusing to overwrite a staged bundle'
pins={
 'chrome_elf.dll':(a.elf_artifact/'chrome_elf.dll',1666560,'673584661cd0044b186e40286b3d57a099b45002d3fc50f334ae1d3d14bc7621'),
 'crashpad_handler.exe':(a.crashpad_binaries/'crashpad_handler.exe',25614848,'76303a50b472a8a97c7d336564f00498ab5d34104d1f5c994056125528d8fd11'),
 'config_guard.exe':(a.crashpad_binaries/'config_guard.exe',91136,'0d7e0e45215c94da469d1c167aaa3533e2a9c563d4acc5f13b567860011a5640')}
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
for name,(source,size,digest) in pins.items():
 assert source.is_file() and source.stat().st_size==size and sha(source)==digest,name
 data=source.read_bytes(); pe=int.from_bytes(data[60:64],'little')
 assert data[:2]==b'MZ' and data[pe:pe+6]==b'PE\0\0\x64\x86',name
source_info=json.loads((a.elf_artifact/'source.json').read_text())
assert source_info['chromium_revision']=='2e81dea53f5ecdc1c057e4c70ecd66151987296a'
assert source_info['cef_revision']=='a5d51ba9db7ee74a523dc247bd09ec91ba4d7446'
assert source_info['cef_crash_patch_sha256']=='28c7eb14cb25305c392586888f271edde9ce56406d7282fd0e2ddd0a89d0ffdd'
notices={
 'CHROMIUM-LICENSE':a.elf_artifact/'notices/LICENSE',
 'CRASHPAD-LICENSE':a.crashpad_source/'LICENSE',
 'MINI_CHROMIUM-LICENSE':a.crashpad_source/'third_party/mini_chromium/mini_chromium/LICENSE',
 'ZLIB-LICENSE':a.crashpad_source/'third_party/zlib/zlib/LICENSE',
 'LLVM-MINGW-LICENSE':a.toolchain/'LICENSE.TXT',
 'IDeck-LICENSE':root/'COPYING', 'IDeck-EXCEPTION':root/'LICENSE-EXCEPTION.md'}
for n,path in notices.items():assert path.is_file() and path.stat().st_size,n
assert sha(a.crashpad_source/'ideck-cef-crashpad.patch')=='e1474ca60831144a5c096e8dcd3f8e0a36307b55ceb1ab63fe45883dcd396d85'
a.output.mkdir(parents=True);(a.output/'notices').mkdir()
for name,(source,_,_) in pins.items():shutil.copyfile(source,a.output/name)
for name,path in notices.items():shutil.copyfile(path,a.output/'notices'/name)
# Retain the artifact's complete notice tree, rather than guessing which upstream
# dependencies can be removed. No source/executable or private files in this tree.
shutil.copytree(a.elf_artifact/'notices',a.output/'notices/chromium')
shutil.copyfile(a.crashpad_source/'third_party/mini_chromium/mini_chromium/base/third_party/icu/LICENSE',a.output/'notices/ICU-LICENSE')
provenance={'schema':1,'steam_manifest_version':'1769025840','scope':'Source-built compatibility components only; Valve libcef/helper/client are downloaded separately.',
 'chromium':source_info,'crashpad_revision':'1174aa4fc3196f478b5b4b77fc970d1cb85cb7cf','mini_chromium_revision':'a6607b1fd76b740f31c2249fef2c0bec27ffbe52',
 'cef_crashpad_patch_sha256':'e1474ca60831144a5c096e8dcd3f8e0a36307b55ceb1ab63fe45883dcd396d85',
 'components':{n:{'bytes':size,'sha256':digest} for n,(_,size,digest) in pins.items()},
 'rebuild':['experiments/cef64/README.md','experiments/cef64/crashpad/README.md','experiments/cef64/crashpad/config_guard.c'],
 'release_source_required':True,'fresh_setup_device_validation':False}
(a.output/'PROVENANCE.json').write_text(json.dumps(provenance,indent=2,sort_keys=True)+'\n')
print('PASS pinned open components and complete notices staged; no Valve files')
