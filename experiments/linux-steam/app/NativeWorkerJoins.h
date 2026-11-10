/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_NATIVE_WORKER_JOINS_H
#define IDECK_NATIVE_WORKER_JOINS_H
#include "NativeWorkers.h"
#include <stdint.h>
/* Isolated prototype, not enabled/linked by the app. TIMER/PROFILE/TTY workers
 * become joinable and an owned reaper joins after their bodies finish; slots
 * are reusable ONLY after actual pthread_join (including TLS). FORWARD keeps
 * its original owner, which must use join_external() rather than double-join.
 * No cancel/detach/reset; finish can remain blocked on live/TLS-held workers.
 * All tracked joins is NOT full Linux teardown or permission to launch Wine.
 */
int ideck_worker_joins_initialize(void);
int ideck_worker_joins_start(enum ideck_worker_kind,pthread_t *,const pthread_attr_t *,void *(*)(void *),void *);
int ideck_worker_joins_external(pthread_t,void **);
/* Initialize/seal/finish are restricted to one native owner thread/lifetime. */
int ideck_worker_joins_seal(void);
int ideck_worker_joins_finish(void);
struct ideck_worker_joins_snapshot {
    uint64_t started,reaped,externally_joined,rejected;
    unsigned capacity,active,managed,external,joining,sealed,reaper_started,reaper_joined;
    int error,all_tracked_worker_threads_joined;
};
int ideck_worker_joins_snapshot(struct ideck_worker_joins_snapshot *);
#endif
