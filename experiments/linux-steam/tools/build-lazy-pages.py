#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Opt-in copied LinuxRunner memory.c: co-materialize lazy private pages.

No vendor/base mutation, slab ownership, cap increase, JIT, COW or shared change.
Existing mapping refcounts own the one native mapping until its last page exits.
"""
import argparse,hashlib,json,shlex,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for name in ('source','build','archive','output'):p.add_argument(name,type=Path)
p.add_argument('--sanitize',action='store_true');a=p.parse_args()
src,build,archive,out=[getattr(a,n).resolve() for n in ('source','build','archive','output')]
pin='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
assert subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip()==pin
assert not subprocess.check_output(['git','-C',str(src),'status','--porcelain','--untracked-files=no'],text=True).strip()
assert not out.exists();out.mkdir(parents=True)
original=subprocess.check_output(['git','-C',str(src),'show',pin+':kernel/memory.c']);assert original==(src/'kernel/memory.c').read_bytes()
body=original.decode()
old='pt_map_nothing(mem, page, 1, res->flags & ~P_GROWSDOWN)'
assert body.count(old)==1
body=body.replace(old,'ideck_materialize_lazy_group(mem, page, res)')
anchor='static void reacquire_read_after_failed_jit_upgrade(wrlock_t *lock) {'
assert body.count(anchor)==1
helper='''/* Caller holds mem write lock and has revalidated this reservation.
 * Materialize only absent adjacent pages inside BOTH the same reservation and
 * one aligned native-page group. Never overwrite a populated PTE or cross a
 * protection boundary. In particular, PROT_NONE reservations stay untouched.
 * Shared mappings are not lazy in this pin. COW remains the original path.
 */
static int ideck_materialize_lazy_group(struct mem *mem, page_t page,
        const struct mem_reservation *res) {
    pages_t group = real_page_size / PAGE_SIZE;
    if (group == 0 || group > 16 || (group & (group - 1)) != 0)
        group = 1;
    page_t first = page, end = page + 1;
    page_t lower = page & ~(group - 1), upper = lower + group;
    if (lower < res->start) lower = res->start;
    page_t reservation_end = res->start + res->pages;
    if (upper > reservation_end) upper = reservation_end;
    while (first > lower && mem_pt(mem, first - 1) == NULL) first--;
    while (end < upper && mem_pt(mem, end) == NULL) end++;
    return pt_map_nothing(mem, first, end - first, res->flags & ~P_GROWSDOWN);
}
const char *ideck_lazy_pages_marker(void) {return "IDECK_LAZY_NATIVE_GROUP_V1";}

'''
body=body.replace(anchor,helper+anchor)
generated=out/'memory.c';generated.write_text(body)
entry=next(x for x in json.loads((build/'compile_commands.json').read_text()) if x['file'].endswith('/kernel/memory.c'))
cmd=shlex.split(entry['command']);obj=out/Path(cmd[cmd.index('-o')+1]).name
cmd[cmd.index(entry['file'])]=str(generated);cmd[cmd.index('-o')+1]=str(obj)
for key,value in [('-MF',out/'memory.d'),('-MQ',obj)]:
 if key in cmd:cmd[cmd.index(key)+1]=str(value)
if a.sanitize:cmd+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
subprocess.run(cmd,cwd=entry['directory'],check=True)
hashof=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
before=hashof(archive);target=out/'libish.a';shutil.copy2(archive,target)
subprocess.run(['xcrun','ar','r',str(target),str(obj)],check=True);assert before==hashof(archive)
(out/'build-evidence.json').write_text(json.dumps(dict(linuxrunner=pin,base_archive_sha256=before,base_unchanged=True,
 original_sha256=hashlib.sha256(original).hexdigest(),generated_sha256=hashof(generated),archive_sha256=hashof(target),
 sanitized_unit=a.sanitize,marker='IDECK_LAZY_NATIVE_GROUP_V1',scope='co-materialize absent adjacent pages in same reservation/native group only; no COW/cap/shared/allocator lifetime modification'),indent=2)+'\n')
print('Copied lazy-page grouping archive built; vendor/base unchanged')
