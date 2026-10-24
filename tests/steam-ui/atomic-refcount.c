/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * Synthetic x86-64 instruction probe; no Chromium code, Steam, network or accounts.
 * Same clear-bit CAS sequence observed before chrome_elf's refcount abort.
 * Passing does NOT validate PartitionAlloc or prove that FEX is correct in general.
 */
#include <stdint.h>
#include <stdio.h>
#ifdef _WIN32
#include <windows.h>
#define THREAD_RESULT DWORD WINAPI
#else
#include <pthread.h>
#define THREAD_RESULT void *
#endif
#define THREADS 4
#define ROUNDS 50000
static volatile uint32_t counter;
struct job { unsigned failures; uint32_t private_word; };
static struct job jobs[THREADS];
static uint32_t clear_held(volatile uint32_t *p) {
    uint32_t old, next;
    __asm__ volatile("movl %2,%0\n1: movl %0,%1\nandl $-2,%1\nlock cmpxchgl %1,%2\njne 1b"
        : "=&a"(old), "=&c"(next), "+m"(*p) : : "cc", "memory");
    return old;
}
static uint32_t cas(volatile uint32_t *p, uint32_t expected, uint32_t desired, unsigned char *equal) {
    unsigned char z;
    __asm__ volatile("lock cmpxchgl %3,%1\nsete %2"
        : "+a"(expected), "+m"(*p), "=qm"(z) : "r"(desired) : "cc", "memory");
    *equal = z; return expected;
}
static THREAD_RESULT worker(void *argument) {
    struct job *j = argument;
    for (unsigned i = 0; i < ROUNDS; ++i) {
        unsigned char equal;
        j->private_word = 5;
        uint32_t old = cas(&j->private_word, 7, 99, &equal);
        if (equal || old != 5 || j->private_word != 5) { j->failures++; break; }
        if (clear_held(&j->private_word) != 5 || j->private_word != 4) { j->failures++; break; }
        old = __atomic_load_n(&counter, __ATOMIC_RELAXED);
        do { uint32_t observed = cas(&counter, old, old+1, &equal); if (!equal) old = observed; } while (!equal);
    }
#ifdef _WIN32
    return 0;
#else
    return NULL;
#endif
}
int main(void) {
#ifdef _WIN32
    HANDLE threads[THREADS];
    for (unsigned i=0;i<THREADS;i++) {
        threads[i]=CreateThread(NULL,0,worker,&jobs[i],0,NULL);
        if (!threads[i]) { puts("atomic-probe thread-create-failed"); return 10; }
    }
    if (WaitForMultipleObjects(THREADS,threads,TRUE,30000)!=WAIT_OBJECT_0) {
        puts("atomic-probe join-failed-or-timeout"); return 11;
    }
    for (unsigned i=0;i<THREADS;i++) CloseHandle(threads[i]);
#else
    pthread_t threads[THREADS];
    for (unsigned i=0;i<THREADS;i++) if (pthread_create(&threads[i],NULL,worker,&jobs[i])) return 10;
    for (unsigned i=0;i<THREADS;i++) if (pthread_join(threads[i],NULL)) return 11;
#endif
    unsigned failures=0;
    for (unsigned i=0;i<THREADS;i++) failures+=jobs[i].failures;
    int pass=!failures && counter==THREADS*ROUNDS;
    printf("atomic-probe failures=%u counter=%u expected=%u result=%s\n",failures,(unsigned)counter,THREADS*ROUNDS,pass?"PASS":"FAIL");
    return pass?0:12;
}
