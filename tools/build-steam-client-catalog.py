#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Generate PUBLIC metadata only from the saved Valve manifest and verified inventory.
First run fetch-steam-ui-client.py against official HTTPS packages in a new private
staging directory. This tool never fetches executables, updates pins in Swift, or
copies binaries. Review the printed metadata hash before changing the Swift pin.
"""
import argparse, hashlib, importlib.util, json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--manifest',type=Path,required=True);p.add_argument('--inventory',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
spec=importlib.util.spec_from_file_location('fetch',Path(__file__).with_name('fetch-steam-ui-client.py'));fetch=importlib.util.module_from_spec(spec);spec.loader.exec_module(fetch)
raw=a.manifest.read_bytes();version,packages=fetch.parse_manifest(raw.decode(),'win32');inventory=json.loads(a.inventory.read_text())
if version!='1769731672' or hashlib.sha256(raw).hexdigest()!='4b8aa78d95dd7a1475c7849c3e783b136452d34be67342b53728799d697c4823':p.error('not the reviewed historical Valve manifest')
if inventory['version']!=version or inventory['manifest_sha256']!=hashlib.sha256(raw).hexdigest() or inventory['packages']!=packages:p.error('inventory does not match manifest')
files=inventory['files']
if len(files)!=6233 or sum(f['bytes'] for f in files.values())!=729535453:p.error('not a complete reviewed public client inventory')
result=dict(schema=1,version=version,manifestSHA256=inventory['manifest_sha256'],origin=fetch.CDN,expandedBytes=sum(v['bytes'] for v in files.values()),packages=[dict(name=k,file=v['file'],bytes=int(v['size']),sha256=v['sha2']) for k,v in packages.items()],files=files)
a.output.write_text(json.dumps(result,sort_keys=True,separators=(',',':'))+'\n')
print('Metadata SHA256:',hashlib.sha256(a.output.read_bytes()).hexdigest())
