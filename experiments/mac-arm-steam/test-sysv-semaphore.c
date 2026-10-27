// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
#include <sys/types.h>
#include <sys/ipc.h>
#include <sys/sem.h>
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
static int waiting_id, wait_result, wait_error;
static short wait_flags;
static void *wait_for_token(void *unused) {
    (void)unused; struct sembuf op = {0, -1, wait_flags};
    wait_result = semop(waiting_id, &op, 1); wait_error = errno; return NULL;
}
static void wait_until_blocked(int id) {
    int i; for (i = 0; i < 1000000 && semctl(id, 0, GETNCNT) != 1; ++i) sched_yield();
    assert(i < 1000000);
}
int main(void) {
    assert(semget(12345, 1, 0600) == -1 && errno == ENOENT);
    int id = semget(12345, 1, IPC_CREAT | IPC_EXCL | 0600); assert(id >= 0);
    assert(semget(12345, 0, 0) == id);
    assert(semget(12345, 1, IPC_CREAT | IPC_EXCL | 0600) == -1 && errno == EEXIST);
    union semun value = {.val = 2}; assert(semctl(id, 0, SETVAL, value) == 0);
    struct sembuf batch[] = {{0,-1,0},{0,-2,IPC_NOWAIT}};
    assert(semop(id,batch,2) == -1 && errno == EAGAIN); assert(semctl(id,0,GETVAL) == 2);
    struct sembuf unsupported = {0,-1,020000}; assert(semop(id,&unsupported,1) == -1 && errno == ENOSYS);
    assert(semctl(id,0,GETVAL) == 2); value.val = 0; assert(semctl(id,0,SETVAL,value)==0);
    waiting_id=id; wait_flags=SEM_UNDO; pthread_t worker; assert(pthread_create(&worker,NULL,wait_for_token,NULL)==0);
    wait_until_blocked(id); struct sembuf give={0,1,0}; assert(semop(id,&give,1)==0);
    assert(pthread_join(worker,NULL)==0); assert(wait_result==0); assert(semctl(id,0,GETVAL)==0);
    assert(pthread_create(&worker,NULL,wait_for_token,NULL)==0); wait_until_blocked(id);
    assert(semctl(id,0,IPC_RMID)==0); assert(pthread_join(worker,NULL)==0); assert(wait_result==-1 && wait_error==EIDRM);
    int replacement=semget(IPC_PRIVATE,1,0600); assert(replacement!=id);
    assert(semctl(id,0,GETVAL)==-1 && errno==EINVAL); assert(semctl(replacement,0,IPC_RMID)==0);
    int handles[128]; for(int i=0;i<128;++i){handles[i]=semget(IPC_PRIVATE,1,0600);assert(handles[i]>=0);}
    assert(semget(IPC_PRIVATE,1,0600)==-1 && errno==ENOSPC);
    for(int i=0;i<128;++i)assert(semctl(handles[i],0,IPC_RMID)==0);
    puts("PASS process-local semaphore: atomic batch, blocking, remove wake, stale IDs, capacity, unsupported flags and thread exit without process undo");
}
