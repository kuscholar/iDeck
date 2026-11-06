#!/usr/bin/env python3
"""Compile the real menu policy: focus denial must never launch another Steam."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root/'build/ideck-control/ideck-control.c').read_text()
policy = source.split('static const char *steam_menu(void)', 1)[1].split('static int input_diagnostic_allowed', 1)[0]
policy = 'static const char *steam_menu(void)' + policy
fixture = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
typedef unsigned UINT;
#define VK_CONTROL 17
#define KEYEVENTF_KEYUP 2
static int result,calls,events,sleeps,failed;
static int focus_existing_big_picture(void){calls++;return result;}
static UINT key(unsigned vk,unsigned flags){
 const unsigned keys[]={17,'1','1',17}, states[]={0,0,2,2};
 assert(events<4&&vk==keys[events]&&flags==states[events]);events++;
 return events==failed?0:1;
}
static void Sleep(unsigned ms){assert(ms==100);sleeps++;}
'''
tests = r'''
int main(void){
 for(result=-2;result<=0;result++){
  calls=events=sleeps=0;
  const char *expected=result==-2?"steam-window-unresponsive":result==-1?"steam-window-unavailable":"steam-focus-pending";
  assert(!strcmp(steam_menu(),expected)&&calls==1&&!events&&!sleeps);
 }
 result=1;
 for(failed=0;failed<=4;failed++){
  calls=events=sleeps=0;
  assert(!strcmp(steam_menu(),failed?"input-unavailable":"menu-requested"));
  assert(calls==1&&events==4&&sleeps==1); /* Releases stay balanced even after a failed down. */
 }
 puts("PASS production Steam menu: no child launch on missing/hung/denied window, bounded focus, balanced Ctrl+1 and failed input");
}
'''
with tempfile.TemporaryDirectory() as temp:
    p = Path(temp)
    (p/'menu.c').write_text(fixture+policy+tests)
    subprocess.run(['clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'menu.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
