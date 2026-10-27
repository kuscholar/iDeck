// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Experimental, process-local System V semaphore subset for native Steam on iOS.
// This does not provide OS process isolation or cross-process IPC. Never use it
// as proof that a native Steam Helper process can run on iOS.
#include <sys/types.h>
#include <sys/ipc.h>
#include <sys/sem.h>
#include <errno.h>
#include <limits.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdio.h>
#include <unistd.h>

#define SLOTS 128
#define MAX_OPS 32
#define MAX_VALUE 32767
struct slot { int active, generation, id, value, negative_waiters, zero_waiters; key_t key; };
static struct slot slots[SLOTS];
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t changed = PTHREAD_COND_INITIALIZER;
static struct slot *lookup(int id) {
    if (id < SLOTS) return NULL;
    struct slot *s = &slots[id % SLOTS];
    return s->active && s->id == id ? s : NULL;
}
static int fail(int error) { errno = error; return -1; }
int semget(key_t key, int count, int flags) {
    if (count < 0 || count > 1 || (flags & ~(IPC_CREAT | IPC_EXCL | 0777))) return fail(EINVAL);
    pthread_mutex_lock(&lock);
    if (key != IPC_PRIVATE) for (int i = 0; i < SLOTS; ++i) {
        struct slot *s = &slots[i];
        if (!s->active || s->key != key) continue;
        if ((flags & IPC_CREAT) && (flags & IPC_EXCL)) { pthread_mutex_unlock(&lock); return fail(EEXIST); }
        int id = s->id; pthread_mutex_unlock(&lock); return id;
    }
    if (key != IPC_PRIVATE && !(flags & IPC_CREAT)) { pthread_mutex_unlock(&lock); return fail(ENOENT); }
    if (count != 1) { pthread_mutex_unlock(&lock); return fail(EINVAL); }
    for (int i = 0; i < SLOTS; ++i) {
        struct slot *s = &slots[i];
        // A removed slot cannot be reused while old waiters still reference it.
        if (s->active || s->negative_waiters || s->zero_waiters || s->generation >= INT_MAX / SLOTS - 1) continue;
        s->generation++; s->id = s->generation * SLOTS + i; s->key = key; s->value = 0; s->active = 1;
        int id = s->id; pthread_mutex_unlock(&lock);
        fprintf(stderr, "[ideck-mac-ipc] semget local=1 count=1 flags=0x%x\n", flags);
        return id;
    }
    pthread_mutex_unlock(&lock); return fail(ENOSPC);
}
int semctl(int id, int number, int command, ...) {
    int value = 0;
    if (command == SETVAL) { va_list ap; va_start(ap, command); union semun arg = va_arg(ap, union semun); va_end(ap); value = arg.val; }
    pthread_mutex_lock(&lock);
    struct slot *s = lookup(id);
    if (!s) { pthread_mutex_unlock(&lock); return fail(EINVAL); }
    if (number != 0 && command != IPC_RMID) { pthread_mutex_unlock(&lock); return fail(EINVAL); }
    int result;
    switch (command) {
    case IPC_RMID: s->active = 0; pthread_cond_broadcast(&changed); result = 0; break;
    case SETVAL:
        if (value < 0 || value > MAX_VALUE) { pthread_mutex_unlock(&lock); return fail(ERANGE); }
        s->value = value; pthread_cond_broadcast(&changed); result = 0; break;
    case GETVAL: result = s->value; break;
    case GETPID: result = getpid(); break;
    case GETNCNT: result = s->negative_waiters; break;
    case GETZCNT: result = s->zero_waiters; break;
    default:
        pthread_mutex_unlock(&lock);
        fprintf(stderr, "[ideck-mac-ipc] semctl unsupported-command=%d\n", command);
        return fail(ENOSYS);
    }
    pthread_mutex_unlock(&lock); return result;
}
int semop(int id, struct sembuf *operations, size_t count) {
    if (!operations || count == 0 || count > MAX_OPS) return fail(EINVAL);
    struct sembuf ops[MAX_OPS];
    for (size_t i = 0; i < count; ++i) {
        ops[i] = operations[i];
        if (ops[i].sem_num != 0) return fail(EFBIG);
        if (ops[i].sem_flg & ~(IPC_NOWAIT | SEM_UNDO)) {
            fprintf(stderr, "[ideck-mac-ipc] semop unsupported-flags=0x%x\n", (unsigned short)ops[i].sem_flg);
            return fail(ENOSYS);
        }
    }
    // SEM_UNDO is scoped to the single hosting OS process, not a pthread.
    // All these process-local objects cease to exist at that process's exit;
    // no surviving process can observe a restored value. No fork, cross-process
    // sharing or pseudo-process identity is implemented by this registry.
    int old_cancel;
    pthread_setcancelstate(PTHREAD_CANCEL_DISABLE, &old_cancel);
    pthread_mutex_lock(&lock);
    int result = -1, error = EINVAL;
    struct slot *s = lookup(id);
    if (!s) goto done;
    for (;;) {
        if (!s->active || s->id != id) { error = EIDRM; break; }
        int value = s->value, blocked = 0;
        for (size_t i = 0; i < count; ++i) {
            int next = value + ops[i].sem_op;
            if (next > MAX_VALUE) { error = ERANGE; goto done; }
            if ((!ops[i].sem_op && value != 0) || next < 0) {
                if (ops[i].sem_flg & IPC_NOWAIT) { error = EAGAIN; goto done; }
                blocked = ops[i].sem_op == 0 ? 2 : 1; break;
            }
            value = next;
        }
        if (!blocked) { s->value = value; pthread_cond_broadcast(&changed); result = 0; break; }
        int *waiters = blocked == 1 ? &s->negative_waiters : &s->zero_waiters;
        (*waiters)++; int status = pthread_cond_wait(&changed, &lock); (*waiters)--;
        if (status) { error = status; break; }
    }
done:
    pthread_mutex_unlock(&lock);
    pthread_setcancelstate(old_cancel, NULL);
    return result == 0 ? 0 : fail(error);
}
