#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise actual early profile policy without mapping VA or touching Steam."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = r'''
#include <assert.h>
#include <stdio.h>
#include "ideck_runtime_selection.h"
static int valid=1;
static int read_cfg(const char *key,char *out,size_t n) {
 const char *value=NULL;
 if(!strcmp(key,"steam64.env.MADEIRA_CEF64_SOURCE_LAYOUT"))value=valid?"1":"0";
 if(!strcmp(key,"steam64.env.MADEIRA_STEAM_UI_SESSION"))value="1";
 if(!strcmp(key,"steam64.env.MADEIRA_CPU_COUNT"))value="1";
 if(!strcmp(key,"steam64.env.MADEIRA_JITLESS"))value="0";
 if(!strcmp(key,"steam64.env.MADEIRA_STEAM_UI_SAMPLING"))value="1";
 if(!value)return 0;
 assert(strlen(value)<n);strcpy(out,value);return 1;
}
static void clear(void) {
 unsetenv("MADEIRA_CEF64_SOURCE_LAYOUT");unsetenv("MADEIRA_STEAM_UI_SESSION");
 unsetenv("MADEIRA_CPU_COUNT");unsetenv("MADEIRA_CEF64_CONFIG_RESTORE");
 unsetenv("MADEIRA_JITLESS");unsetenv("MADEIRA_STEAM_UI_SAMPLING");
}
int main(void) {
 char *normal[]={"app",NULL};
 char *explicit[]={"app","madeira-steam64-big-picture-experiment",NULL};
 char *legacy[]={"app","madeira-runtime-diagnostics",NULL};
 char *both[]={"app","madeira-runtime-diagnostics","madeira-steam64-experiment",NULL};
 assert(!ideck_steam64_selected(NULL,1,normal));
 assert(ideck_steam64_selected(NULL,2,explicit));
 assert(ideck_steam64_selected("steam64",1,normal));
 assert(!ideck_steam64_selected("steam64",2,legacy));
 assert(ideck_steam64_selected("steam64",3,both));
 assert(!ideck_steam64_selected("steam64-old",1,normal));
 clear();assert(!ideck_steam64_early_environment(NULL,1,normal,read_cfg));
 assert(!getenv("MADEIRA_CEF64_SOURCE_LAYOUT"));
 assert(!ideck_steam64_early_environment("steam64",2,legacy,read_cfg));
 assert(!getenv("MADEIRA_CEF64_SOURCE_LAYOUT"));
 valid=0;assert(ideck_steam64_early_environment("steam64",1,normal,read_cfg)==-1);
 assert(!getenv("MADEIRA_STEAM_UI_SESSION"));
 valid=1;setenv("MADEIRA_CPU_COUNT","2",1);
 assert(ideck_steam64_early_environment("steam64",1,normal,read_cfg)==1);
 assert(!strcmp(getenv("MADEIRA_CEF64_SOURCE_LAYOUT"),"1"));
 assert(!strcmp(getenv("MADEIRA_STEAM_UI_SESSION"),"1"));
 assert(!strcmp(getenv("MADEIRA_CPU_COUNT"),"2")); /* explicit value retained */
 assert(!strcmp(getenv("MADEIRA_JITLESS"),"0")); /* available before Foundation snapshots */
 assert(!strcmp(getenv("MADEIRA_STEAM_UI_SAMPLING"),"1"));
 clear();setenv("MADEIRA_JITLESS","1",1);
 assert(ideck_steam64_early_environment("steam64",1,normal,read_cfg)==1);
 assert(!strcmp(getenv("MADEIRA_JITLESS"),"1")); /* explicit compatibility override retained */
 clear();setenv("MADEIRA_CEF64_CONFIG_RESTORE","1",1);
 assert(!ideck_steam64_early_environment("steam64",2,explicit,read_cfg));
 assert(!getenv("MADEIRA_CEF64_SOURCE_LAYOUT"));clear();
 puts("PASS persisted native runtime: ordinary open, explicit diagnostic override, early config, failure and restore isolation");
}
'''
with tempfile.TemporaryDirectory() as temp:
    d = Path(temp)
    (d / 'main.c').write_text(source)
    subprocess.run(['clang', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                    '-I'+str(root/'build/diagnostics'), str(d/'main.c'), '-o', str(d/'test')], check=True)
    subprocess.run([str(d/'test')], check=True)

native = (root/'app/Madeira/JITAllocator.c').read_text()
body = native.split('static void ideck_cef64_boot_holds(void)', 1)[1]
assert body.index('ideck_steam64_early_environment') < body.index('getenv("MADEIRA_CEF64_SOURCE_LAYOUT")')
swift = (root/'app/Madeira/SteamUIExperiment.swift').read_text()
assert swift.count('selectedRuntime: MadeiraConfig.get("steam-runtime")') == 2
assert 'Text(SteamUIExperiment.steam64 ? "Steam 64-bit' in swift
