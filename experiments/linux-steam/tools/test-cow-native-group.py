#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""HOST real memory-unit grouping/rollback controls; never invokes device."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for n in ('artifacts','output'):p.add_argument(n,type=Path)
a=p.parse_args();base=a.artifacts.resolve();out=a.output.resolve();repo=Path(__file__).resolve().parents[3];tools=Path(__file__).parent
assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(mode=0o700,parents=True)
src=repo/'vendor/LinuxRunner';host=base/'host'
subprocess.run([sys.executable,tools/'build-cow-native-group.py',src,host,host/'libish.a',src/'kernel/memory.c',out/'kernel','--sanitize','--host-inject'],check=True)
flags=['-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DISH_INTERNAL=1','-I'+str(src),'-I'+str(host),'-fsanitize=address,undefined','-fno-sanitize-recover=all','-Wall','-Wextra','-Werror']
rows=[];env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0')
for name,unit in [('granularity','cow-backing-control.c'),('boundary','cow-group-boundary-control.c')]:
 binary=out/name;subprocess.run(['xcrun','clang',*flags,'-DIDECK_COW_GROUPED=1',tools/unit,out/'kernel/libish.a','-L'+str(host),'-lish_emu','-lfakefs','-lsqlite3','-o',binary],check=True)
 for mode in (['measure'] if name=='granularity' else ['all','protection','shared','hole','different','offset','file','mmap-fail','data-fail','concurrent']):
  log=out/(name+'-'+mode+'.log')
  with log.open('x') as f:r=subprocess.run([binary,*([] if name=='granularity' else [mode])],stdout=f,stderr=subprocess.STDOUT,env=env,timeout=20)
  assert not r.returncode,(mode,log)
  rows.append({'case':name+'-'+mode,'exit':r.returncode,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
(out/'evidence.json').write_text(json.dumps({'scope':'HOST real anonymous CoW mapping/granularity and rollback; memory-unit sanitized, dependencies not. Not iOS/Steam/capacity/game proof','cases':rows,'archive_sha256':hashlib.sha256((out/'kernel/libish.a').read_bytes()).hexdigest()},indent=2)+'\n')
print('HOST 11 actual CoW grouping/rollback/concurrency controls pass')
