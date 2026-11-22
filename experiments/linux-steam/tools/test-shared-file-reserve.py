#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""HOST real Darwin reserve ownership/alias/failure controls; not device proof."""
import argparse,hashlib,json,subprocess,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args()
lab=Path(__file__).resolve().parents[1];out=a.output.resolve()
assert str(out).startswith('/Volumes/easystore/') and not out.exists()
out.mkdir(mode=0o700,parents=True)
for name in ('SharedFileReserve.c','SharedFileReserve.h'):shutil.copy2(lab/'app'/name,out/name)
shutil.copy2(lab/'tools/shared-file-reserve-control.c',out/'control.c')
cmd=['xcrun','clang','-std=c11','-D_DARWIN_C_SOURCE=1','-DIDECK_FILE_RESERVE_HOST_INJECTION=1','-fsanitize=address,undefined','-fno-sanitize-recover=all','-Wall','-Wextra','-Werror',str(out/'SharedFileReserve.c'),str(out/'control.c'),'-pthread','-o',str(out/'control')]
with (out/'compile.log').open('x') as f:subprocess.run(cmd,check=True,stdout=f,stderr=subprocess.STDOUT)
rows=[]
for mode in ('prepare-failure','basic','closed-fd','eligibility','capacity','wrong-release','suspend','suspend-late-release','concurrency','snapshot-busy','map-failure','reset-failure','drain-failure'):
    directory=out/mode;directory.mkdir(mode=0o700)
    with (directory/'test.log').open('x') as f:r=subprocess.run([out/'control',mode,directory],stdout=f,stderr=subprocess.STDOUT,timeout=30)
    rows.append({'mode':mode,'exit':r.returncode,'log_sha256':hashlib.sha256((directory/'test.log').read_bytes()).hexdigest()})
    assert not r.returncode,(mode,directory/'test.log')
(out/'evidence.json').write_text(json.dumps({'scope':'HOST real Darwin file/shared-alias mappings with own reserve; injected original ENOMEM and own failure controls. NOT reproduced system-wide iOS fragmentation, UI or game proof','command':cmd,'tests':rows,'concurrency_allocations':800,'source_sha256':{name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in ('SharedFileReserve.c','SharedFileReserve.h','control.c')}},indent=2)+'\n')
print('HOST13 sanitized real Darwin shared-reserve modes/800 concurrent allocations PASS; NOT device proof')
