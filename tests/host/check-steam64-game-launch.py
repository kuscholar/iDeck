#!/usr/bin/env python3
"""Compile the real fixed game-launch policy with synthetic Windows call results.

This checks isolation and request routing, not Steam licensing or device gameplay.
"""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'build/ideck-control/ideck-control.c').read_text()
gate = source[source.index('static int input_diagnostic_allowed(void)'):source.index('static int steam64_menu_keys(void)')]
command = source[source.index('static const char *diagnostic_hot_roads(void)'):source.index('static void input_status(void)')]
harness = r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
typedef unsigned DWORD;
#define INVALID_FILE_ATTRIBUTES 0xffffffffu
#define FILE_ATTRIBUTE_DIRECTORY 0x10u
static DWORD attributes;
static int file_calls,open_calls,open_result;
static DWORD GetFileAttributesW(const wchar_t *path) {
 assert(!wcscmp(path,L"C:\\Program Files\\Steam\\steamapps\\common\\Hot Roads\\hr.exe"));
 file_calls++;return attributes;
}
static int open_steam(const wchar_t *uri) {
 assert(!wcscmp(uri,L"steam://run/1819280"));open_calls++;return open_result;
}
'''
test = r'''
int main(void) {
 unsetenv("MADEIRA_STEAM_UI_SESSION");unsetenv("MADEIRA_STEAM64_INPUT_DIAGNOSTICS");
 unsetenv("MADEIRA_STEAM64_GAME_LAUNCH_DIAGNOSTICS");unsetenv("WINEPREFIX");
 assert(!strcmp(diagnostic_hot_roads(),"diagnostic-disabled"));
 setenv("MADEIRA_STEAM_UI_SESSION","1",1);setenv("MADEIRA_STEAM64_INPUT_DIAGNOSTICS","1",1);
 setenv("WINEPREFIX","/private/test/wine-steam64",1);
 assert(!strcmp(diagnostic_hot_roads(),"diagnostic-disabled"));
 const char *bad[]={"","0","true","2"};
 for(unsigned i=0;i<sizeof(bad)/sizeof(*bad);i++) {
  setenv("MADEIRA_STEAM64_GAME_LAUNCH_DIAGNOSTICS",bad[i],1);
  assert(!strcmp(diagnostic_hot_roads(),"diagnostic-disabled"));
 }
 setenv("MADEIRA_STEAM64_GAME_LAUNCH_DIAGNOSTICS","1",1);
 setenv("WINEPREFIX","/private/test/wine",1);
 assert(!strcmp(diagnostic_hot_roads(),"diagnostic-disabled"));
 setenv("WINEPREFIX","/private/test/wine-steam64-old",1);
 assert(!strcmp(diagnostic_hot_roads(),"diagnostic-disabled"));
 setenv("WINEPREFIX","/private/test/wine-steam64",1);
 setenv("MADEIRA_STEAM_UI_SESSION","0",1);
 assert(!strcmp(diagnostic_hot_roads(),"diagnostic-disabled"));
 setenv("MADEIRA_STEAM_UI_SESSION","1",1);setenv("MADEIRA_STEAM64_INPUT_DIAGNOSTICS","0",1);
 assert(!strcmp(diagnostic_hot_roads(),"diagnostic-disabled"));
 assert(file_calls==0&&open_calls==0);
 setenv("MADEIRA_STEAM64_INPUT_DIAGNOSTICS","1",1);
 attributes=INVALID_FILE_ATTRIBUTES;assert(!strcmp(diagnostic_hot_roads(),"game-not-installed"));
 attributes=FILE_ATTRIBUTE_DIRECTORY;assert(!strcmp(diagnostic_hot_roads(),"game-not-installed"));
 assert(open_calls==0);
 attributes=0;open_result=0;assert(!strcmp(diagnostic_hot_roads(),"steam-open-failed"));
 open_result=1;assert(!strcmp(diagnostic_hot_roads(),"diagnostic-game-launch-requested"));
 assert(file_calls==4&&open_calls==2);
 puts("PASS: exact fixed Steam game URI, all lab gates, installed-file requirement and failure propagation (ASan/UBSan)");
}
'''
with tempfile.TemporaryDirectory() as directory:
    directory = Path(directory)
    c = directory / 'launch.c'
    c.write_text(harness + gate + command + test)
    subprocess.run(['clang', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                    str(c), '-o', str(directory / 'test')], check=True)
    subprocess.run([str(directory / 'test')], check=True)
