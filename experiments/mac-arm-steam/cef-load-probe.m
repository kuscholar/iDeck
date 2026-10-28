// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Next discriminator ONLY: can normal signed dyld load the genuine retargeted
// CEF framework in this host? No authentication, browser creation or fake PID.
#import <Foundation/Foundation.h>
#import <dlfcn.h>
#import <limits.h>
#import <stdint.h>
#import <stdio.h>
#import <stdlib.h>
#import <string.h>
#import <unistd.h>
__attribute__((constructor)) static void CEFLoadProbe(void) {
    const char *enabled=getenv("IDeckCEFLoadProbe");
    if (!enabled || strcmp(enabled,"1")!=0) return;
    @autoreleasepool {
        void *system=dlopen("/usr/lib/libSystem.B.dylib",RTLD_LAZY);
        int (*pathfn)(char *,uint32_t *)=dlsym(system,"_NSGetExecutablePath");
        char raw[PATH_MAX];uint32_t size=sizeof raw;
        if (!pathfn || pathfn(raw,&size)!=0) {fprintf(stderr,"[ideck-mac-cef-probe] setup=failed\n");_exit(2);}
        NSString *root=[@(raw) stringByDeletingLastPathComponent];
        NSString *path=[root stringByAppendingPathComponent:@"Mac/Contents/Frameworks/Chromium Embedded Framework.framework/Chromium Embedded Framework"];
        fprintf(stderr,"[ideck-mac-cef-probe] load=begin\n");
        dlerror();void *cef=dlopen(path.fileSystemRepresentation,RTLD_NOW|RTLD_LOCAL);
        if (!cef) {const char *error=dlerror();fprintf(stderr,"[ideck-mac-cef-probe] load=failed error=%.1024s\n",error?error:"unknown");_exit(3);}
        const char *names[]={"cef_initialize","cef_execute_process","cef_run_message_loop","cef_browser_host_create_browser"};
        int complete=1;
        for(unsigned i=0;i<sizeof names/sizeof names[0];++i) {
            int present=dlsym(cef,names[i])!=NULL;complete &= present;
            fprintf(stderr,"[ideck-mac-cef-probe] export=%s present=%d\n",names[i],present);
        }
        fprintf(stderr,"[ideck-mac-cef-probe] load=complete exports=%d initialization=NOT_ATTEMPTED\n",complete);
        // Explicit diagnostic session ends here; never run Steam main afterwards.
        _exit(complete?0:4);
    }
}
