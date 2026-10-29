// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
#ifndef MADEIRA_PIPE2_COMPAT_H
#define MADEIRA_PIPE2_COMPAT_H
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
/* Wine lives in-process: no native fork/exec occurs between pipe and fcntl.
 * Native iOS 27 pipe2 must not be a weak unresolved call on supported iOS 26.
 * Provide a real local implementation for all Wine archive references. */
static int madeira_pipe2_compat(int descriptors[2], int flags)
{
    int pair[2];
    if (flags & ~(O_CLOEXEC | O_NONBLOCK)) { errno = EINVAL; return -1; }
    if (!descriptors) { errno = EFAULT; return -1; }
    if (pipe(pair) == -1) return -1;
    for (int i = 0; i < 2; ++i) {
        if ((flags & O_CLOEXEC) && fcntl(pair[i], F_SETFD, FD_CLOEXEC) == -1) goto fail;
        if (flags & O_NONBLOCK) {
            int current = fcntl(pair[i], F_GETFL);
            if (current == -1 || fcntl(pair[i], F_SETFL, current | O_NONBLOCK) == -1) goto fail;
        }
    }
    descriptors[0] = pair[0]; descriptors[1] = pair[1];
    return 0;
fail: {
    int saved = errno;
    close(pair[0]); close(pair[1]); errno = saved;
    return -1;
}
}
#endif
