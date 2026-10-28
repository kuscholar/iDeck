#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Real compiler failure injection: never replace final shims with partial builds.
Uses synthetic generated sources only. No Valve files, profiles or device calls.
Pass a checkout of the pinned MIT reference; it is read through git-show.
"""
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile

REPO=Path(__file__).resolve().parents[2]
reference=Path(sys.argv[1]).resolve()
for failing in ['libSystem','AppKit']:
    with tempfile.TemporaryDirectory(prefix='ideck-compile-failure-') as folder:
        root=Path(folder).resolve();app=root/'Steam-iOS.app'
        (app/'Frameworks').mkdir(parents=True);(root/'shims').mkdir()
        original=plistlib.dumps({'CFBundleIdentifier':'com.kuschqin.ideck.maclab.macprobe','SHIMMacRoot':'Mac'})
        (app/'Info.plist').write_bytes(original)
        previous={}
        for name in ['libSystem','AppKit','CoreGraphics']:
            path=app/'Frameworks'/('libShim_'+name+'.dylib')
            previous[path]=('previous synthetic '+name).encode();path.write_bytes(previous[path])
            (root/'shims'/('Shim_'+name+'.m')).write_text('#error deliberate '+failing+' failure\n' if name==failing else '#import <Foundation/Foundation.h>\n')
        receipt=root/'ideck-shim-build.json';receipt.write_text('previous success must be invalidated')
        result=subprocess.run([sys.executable,str(REPO/'scripts/experiments/build-mac-steam-overrides.py'),'--reference',str(reference),'--converted',str(root)],capture_output=True,text=True)
        assert result.returncode!=0, 'Intended compiler failure unexpectedly succeeded'
        assert 'deliberate '+failing+' failure' in result.stderr, result.stderr[-1800:]
        if failing=='AppKit':
            assert 'Compiled pending libShim_libSystem.dylib' in result.stdout, result.stdout
        for path,value in previous.items():assert path.read_bytes()==value, str(path)+' was overwritten'
        assert (app/'Info.plist').read_bytes()==original
        assert not receipt.exists(), 'Stale success receipt survived failed build'
        assert not list(root.glob('.ideck-steam-overrides-*')), 'Pending compile files leaked'
        print('PASS '+failing+' failure: final binaries/Info preserved, old receipt invalidated, pending output cleaned')

# Optional full-success fixture: public-converter-generated shim sources only,
# not the client app or its proprietary libraries. Never edits these inputs.
if len(sys.argv)>2:
    import hashlib,json,shutil
    generated=Path(sys.argv[2]).resolve()
    with tempfile.TemporaryDirectory(prefix='ideck-compile-success-') as folder:
        root=Path(folder).resolve();app=root/'Steam-iOS.app'
        (app/'Frameworks').mkdir(parents=True);(root/'shims').mkdir()
        (app/'Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier':'com.kuschqin.ideck.maclab.macprobe','SHIMMacRoot':'Mac'}))
        for name in ['libSystem','AppKit','CoreGraphics']:
            filename='Shim_'+name+'.m';shutil.copyfile(generated/filename,root/'shims'/filename)
        result=subprocess.run([sys.executable,str(REPO/'scripts/experiments/build-mac-steam-overrides.py'),'--reference',str(reference),'--converted',str(root)],capture_output=True,text=True)
        assert result.returncode==0,result.stderr[-2400:]
        receipt=json.loads((root/'ideck-shim-build.json').read_text())
        assert receipt['state']=='unsigned' and len(receipt['outputSHA256'])==3
        for name,expected in receipt['outputSHA256'].items():
            data=(app/'Frameworks'/name).read_bytes()
            assert data[:4]==b'\xcf\xfa\xed\xfe'
            assert hashlib.sha256(data).hexdigest()==expected
        assert plistlib.loads((app/'Info.plist').read_bytes())['IDeckCaseView'] is True
        assert not list(root.glob('.ideck-steam-overrides-*'))
        print('PASS complete compile: all three Mach-O outputs and unsigned receipt hashes verified; no signing/install')
