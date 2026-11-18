#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Measure real glibc active-thread mappings and a guest-only soft stack limit."""
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
elf=out/'pthread-cache-probe.elf';cmd=['xcrun','clang','--target=aarch64-linux-gnu','--ld-path='+str(b/'tool-bin/ld.lld'),'-nostdlib','-ffreestanding','-fno-builtin','-fno-stack-protector','-O2','-Wall','-Wextra','-Werror','-fPIE',str(lab/'guest/pthread-stack-peak-probe.c'),str(repo/'experiments/linux-steam/guest/xlib-glibc-start.S'),str(lib),'-Wl,-pie,-e,_start,-dynamic-linker,/lib/ld-linux-aarch64.so.1','-o',str(elf)]
with (out/'build.log').open('x') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
env={k:v for k,v in os.environ.items() if not k.startswith('ISH_')};env.update(ISH_JIT='0',TERM='dumb')
# Compile the SAME fixed policy bytes used by initial and retained frontend.
fixture=out/'policy.c';fixture.write_text('#include <stdio.h>\n#include "GuestSteamStackPolicy.h"\nint main(void){return fputs(IDECK_GUEST_STEAM_STACK_POLICY,stdout)<0;}\n')
policies={}
for gate in (0,1,2):
 exe=out/f'policy{gate}'
 compiled=subprocess.run(['xcrun','clang','-Wall','-Wextra','-Werror','-I'+str(lab/'app'),f'-DIDECK_LAB_PTHREAD_STACK_SOFT_LIMIT={gate}',str(fixture),'-o',str(exe)],capture_output=True)
 assert (compiled.returncode==0)==(gate!=2)
 if gate!=2:policies[gate]=subprocess.check_output([exe],text=True)
 else:assert b'explicit default-off guest stack policy' in compiled.stderr
assert policies[0]=='' and policies[1].count('ulimit -S -s 4096')==1
# Same full frontend command remains byte-identical at the default gate.
original=subprocess.check_output(['git','show','4eb7b86e788eb032b6be148decaf10982e2ed558:experiments/linux-steam/app/LinuxSteamSession.h'],cwd=repo)
(out/'OldLinuxSteamSession.h').write_bytes(original)
wire={}
for label,header,gate in [('old','OldLinuxSteamSession.h',0),('default','LinuxSteamSession.h',0),('enabled','LinuxSteamSession.h',1)]:
 c=out/(label+'-command.c');c.write_text('#include <stdio.h>\n#include "'+header+'"\nint main(void){const char a[]=IDECK_LINUX_STEAM_ARGS;return fwrite(a,1,sizeof a,stdout)!=sizeof a;}\n')
 exe=out/(label+'-command');subprocess.run(['xcrun','clang','-Wall','-Wextra','-Werror','-I'+str(lab/'app'),'-I'+str(out),f'-DIDECK_LAB_PTHREAD_STACK_SOFT_LIMIT={gate}',str(c),'-o',str(exe)],check=True)
 wire[label]=subprocess.check_output([exe]);(out/(label+'-command.bin')).write_bytes(wire[label])
assert wire['old']==wire['default']
assert wire['enabled'].replace(policies[1].encode(),b'',1)==wire['default']
assert wire['enabled'].index(b'x11vnc ')<wire['enabled'].index(policies[1].encode())<wire['enabled'].index(b'./steamrtarm64/steam')
rows=[]
for name,tunable in [('default',''),('disabled','GLIBC_TUNABLES=glibc.pthread.stack_cache_size=0'),('soft4m','GLIBC_TUNABLES=glibc.pthread.stack_cache_size=0')]:
 root=out/(name+'-root');subprocess.run(['cp','-cR',source,root],check=True,timeout=180)
 with (out/(name+'-install.log')).open('x') as f:r=subprocess.run([str(b/'host/ish'),'-f',str(root),'/bin/sh','-c','set -eu; umask 077; test ! -e /ideck-pthread-cache-probe; cat > /ideck-pthread-cache-probe; chmod 700 /ideck-pthread-cache-probe'],input=elf.read_bytes(),stdout=f,stderr=subprocess.STDOUT,env=env,timeout=60)
 assert not r.returncode,(name,'VFS install')
 script='set -eu; '+policies[int(name=='soft4m')]+tunable+' /lib/ld-linux-aarch64.so.1 --list-tunables > /pthread-cache-tunables.txt; '+tunable+' /ideck-pthread-cache-probe > /pthread-cache-results.txt'
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
assert rows[2]['values']['stack_soft_bytes']=='4194304' and rows[1]['values']['stack_soft_bytes']=='8388608'
assert rows[2]['values']['stack_hard_bytes']==rows[1]['values']['stack_hard_bytes']
for wave in range(4):
 assert rows[2]['values'][f'wave{wave}_thread_stack_bytes']=='4194304'
 first=int(rows[1]['values'][f'wave{wave}_active_vm_bytes'])-int(rows[1]['values']['baseline_vm_bytes'])
 second=int(rows[2]['values'][f'wave{wave}_active_vm_bytes'])-int(rows[2]['values']['baseline_vm_bytes'])
 assert first-second>=16*1024*1024
# Exercise policy failure under a deliberately smaller hard limit in this NEW
# disposable guest process only. set -e must prevent the following launch token.
policy_readback=(root/'data/tmp/ideck-steam-stack-policy.txt').read_text()
assert policy_readback=='soft_kib=4096\nhard_kib=unlimited\n'
negative='set -eu; ulimit -S -s 2048; ulimit -H -s 2048; '+policies[1]+'echo unexpected > /ideck-unexpected-launch'
with (out/'hardlimit-failure.log').open('x') as f:
 refused=subprocess.run([str(b/'host/ish'),'-f',str(root),'/bin/sh','-c',negative],stdout=f,stderr=subprocess.STDOUT,env=env,timeout=20)
assert refused.returncode!=0 and not (root/'data/ideck-unexpected-launch').exists(),'Must not launch after failed policy'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'evidence.json').write_text(json.dumps({'scope':'HOST real ARM64 glibc32 pthreads/default-vs-zero cache and standard guest-only4MiB soft-limit in isolated account-free VFS clones; actual VM maps and loader tunable. NOT Air/Steam/UI/game/capacity success','rows':rows,'source_sha256':sha((lab/'guest/pthread-stack-peak-probe.c')),'glibc_sha256':sha(lib),'guest_elf_sha256':sha(elf),'host_cli_sha256':sha(b/'host/ish'),'driver_sha256':sha(Path(__file__)),'production_policy_header_sha256':sha(lab/'app/GuestSteamStackPolicy.h'),'default_command_byte_identical':True,'enabled_command_only_fixed_policy':True,'invalid_gate_refused':True,'predecessor_command_revision':'4eb7b86e788eb032b6be148decaf10982e2ed558','actual_numeric_policy_readback':policy_readback,'policy_failure_blocks_launch':True,'failure_exit':refused.returncode},indent=2)+'\n')
print('HOST active-stack default/cache-off/soft4MiB controls complete; NOT Steam or device validation')
