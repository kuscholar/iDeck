#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""HOST real memory-unit grouping/rollback controls; never invokes device."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for n in ('artifacts','output'):p.add_argument(n,type=Path)
p.add_argument('--native-pages-per-group',type=int,choices=(1,2),default=1)
p.add_argument('--backing-broker',action='store_true')
a=p.parse_args();base=a.artifacts.resolve();out=a.output.resolve();repo=Path(__file__).resolve().parents[3];tools=Path(__file__).parent
assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(mode=0o700,parents=True)
src=repo/'vendor/LinuxRunner';host=base/'host'
subprocess.run([sys.executable,tools/'build-cow-native-group.py',src,host,host/'libish.a',src/'kernel/memory.c',out/'kernel','--sanitize','--host-inject','--native-pages-per-group',str(a.native_pages_per_group),*(['--backing-broker'] if a.backing_broker else [])],check=True)
flags=['-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DISH_INTERNAL=1','-I'+str(src),'-I'+str(host),'-I'+str(tools.parent/'app'),'-fsanitize=address,undefined','-fno-sanitize-recover=all','-Wall','-Wextra','-Werror']
if a.backing_broker:flags+=['-DIDECK_LAB_COW_BROKER=1']
rows=[];env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0')
for name,unit in [('granularity','cow-backing-control.c'),('boundary','cow-group-boundary-control.c')]:
 binary=out/name;subprocess.run(['xcrun','clang',*flags,'-DIDECK_COW_GROUPED=1','-DIDECK_COW_NATIVE_PAGES='+str(a.native_pages_per_group),tools/unit,out/'kernel/libish.a','-L'+str(host),'-lish_emu','-lfakefs','-lsqlite3','-o',binary],check=True)
 for mode in (['dense','sparse'] if name=='granularity' else ['all','protection','shared','hole','different','offset','file','mmap-fail','data-fail','concurrent']):
  log=out/(name+'-'+mode+'.log')
  with log.open('x') as f:r=subprocess.run([binary,mode],stdout=f,stderr=subprocess.STDOUT,env=env,timeout=20)
  assert not r.returncode,(mode,log)
  rows.append({'case':name+'-'+mode,'exit':r.returncode,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
(out/'evidence.json').write_text(json.dumps({'scope':'HOST real anonymous CoW mapping/granularity and rollback; memory-unit sanitized, dependencies not. Not iOS/Steam/capacity/game proof','backing_broker':a.backing_broker,'native_pages_per_group':a.native_pages_per_group,'cases':rows,'archive_sha256':hashlib.sha256((out/'kernel/libish.a').read_bytes()).hexdigest()},indent=2)+'\n')
print('HOST 12 actual CoW grouping/rollback/concurrency controls pass')
