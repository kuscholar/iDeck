#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Read-only FINAL hybrid app boot resource checks, not runtime/device success."""
import argparse,hashlib,json,plistlib,re
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('app',type=Path);p.add_argument('prepared_evidence',type=Path);a=p.parse_args()
e=json.loads(a.prepared_evidence.read_text());pin=e['compiled_rootfs_pin'];assert re.fullmatch('[0-9a-f]{64}',pin)
info=plistlib.loads((a.app/'Info.plist').read_bytes());assert info.get('LinuxLabRootFSSHA256')==pin,'Final app is missing the actual compiled RootFS pin'
callback=e.get('cold_setup_callback_scheme')
if callback:
 schemes=[s for t in info.get('CFBundleURLTypes',[]) for s in t.get('CFBundleURLSchemes',[])]
 assert schemes==[callback],'Final cold Lab callback must not route to the working app'
expected=e['own_guest_resource_hashes'];assert set(expected)=={'ideck-madeira','compatibilitytool.vdf','toolmanifest.vdf'}
for name,sha in expected.items():
 f=a.app/'LabCompatibility'/name;assert f.is_file() and not f.is_symlink(),name
 assert hashlib.sha256(f.read_bytes()).hexdigest()==sha,'Final resource mismatch: '+name
elf=(a.app/'LabCompatibility/ideck-madeira').read_bytes();assert len(elf)>=64 and elf[:6]==b'\x7fELF\x02\x01' and int.from_bytes(elf[18:20],'little')==183
print(json.dumps({'scope':'Actual FINAL app pin/own resources/ARM64 ELF/callback metadata only, NOT runtime/device/Steam/game proof','rootfs_pin':pin,'resources_sha256':expected,'ARM64_ELF':True,'cold_callback_scheme':callback,'build':info.get('CFBundleVersion')}))
