// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Explicit lab-only discriminator: can supported native posix_spawn launch our
// own signed binary? No fake PID/result or alternate sandbox/entitlement route.
#include <dlfcn.h>
#include <errno.h>
#include <limits.h>
#include <spawn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>
__attribute__((constructor)) static void NativeProcessProbe(void) {
    const char *child=getenv("IDeckNativeProcessChild");
    if (child && strcmp(child,"1")==0) _exit(0);
    const char *enabled=getenv("IDeckNativeProcessProbe");
    if (!enabled || strcmp(enabled,"1")!=0) return;
    void *system=dlopen("/usr/lib/libSystem.B.dylib",RTLD_LAZY);
    int (*pathfn)(char *,uint32_t *)=dlsym(system,"_NSGetExecutablePath");
    int (*spawnfn)(pid_t *,const char *,const posix_spawn_file_actions_t *,const posix_spawnattr_t *,char *const [],char *const [])=dlsym(system,"posix_spawn");
    char path[PATH_MAX];uint32_t length=sizeof path;
    if (!pathfn || !spawnfn || pathfn(path,&length)!=0) {fprintf(stderr,"[ideck-mac-probe] native-spawn setup=failed\n");return;}
    char *argv[]={path,NULL};char *env[]={"IDeckNativeProcessChild=1",NULL};pid_t pid=-1;
    int result=spawnfn(&pid,path,NULL,NULL,argv,env),status=-1,waited=0;
    if (result==0) {waited=waitpid(pid,&status,0)==pid;}
    fprintf(stderr,"[ideck-mac-probe] native-spawn result=%d created=%d waited=%d exit=%d\n",result,result==0,waited,waited&&WIFEXITED(status)?WEXITSTATUS(status):-1);
}
