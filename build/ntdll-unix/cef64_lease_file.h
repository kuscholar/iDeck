/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * Bounded numeric-only experiment evidence. Never changes a VM/lease result.
 */
#ifndef IDECK_CEF64_LEASE_FILE_H
#define IDECK_CEF64_LEASE_FILE_H
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#ifndef IDECK_CEF64_LEASE_CLOCK
#define IDECK_CEF64_LEASE_CLOCK clock_gettime
#endif
#define IDECK_CEF64_LEASE_FILE_BYTES (512u * 1024u)

/* Caller supplies only numeric operation metadata, under virtual_mutex. The
 * separate mutex also makes the writer usable in a host concurrency test.
 * Each app lifetime creates its own exclusive file. Existing evidence and
 * symlinks are never overwritten. No account, command line or file payload.
 */
static void ideck_cef64_lease_file(int layout, unsigned event, unsigned slot,
                                  uint64_t owner, uint64_t base, uint64_t size,
                                  uint64_t requested, uint64_t resolved,
                                  unsigned type, unsigned status, int remaining,
                                  unsigned pid, unsigned tid)
{
    static pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
    static char path[4096];
    static dev_t device;
    static ino_t inode;
    static unsigned sequence, bytes;
    static int state; /* 0 uninitialized, 1 active, -1 stopped */
    int saved_errno = errno, fd = -1;
    const char *session = getenv("MADEIRA_STEAM_UI_SESSION");
    const char *trace = getenv("MADEIRA_CEF64_LEASE_TRACE");
    const char *file = getenv("MADEIRA_CEF64_LEASE_FILE");
    const char *events[] = {"adopt", "refuse", "free"};
    if (!layout || event >= 3 || !session || strcmp(session,"1") ||
        !trace || strcmp(trace,"1") || !file || strcmp(file,"1")) goto done;
    pthread_mutex_lock(&mutex);
    if (state < 0) goto unlock;
    if (!state)
    {
        const char suffix[] = "/wine-steam64";
        const char *prefix = getenv("WINEPREFIX");
        size_t length = prefix ? strlen(prefix) : 0;
        struct timespec now;
        int n;
        state = -1; /* One creation attempt; failed diagnostics never retry. */
        if (!prefix || prefix[0] != '/' || length < sizeof(suffix)-1 ||
            strcmp(prefix + length - (sizeof(suffix)-1),suffix) ||
            strstr(prefix,"/../") || strstr(prefix,"/./") ||
            IDECK_CEF64_LEASE_CLOCK(CLOCK_REALTIME,&now) || now.tv_sec < 0 ||
            now.tv_nsec < 0 || now.tv_nsec >= 1000000000) goto unlock;
        n = snprintf(path,sizeof(path),"%s/drive_c/ideck-cef64-leases-%ld-%" PRIu64 "-%ld.txt",
                     prefix,(long)getpid(),(uint64_t)now.tv_sec,now.tv_nsec);
        if (n < 0 || (size_t)n >= sizeof(path)) goto unlock;
        fd = open(path,O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC|O_NOFOLLOW,0600);
        if (fd < 0) goto unlock;
        struct stat st;
        if (fstat(fd,&st) || !S_ISREG(st.st_mode) || st.st_nlink != 1)
            goto stop;
        device = st.st_dev; inode = st.st_ino; state = 1;
    }
    else
    {
        fd = open(path,O_WRONLY|O_APPEND|O_CLOEXEC|O_NOFOLLOW);
        if (fd < 0) { state = -1; goto unlock; }
        struct stat st;
        if (fstat(fd,&st) || !S_ISREG(st.st_mode) || st.st_nlink != 1 ||
            st.st_dev != device || st.st_ino != inode || st.st_size != bytes)
            goto stop; /* Refuse replacements, external appends or truncation. */
    }
    char line[384];
    struct timespec monotonic = {0};
    if (IDECK_CEF64_LEASE_CLOCK(CLOCK_MONOTONIC,&monotonic)) goto stop;
    int n = snprintf(line,sizeof(line),
        "{\"seq\":%u,\"seconds\":%" PRIu64 ",\"nanos\":%ld,\"event\":\"%s\",\"slot\":%u,"
        "\"owner\":\"0x%" PRIx64 "\",\"base\":\"0x%" PRIx64 "\",\"size\":\"0x%" PRIx64 "\","
        "\"requested\":\"0x%" PRIx64 "\",\"resolved\":\"0x%" PRIx64 "\",\"type\":\"0x%x\","
        "\"status\":\"0x%x\",\"remaining\":%d,\"pid\":%u,\"tid\":%u}\n",
        sequence+1,(uint64_t)monotonic.tv_sec,monotonic.tv_nsec,events[event],slot,
        owner,base,size,requested,resolved,type,status,remaining,pid,tid);
    if (n < 0 || (size_t)n >= sizeof(line)) goto stop;
    if (sequence >= 4096 || (unsigned)n > IDECK_CEF64_LEASE_FILE_BYTES - bytes - 64)
    {
        static const char footer[] = "{\"event\":\"budget-exhausted\",\"complete\":false}\n";
        (void)write(fd,footer,sizeof(footer)-1);
        goto stop;
    }
    /* One bounded write. Any partial/error result ends evidence collection;
     * never retry an operation or affect the original VM status. */
    if (write(fd,line,(size_t)n) != n) goto stop;
    bytes += (unsigned)n; sequence++;
    close(fd); fd = -1;
    goto unlock;
stop:
    state = -1;
    if (fd >= 0) close(fd);
unlock:
    pthread_mutex_unlock(&mutex);
done:
    errno = saved_errno;
}
#endif
