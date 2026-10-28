// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Does unmodified MH_EXECUTE Helper support standard in-process dlopen? No entry
// call, PID virtualization, argv/env mutation, helper conversion or CEF patch.
#import <Foundation/Foundation.h>
#import <dlfcn.h>
#import <stdio.h>
#import <stdlib.h>
#import <string.h>
#import <unistd.h>
__attribute__((constructor)) static void HelperLoadProbe(void) {
    const char *setting=getenv("IDeckNativeHelperLoadProbe");if(!setting || strcmp(setting,"1"))return;
    @autoreleasepool {
        NSString *root=[[NSBundle mainBundle] bundlePath];
        NSString *path=[root stringByAppendingPathComponent:@"Mac/Contents/Frameworks/Steam Helper.app/Contents/MacOS/Steam Helper"];
        fputs("[ideck-helper-load] begin=1 entry-called=0 filetype-unmodified=1\n",stderr);
        dlerror();void *handle=dlopen(path.fileSystemRepresentation,RTLD_NOW|RTLD_LOCAL);
        if(!handle) {
            const char *error=dlerror();
            // Fixed categorical output only. dlerror can contain container paths.
            int executable=error && (strstr(error,"main executable") || strstr(error,"MH_EXECUTE"));
            fprintf(stderr,"[ideck-helper-load] loaded=0 rejects-main-executable=%d entry-called=0 error-text=REDACTED\n",executable);
            _exit(executable?0:3);
        }
        fputs("[ideck-helper-load] loaded=1 entry-called=0 cef-status=UNVERIFIED\n",stderr);
        _exit(4); // Unexpected load is diagnostic only, never implicit success.
    }
}
