/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "SharedFileReserve.h"
#include <sys/mman.h>
#include <sys/stat.h>
#include <pthread.h>
#include <unistd.h>
#include <errno.h>
#include <stdint.h>
#include <stdatomic.h>
#include <string.h>
#if IDECK_FILE_RESERVE_HOST_INJECTION
#if defined(__ENVIRONMENT_IPHONE_OS_VERSION_MIN_REQUIRED__)
#error Host injection must never be compiled into an iOS artifact
#endif
extern void *ideck_file_reserve_test_map(void *, size_t, int, int, int, off_t);
extern int ideck_file_reserve_test_unmap(void *, size_t);
#define own_map ideck_file_reserve_test_map
#define own_unmap ideck_file_reserve_test_unmap
#else
#define own_map mmap
#define own_unmap munmap
#endif

enum { FRESH, READY, POISONED, DRAINED, SUSPENDED };
enum { FREE, HEAD, TAIL, QUARANTINED };
enum { MAX_SLOTS = IDECK_FILE_RESERVE_BYTES / 4096u };
static pthread_mutex_t gate = PTHREAD_MUTEX_INITIALIZER;
static unsigned char *base;
static _Atomic uintptr_t published_base;
static unsigned char occupied[MAX_SLOTS];
static size_t lengths[MAX_SLOTS];
static unsigned spans[MAX_SLOTS];
static struct ideck_file_reserve_stats stats;
static uint64_t suspension;

int ideck_file_reserve_prepare(void) {
    int saved = errno, error = 0;
    pthread_mutex_lock(&gate);
    if (stats.state != FRESH) { error = -EBUSY; goto done; }
    long page = sysconf(_SC_PAGESIZE);
    if (page < 4096 || page > 65536 || (page & (page - 1)) ||
        IDECK_FILE_RESERVE_BYTES % (size_t)page) {
        stats.state = POISONED; error = -EINVAL; goto done;
    }
    stats.page_bytes = (size_t)page;
    stats.slots = IDECK_FILE_RESERVE_BYTES / (unsigned)page;
    void *p = own_map(NULL, IDECK_FILE_RESERVE_BYTES, PROT_NONE,
                     MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) {
        stats.state = POISONED; error = -(errno ? errno : ENOMEM); goto done;
    }
    base = p; stats.state = READY;
    atomic_store_explicit(&published_base, (uintptr_t)base, memory_order_release);
done:
    pthread_mutex_unlock(&gate); errno = saved; return error;
}

void *ideck_file_reserve_after_enomem(int fd, size_t bytes, off_t offset,
                                     int prot, int flags, int original_errno) {
    int saved = errno;
    void *result = MAP_FAILED;
    if (original_errno != ENOMEM || fd < 0 || !bytes ||
        bytes > IDECK_FILE_RESERVE_BYTES || offset ||
        prot != (PROT_READ | PROT_WRITE) || flags != MAP_SHARED) goto finish;
    struct stat file;
    if (fstat(fd, &file) || !S_ISREG(file.st_mode) || file.st_size < 0 ||
        (uint64_t)file.st_size < bytes) goto finish;
    pthread_mutex_lock(&gate);
    if (stats.state != READY || bytes % stats.page_bytes) goto unlock;
    stats.attempts++;
    unsigned needed = (unsigned)(bytes / stats.page_bytes), first = 0, run = 0;
    for (unsigned i = 0; i < stats.slots; i++) {
        if (occupied[i] != FREE) { run = 0; continue; }
        if (!run) first = i;
        if (++run == needed) break;
    }
    if (run != needed) { stats.capacity_refusals++; goto unlock; }
    /* The selected span is still our original PROT_NONE reservation. The
     * address is derived solely from that owned base, never a guest hint. */
    void *selected = base + (size_t)first * stats.page_bytes;
    void *mapped = own_map(selected, bytes, prot, flags | MAP_FIXED, fd, 0);
    if (mapped != selected) {
        /* On failure the OS may not guarantee preservation of the old span.
         * Never restore over an unknown mapping or expose/reuse this address. */
        memset(occupied + first, QUARANTINED, needed);
        stats.quarantined += needed; stats.map_failures++;
        stats.state = POISONED; goto unlock;
    }
    occupied[first] = HEAD;
    if (needed > 1) memset(occupied + first + 1, TAIL, needed - 1);
    lengths[first] = bytes; spans[first] = needed;
    stats.live++; stats.live_bytes += bytes; stats.mapped++;
    if (stats.live_bytes > stats.peak_bytes) stats.peak_bytes = stats.live_bytes;
    result = mapped;
unlock:
    pthread_mutex_unlock(&gate);
finish:
    errno = saved; return result;
}

int ideck_file_reserve_release(void *pointer, size_t bytes) {
    int saved = errno, result = 0;
    uintptr_t address = (uintptr_t)pointer;
    uintptr_t published = atomic_load_explicit(&published_base, memory_order_acquire);
    if (!published || address < published ||
        address - published >= IDECK_FILE_RESERVE_BYTES) return 0;
    pthread_mutex_lock(&gate);
    uintptr_t first = (uintptr_t)base;
    if (!base || address < first || address - first >= IDECK_FILE_RESERVE_BYTES)
        goto done;
    size_t delta = address - first;
    unsigned index = (unsigned)(delta / stats.page_bytes);
    if (stats.state == SUSPENDED) {
        /* A release after the boundary contradicts quiescence. Keep the
         * owned range reserved and refuse resumption for this lifetime. */
        stats.invalid_releases++;
        stats.state = POISONED;
        result = -EINVAL;
        goto done;
    }
    if (stats.state == DRAINED || delta % stats.page_bytes ||
        occupied[index] != HEAD || lengths[index] != bytes) {
        stats.invalid_releases++; result = -EINVAL; goto done;
    }
    unsigned count = spans[index];
    /* The last Linux backing reference has ended. Replace exactly our LIVE
     * span with an empty owned reservation, releasing the file backing while
     * retaining contiguous VA for later allocations. Never zero the file. */
    void *empty = own_map(pointer, bytes, PROT_NONE,
                         MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED, -1, 0);
    stats.live--; stats.live_bytes -= bytes;
    lengths[index] = 0; spans[index] = 0;
    if (empty != pointer) {
        memset(occupied + index, QUARANTINED, count);
        stats.quarantined += count; stats.release_failures++;
        stats.state = POISONED; result = -EIO;
    } else {
        memset(occupied + index, FREE, count);
        stats.released++; result = 1;
    }
done:
    pthread_mutex_unlock(&gate); errno = saved; return result;
}

int ideck_file_reserve_snapshot(struct ideck_file_reserve_stats *out) {
    if (!out) return -EINVAL;
    if (pthread_mutex_trylock(&gate)) return -EBUSY;
    *out = stats;
    pthread_mutex_unlock(&gate); return 0;
}

int ideck_file_reserve_suspend(uint64_t *token) {
    if (!token) return -EINVAL;
    *token = 0;
    pthread_mutex_lock(&gate);
    int error = 0;
    if (stats.state != READY || stats.live || stats.quarantined) {
        error = -EBUSY;
    } else if (suspension == UINT64_MAX) {
        error = -EOVERFLOW;
    } else {
        stats.state = SUSPENDED;
        *token = ++suspension;
    }
    pthread_mutex_unlock(&gate);
    return error;
}

int ideck_file_reserve_resume(uint64_t token) {
    if (!token) return -EINVAL;
    pthread_mutex_lock(&gate);
    int error = 0;
    if (stats.state != SUSPENDED) {
        error = -EBUSY;
    } else if (token != suspension) {
        error = -ESTALE;
    } else {
        stats.state = READY;
    }
    pthread_mutex_unlock(&gate);
    return error;
}

int ideck_file_reserve_drain(void) {
    int saved = errno, error = 0;
    pthread_mutex_lock(&gate);
    if (stats.state != READY || stats.live || stats.quarantined) {
        error = -EBUSY; goto done;
    }
    if (own_unmap(base, IDECK_FILE_RESERVE_BYTES)) {
        stats.state = POISONED; error = -(errno ? errno : EIO); goto done;
    }
    stats.state = DRAINED;
done:
    pthread_mutex_unlock(&gate); errno = saved; return error;
}
const char *ideck_file_reserve_marker(void) {
    return "IDECK_SHARED_FILE_RESERVE_V1";
}
