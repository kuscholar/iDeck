/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "LinuxLabRuntime.h"
#include "NativeKernelLog.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
extern uint64_t ideck_private_discard_count(void),ideck_private_discard_replaced_bytes(void);
int main(int argc,char **argv){
    assert(argc==3 && !ideck_native_log_start(argv[2]));
    assert(!ideck_linux_lab_run(argv[1]));
    uint64_t calls=ideck_private_discard_count(),bytes=ideck_private_discard_replaced_bytes();
    printf("HOST actual ARM64 SVC reached replacement: calls=%llu guest_bytes=%llu; NOT physical reclaimed bytes\n",(unsigned long long)calls,(unsigned long long)bytes);
    assert(calls==1 && bytes==65536);
    return 0;
}
