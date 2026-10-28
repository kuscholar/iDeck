// SPDX-License-Identifier: GPL-3.0-or-later
#include "launch-summary.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
int main(void) {
    char *text=NULL;size_t size=0;FILE *out=open_memstream(&text,&size);assert(out);
    const char *args[]={"/private/account-name/Steam Helper","-steamid=76561199999999999","-cachedir","/private/login/cache","--mojo-platform-channel-handle=secret-endpoint","--password=never-print-this","--single-process",NULL};
    ideck_launch_summary(out,args,8);ideck_launch_summary(out,"private text password -cachedir=secret --single-process --unknown=account-name",0);ideck_launch_summary(out,(void *)1,0x28);fclose(out);
    assert(strstr(text,"target-kind=steam-helper") && strstr(text,"switch=--single-process") && strstr(text,"lexical-switch=-cachedir"));
    assert(!strstr(text,"765611") && !strstr(text,"account-name") && !strstr(text,"/private") && !strstr(text,"secret-endpoint") && !strstr(text,"never-print-this") && !strstr(text,"private text"));
    free(text);puts("launch summary PASS: fixed switch names only; path/account/token/password/text values redacted");
}
