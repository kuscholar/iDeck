// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
#include "launch-summary.h"
#include <string.h>
static const char *const keys[]={"-cachedir","-logdir","-steampid","-buildid","-steamid","-steampath","-clientui","-uimode","-steamuniverse","-lang","-type","--type","--single-process","--no-sandbox","--disable-gpu","--disable-gpu-compositing","--disable-software-rasterizer","--enable-features","--disable-features","--mojo-platform-channel-handle","-ipcserver","-ipcclient","-pipe","-shmem","-launcher","--shared-files","--field-trial-handle","--user-data-dir"};
void ideck_launch_summary(FILE *out,const void *command,uint32_t flags) {
    if(!out)return;
    fprintf(out,"[ideck-launch] flags=0x%x form=%s values=REDACTED\n",flags,(flags&0x18)?"argv":"text");
    if(!command || (flags&0x20))return; // Original returns before inspecting command.
    if(!(flags&0x18)) {
        // Lexical hints only, no shell execution or command reconstruction.
        const char *text=command;size_t size=strnlen(text,16384);
        if(size==16384){fprintf(out,"[ideck-launch] text-capped=1\n");return;}
        for(unsigned k=0;k<sizeof keys/sizeof keys[0];++k) {
            size_t n=strlen(keys[k]);
            for(size_t i=0;i+n<=size;++i) {
                if(i && text[i-1]!=' ' && text[i-1]!='\t' && text[i-1]!='\"')continue;
                if(!memcmp(text+i,keys[k],n) && (!text[i+n] || text[i+n]=='=' || text[i+n]==' ' || text[i+n]=='\t' || text[i+n]=='\"')) {
                    fprintf(out,"[ideck-launch] lexical-switch=%s\n",keys[k]);break;
                }
            }
        }
        return;
    }
    const char *const *args=command;unsigned count=0,unknown=0;
    const char *kind="other";
    if(args[0]) {
        size_t size=strnlen(args[0],4096);
        if(size<4096) {
            const char *base=strrchr(args[0],'/');base=base?base+1:args[0];
            if(strcmp(base,"Steam Helper")==0)kind="steam-helper";
            else if(strcmp(base,"steam_osx")==0)kind="steam-main";
        }
    }
    fprintf(out,"[ideck-launch] target-kind=%s\n",kind);
    for(;count<128 && args[count];++count) {
        if(!count)continue;
        if(strnlen(args[count],257)>256){++unknown;continue;}
        int known=0;
        for(unsigned i=0;i<sizeof keys/sizeof keys[0];++i) {
            size_t n=strlen(keys[i]);
            if(strncmp(args[count],keys[i],n)==0 && (!args[count][n] || args[count][n]=='=')) {
                fprintf(out,"[ideck-launch] switch=%s\n",keys[i]);known=1;break;
            }
        }
        if(!known)++unknown;
    }
    fprintf(out,"[ideck-launch] argument-count=%u unknown-redacted=%u capped=%d\n",count,unknown,count==128);
}
