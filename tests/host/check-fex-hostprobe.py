#!/usr/bin/env python3
"""Check the FEX host feature probe (WineProcessBridge.m madeira_publish_host_probe).

The app answers FEX's question "which ARMv8/9 features does this core have" with the
hw.optional sysctls, in FEX_MADEIRA_HOSTPROBE ("AFP=1,FLAGM=1,...", "?" when a sysctl does
not exist). Both FEX modules parse it in Source/Windows/Common/CPUFeatures.cpp.

- the probe function is compiled on this host with a stand-in sysctlbyname and run for a
  core with everything, one without some features, and one whose OS lacks some sysctls;
- the string stays within the function's buffer (a longer one publishes nothing);
- FEX's own parsers (the Absent and Has lambdas of CPUFeatures.cpp, compiled as written)
  read every key the app publishes exactly as published: no key is mistaken for another
  that contains it (RCPC in LRCPC2/LRCPC3, FLAGM in FLAGM2, ...);
- every key FEX reads is one the app publishes.
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
bridge = (root / 'app/Madeira/WineProcessBridge.m').read_text()
start = bridge.index('static void madeira_publish_host_probe(void)\n{')
end = bridge.index('\n}\n', start) + 3
probe_fn = bridge[start:end]
keys = re.findall(r'\{ "([A-Z0-9]+)",\s*"(hw\.optional\.[A-Za-z0-9_.]+)" \}', probe_fn)
names = [k for k, _ in keys]
assert len(names) == len(set(names)) and len(names) >= 19, names
for new in ('LSE2', 'LRCPC3', 'FRINTTS', 'RPRES', 'CSSC', 'MOPS', 'ECV', 'WFXT'):
    assert new in names, new

cpuf_path = root / 'FEX/Source/Windows/Common/CPUFeatures.cpp'
cpuf = cpuf_path.read_text()
absent = re.search(r'const auto Absent = \[Probe\]\(const char\* Key\) \{.*?\n    \};', cpuf, re.S).group(0)
has = re.search(r'const auto Has = \[Probe\]\(const char\* Key, char Want\) \{.*?\n    \};', cpuf, re.S).group(0)
read_keys = set(re.findall(r'Absent\("([A-Z0-9]+)"\)', cpuf)) | set(re.findall(r'Has\("([A-Z0-9]+)", ', cpuf))
assert read_keys and read_keys <= set(names), sorted(read_keys - set(names))

harness = r'''
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <unistd.h>
static const char* const* Table;
static int sysctlbyname(const char* name, void* out, size_t* size, void*, size_t) {
  for (const char* const* t = Table; *t; t += 2) {
    if (!strcmp(*t, name)) {
      if (!strcmp(t[1], "missing")) { errno = ENOENT; return -1; }
      *(int32_t*)out = atoi(t[1]);
      *size = sizeof(int32_t);
      return 0;
    }
  }
  errno = ENOENT;
  return -1;
}
@PROBE@
static bool Absent(const char* Probe, const char* Key) {
@ABSENT@
  return Absent(Key);
}
static bool Has(const char* Probe, const char* Key, char Want) {
@HAS@
  return Has(Key, Want);
}
int main(int argc, char** argv) {
  Table = (const char* const*)(argv + 1);
  unsetenv("FEX_MADEIRA_HOSTPROBE");
  madeira_publish_host_probe();
  const char* Probe = getenv("FEX_MADEIRA_HOSTPROBE");
  if (!Probe) { printf("UNSET\n"); return 0; }
  printf("%s\n", Probe);
  for (int i = 1; argv[i]; i += 2) {
    const char* Key = argv[i];
    if (!strncmp(Key, "key:", 4)) {
      printf("%s absent=%d has1=%d has0=%d\n", Key + 4, Absent(Probe, Key + 4), Has(Probe, Key + 4, '1'), Has(Probe, Key + 4, '0'));
    }
  }
}
'''

with tempfile.TemporaryDirectory(prefix='fex-hostprobe-') as tmp:
    tmp = Path(tmp)
    src = tmp / 'probe.cpp'
    body = probe_fn.replace('static void madeira_publish_host_probe(void)', 'static void madeira_publish_host_probe()')
    src.write_text(harness.replace('@PROBE@', body)
                          .replace('@ABSENT@', '  ' + absent.strip())
                          .replace('@HAS@', '  ' + has.strip()))
    exe = tmp / 'probe'
    subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-O1', '-Wall', '-Wno-unused-function',
                    '-fsanitize=address,undefined', '-fno-sanitize-recover=all', str(src), '-o', str(exe)],
                   check=True)

    def run(values):
        argv = []
        for key, sysctl in keys:
            argv += [sysctl, values.get(key, '1')]
        argv += [x for key in names for x in ('key:' + key, '')]
        out = subprocess.check_output([str(exe)] + argv, text=True, stderr=subprocess.DEVNULL).splitlines()
        return out[0], {l.split()[0]: dict(kv.split('=') for kv in l.split()[1:]) for l in out[1:]}

    # A core with everything (what A19 is expected to report), one without the newer
    # features (A12/A13-like) and an OS that lacks some of the sysctls.
    cases = (
        {},
        {'AFP': '0', 'FLAGM': '0', 'FLAGM2': '0', 'LRCPC2': '0', 'LSE2': '0', 'FRINTTS': '0', 'CSSC': '0'},
        {'LRCPC3': 'missing', 'CSSC': 'missing', 'MOPS': 'missing', 'RCPC': '0', 'FLAGM2': 'missing'},
    )
    for values in cases:
        probe, parsed = run(values)
        assert probe != 'UNSET' and len(probe) < 256, probe
        expect = []
        for key, _ in keys:
            v = values.get(key, '1')
            v = '?' if v == 'missing' else v
            expect.append(f'{key}={v}')
        assert probe == ','.join(expect), (probe, expect)
        for key in names:
            v = values.get(key, '1')
            got = parsed[key]
            assert got['absent'] == ('1' if v == '0' else '0'), (key, v, got)
            assert got['has1'] == ('1' if v == '1' else '0'), (key, v, got)
            assert got['has0'] == ('1' if v == '0' else '0'), (key, v, got)
print('PASS: the probe publishes', len(names), 'keys within its buffer, and FEX reads each one exactly as published')
