/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Host only one-shot allocation fault for the real copied engine. */
#if defined(__ENVIRONMENT_IPHONE_OS_VERSION_MIN_REQUIRED__)
#error HOST allocation injection forbidden on iOS
#endif
#include "LinuxLabRuntime.h"
#include "NativeKernelLog.h"
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <stdatomic.h>
extern _Atomic uint64_t ideck_fiber_hash_growth_failures;
extern _Atomic uint64_t asbestos_stat_cap_flushes;
static unsigned failures,growths;
void *ideck_hash_test_calloc(size_t n,size_t size){
    if(n>1024){growths++;if(!failures){failures++;return NULL;}}
    return calloc(n,size);
}
int main(int argc,char **argv){
    assert(argc==3&&!ideck_native_log_start(argv[2]));int result=ideck_linux_lab_run(argv[1]);
    printf("HOST real engine guest wait=%d injected=%u growth_attempts=%u guarded_failures=%llu actual_cap_flushes=%llu\n",result,failures,growths,(unsigned long long)atomic_load(&ideck_fiber_hash_growth_failures),(unsigned long long)atomic_load(&asbestos_stat_cap_flushes));
    assert(!result&&failures==1&&growths>=2&&atomic_load(&ideck_fiber_hash_growth_failures)==1&&atomic_load(&asbestos_stat_cap_flushes)>0);
    return 0;
}
