#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Rebuild only experimental shims in a disposable converted Steam COPY.
No download, device operation, signing, authentication or main-project edits.
Reference source is read from its pinned Git revision, never edited in place.
Re-sign the rebuilt dylibs and enclosing app before any device installation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import subprocess
import tempfile

PIN = 'c2562a333d4de4c08da4ceb4a4f1485bddb84e04'
REPO = Path(__file__).resolve().parents[2]
OWN = REPO / 'experiments/mac-arm-steam'


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Unexpected reference contract; inspect pinned source before patching')
    return text.replace(old, new)


def remove_generated_function(text, symbol):
    # Only the known zero-argument NULL placeholder may be removed. Never replace
    # an existing real implementation or edit the proprietary client's code.
    pattern = r'(__attribute__\(\(visibility\("default"\)\)\) void \*shim_f(\d+)\(void\) __asm__\("_' + re.escape(symbol) + r'"\);)\nvoid \*shim_f\2\(void\) \{[^\n]*return 0; \}'
    text, count = re.subn(pattern, '// iDeck override: ' + symbol, text)
    if count != 1:
        raise ValueError('Missing or changed generated placeholder: ' + symbol)
    return text


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--converted', type=Path, required=True, help='Converter output holding shims/ and Steam-iOS.app/')
    a = p.parse_args()
    reference, converted = a.reference.resolve(), a.converted.resolve()
    if converted.is_relative_to(REPO):
        raise ValueError('Converted proprietary inputs must remain outside the repository')
    revision = subprocess.check_output(['git', '-C', str(reference), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != PIN:
        raise ValueError('Unexpected reference revision')
    app = converted / 'Steam-iOS.app'
    info = plistlib.loads((app / 'Info.plist').read_bytes())
    if info.get('CFBundleIdentifier') != 'com.kuschqin.ideck.maclab.macprobe' or info.get('SHIMMacRoot') != 'Mac':
        raise ValueError('Only the isolated, converted native Steam experiment is supported')
    receipt = converted / 'ideck-shim-build.json'
    # A failed attempt must not leave a previous success receipt eligible for
    # deployment. Existing app binaries remain intact on any compiler failure.
    receipt.unlink(missing_ok=True)
    sdk = subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip()
    def original(path):
        return subprocess.check_output(['git','-C',str(reference),'show',PIN+':'+path], text=True)
    with tempfile.TemporaryDirectory(prefix='.ideck-steam-overrides-', dir=converted) as tmp:
        tmp = Path(tmp)
        sources = {}
        staged = []
        inputs = {str(Path(__file__).resolve().relative_to(REPO)): hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        for header in sorted(OWN.glob('*.h')):
            inputs[str(header.relative_to(REPO))] = hashlib.sha256(header.read_bytes()).hexdigest()
        names = subprocess.check_output(['git','-C',str(reference),'ls-tree','--name-only',PIN,'shim/overrides/'], text=True).splitlines()
        for path in names:
            name = Path(path).name
            if name.endswith('.m') and name.startswith(('libSystem', 'CoreGraphics', 'AppKit')):
                text = original(path)
                if name == 'libSystem.m':
                    text = replace_once(text, '    const char *f = FixCase(p, buf, size);',
                        '    extern const char *IDeckCasePath(const char *, char *, size_t);\n    const char *f = IDeckCasePath(p, buf, size);')
                    text = replace_once(text, '    LogMissing("open", path, r); return r;',
                        '    LogMissing("open", path, r); extern void IDeckObservePinConfig(const char *, int, int); IDeckObservePinConfig(path, 0, r); return r;')
                    text = replace_once(text,
                        'EXPORT FILE *fopen(const char *path, const char *m) { REAL(FILE *, "fopen", const char *, const char *); char buf[PATH_MAX]; return real(Redirect(path, buf, sizeof buf), m); }',
                        'EXPORT FILE *fopen(const char *path, const char *m) { REAL(FILE *, "fopen", const char *, const char *); char buf[PATH_MAX]; FILE *r = real(Redirect(path, buf, sizeof buf), m); extern void IDeckObservePinConfig(const char *, int, int); IDeckObservePinConfig(path, 1, r ? 0 : -1); return r; }')
                if name == 'CoreGraphics.m':
                    start = text.index('EXPORT CGDisplayModeRef CGDisplayCopyDisplayMode(')
                    end = text.index('EXPORT size_t CGDisplayModeGetWidth(', start)
                    text = text[:start] + '// iDeck CF ownership override\n' + text[end:]
                if name == 'AppKit.m':
                    text = replace_once(text,
                        '- (void)makeMainWindow { [self makeKeyAndOrderFront:nil]; }',
                        '- (void)makeMainWindow { extern void IDeckWindowMakeMain(id); IDeckWindowMakeMain(self); }')
                    text = replace_once(text, '@property NSUInteger phase, momentumPhase;',
                        '@property NSUInteger phase, momentumPhase;\nIDECK_OTHER_EVENT_FIELDS')
                    text = replace_once(text, '@implementation NSEvent\nSHIM_RESOLVE',
                        '@implementation NSEvent\nSHIM_RESOLVE\nIDECK_OTHER_EVENT_FACTORY')
                    text = replace_once(text, '- (id)subtype { return nil; }\n', '')
                    text = (OWN/'other-event.h').read_text() + '\n' + text
                out = tmp / name; out.write_text(text); sources[name] = out
        for component, own, reexport in [
            ('libSystem', ['sysv-semaphore.c','native-process-probe.c','native-vm-probe.c','native-vm-range-probe.c','native-small-pool-probe.c','pool-layout.c','cef-load-probe.m','helper-load-probe.m','helper-path.c','synthetic-helper-probe.m','exec-diagnostic.c','casefold-path.m','casefold-probe.m','volume-case-view.m','pin-config-observer.c'], ['-Wl,-reexport_library,'+sdk+'/usr/lib/libSystem.B.tbd']),
            ('AppKit', ['appkit-font.m','font-advancement.m','font-matrix-constant.m','bitmap-image-rep.m','window-main.m'], ['-Wl,-reexport_framework,UIKit']),
            ('CoreGraphics', ['display-pixel-encoding.m','display-mode-object.m'], ['-Wl,-reexport_framework,CoreGraphics'])]:
            text = (converted/'shims'/('Shim_'+component+'.m')).read_text()
            inputs['generated/Shim_'+component+'.m'] = hashlib.sha256(text.encode()).hexdigest()
            # Accept pristine generated source or our own idempotent sentinel.
            if component == 'CoreGraphics' and 'SHIM STUB CoreGraphics CGDisplayModeCopyPixelEncoding' in text:
                text = remove_generated_function(text, 'CGDisplayModeCopyPixelEncoding')
            if component == 'AppKit' and 'SHIM STUB AppKit NSFontIdentityMatrix' in text:
                text = remove_generated_function(text, 'NSFontIdentityMatrix')
            generated = tmp / ('Shim_'+component+'.m'); generated.write_text(text)
            output = app/'Frameworks'/('libShim_'+component+'.dylib')
            pending = tmp / output.name
            command = ['xcrun','-sdk','iphoneos','clang','-fobjc-arc','-target','arm64-apple-ios17.0',
                       '-dynamiclib','-install_name','@rpath/'+output.name,'-Wno-incompatible-library-redeclaration']
            for framework in ['Foundation','UIKit','QuartzCore','CoreGraphics','CoreText','Metal','GameController']:
                command += ['-framework', framework]
            command += reexport + [str(generated)] + [str(path) for name,path in sorted(sources.items()) if name.startswith(component)]
            for name in own:
                path = OWN/name
                inputs[str(path.relative_to(REPO))] = hashlib.sha256(path.read_bytes()).hexdigest()
            command += [str(OWN/name) for name in own] + ['-o', str(pending)]
            subprocess.run(command, check=True)
            staged.append((pending, output))
            print('Compiled pending', output.name)
        # All three compilations must succeed before any final dylib changes.
        # This is not a filesystem transaction: an I/O failure still invalidates
        # the receipt and must stop signing/deployment.
        hashes = {}
        for pending, output in staged:
            pending.replace(output)
            hashes[output.name] = hashlib.sha256(output.read_bytes()).hexdigest()
    # Enable the view only if its on-device eight-operation self-test also passes.
    info['IDeckCaseView'] = True
    (app/'Info.plist').write_bytes(plistlib.dumps(info))
    receipt.write_text(json.dumps({'referenceRevision': PIN, 'state': 'unsigned',
                                  'inputs': inputs, 'outputSHA256': hashes}, indent=2)+'\n')
    print('UNSIGNED output: re-sign every rebuilt dylib and the enclosing app; verify --deep --strict.')


if __name__ == '__main__':
    main()
