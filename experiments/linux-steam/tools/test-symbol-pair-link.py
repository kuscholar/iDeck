#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Actual iOS kernel+wineserver archive link discriminator, not a final App.

Only these two archives are all-loaded: all-loading the engine too forces four
pre-existing duplicate gadget aliases, unlike ordinary lazy App linkage. Engine
and system references intentionally remain unresolved in this relocatable file.
Does not execute Wine or certify a prepared archive's source provenance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('ordinary_kernel', type=Path)
p.add_argument('namespaced_kernel', type=Path)
p.add_argument('wineserver', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
out = a.output.resolve()
assert str(out).startswith('/Volumes/easystore/') and not out.exists()
out.mkdir(mode=0o700, parents=True)
hashof = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
rows = []
for name, kernel in [('ordinary', a.ordinary_kernel), ('namespaced', a.namespaced_kernel)]:
    kernel = kernel.resolve()
    server = a.wineserver.resolve()
    output = out / (name + '.o')
    command = ['xcrun', 'ld', '-r', '-arch', 'arm64', '-platform_version', 'ios', '26.0', '27.0',
               '-all_load', str(kernel), str(server), '-o', str(output)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    log = result.stdout + result.stderr
    (out / (name + '.log')).write_text(log)
    row = dict(variant=name, status=result.returncode, kernel_sha256=hashof(kernel),
               wineserver_sha256=hashof(server), log_sha256=hashlib.sha256(log.encode()).hexdigest())
    if name == 'ordinary':
        assert result.returncode and "duplicate symbol '_current'" in log, log
    else:
        assert not result.returncode, log
        symbols = subprocess.check_output(['nm', '-m', '-g', str(output)], text=True)
        (out / 'namespaced.symbols.txt').write_text(symbols)
        definitions = [line for line in symbols.splitlines() if
                       line.endswith('external _current') or line.endswith('external _ideck_linux_current')]
        assert len(definitions) == 2, definitions
        assert any('(__DATA,__common) external _current' in line for line in definitions), definitions
        assert any('(__DATA,__thread_vars) external _ideck_linux_current' in line for line in definitions), definitions
        row.update(current_definitions=definitions, output_sha256=hashof(output))
    rows.append(row)
(out / 'evidence.json').write_text(json.dumps(dict(scope='Actual iOS kernel/server pair relocatable link ONLY; NOT complete Mach-O App, Wine execution or iPad test',
    prepared_wine_source_revision_not_artifact_verified=True, results=rows), indent=2) + '\n')
print('Actual archive pair: ordinary duplicate current; namespaced link PASS with distinct regular/TLS definitions')
