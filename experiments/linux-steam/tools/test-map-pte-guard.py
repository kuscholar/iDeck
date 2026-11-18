#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""HOST real whole-kernel ordinary-map ENOMEM regression, no Air injection."""
import argparse,hashlib,json,os,re,shlex,shutil,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for n in ('artifacts','output'):p.add_argument(n,type=Path)
a=p.parse_args();out=a.output.resolve();base=a.artifacts.resolve();build=base/'host';repo=Path(__file__).resolve().parents[3];src=repo/'vendor/LinuxRunner';tools=Path(__file__).resolve().parent
assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(mode=0o700,parents=True)
archive=build/'libish.a';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
subprocess.run([sys.executable,tools/'build-map-pte-guard.py',src,build,archive,out/'guard','--host-inject'],check=True)
entry=next(e for e in json.loads((build/'compile_commands.json').read_text()) if e['file'].endswith('/kernel/memory.c'));cmd=shlex.split(entry['command']);obj=out/Path(cmd[cmd.index('-o')+1]).name;cmd[cmd.index('-o')+1]=str(obj)
for k,v in [('-MF',out/'baseline.d'),('-MQ',obj)]:
 if k in cmd:cmd[cmd.index(k)+1]=str(v)
cmd+=['-Dcalloc=ideck_test_calloc','-Dmalloc=ideck_test_malloc','-Dfree=ideck_test_free','-fsanitize=address,undefined','-fno-sanitize-recover=all']
subprocess.run(cmd,cwd=entry['directory'],check=True);baseline=out/'baseline.a';shutil.copy2(archive,baseline);subprocess.run(['xcrun','ar','r',baseline,obj],check=True)
# Original lacks ONLY the added numeric observer; no ordinary-map stubs.
stub=out/'baseline-counter.c';stub.write_text('#include <stdatomic.h>\n#include <stdint.h>\n_Atomic uint64_t ideck_map_pte_allocation_failures;\n')
flags=['-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DISH_INTERNAL=1','-I'+str(src),'-I'+str(build),'-fsanitize=address,undefined','-fno-sanitize-recover=all','-Wall','-Wextra','-Werror']
for name,lib in [('baseline',baseline),('guard',out/'guard/libish.a')]:
 subprocess.run(['xcrun','clang',*flags,tools/'map-pte-control.c',*([stub] if name=='baseline' else []),lib,build/'libish_emu.a',build/'libfakefs.a','-lsqlite3','-o',out/(name+'-control')],check=True)
env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0');rows=[]
with (out/'baseline.log').open('x') as f:r=subprocess.run([out/'baseline-control','baseline','fresh','3','0'],stdout=f,stderr=subprocess.STDOUT,env=env,timeout=20)
text=(out/'baseline.log').read_text();assert r.returncode!=0 and any(s in text for s in ['AddressSanitizer','runtime error:']) and ('mem_pt_new' in text or 'memory.c:25' in text),'Exact original PTE failure did not reproduce'
negative=r.returncode
for kind in ('fresh','replace','none'):
 def run(c,m):
  log=out/f'{kind}-calloc{c}-malloc{m}.log'
  with log.open('x') as f:r=subprocess.run([out/'guard-control','guard',kind,str(c),str(m)],stdout=f,stderr=subprocess.STDOUT,env=env,timeout=20)
  assert r.returncode==0,(kind,c,m,log)
  text=log.read_text();rows.append({'kind':kind,'fail_calloc':c,'fail_malloc':m,'exit':0,'log_sha256':sha(log)})
  return text
 text=run(0,0);n=int(re.search(r'calloc=(\d+)',text)[1]);assert n>0
 for i in range(1,n+1):run(i,0)
 run(0,1)
(out/'evidence.json').write_text(json.dumps({'scope':'HOST original full-kernel native PTE null failure reproduced; actual guarded memory.c ASanUBSan, every ordinary-map PTE allocation failure, input backing/old mappings/refs/anon accounting/empty metadata rollback. NOT Air/CEF/full engine initial-OOM/game/return proof','linuxrunner':'d1419782da2e299fe22f1ddb85c70ae3d1e276b1','original_negative_exit':negative,'negative_sha256':sha(out/'baseline.log'),'rows':rows,'sources_sha256':{n:sha(tools/n) for n in ['map_pte_patch.py','build-map-pte-guard.py','map-pte-control.c','test-map-pte-guard.py']}},indent=2)+'\n')
print('HOST real ordinary-map original failure and',len(rows),'rollback/success cases PASS')
