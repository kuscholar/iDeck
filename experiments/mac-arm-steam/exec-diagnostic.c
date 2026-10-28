// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Observe native re-exec without changing its result or printing unknown argument values.
#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static const char *ExecKind(const char *path) {
    if (!path) return "<null>";
    const char *slash=strrchr(path,'/');const char *base=slash?slash+1:path;
    static const char *const known[]={"steam_osx","Steam Helper","libtier0_s.dylib","steamclient.dylib"};
    for(unsigned i=0;i<sizeof known/sizeof known[0];++i)if(!strcmp(base,known[i]))return known[i];
    return "other-redacted";
}
int execv(const char *path, char *const arguments[]) {
    int incoming=errno;
    typedef int (*Exec)(const char *, char *const []);
    Exec real = (Exec)dlsym(RTLD_NEXT, "execv");
    fprintf(stderr, "[ideck-mac-exec] request executable=%s\n", ExecKind(path));
    static const char *const known[] = {
        "-nobootstrapperupdate", "-skipinitialbootstrap", "-noarchrestart",
        "-inhibitbootstrap", "-silent", "-foreground", "-noverifyfiles",
        "-forcesteamupdate", "-forceguiupdater", "-steam_launcher", "-clientui",
        "-no-cef-sandbox", "-bigpicture", "-nocrashmonitor", "-cef-disable-gpu"
    };
    unsigned count = 0, unknown = 0;
    if (arguments) for (; count < 64 && arguments[count]; ++count) {
        if (count == 0) continue;
        int recognized = 0;
        for (unsigned i = 0; i < sizeof(known) / sizeof(known[0]); ++i) {
            if (strcmp(arguments[count], known[i]) == 0) {
                fprintf(stderr, "[ideck-mac-exec] known-flag=%s\n", known[i]);
                recognized = 1; break;
            }
        }
        if (!recognized) unknown++;
    }
    fprintf(stderr, "[ideck-mac-exec] argv-count=%u redacted-count=%u observer=2\n", count, unknown);
    if (!real) { errno = ENOSYS; return -1; }
    errno=incoming;int result = real(path, arguments), saved = errno;
    fprintf(stderr, "[ideck-mac-exec] returned result=%d errno=%d\n", result, saved);
    errno = saved;
    return result;
}

// Observers forward native process calls unchanged. In particular, returning a
// fabricated PID or successful spawn would violate Steam's IPC expectations.
#include <spawn.h>
#include <sys/types.h>
int posix_spawn(pid_t *pid, const char *path, const posix_spawn_file_actions_t *actions,
                const posix_spawnattr_t *attrs, char *const argv[], char *const envp[]) {
    int incoming=errno;
    typedef int (*Spawn)(pid_t *,const char *,const posix_spawn_file_actions_t *,const posix_spawnattr_t *,char *const [],char *const []);
    Spawn real=(Spawn)dlsym(RTLD_NEXT,"posix_spawn");
    if (!real) {errno=incoming;return ENOSYS;}
    errno=incoming;int result=real(pid,path,actions,attrs,argv,envp), saved=errno;
    fprintf(stderr,"[ideck-mac-process] posix_spawn executable=%s result=%d child-created=%d\n",ExecKind(path),result,result==0);
    errno=saved;return result;
}
pid_t fork(void) {
    int incoming=errno;
    pid_t (*real)(void)=dlsym(RTLD_NEXT,"fork");
    if (!real) {errno=ENOSYS;return -1;}
    Dl_info caller = {0};
    void *returnPC = __builtin_return_address(0);
    if (dladdr(returnPC, &caller) && caller.dli_fbase)
        fprintf(stderr,"[ideck-mac-process] fork caller=%s+0x%lx\n",ExecKind(caller.dli_fname),(unsigned long)((char *)returnPC-(char *)caller.dli_fbase));
    errno=incoming;pid_t result=real();int saved=errno;
    fprintf(stderr,"[ideck-mac-process] fork result=%ld errno=%d\n",(long)result,result<0?saved:0);
    errno=saved;return result;
}
int execvp(const char *path, char *const argv[]) {
    int incoming=errno;
    int (*real)(const char *,char *const [])=dlsym(RTLD_NEXT,"execvp");
    if (!real) {errno=ENOSYS;return -1;}
    fprintf(stderr,"[ideck-mac-process] execvp executable=%s\n",ExecKind(path));
    errno=incoming;int result=real(path,argv),saved=errno;
    fprintf(stderr,"[ideck-mac-process] execvp returned=%d errno=%d\n",result,saved);
    errno=saved;return result;
}
