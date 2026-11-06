#!/usr/bin/env python3
"""Exercise the production Steam-only sampling policy, without running Wine."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = r'''
#include <assert.h>
#include <stdio.h>
#include "SteamUIDiagnostics.h"
int main(void) {
 const char *sessions[]={NULL,"0","1","11"};
 const char *values[]={NULL,"","0","1","2"};
 setenv("MADEIRA_JITLESS","1",1);
 setenv("MADEIRA_CPU_COUNT","1",1);
 setenv("MADEIRA_WARMER_SWEEP_CYCLES","19",1);
 for (unsigned i=0;i<4;i++) for(unsigned k=0;k<5;k++) for(unsigned j=0;j<5;j++) {
  unsetenv("MADEIRA_STEAM_UI_SESSION");unsetenv("MADEIRA_LEAN_DIAG");
  unsetenv("MADEIRA_STEAM_UI_SAMPLING");
  if(sessions[i])setenv("MADEIRA_STEAM_UI_SESSION",sessions[i],1);
  if(values[k])setenv("MADEIRA_LEAN_DIAG",values[k],1);
  if(values[j])setenv("MADEIRA_STEAM_UI_SAMPLING",values[j],1);
  assert(madeira_steam_ui_diagnostic_defaults()==(i==2));
  const char *lean=getenv("MADEIRA_LEAN_DIAG");
  const char *sampling=getenv("MADEIRA_STEAM_UI_SAMPLING");
  /* Defaulting pure sampling must never write the VM-maintenance policy. */
  if(values[k])assert(lean&&!strcmp(lean,values[k])); else assert(!lean);
  if(values[j])assert(sampling&&!strcmp(sampling,values[j]));
  else if(i==2)assert(sampling&&!strcmp(sampling,"0")); else assert(!sampling);
  int broad=lean&&*lean&&strcmp(lean,"0");
  int pure=sampling&&!strcmp(sampling,"0");
  int disabled=i==2&&(pure||broad);
  assert(madeira_steam_ui_sampling_disabled()==disabled);
  assert(madeira_steam_ui_periodic_stacks_enabled()==!disabled);
  assert(!strcmp(getenv("MADEIRA_WARMER_SWEEP_CYCLES"),"19"));
  assert(!strcmp(getenv("MADEIRA_JITLESS"),"1"));
  assert(!strcmp(getenv("MADEIRA_CPU_COUNT"),"1"));
 }
 puts("PASS pure sampling: 100 session/override/lean cases; VM/JS/CPU unchanged");
}

'''
with tempfile.TemporaryDirectory() as temp:
    p = Path(temp)
    (p / 'main.c').write_text(source)
    subprocess.run(['clang', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                    '-I'+str(root/'app/Madeira'), str(p/'main.c'), '-o', str(p/'check')], check=True)
    subprocess.run([str(p/'check')], check=True)

bridge = (root/'app/Madeira/WineProcessBridge.m').read_text()
assert bridge.index('madeira_steam_ui_diagnostic_defaults();') > bridge.index('game config env:')
compositor = (root/'app/Madeira/Winios/Winios.m').read_text()
assert 'if (!stack_timer && madeira_steam_ui_periodic_stacks_enabled())' in compositor
# Actual main-thread-stall evidence must still be captured on demand.
heartbeat = compositor.split('static void winios_main_heartbeat(', 1)[1].split('static void *winios_freeze_watch', 1)[0]
assert 'ios_dump_all_thread_stacks();' in heartbeat

server = (root/'build/ntdll-unix/server_ios.c').read_text()
assert '#include "../../app/Madeira/SteamUIDiagnostics.h"' in server
assert 'ios_lean_diag = broad_lean || madeira_steam_ui_sampling_disabled();' in server
assert 'if (!ios_lean_diag) dispatch_async' in server
virtual = (root/'build/ntdll-unix/virtual_ios.c').read_text()
assert 'MADEIRA_STEAM_UI_SAMPLING' not in virtual
