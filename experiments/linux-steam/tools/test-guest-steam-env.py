#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""HOST exact constant guest environment contract at both feature gates."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args();out=a.output.resolve();repo=Path(__file__).resolve().parents[3];app=repo/'experiments/linux-steam/app'
assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(mode=0o700,parents=True)
c=out/'control.c';c.write_text('''#include "GuestSteamEnvironment.h"
#include <stdio.h>
int main(void){const unsigned char *s=(const unsigned char*)ideck_guest_steam_environment();for(unsigned i=0;i<1024;i++){printf("%02x",s[i]);if(i&&s[i]==0&&s[i-1]==0)return 0;}return 1;}
''')
expected=b'HOME=/root\0PATH=/usr/bin:/bin\0LANG=C\0STEAM_RUNTIME=1\0LD_LIBRARY_PATH=/Steam/steamrtarm64:/Steam/steamrtarm64/libs:/lib/aarch64-linux-gnu\0\0';rows=[]
for enabled in (0,1):
 binary=out/f'control{enabled}';cmd=['xcrun','clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all',f'-DIDECK_LAB_PTHREAD_STACK_CACHE_OFF={enabled}','-I'+str(app),c,'-o',binary]
 subprocess.run([str(x) for x in cmd],check=True)
 r=subprocess.run([binary],capture_output=True,check=True,env=dict(os.environ,GLIBC_TUNABLES='unrelated-host-value',HOME='/unrelated-host-home'),timeout=10);actual=bytes.fromhex(r.stdout.decode())
 desired=expected if not enabled else expected.replace(b'STEAM_RUNTIME=1\0',b'STEAM_RUNTIME=1\0GLIBC_TUNABLES=glibc.pthread.stack_cache_size=0\0')
 assert actual==desired
 rows.append({'enabled':enabled,'entry_count':len(actual[:-2].split(b'\0')),'bytes_sha256':hashlib.sha256(actual).hexdigest()})
cmd=['xcrun','clang','-DIDECK_LAB_PTHREAD_STACK_CACHE_OFF=2','-I'+str(app),'-c',c,'-o',out/'invalid.o'];r=subprocess.run([str(x) for x in cmd],capture_output=True);assert r.returncode and b'explicit default-off' in r.stderr
(out/'evidence.json').write_text(json.dumps({'scope':'HOST actual shared guest-env header bytes/default identity/one fixed entry/invalid gate refusal. NOT guest loader/Steam/on-Air effect proof','rows':rows,'invalid_gate_refused':True,'header_sha256':hashlib.sha256((app/'GuestSteamEnvironment.h').read_bytes()).hexdigest()},indent=2)+'\n')
print('HOST guest Steam environment: original default bytes / exact fixed cache key / invalid gate PASS')
