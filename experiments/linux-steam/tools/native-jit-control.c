/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST-only qualification of the pinned optional ARM64 emitter. */
#if defined(__ENVIRONMENT_IPHONE_OS_VERSION_MIN_REQUIRED__)
#error This host control must not activate code generation on an iOS device
#endif
#ifndef ISH_JIT
#error Compile adapters with the same optional engine layout
#endif
#include "LinuxLabRuntime.h"
#include "asbestos/guest-arm64/jit.h"
#include "platform/native_fault.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

int main(int argc,char **argv) {
    assert(argc==3);
    int expect_native=!strcmp(argv[2],"native");
    assert(expect_native||!strcmp(argv[2],"interpreter"));
    if(expect_native)assert(ish_app_native_fault_install()==0);
    struct timespec begin,end;
    assert(!clock_gettime(CLOCK_MONOTONIC,&begin));
    int status=ideck_linux_lab_run(argv[1]);
    assert(!clock_gettime(CLOCK_MONOTONIC,&end));
    uint64_t blocks=0,segments=0,bytes=0;
    jit_counters(&blocks,&segments,&bytes);
    char description[2048];
    size_t length=jit_describe(description,sizeof description);
    assert(length<sizeof description);
    description[length]=0;
    printf("guest_status=%d blocks=%llu segments=%llu code_bytes=%llu elapsed_ns=%llu\n%s\n",
        status,(unsigned long long)blocks,(unsigned long long)segments,(unsigned long long)bytes,
        (unsigned long long)((end.tv_sec-begin.tv_sec)*1000000000LL+end.tv_nsec-begin.tv_nsec),description);
    assert(status==0);
    if(expect_native)assert(blocks>0&&segments>0&&bytes>0&&strstr(description,"mode: JIT"));
    else assert(blocks==0&&segments==0&&bytes==0);
    assert(ideck_linux_lab_run(argv[1])==-16);
    return 0;
}
