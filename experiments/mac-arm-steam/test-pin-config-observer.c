// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
extern void IDeckObservePinConfig(const char*,int,int);
int main(void) {
    FILE* capture=tmpfile();assert(capture);int original=dup(STDERR_FILENO);
    assert(original>=0 && dup2(fileno(capture),STDERR_FILENO)>=0);
    unsetenv("IDeckNativePinProbe");errno=EAGAIN;
    IDeckObservePinConfig("steam.cfg",0,3);assert(errno==EAGAIN);
    setenv("IDeckNativePinProbe","0",1);IDeckObservePinConfig("steam.cfg",0,3);
    setenv("IDeckNativePinProbe","1",1);
    IDeckObservePinConfig("/PRIVATE_ACCOUNT/private-password.txt",0,3);
    IDeckObservePinConfig(NULL,0,-1);IDeckObservePinConfig("steam.cfg",2,3);
    fflush(stderr);assert(ftell(capture)==0);
    errno=ENOENT;IDeckObservePinConfig("/PRIVATE_ACCOUNT/steam.cfg",0,-1);assert(errno==ENOENT);
    errno=EBUSY;IDeckObservePinConfig("Steam.CFG",1,0);assert(errno==EBUSY);
    for (unsigned i=0;i<50;++i) {
        errno=ERANGE;IDeckObservePinConfig("steam.cfg",0,4);assert(errno==ERANGE);
    }
    fflush(stderr);assert(dup2(original,STDERR_FILENO)>=0);close(original);
    rewind(capture);char output[8192]={0};size_t n=fread(output,1,sizeof(output)-1,capture);assert(n>0);fclose(capture);
    assert(!strstr(output,"PRIVATE_ACCOUNT") && !strstr(output,"password"));
    assert(strstr(output,"api=open config-open=1 opened=0"));
    assert(strstr(output,"api=fopen config-open=1 opened=1 error=0"));
    unsigned lines=0;for (size_t i=0;i<n;++i)lines+=output[i]=='\n';assert(lines==32);
    puts("pin observer PASS: exact opt-in/basename/API gates, errno preserved, no private payload, bounded32 records");
    return 0;
}
