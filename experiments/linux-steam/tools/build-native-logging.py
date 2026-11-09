#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Opt-in bounded app-private sink for pinned kernel log.c; no vendor mutation."""
import argparse,hashlib,json,shlex,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ('source','build','archive','output'):p.add_argument(name,type=Path)
p.add_argument('--sanitize',action='store_true');a=p.parse_args()
src,build,archive,out=[getattr(a,n).resolve() for n in ('source','build','archive','output')]
pin='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
assert subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip()==pin
assert not subprocess.check_output(['git','-C',str(src),'status','--porcelain','--untracked-files=no'],text=True).strip()
assert not out.exists();out.mkdir(parents=True)
original=subprocess.check_output(['git','-C',str(src),'show',pin+':kernel/log.c']);assert original==(src/'kernel/log.c').read_bytes()
old='''static void log_line(const char *line) {
    struct iovec output[2] = {{(void *) line, strlen(line)}, {"\\n", 1}};
    writev(666, output, 2);
}'''
body=original.decode();assert body.count(old)==1
body=body.replace(old,'''static void log_line(const char *line) {
    ideck_native_log_line(line);
}''');body='#include "NativeKernelLog.h"\n'+body
body+='\nconst char *ideck_native_log_bridge_marker(void){return "IDECK_NATIVE_LOG_BRIDGE_V1";}\n'
generated=out/'log.c';generated.write_text(body);lab=Path(__file__).resolve().parents[1];shutil.copy2(lab/'app/NativeKernelLog.h',out/'NativeKernelLog.h')
entry=next(x for x in json.loads((build/'compile_commands.json').read_text()) if x['file'].endswith('/kernel/log.c'));cmd=shlex.split(entry['command'])
assert '-DLOG_HANDLER_DPRINTF=1' in cmd
obj=out/Path(cmd[cmd.index('-o')+1]).name;cmd[cmd.index(entry['file'])]=str(generated);cmd[cmd.index('-o')+1]=str(obj)
for key,value in [('-MF',out/'log.d'),('-MQ',obj)]:
 if key in cmd:cmd[cmd.index(key)+1]=str(value)
if a.sanitize:cmd+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
subprocess.run(cmd,cwd=entry['directory'],check=True)
hashof=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
before=hashof(archive);target=out/'libish.a';shutil.copy2(archive,target);subprocess.run(['xcrun','ar','r',str(target),str(obj)],check=True);assert before==hashof(archive)
(out/'build-evidence.json').write_text(json.dumps(dict(linuxrunner=pin,base_archive_sha256=before,base_unchanged=True,
 original_sha256=hashlib.sha256(original).hexdigest(),generated_sha256=hashof(generated),archive_sha256=hashof(target),
 sanitized_unit=a.sanitize,marker='IDECK_NATIVE_LOG_BRIDGE_V1'),indent=2)+'\n')
print('Copied native log bridge built; vendor/base unchanged')
