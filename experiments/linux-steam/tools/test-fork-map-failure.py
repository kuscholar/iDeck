#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Real HOST kernel allocation-failure regression, no failure injection on Air."""
import argparse,hashlib,json,os,shlex,shutil,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for n in ('artifacts','archive','output'):p.add_argument(n,type=Path)
a=p.parse_args();repo=Path(__file__).resolve().parents[3];src=repo/'vendor/LinuxRunner';tools=Path(__file__).parent
build=a.artifacts.resolve()/'host';archive=a.archive.resolve();out=a.output.resolve()
assert str(out).startswith('/Volumes/easystore/') and not out.exists() and archive.is_file();out.mkdir(mode=0o700)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
subprocess.run([sys.executable,tools/'build-fork-map-failure.py',src,build,archive,out/'fixed','--sanitize','--host-inject'],check=True)
flags=['-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DISH_INTERNAL=1','-I'+str(src),'-I'+str(build),'-fsanitize=address,undefined','-fno-sanitize-recover=all','-Wall','-Wextra','-Werror']
def link(lib,binary):
 subprocess.run(['xcrun','clang',*flags,tools/'fork-map-failure-control.c',lib,'-L'+str(build),'-lish_emu','-lfakefs','-lsqlite3','-o',binary],check=True)
# Compile the unchanged pinned memory unit with identical HOST injection only.
entry=next(e for e in json.loads((build/'compile_commands.json').read_text()) if e['file'].endswith('/kernel/memory.c'))
cmd=shlex.split(entry['command']);obj=out/Path(cmd[cmd.index('-o')+1]).name
cmd[cmd.index('-o')+1]=str(obj)
for k,v in [('-MF',out/'baseline.d'),('-MQ',obj)]:
 if k in cmd:cmd[cmd.index(k)+1]=str(v)
cmd+=['-Dcalloc=ideck_test_calloc','-Dmalloc=ideck_test_malloc','-fsanitize=address,undefined','-fno-sanitize-recover=all']
subprocess.run(cmd,cwd=entry['directory'],check=True)
baseline=out/'baseline.a';shutil.copy2(archive,baseline);subprocess.run(['xcrun','ar','r',baseline,obj],check=True)
link(baseline,out/'baseline-control');link(out/'fixed/libish.a',out/'fixed-control')
env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:abort_on_error=1')
with (out/'baseline.log').open('x') as f:r=subprocess.run([out/'baseline-control','copy','4','0'],stdout=f,stderr=subprocess.STDOUT,env=env,timeout=15)
assert r.returncode!=0,'Baseline did not reproduce allocation fault'
assert any(s in (out/'baseline.log').read_text() for s in ['runtime error:','AddressSanitizer:']),r.returncode
assert any(s in (out/'baseline.log').read_text() for s in ['mem_pt_new','pt_copy_on_write','memory.c:722:']), 'Wrong baseline failure layer'
baseline_exit=r.returncode
rows=[]
cases=[('copy',0,0)]+[(mode,n,0) for mode in ('copy','clone') for n in range(1,11)]+[(mode,0,n) for mode in ('copy','clone') for n in (1,2)]
for i,case in enumerate(cases):
 log=out/f'fixed-{i}.log'
 with log.open('x') as f:r=subprocess.run([out/'fixed-control',*[str(x) for x in case]],stdout=f,stderr=subprocess.STDOUT,env=env,timeout=15)
 assert r.returncode==0,(case,log)
 rows.append({'case':case,'exit':r.returncode,'log_sha256':sha(log)})
(out/'evidence.json').write_text(json.dumps({'scope':'HOST exact memory/mm_copy/clone on pinned kernel; baseline fault reproduced; changed3units ASan/UBSan; no real-device pressure/capacity/game proof','baseline_exit':baseline_exit,'baseline_log_sha256':sha(out/'baseline.log'),'cases':rows,'archive_sha256':sha(out/'fixed/libish.a')},indent=2)+'\n')
print('HOST baseline null fault reproduced; fixed25 allocation/copy/clone controls PASS')
