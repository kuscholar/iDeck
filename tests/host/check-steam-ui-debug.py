#!/usr/bin/env python3
"""Compile the actual bridge debug policy; verify lab opt-in never enables traces."""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
s = (root / 'app/Madeira/WineProcessBridge.m').read_text()
start = s.index('        {\n            const char *verbose = getenv("MADEIRA_DEBUG_VERBOSE");')
end = s.index('\n\n        // Phase 3D investigation:', start)
policy = s[start:end]
fixture = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define LOG(...) ((void)0)
static const char *selected;
static int fixture_setenv(const char *key, const char *value, int overwrite) {
 assert(!strcmp(key,"WINEDEBUG") && overwrite==1 && !selected);
 selected=value;return 0;
}
#define setenv fixture_setenv
int main(void) {
''' + policy + r'''
 assert(selected);puts(selected);return 0;
}
'''
with tempfile.TemporaryDirectory() as directory:
    p=Path(directory);(p/'policy.c').write_text(fixture)
    subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'policy.c'),'-o',str(p/'policy')],check=True)
    for session in (None,'0','1','11'):
        for module in (None,'0','1','11'):
            for verbose in (None,'1'):
                env={k:v for k,v in os.environ.items() if k not in ('MADEIRA_STEAM_UI_SESSION','MADEIRA_STEAM_UI_MODULE_ERRORS','MADEIRA_DEBUG_VERBOSE')}
                for key,value in [('MADEIRA_STEAM_UI_SESSION',session),('MADEIRA_STEAM_UI_MODULE_ERRORS',module),('MADEIRA_DEBUG_VERBOSE',verbose)]:
                    if value is not None:env[key]=value
                actual=subprocess.check_output([str(p/'policy')],env=env,text=True).strip()
                if session=='1':
                    assert actual==('-all,err+module' if module=='1' else '-all')
                    assert 'trace' not in actual and 'relay' not in actual
                elif verbose=='1':
                    assert actual.startswith('err+all,fixme+all,') and 'trace+process' in actual
                else:assert actual=='err+all,err-virtual,fixme-d3dcompiler'
print('PASS actual bridge policy: exact session/module opt-in, no lab trace channels even with verbose=1, ordinary behavior retained; ASan/UBSan')
