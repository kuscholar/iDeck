#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Measure pinned HOST CoW backing granularity; never changes runtime policy."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('artifacts',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
base=a.artifacts.resolve();out=a.output.resolve();repo=Path(__file__).resolve().parents[3]
src=repo/'vendor/LinuxRunner';host=base/'host';unit=Path(__file__).with_name('cow-backing-control.c')
assert subprocess.check_output(['git','-C',src,'rev-parse','HEAD'],text=True).strip()=='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
assert not subprocess.check_output(['git','-C',src,'status','--porcelain','--untracked-files=no'],text=True).strip()
assert str(out).startswith('/Volumes/easystore/') and not out.exists() and (host/'libish.a').is_file()
out.mkdir(mode=0o700);binary=out/'control'
cmd=['xcrun','clang','-DGUEST_ARM64=1','-DENGINE_ASBESTOS=1','-DISH_INTERNAL=1','-I'+str(src),'-I'+str(host),'-fsanitize=address,undefined','-Wall','-Wextra','-Werror',str(unit),str(host/'libish.a'),'-L'+str(host),'-lish_emu','-lfakefs','-lsqlite3','-o',str(binary)]
subprocess.run(cmd,check=True)
with (out/'control.log').open('x') as f:r=subprocess.run([binary],stdout=f,stderr=subprocess.STDOUT,timeout=20,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0'))
assert not r.returncode
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'evidence.json').write_text(json.dumps({'scope':'HOST pinned CoW granularity, harness sanitized only; rounded mapping capacity is NOT physical RSS, exact VM region count, Darwin limit or device root-cause proof','exit':r.returncode,'command':cmd,'source_sha256':sha(unit),'log_sha256':sha(out/'control.log'),'archive_sha256':sha(host/'libish.a')},indent=2)+'\n')
print((out/'control.log').read_text())
