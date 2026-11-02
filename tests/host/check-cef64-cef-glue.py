#!/usr/bin/env python3
"""Check real published CEF patch against pristine pinned Chromium files.

Usage: check-cef64-cef-glue.py /path/to/Chromium126 /path/to/CEF-pinned-source [original-gn-cache]
Does not modify either input checkout or run a downloaded executable.
"""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'experiments/cef64'))
sys.dont_write_bytecode = True
import cef_glue
from prepare import focused_elf_build, gn_target

if len(sys.argv) not in (3, 4):
    raise SystemExit(__doc__)
chromium, cef = (Path(p).resolve() for p in sys.argv[1:3])
patch = cef / 'patch/patches/crashpad_1995.patch'
cef_build = subprocess.check_output(['git', 'show', 'HEAD:BUILD.gn'], cwd=cef) if (cef / '.git').exists() else (cef / 'BUILD.gn').read_bytes()
assert hashlib.sha256(patch.read_bytes()).hexdigest() == cef_glue.PATCH_SHA256
assert 'refs/tags/126.0.6478.183' in (cef / 'CHROMIUM_BUILD_COMPATIBILITY.txt').read_text()
files = [s[4:] for s in patch.read_text().splitlines() if s.startswith('+++ ')]
assert len(files) == 10
with tempfile.TemporaryDirectory() as directory:
    temp = Path(directory)
    for filename in files:
        target = temp / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(subprocess.check_output(['git', 'show', 'HEAD:' + filename], cwd=chromium))
    # This temporary fixture is outside the cloned repository. On Windows it
    # would otherwise inherit the runner's global auto-CRLF setting instead of
    # the real source checkout's explicit core.autocrlf=false.
    subprocess.run(['git', '-c', 'core.autocrlf=false', 'apply', '-p0', '--check', str(patch)], cwd=temp, check=True)
    subprocess.run(['git', '-c', 'core.autocrlf=false', 'apply', '-p0', str(patch)], cwd=temp, check=True)
    patched = (temp / 'chrome/chrome_elf/BUILD.gn').read_bytes()
    focused = focused_elf_build(patched, cef_glue.PATCHED_ELF_BUILD_SHA256).decode()
    assert '//cef:chrome_elf_set' in focused and '//cef/libcef/features' in focused
    # Preserve the exact published production crash target, apart from the
    # existing one-header dependency relocation. Do not stub its C++ calls.
    original_target = gn_target(patched.decode(), 'static_library', 'crash')
    assert gn_target(focused, 'static_library', 'crash') == original_target.replace('"//content/public/common:result_codes"', '":content_result_codes"')
    cpp = (temp / 'chrome/chrome_elf/crash/crash_helper.cc').read_text()
    assert 'CefCrashReporterClient::InitializeCrashReportingForProcess();' in cpp
    target = cef_glue.focused_cef_target(cef_build).decode()
    assert target.count(cef_glue.V8_GENERATOR_DEP) == 1
    assert gn_target(target, 'static_library', 'chrome_elf_set').replace(cef_glue.V8_GENERATOR_DEP, '') == gn_target(cef_build.decode(), 'static_library', 'chrome_elf_set')
    for bad in (b'', cef_build + b'\n'):
        try:
            cef_glue.focused_cef_target(bad)
            raise AssertionError('unknown CEF metadata accepted')
        except ValueError:
            pass
for filename, (_, target, _) in cef_glue.BUILD_FLAGS.items():
    data = (Path(sys.argv[3]) / filename).read_bytes() if len(sys.argv) == 4 else subprocess.check_output(['git', 'show', 'HEAD:' + filename], cwd=chromium)
    focused = cef_glue.focused_buildflag_file(filename, data).decode()
    assert gn_target(focused, 'buildflag_header', target) == gn_target(data.decode(), 'buildflag_header', target)
    assert 'component(' not in focused and 'fuzzer_test(' not in focused
print('PASS: entire hash-pinned published CEF crash patch applies to ten pristine Chromium files; exact production CEF/crash GN targets retained; no runtime or Valve ABI claim')
