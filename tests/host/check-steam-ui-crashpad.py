#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Exercise the production Steam Crashpad admission policy, not Chromium itself."""
from pathlib import Path
import subprocess
import tempfile
source = (Path(__file__).resolve().parents[2] / 'build/ntdll-unix/process_ios.c').read_text()
start = source.index('static int ios_steam_ui_crashpad_allowed(')
end = source.index('/* What kind of Social Club process', start)
code = '#include <stdint.h>\n#include <stdlib.h>\n#include <string.h>\n#include <assert.h>\ntypedef uint16_t WCHAR;\n' + source[start:end]
code += r'''
static int run(const char *s) {
 WCHAR cl[512]; int n=(int)strlen(s); assert(n<512);
 for(int i=0;i<n;i++)cl[i]=(unsigned char)s[i];
 return ios_steam_ui_crashpad_allowed(cl,n);
}
int main(void) {
 unsetenv("MADEIRA_STEAM_UI_SESSION"); unsetenv("MADEIRA_STEAM_UI_ALLOW_CRASHPAD");
 assert(!run("helper --type=crashpad-handler"));
 setenv("MADEIRA_STEAM_UI_ALLOW_CRASHPAD","1",1);
 assert(!run("helper --type=crashpad-handler"));
 setenv("MADEIRA_STEAM_UI_SESSION","1",1);
 assert(run("helper --type=crashpad-handler"));
 assert(run("helper \"--type=crashpad-handler\" --database=x"));
 assert(!run("helper --type=renderer"));
 assert(!run("helper --type=gpu-process"));
 assert(!run("helper --type=utility"));
 assert(!run("helper --type=crashpad-handler-extra"));
 assert(!run("helper --type=crashpad-handler=extra"));
 assert(!run("helper --type=crashpad"));
 assert(!run("helper --type=renderer --type=crashpad-handler"));
 assert(!run("helper x--type=crashpad-handler"));
 assert(!run("helper")); assert(!run(""));
 setenv("MADEIRA_STEAM_UI_SESSION","0",1);
 assert(!run("helper --type=crashpad-handler"));
 return 0;
}
'''
with tempfile.TemporaryDirectory() as temp:
 p=Path(temp);(p/'gate.c').write_text(code)
 subprocess.run(['clang','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(p/'gate.c'),'-o',str(p/'gate')],check=True)
 subprocess.run([str(p/'gate')],check=True)
print('PASS: production dual-gated exact Crashpad admission; renderer/GPU/utility/ambiguous types denied (ASan/UBSan)')
