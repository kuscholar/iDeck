// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define dlopen test_open
#define dlsym test_symbol
#include "tier0-process-observer.c"
#undef dlopen
#undef dlsym
static const char Command[]="private-command -cachedir=private-path";
static char *Env[]={"PRIVATE_TOKEN=not-for-output",NULL};
static const char Directory[]="/private/test-directory";
static int Calls;
static int fake_create(const void *command,uint32_t flags,char *const env[],const char *directory) {
    assert(command==Command && flags==4 && env==Env && directory==Directory);
    assert(errno==EDOM);++Calls;errno=EAGAIN;return 57;
}
void *test_open(const char *path,int flags){assert(strstr(path,"libtier0_s.dylib") && flags==(RTLD_NOW|RTLD_LOCAL));errno=ENOENT;return (void *)42;}
void *test_symbol(void *handle,const char *symbol){assert(handle==(void *)42 && !strcmp(symbol,"CreateSimpleProcess"));errno=EINVAL;return (void *)fake_create;}
int main(void) {
    for(int i=0;i<2;++i){setenv("IDeckNativeProcessObserver",i?"1":"0",1);errno=EDOM;int r=CreateSimpleProcess(Command,4,Env,Directory);assert(r==57 && errno==EAGAIN);}
    assert(Calls==2);puts("tier0 observer PASS: exact arguments, result and incoming/outgoing errno preserved; no actual process creation");
}
