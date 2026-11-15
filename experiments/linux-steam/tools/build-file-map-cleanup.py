#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Compile a separately opted-in file-backend ownership fix into a copied archive."""
import argparse,hashlib,json,shlex,shutil,subprocess,sys,importlib.util
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for n in ('source','build','archive','output'):p.add_argument(n,type=Path)
p.add_argument('--mmap-failure-probe',action='store_true',help='Lab-only once-per-lifetime native control mappings on a bounded shared-file ENOMEM; original request still fails')
a=p.parse_args();src,build,archive,out=[getattr(a,n).resolve() for n in ('source','build','archive','output')]
assert all(str(p).startswith('/Volumes/easystore/') for p in (build,archive,out)) and not out.exists()
subprocess.run([sys.executable,str(Path(__file__).with_name('file-map-cleanup.py')),src,out],check=True)
generated=out/'real.c'
if a.mmap_failure_probe:
    tool=Path(__file__).with_name('file-mmap-probe.py')
    spec=importlib.util.spec_from_file_location('file_mmap_probe',tool);probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)
    generated.write_text(probe.patched(generated.read_text()))
    shutil.copy2(Path(__file__).parents[1]/'app/FileMmapProbe.inc',out/'FileMmapProbe.inc')
with generated.open('a') as f:f.write('\nconst char *ideck_file_map_cleanup_marker(void){return "IDECK_FILE_MAP_FAILURE_RELEASE_V1";}\n')
entry=next(e for e in json.loads((build/'compile_commands.json').read_text()) if e['file'].endswith('/fs/real.c'))
cmd=shlex.split(entry['command']);obj=out/Path(cmd[cmd.index('-o')+1]).name
cmd[cmd.index(entry['file'])]=str(generated);cmd[cmd.index('-o')+1]=str(obj)
for key,value in [('-MF',out/'real.d'),('-MQ',obj)]:
 if key in cmd:cmd[cmd.index(key)+1]=str(value)
subprocess.run(cmd,cwd=entry['directory'],check=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=sha(archive);target=out/'libish.a';shutil.copy2(archive,target)
subprocess.run(['xcrun','ar','r',target,obj],check=True);assert sha(archive)==before
e=json.loads((out/'evidence.json').read_text());e.update(base_archive_sha256=before,base_archive_unchanged=True,file_mmap_failure_probe_enabled=a.mmap_failure_probe,
 generated_sha256=sha(generated),object_sha256=sha(obj),archive_sha256=sha(target),command=cmd)
if a.mmap_failure_probe:e['file_mmap_probe_source_sha256']=sha(out/'FileMmapProbe.inc')
(out/'evidence.json').write_text(json.dumps(e,indent=2)+'\n')
print('Copied file-mapping failed-transfer cleanup archive built; original failure cause/cap/Valve/FEX unchanged')
