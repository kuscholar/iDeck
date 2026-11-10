#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Build separate pinned LinuxRunner archives with namespaced task TLS.

Never edits vendor/base archives, an App target, Wine, or device state. The
copied header and compile_commands retain the namespace for later overlays.
Native adapters must use the SAME forced include and flag when eventually
linking these archives. A symbol check is not runtime/game/device validation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('output', type=Path)
parser.add_argument('--platform', choices=('host', 'ios'), required=True)
parser.add_argument('--meson', required=True)
parser.add_argument('--ninja', required=True)
args = parser.parse_args()
repo = Path(__file__).resolve().parents[3]
source = repo / 'vendor/LinuxRunner'
pin = 'd1419782da2e299fe22f1ddb85c70ae3d1e276b1'
assert subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip() == pin
assert not subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain', '--untracked-files=no'], text=True).strip()
out = args.output.resolve()
assert str(out).startswith('/Volumes/easystore/') and not out.exists()
out.mkdir(parents=True, mode=0o700)
header = out / 'LinuxSymbolNamespace.h'
shutil.copy2(repo / 'experiments/linux-steam/app/LinuxSymbolNamespace.h', header)
c_args = ['-DIDECK_LAB_LINUX_SYMBOL_NAMESPACE=1', '-include', str(header)]
command = [args.meson, 'setup', str(out / 'build'), str(source)]
sdk = None
if args.platform == 'ios':
    sdk = subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip()
    cross = out / 'cross.ini'
    cross.write_text("[binaries]\nc = ['xcrun', '--sdk', 'iphoneos', 'clang']\nar = ['xcrun', 'ar']\n"
                     "[host_machine]\nsystem = 'darwin'\ncpu_family = 'aarch64'\ncpu = 'aarch64'\nendian = 'little'\n"
                     "[properties]\nneeds_exe_wrapper = true\n[built-in options]\n"
                     'c_args = ' + repr(['-target', 'arm64-apple-ios26.0', '-isysroot', sdk] + c_args) + '\n'
                     'c_link_args = ' + repr(['-target', 'arm64-apple-ios26.0', '-isysroot', sdk]) + '\n')
    command += ['--cross-file', str(cross)]
else:
    command += ['-Dc_args=' + json.dumps(c_args)]
command += ['-Dengine=asbestos', '-Dguest_arch=arm64', '-Djit=false', '-Djit_emit=false',
            '-Dcli_aot=', '-Dvdso_required=true']
environment = dict(os.environ)
environment['PATH'] = str(Path(args.ninja).resolve().parent) + os.pathsep + environment['PATH']
subprocess.run(command, check=True, env=environment)
subprocess.run([args.ninja, '-j4', '-C', str(out / 'build'), 'libish.a', 'libish_emu.a', 'libfakefs.a'], check=True, env=environment)
# The existing adapter requires this already-qualified generated dirfd guard;
# reuse its patch/compiler command, including our forced namespace declaration.
subprocess.run(['python3', str(repo/'experiments/linux-steam/tools/overlay-dirfd.py'),
                str(source), str(out/'build')], check=True, env=environment)
hashof = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
archives = {}
for name in ('libish.a', 'libish_emu.a', 'libfakefs.a'):
    archive = out / 'build' / name
    symbols = subprocess.check_output(['nm', '-m', '-g', str(archive)], text=True, stderr=subprocess.DEVNULL)
    (out / (name + '.symbols.txt')).write_text(symbols)
    assert not any(line.rstrip().endswith('external _current') for line in symbols.splitlines()), name
    archives[name] = dict(sha256=hashof(archive), namespaced_rows=[line for line in symbols.splitlines()
                                                                if line.rstrip().endswith('external _ideck_linux_current')])
definitions = [line for line in archives['libish.a']['namespaced_rows'] if '(__DATA,__thread_vars)' in line]
assert len(definitions) == 1, definitions
(out / 'evidence.json').write_text(json.dumps(dict(scope='Darwin arm64 isolated archives/symbols only, NOT final app or runtime coexistence',
    linuxrunner=pin, platform=args.platform, sdk=sdk, namespace_header_sha256=hashof(header),
    builder_sha256=hashof(Path(__file__)), archives=archives,
    existing_dirfd_overlay_sha256=hashof(repo/'experiments/linux-steam/patches/linuxrunner-dirfd.patch'),
    compile_commands_sha256=hashof(out/'build/compile_commands.json')), indent=2) + '\n')
print('Built isolated task-TLS namespace; ordinary sources/targets and device unchanged')
