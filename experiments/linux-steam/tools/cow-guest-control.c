/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST runner for the existing ARM64 lazy/protection/fork fixture. */
#include "LinuxLabRuntime.h"
#include "NativeKernelLog.h"
#include <assert.h>
#include <stdio.h>
int main(int argc,char **argv) {
    assert(argc==3 && ideck_native_log_start(argv[2])==0);
    int result=ideck_linux_lab_run(argv[1]);
    printf("HOST real ARM64 guest wait=%d stage=%s\n",result,ideck_linux_lab_stage());
    assert(result==0 && ideck_linux_lab_run(argv[1])==-16);
    return 0;
}
