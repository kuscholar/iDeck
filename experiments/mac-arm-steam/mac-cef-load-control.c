// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Host control ONLY. No cef_initialize, Steam main, authentication or UI.
#include <ctype.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

static int HashIsPublicFingerprint(const char* text) {
    if (!text) return 0;
    for (unsigned i=0;i<40;++i)
        if (!isxdigit((unsigned char)text[i])) return 0;
    return text[40]=='\0';
}
int main(int argc,char** argv) {
    if (argc!=2) {fputs("usage: mac-cef-load-control /private/official/CEF\n",stderr);return 1;}
    fputs("[ideck-mac-cef-control] host-only=1 load=begin cef-initialized=0\n",stderr);
    void* handle=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
    if (!handle) {
        const char* error=dlerror();
        fprintf(stderr,"[ideck-mac-cef-control] loaded=0 missing-image=%d signing-category=%d error-text=REDACTED\n",
            error && (strstr(error,"image not found") || strstr(error,"no such file")),
            error && (strstr(error,"signature") || strstr(error,"not permitted")));
        return 2;
    }
    int (*version)(int)=(int(*)(int))dlsym(handle,"cef_version_info");
    const char* (*hash)(int)=(const char*(*)(int))dlsym(handle,"cef_api_hash");
    if (!version || !hash) {fputs("[ideck-mac-cef-control] exports=missing\n",stderr);return 3;}
    const char* platform=hash(0);const char* universal=hash(1);
    if (!HashIsPublicFingerprint(platform) || !HashIsPublicFingerprint(universal)) {
        fputs("[ideck-mac-cef-control] metadata=unsupported\n",stderr);return 4;
    }
    fprintf(stderr,"[ideck-mac-cef-control] loaded=1 cef=%d.%d.%d chromium=%d.%d.%d.%d platform=%s universal=%s cef-initialized=0 browser=0\n",
        version(0),version(1),version(2),version(4),version(5),version(6),version(7),platform,universal);
    // Deliberately do not invoke any CEF lifecycle API or unload an initialized
    // framework. The ordinary host process exit reclaims the load-only control.
    return 0;
}
