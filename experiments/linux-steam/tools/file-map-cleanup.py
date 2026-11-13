#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Generate an opt-in private realfs copy; never change the pinned vendor tree.

pt_map does not take a native mapping on error (the IPC/anonymous callers already
release their own). Retain that contract in all three realfs file-map branches.
This fixes a failure-path leak, not the cause of the original allocation failure.
"""
import argparse,hashlib,json,subprocess,re
from pathlib import Path

PIN='d1419782da2e299fe22f1ddb85c70ae3d1e276b1'
OLD='return pt_map(mem, start, pages, memory, correction, prot);'
NEW="""int mapping_error = pt_map(mem, start, pages, memory, correction, prot);
if (mapping_error < 0) {
    /* Ownership was NOT transferred. Never touch existing guest PTEs. */
    int saved = errno;
    munmap(memory, map_size);
    errno = saved;
}
return mapping_error;"""

def patched(body):
    assert body.count(OLD)==3,'Pinned realfs transfer contract changed'
    def replace(match):
        indent=match.group(1)
        return '\n'.join(indent+line for line in NEW.splitlines())
    return re.sub(r'^([ \t]*)'+re.escape(OLD),replace,body,flags=re.M)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    src=a.source.resolve();out=a.output.resolve()
    assert str(out).startswith('/Volumes/easystore/') and not out.exists()
    assert subprocess.check_output(['git','-C',src,'rev-parse','HEAD'],text=True).strip()==PIN
    original=subprocess.check_output(['git','-C',src,'show',PIN+':fs/real.c'])
    assert original==(src/'fs/real.c').read_bytes()
    body=patched(original.decode());out.mkdir(mode=0o700,parents=True)
    (out/'real.c').write_text(body)
    (out/'evidence.json').write_text(json.dumps({'linuxrunner':PIN,
        'source_sha256':hashlib.sha256(original).hexdigest(),
        'generated_sha256':hashlib.sha256(body.encode()).hexdigest(),
        'scope':'Private opt-in file mapping failure cleanup only; not root ENOMEM/game/device proof'},indent=2)+'\n')

if __name__=='__main__':main()
