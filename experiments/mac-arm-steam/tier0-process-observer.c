// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Exact audited ARM64 tier0 four-register boundary. Observation only; no spawn,
// PID virtualization, argument/env mutation, debugger ports or plugin injection.
#include "launch-summary.h"
#include <dlfcn.h>
#include <errno.h>
#include <pthread.h>
#include <stdlib.h>
#include <string.h>
typedef int (*Create)(const void *,uint32_t,char *const [],const char *);
static Create Original;
static pthread_once_t Once=PTHREAD_ONCE_INIT;
static void Resolve(void) {
    void *handle=dlopen("@loader_path/../Mac/Contents/MacOS/libtier0_s.dylib",RTLD_NOW|RTLD_LOCAL);
    if(handle)Original=(Create)dlsym(handle,"CreateSimpleProcess");
}
int CreateSimpleProcess(const void *command,uint32_t flags,char *const env[],const char *directory) {
    int incoming=errno;pthread_once(&Once,Resolve);
    if(!Original){errno=ENOSYS;fprintf(stderr,"[ideck-tier0] original=unavailable result=0\n");return 0;}
    const char *setting=getenv("IDeckNativeProcessObserver");int enabled=setting && !strcmp(setting,"1");
    if(enabled) {
        ideck_launch_summary(stderr,command,flags);
        fprintf(stderr,"[ideck-tier0] env-provided=%d directory-provided=%d\n",env!=NULL,directory!=NULL);
    }
    errno=incoming;int result=Original(command,flags,env,directory),saved=errno;
    if(enabled)fprintf(stderr,"[ideck-tier0] original-result=%d errno=%d unchanged=1\n",result,saved);
    errno=saved;return result;
}
