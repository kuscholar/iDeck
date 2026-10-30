// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Does unmodified MH_EXECUTE Helper support standard in-process dlopen? No entry
// call, PID virtualization, argv/env mutation, helper conversion or CEF patch.
#import <Foundation/Foundation.h>
#import <dlfcn.h>
#import <fcntl.h>
#import <limits.h>
#import <mach-o/loader.h>
#import "helper-path.h"
#import <stdio.h>
#import <stdlib.h>
#import <string.h>
#import <unistd.h>
__attribute__((constructor)) static void HelperLoadProbe(void) {
    const char *setting=getenv("IDeckNativeHelperLoadProbe");
    const char *candidate=getenv("IDeckNativeHelperBundleProbe");
    int bundle=candidate && !strcmp(candidate,"1");
    int original=setting && !strcmp(setting,"1");
    if(!bundle && !original)return;
    if(bundle && original){fputs("[ideck-helper-bundle] conflicting-probes=1\n",stderr);_exit(2);}
    @autoreleasepool {
        void *system=dlopen("/usr/lib/libSystem.B.dylib",RTLD_LAZY);
        int (*pathfn)(char *,uint32_t *)=system?dlsym(system,"_NSGetExecutablePath"):NULL;
        char raw[PATH_MAX],path[PATH_MAX];uint32_t n=sizeof raw;
        if(!pathfn || pathfn(raw,&n) || !ideck_native_helper_path(raw,path,sizeof path)) {
            fputs("[ideck-helper-load] setup=failed diagnostic-result=2 entry-called=0\n",stderr);_exit(2);
        }
        if(bundle){
            NSString *folder=[[@(raw) stringByDeletingLastPathComponent] stringByAppendingPathComponent:@"Mac/Contents/MacOS/IDeckNativeHelperLoad.bundle"];
            if(folder.length>=sizeof path){fputs("[ideck-helper-bundle] setup=failed\n",stderr);_exit(2);}
            strlcpy(path,folder.fileSystemRepresentation,sizeof path);
        }
        int fd=open(path,O_RDONLY);struct mach_header_64 header={0};
        int verified=fd>=0 && read(fd,&header,sizeof header)==sizeof header && header.magic==MH_MAGIC_64 && header.cputype==CPU_TYPE_ARM64 && header.filetype==(bundle?MH_BUNDLE:MH_EXECUTE);
        if(fd>=0)close(fd);
        if(!verified){fputs("[ideck-helper-load] preflight=failed diagnostic-result=2 entry-called=0\n",stderr);_exit(2);}
        if(bundle)fputs("[ideck-helper-bundle] begin=1 native-path=verified preflight=arm64-MH_BUNDLE entry-called=0 instructions-unchanged=1\n",stderr);
        else fputs("[ideck-helper-load] begin=1 native-path=verified preflight=arm64-MH_EXECUTE entry-called=0 filetype-unmodified=1\n",stderr);
        dlerror();void *handle=dlopen(path,RTLD_NOW|RTLD_LOCAL);
        if(!handle) {
            const char *error=dlerror();
            // Fixed categorical output only. dlerror can contain container paths.
            int executable=error && (strstr(error,"main executable") || strstr(error,"MH_EXECUTE") || strstr(error,"not a dylib") || strstr(error,"not a bundle"));
            int missing=error && (strstr(error,"no such file") || strstr(error,"image not found"));
            if(bundle){fprintf(stderr,"[ideck-helper-bundle] loaded=0 executable-category=%d missing-image=%d missing-symbol=%d entry-called=0 error-text=REDACTED\n",executable,missing,error && (strstr(error,"Symbol not found") || strstr(error,"symbol not found")));_exit(3);}
            fprintf(stderr,"[ideck-helper-load] loaded=0 rejects-main-executable=%d missing-image=%d entry-called=0 diagnostic-result=%d error-text=REDACTED\n",executable,missing,executable?0:3);
            _exit(executable?0:3);
        }
        if(bundle){fputs("[ideck-helper-bundle] loaded=1 entry-called=0 cef-initialized=0\n",stderr);_exit(0);}
        fputs("[ideck-helper-load] loaded=1 entry-called=0 cef-status=UNVERIFIED\n",stderr);
        _exit(4); // Unexpected load is diagnostic only, never implicit success.
    }
}
