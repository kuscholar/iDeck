/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "WindowsLaunchMap.h"
#include <string.h>
#include <errno.h>
static int convert(const char *guest,char *windows,size_t capacity) {
    static const char native[]="C:\\SteamLibrary\\steamapps\\common\\";
    size_t root=sizeof IDECK_LAUNCH_ROOT-1;
    if(strncmp(guest,IDECK_LAUNCH_ROOT,root))return -ENOTSUP;
    const char *tail=guest+root;
    size_t length=strlen(tail),base=sizeof native-1;
    if(!length||base+length>=capacity)return -ENAMETOOLONG;
    memcpy(windows,native,base);
    for(size_t i=0;i<length;i++) {
        if(strchr(":\"<>|?*",tail[i]))return -ENOTSUP;
        windows[base+i]=tail[i]=='/'?'\\':tail[i];
    }
    windows[base+length]=0;return 0;
}
int ideck_windows_launch_map(const struct ideck_launch_request *input,struct ideck_windows_launch_map *out) {
    if(!input||!out)return -EINVAL;
    struct ideck_launch_request request=*input;
    if(ideck_launch_validate(&request,sizeof request))return -EINVAL;
    size_t root=sizeof IDECK_LAUNCH_ROOT-1;
    if(strncmp(request.install,IDECK_LAUNCH_ROOT,root))return -ENOTSUP;
    const char *folder=request.install+root;size_t n=strlen(folder);
    if(!n||n>240||strchr(folder,'/')||folder[n-1]==' '||folder[n-1]=='.')return -ENOTSUP;
    struct ideck_windows_launch_map mapped={.appid=request.appid,.verb=request.verb,.argc=request.argc};
    int e=convert(request.install,mapped.install,sizeof mapped.install);if(e)return e;
    if((e=convert(request.executable,mapped.executable,sizeof mapped.executable)))return e;
    if((e=convert(request.working,mapped.working,sizeof mapped.working)))return e;
    size_t from=0,to=0;
    for(unsigned i=0;i<request.argc;i++) {
        const char *arg=request.arguments+from;size_t original=strlen(arg)+1;
        if(!strncmp(arg,IDECK_LAUNCH_ROOT,root)) {
            if((e=convert(arg,mapped.arguments+to,sizeof mapped.arguments-to)))return e;
        } else {
            if(to+original>sizeof mapped.arguments)return -E2BIG;
            memcpy(mapped.arguments+to,arg,original);
        }
        to+=strlen(mapped.arguments+to)+1;from+=original;
    }
    mapped.argument_bytes=(uint32_t)to;*out=mapped;return 0;
}
