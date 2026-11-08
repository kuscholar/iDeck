/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_NATIVE_WORKERS_H
#define IDECK_NATIVE_WORKERS_H
#include <pthread.h>
enum ideck_worker_kind { IDECK_WORKER_TIMER, IDECK_WORKER_PROFILE, IDECK_WORKER_TTY, IDECK_WORKER_FORWARD, IDECK_WORKER_KINDS };
/* Copied-archive instrumentation only. Reserve BEFORE pthread_create, retire
 * only after the wrapped original body/nested cleanup or creation failure. */
int ideck_native_worker_start(enum ideck_worker_kind kind,pthread_t *thread,
    const pthread_attr_t *attributes,void *(*entry)(void *),void *argument);
void ideck_native_worker_retire_timer(void *unused);
void ideck_native_worker_retire_profile(void *unused);
void ideck_native_worker_retire_tty(void *unused);
void ideck_native_worker_retire_forward(void *unused);
/* -1 means invalid accounting, never a clean state. Counts do not prove that
 * VM/TLS/socket/Mach resources are reclaimed or that runtime restart is safe. */
int ideck_native_workers_live(enum ideck_worker_kind kind);
int ideck_native_workers_total(void);
const char *ideck_native_workers_marker(void);
#endif
