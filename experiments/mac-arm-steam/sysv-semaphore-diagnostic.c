// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Isolated native Steam experiment only. This is a diagnostic, not IPC emulation.
// iOS terminates the real semget syscall with SIGSYS. Report the contract and
// return ENOSYS; never fabricate a successful semaphore or ownership result.
#include <errno.h>
#include <stdio.h>
#include <sys/types.h>

__attribute__((visibility("default")))
int semget(key_t key, int count, int flags) {
    (void)key; // Do not log a possibly identifying IPC key.
    fprintf(stderr, "[ideck-mac-ipc] semget count=%d flags=0x%x result=ENOSYS\n", count, flags);
    errno = ENOSYS;
    return -1;
}
