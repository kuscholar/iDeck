#!/usr/bin/env python3
"""Reject propagated allocation failures without requiring the old fatal text."""
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md.
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
tool = root / 'tools/analyze-steam-ui-pools.py'
spec = importlib.util.spec_from_file_location('allocation_evidence', tool)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

secret = 'PRIVATE_ACCOUNT_PAYLOAD_MUST_NOT_APPEAR'
propagated = f'''I 6C [ideck-fex-ir] local half=2MiB paired=4MiB maxinst=256
[va-scan] FAILED window=0x7500000000..0x7760000000 size=0x1000000
[fex-va] live arena=0x7500000000..0x7760000000 request=0x1000000 align_mask=0xffffff views=1235 covered=0x256c1a000 free=0x93e6000 committed=0x121373000 overlap=0x0 holes=561 maxgap=0x100e000 max_aligned_gap=0xd90000 secret={secret}
04ac:err:module:loader_init arm64ec_thread_init failed c0000017 -- terminating this thread only {secret}
'''
result = module.analyze_fex(propagated.splitlines())
assert result['assessment'] == 'allocation-failure-observed'
assert result['counters']['allocator_fatals'] == 0
assert result['counters']['ir_buffer_rejections'] == 0
assert result['counters']['thread_initialization_failures'] == 1
assert result['counters']['owned_arena_scan_failures'] == 1
assert result['thread_failure_statuses'] == {'0xc0000017': 1}
assert result['recent_failure_censuses'][0]['max_aligned_gap'] == 0xd90000
assert secret not in json.dumps(result)

unrelated = '''[va-scan] FAILED window=0x100000000..0x7100000000 size=0x477000
04ac:err:module:loader_init arm64ec_thread_init failed 00000000
I 6C [ideck-fex-ir] local half=2MiB paired=4MiB maxinst=256
'''
assert module.analyze_fex(unrelated.splitlines())['assessment'] == 'no-matched-failure'
assert module.analyze_fex([])['assessment'] == 'no-matched-failure'
assert 'not a PASS' in ' '.join(module.analyze_fex([])['limits'])
for line, kind in [('[ideck-fex-ir] rejected NULL or out-of-bounds IR buffer before node access', 'ir_buffer_rejections'),
                   ('FEXAlloc could not allocate bytes=0x1000000', 'allocator_fatals'),
                   ('[FEX-iOS] ThreadInit: thread state unavailable -- unwinding thread 0x42', 'thread_state_unavailable')]:
    assert module.analyze_fex([line])['counters'][kind] == 1
assert module.analyze_fex(['04AC:err:module:loader_init arm64ec_thread_init failed 0xC0000005'])[
    'thread_failure_statuses'] == {'0xc0000005': 1}
many = module.analyze_fex((propagated * 40).splitlines())
assert len(many['bounded_failure_samples']) == 16
assert len(many['recent_failure_censuses']) == 8
assert many['counters']['thread_initialization_failures'] == 40

with tempfile.TemporaryDirectory() as directory:
    log = Path(directory) / 'own.log'
    output = Path(directory) / 'report.json'
    log.write_text(propagated)
    command = [sys.executable, str(tool), str(log), '--output', str(output)]
    assert subprocess.run(command, capture_output=True).returncode == 0
    assert subprocess.run(command + ['--fail-on-fex-allocation-error'], capture_output=True).returncode == 2
    assert secret not in output.read_text()
    log.write_text(unrelated)
    assert subprocess.run(command + ['--fail-on-fex-allocation-error'], capture_output=True).returncode == 0
print('PASS propagated thread-init/OOM detection, unrelated-range exclusions, bounded redaction and CLI failure status; no runtime-success claim')
