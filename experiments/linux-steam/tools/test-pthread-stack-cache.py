#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Compare a real ARM64 glibc pthread stack cache in fresh account-free roots."""
import argparse,json,os,hashlib,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);
for n in ('artifacts','source_root','output'):p.add_argument(n,type=Path)
a=p.parse_args();repo=Path(__file__).resolve().parents[3];lab=repo/'experiments/linux-steam';b=a.artifacts.resolve();source=a.source_root.resolve();out=a.output.resolve();assert all(str(p).startswith('/Volumes/easystore/') for p in (b,source,out))
assert not out.exists() and (source/'meta.db').is_file()
for n in ['Steam/config/loginusers.vdf','Steam/userdata','root/.steam/config/loginusers.vdf']:assert not (source/'data'/n).exists(),'Preserve account-bearing root'
r=subprocess.run(['lsof','-t',str(source/'meta.db')],capture_output=True,text=True);assert r.returncode in (0,1) and not r.stderr.strip() and not r.stdout.strip(),'Preserve active/unverified source root'
out.mkdir(mode=0o700)
lib=source/'data/usr/lib/aarch64-linux-gnu/libc.so.6';assert lib.read_bytes()[:4]==b'\x7fELF'
elf=out/'pthread-cache-probe.elf';cmd=['xcrun','clang','--target=aarch64-linux-gnu','--ld-path='+str(b/'tool-bin/ld.lld'),'-nostdlib','-ffreestanding','-fno-builtin','-fno-stack-protector','-O2','-Wall','-Wextra','-Werror','-fPIE',str(lab/'guest/pthread-cache-probe.c'),str(repo/'experiments/linux-steam/guest/xlib-glibc-start.S'),str(lib),'-Wl,-pie,-e,_start,-dynamic-linker,/lib/ld-linux-aarch64.so.1','-o',str(elf)]
with (out/'build.log').open('x') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
env={k:v for k,v in os.environ.items() if not k.startswith('ISH_')};env.update(ISH_JIT='0',TERM='dumb')
rows=[]
for name,tunable in [('default',''),('disabled','GLIBC_TUNABLES=glibc.pthread.stack_cache_size=0')]:
 root=out/(name+'-root');subprocess.run(['cp','-cR',source,root],check=True,timeout=180)
 with (out/(name+'-install.log')).open('x') as f:r=subprocess.run([str(b/'host/ish'),'-f',str(root),'/bin/sh','-c','set -eu; umask 077; test ! -e /ideck-pthread-cache-probe; cat > /ideck-pthread-cache-probe; chmod 700 /ideck-pthread-cache-probe'],input=elf.read_bytes(),stdout=f,stderr=subprocess.STDOUT,env=env,timeout=60)
 assert not r.returncode,(name,'VFS install')
 script='set -eu; '+tunable+' /lib/ld-linux-aarch64.so.1 --list-tunables > /pthread-cache-tunables.txt; '+tunable+' /ideck-pthread-cache-probe > /pthread-cache-results.txt'
 start=time.monotonic()
 with (out/(name+'-run.log')).open('x') as f:r=subprocess.run([str(b/'host/ish'),'-f',str(root),'/bin/sh','-c',script],stdout=f,stderr=subprocess.STDOUT,env=env,timeout=120)
 assert not r.returncode,(name,'Probe failed',r.returncode)
 report=(root/'data/pthread-cache-results.txt').read_text();assert 'complete=PASS' in report,report
 (out/(name+'-results.txt')).write_text(report);values=dict(line.split('=',1) for line in report.splitlines() if '=' in line)
 tunables=(root/'data/pthread-cache-tunables.txt').read_text();line=next(x for x in tunables.splitlines() if x.startswith('glibc.pthread.stack_cache_size:'))
 row={'mode':name,'exit':r.returncode,'elapsed_s':time.monotonic()-start,'values':values,'actual_loader_tunable':line};rows.append(row);print(row,flush=True)
assert all(row['values']['glibc']=='2.41' for row in rows),'Requalify this version-specific control'
assert '0x2800000 ' in rows[0]['actual_loader_tunable'] and ': 0x0 ' in rows[1]['actual_loader_tunable']
for wave in range(4):
 assert rows[0]['values'][f'wave{wave}_thread_stack_bytes']==rows[1]['values'][f'wave{wave}_thread_stack_bytes']=='8388608'
 assert int(rows[0]['values'][f'wave{wave}_vm_bytes'])-int(rows[1]['values'][f'wave{wave}_vm_bytes'])>=16*1024*1024
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'evidence.json').write_text(json.dumps({'scope':'HOST real ARM64 glibc32 pthreads/default-vs-zero stack cache in isolated account-free VFS clones; actual VM maps and loader tunable. NOT Air/Steam/UI/game/capacity success','rows':rows,'source_sha256':sha(lab/'guest/pthread-cache-probe.c'),'glibc_sha256':sha(lib),'guest_elf_sha256':sha(elf),'host_cli_sha256':sha(b/'host/ish'),'driver_sha256':sha(Path(__file__))},indent=2)+'\n')
print('HOST default/disabled real glibc stack-cache controls complete')
