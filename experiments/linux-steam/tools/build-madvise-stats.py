#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Copied pinned mmap.c: observation by default, explicit discard experiment.

Without either discard option the original syscall policy remains unchanged.
"""
import argparse,hashlib,json,shlex,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ('source','build','archive','output'):p.add_argument(name,type=Path)
p.add_argument('--sanitize',action='store_true')
p.add_argument('--host-private-discard',action='store_true',help='HOST ONLY exclusive whole-backing replacement experiment, not the iOS app')
p.add_argument('--experimental-private-discard',action='store_true',help='Explicit experimental exclusive whole-backing replacement; never a default build')
p.add_argument('--host-fail-second',action='store_true',help='HOST ONLY fail second replacement allocation before any commit')
a=p.parse_args()
assert not a.host_fail_second or a.host_private_discard
assert not (a.host_private_discard and a.experimental_private_discard)
private_discard=a.host_private_discard or a.experimental_private_discard
src,build,archive,out=[getattr(a,n).resolve() for n in ('source','build','archive','output')]
pin='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
assert subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip()==pin
assert not subprocess.check_output(['git','-C',str(src),'status','--porcelain','--untracked-files=no'],text=True).strip()
assert not out.exists();out.mkdir(parents=True)
original=subprocess.check_output(['git','-C',str(src),'show',pin+':kernel/mmap.c']);assert original==(src/'kernel/mmap.c').read_bytes()
signature='dword_t sys_madvise(addr_t addr, dword_t len, dword_t advice) {'
body=original.decode();assert body.count(signature)==1
body=body.replace(signature,'static dword_t ideck_original_madvise(addr_t addr, dword_t len, dword_t advice) {')
body='#include <stdatomic.h>\n#include "MadviseStats.h"\n'+body
body+='''
static _Atomic uint64_t ideck_advice_calls,ideck_advice_dontneed,ideck_advice_dontneed_bytes;
static _Atomic uint64_t ideck_advice_free,ideck_advice_free_bytes;
dword_t sys_madvise(addr_t addr, dword_t len, dword_t advice) {
    atomic_fetch_add_explicit(&ideck_advice_calls,1,memory_order_relaxed);
    if(advice==4) {
        atomic_fetch_add_explicit(&ideck_advice_dontneed,1,memory_order_relaxed);
        atomic_fetch_add_explicit(&ideck_advice_dontneed_bytes,len,memory_order_relaxed);
    } else if(advice==8) {
        atomic_fetch_add_explicit(&ideck_advice_free,1,memory_order_relaxed);
        atomic_fetch_add_explicit(&ideck_advice_free_bytes,len,memory_order_relaxed);
    }
    return ideck_original_madvise(addr,len,advice);
}
void ideck_madvise_stats_read(struct ideck_madvise_stats *out) {
    if(!out)return;
    *out=(struct ideck_madvise_stats){
        atomic_load_explicit(&ideck_advice_calls,memory_order_relaxed),
        atomic_load_explicit(&ideck_advice_dontneed,memory_order_relaxed),
        atomic_load_explicit(&ideck_advice_dontneed_bytes,memory_order_relaxed),
        atomic_load_explicit(&ideck_advice_free,memory_order_relaxed),
        atomic_load_explicit(&ideck_advice_free_bytes,memory_order_relaxed)};
}
const char *ideck_madvise_stats_marker(void){return "IDECK_MADVISE_STATS_V1";}
'''
generated=out/'mmap.c';generated.write_text(body);lab=Path(__file__).resolve().parents[1];shutil.copy2(lab/'app/MadviseStats.h',out/'MadviseStats.h')
if private_discard:
    shutil.copy2(lab/'app/PrivateDiscard.inc',out/'PrivateDiscard.inc')
    body=body.replace('static _Atomic uint64_t ideck_advice_calls,','#include "PrivateDiscard.inc"\nstatic _Atomic uint64_t ideck_advice_calls,',1)
    body=body.replace('    return ideck_original_madvise(addr,len,advice);','    if(advice==4 && ideck_try_private_discard(current->mem,addr,len))return 0;\n    return ideck_original_madvise(addr,len,advice);',1)
    generated.write_text(body)
entry=next(x for x in json.loads((build/'compile_commands.json').read_text()) if x['file'].endswith('/kernel/mmap.c'));cmd=shlex.split(entry['command'])
if a.host_private_discard:
    assert not any('iphoneos' in x.lower() or '-apple-ios' in x.lower() for x in cmd),'Host-only experiment may not target iOS'
if a.host_fail_second:cmd+=['-DIDECK_DISCARD_HOST_FAIL_SECOND=1']
obj=out/Path(cmd[cmd.index('-o')+1]).name;cmd[cmd.index(entry['file'])]=str(generated);cmd[cmd.index('-o')+1]=str(obj)
for key,value in [('-MF',out/'mmap.d'),('-MQ',obj)]:
 if key in cmd:cmd[cmd.index(key)+1]=str(value)
if a.sanitize:cmd+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
subprocess.run(cmd,cwd=entry['directory'],check=True)
hashof=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
before=hashof(archive);target=out/'libish.a';shutil.copy2(archive,target);subprocess.run(['xcrun','ar','r',str(target),str(obj)],check=True);assert before==hashof(archive)
(out/'build-evidence.json').write_text(json.dumps(dict(linuxrunner=pin,base_archive_sha256=before,base_unchanged=True,
 original_sha256=hashlib.sha256(original).hexdigest(),generated_sha256=hashof(generated),archive_sha256=hashof(target),sanitized_unit=a.sanitize,
 marker='IDECK_MADVISE_STATS_V1',host_private_discard=a.host_private_discard,experimental_private_discard=a.experimental_private_discard,host_fail_second=a.host_fail_second,
 private_discard_sha256=hashof(out/'PrivateDiscard.inc') if private_discard else None,
 scope='Experimental exclusive whole-backing replacement; unsupported/partial/aliased mappings use original syscall; host-only unless explicitly experimental' if private_discard else 'numeric request totals only; original syscall return/semantics preserved; not physical reclamation or attribution'),indent=2)+'\n')
print('Copied private-discard experiment built; vendor/base unchanged' if private_discard else 'Copied madvise observation archive built; vendor/base/policy unchanged')
