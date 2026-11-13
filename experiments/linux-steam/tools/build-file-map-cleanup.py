#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Compile a separately opted-in file-backend ownership fix into a copied archive."""
import argparse,hashlib,json,shlex,shutil,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for n in ('source','build','archive','output'):p.add_argument(n,type=Path)
a=p.parse_args();src,build,archive,out=[getattr(a,n).resolve() for n in ('source','build','archive','output')]
assert all(str(p).startswith('/Volumes/easystore/') for p in (build,archive,out)) and not out.exists()
subprocess.run([sys.executable,str(Path(__file__).with_name('file-map-cleanup.py')),src,out],check=True)
generated=out/'real.c'
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
e=json.loads((out/'evidence.json').read_text());e.update(base_archive_sha256=before,base_archive_unchanged=True,
 generated_sha256=sha(generated),object_sha256=sha(obj),archive_sha256=sha(target),command=cmd)
(out/'evidence.json').write_text(json.dumps(e,indent=2)+'\n')
print('Copied file-mapping failed-transfer cleanup archive built; original failure cause/cap/Valve/FEX unchanged')
