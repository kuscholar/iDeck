/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST control: a regular-global fixture is NOT the actual Wine server.
 * The real prepared iOS archive is separately qualified by relocatable link.
 */
#include "LinuxLabRuntime.h"
#include "kernel/task.h"
#include "kernel/mm.h"
#include <assert.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
extern uintptr_t *ideck_test_regular_current(void);
extern int ideck_test_current_selector(void);
static pthread_mutex_t test_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t ready = PTHREAD_COND_INITIALIZER;
static unsigned arrived;
static void *worker(void *argument) {
    assert(current == NULL);
    current = argument; /* Never dereference: independent native TLS fixture. */
    pthread_mutex_lock(&test_mutex);
    arrived++;
    pthread_cond_broadcast(&ready);
    while (arrived != 2) pthread_cond_wait(&ready, &test_mutex);
    pthread_mutex_unlock(&test_mutex);
    assert(current == argument && *ideck_test_regular_current() == UINT64_C(0x55aa11223344));
    current = NULL;
    return NULL;
}
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    assert(current == NULL && ideck_test_current_selector());
    int tokens[2]; pthread_t threads[2];
    for (unsigned i = 0; i < 2; i++) assert(!pthread_create(&threads[i], NULL, worker, &tokens[i]));
    for (unsigned i = 0; i < 2; i++) assert(!pthread_join(threads[i], NULL));
    assert(current == NULL && *ideck_test_regular_current() == UINT64_C(0x55aa11223344));
    int status = ideck_linux_lab_run(argv[1]);
    assert(!status && !current);
    lock(&pids_lock);
    struct task *init = pid_get_task(1);
    assert(init && init->mm && init->mem->mmu.asbestos);
    unsigned references = atomic_load(&init->mm->refcount);
    unsigned used = init->mem->pgdir_used;
    unlock(&pids_lock);
    printf("HOST_NAMESPACE tls_isolated=1 regular_fixture_unchanged=1 objc_selector_current=1 elf_status=%d native_init_mm_refs=%u native_init_pgdir_used=%u\n", status, references, used);
    puts("scope=HOST_NAMESPACE_AND_ELF_ONLY_NOT_ACTUAL_WINE_RUNTIME_APP_OR_IPAD");
    return 0;
}
