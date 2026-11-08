#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Track four pinned native worker providers in a NEW copied archive.

This does not stop threads, restore signals, free global resources or authorize
Wine. Apple iOS retains native-handler forwarding, despite lacking posix_spawn.
"""
import argparse,hashlib,json,re,shlex,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('source',type=Path);p.add_argument('build',type=Path)
p.add_argument('archive',type=Path);p.add_argument('output',type=Path)
p.add_argument('--sanitize',action='store_true')
p.add_argument('--fail-worker-starts',action='store_true',help='HOST ONLY negative control: return EAGAIN, never an iOS build')
a=p.parse_args();src,build,archive,out=map(lambda x:x.resolve(),[a.source,a.build,a.archive,a.output])
pin='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
assert subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip()==pin
assert not subprocess.check_output(['git','-C',str(src),'status','--porcelain','--untracked-files=no'],text=True).strip()
assert not out.exists();out.mkdir(parents=True)
entries=json.loads((build/'compile_commands.json').read_text());lab=Path(__file__).resolve().parents[1]
hashof=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
for name in ['NativeWorkers.c','NativeWorkers.h']:shutil.copy2(lab/'app'/name,out/name)
units=[('util/timer.c','timer_thread','TIMER','timer'),('kernel/guest_profile.c','sampler','PROFILE','profile'),
       ('fs/tty-real.c','real_tty_read_thread','TTY','tty'),('kernel/native_offload.c','pipe_forward_thread','FORWARD','forward')]
objects=[];evidence={}
def compile_copy(relative,generated,object_name):
 entry=next(x for x in entries if x['file'].endswith('/'+relative))
 cmd=shlex.split(entry['command'])
 is_ios=any('iphoneos' in x.lower() or '-apple-ios' in x.lower() for x in cmd)
 if a.fail_worker_starts:assert not is_ios,'Host failure injection may not target iOS'
 cmd[cmd.index(entry['file'])]=str(generated);obj=out/object_name;cmd[cmd.index('-o')+1]=str(obj)
 for key,value in [('-MF',out/(object_name+'.d')),('-MQ',obj)]:
  if key in cmd:cmd[cmd.index(key)+1]=str(value)
 if a.sanitize:cmd+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
 if a.fail_worker_starts and generated.name=='NativeWorkers.c':cmd+=['-DIDECK_HOST_WORKER_CREATE_EAGAIN=1']
 subprocess.run(cmd,cwd=entry['directory'],check=True);return obj
for relative,name,kind,callback in units:
 original=subprocess.check_output(['git','-C',str(src),'show',pin+':'+relative]);assert (src/relative).read_bytes()==original
 body=original.decode();pattern=r'static void \*'+name+r'\(void \*([A-Za-z_][A-Za-z_0-9]*)\) \{';matches=list(re.finditer(pattern,body));assert len(matches)==1
 wrapper=f'''static void *ideck_original_{name}(void *);
static void *{name}(void *argument) {{
    void *result;
    pthread_cleanup_push(ideck_native_worker_retire_{callback}, NULL);
    result=ideck_original_{name}(argument);
    pthread_cleanup_pop(1);
    return result;
}}
'''
 m=matches[0];replacement=wrapper+m.group(0).replace(name,'ideck_original_'+name)
 body=body[:m.start()]+replacement+body[m.end():]
 calls=list(re.finditer(r'pthread_create\([^;\n]*\b'+name+r'\s*,',body));assert len(calls)==1
 m=calls[0];body=body[:m.start()]+m.group(0).replace('pthread_create(','ideck_native_worker_start(IDECK_WORKER_'+kind+',',1)+body[m.end():]
 body='#include "NativeWorkers.h"\n'+body
 generated=out/relative.replace('/','_');generated.write_text(body)
 entry=next(x for x in entries if x['file'].endswith('/'+relative));cmd=shlex.split(entry['command']);object_name=Path(cmd[cmd.index('-o')+1]).name
 objects.append(compile_copy(relative,generated,object_name));evidence[relative]={'original_sha256':hashlib.sha256(original).hexdigest(),'generated_sha256':hashof(generated),'object':object_name}
objects.append(compile_copy('util/timer.c',out/'NativeWorkers.c','ideck_NativeWorkers.c.o'))
basehash=hashof(archive);target=out/'libish.a';shutil.copy2(archive,target)
subprocess.run(['xcrun','ar','r',str(target),*[str(x) for x in objects]],check=True)
assert hashof(archive)==basehash
(out/'build-evidence.json').write_text(json.dumps(dict(linuxrunner=pin,base_archive_sha256=basehash,base_archive_unchanged=True,
 archive_sha256=hashof(target),units=evidence,counter_sha256=hashof(out/'NativeWorkers.c'),header_sha256=hashof(out/'NativeWorkers.h'),
 sanitized_units=a.sanitize,host_start_failure_injected=a.fail_worker_starts,marker='IDECK_NATIVE_WORKERS_V1'),indent=2)+'\n')
print('Copied native-worker archive built; vendor/base unchanged')
