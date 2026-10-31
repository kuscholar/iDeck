// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Fixed categorical, opt-in observations only. No paths or file contents.
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

void IDeckObservePinConfig(const char* path,int api,int result) {
    int saved=errno;
    const char* enabled=getenv("IDeckNativePinProbe");
    if (enabled && !strcmp(enabled,"1") && path && (api==0 || api==1)) {
        const char* name=strrchr(path,'/');name=name?name+1:path;
        if (!strcasecmp(name,"steam.cfg")) {
            static unsigned count;
            unsigned ordinal=__atomic_fetch_add(&count,1,__ATOMIC_RELAXED);
            if (ordinal<32)
                fprintf(stderr,"[ideck-native-pin] api=%s config-open=1 opened=%d error=%d contents=REDACTED\n",
                    api==0?"open":"fopen",result>=0,result>=0?0:saved);
        }
    }
    errno=saved;
}
