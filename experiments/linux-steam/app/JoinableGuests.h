/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_JOINABLE_GUESTS_H
#define IDECK_JOINABLE_GUESTS_H
#include <pthread.h>
#include <stdint.h>
/* Prototype for tracked CHILD guest pthreads only. Initial runtime thread,
 * timers, TTY, native forwarders, signals, mappings and global state are outside
 * this registry. All registered children joined is NOT Linux quiescence, a
 * Wine permission or a runtime-reset certificate. Not linked into the app.
 *
 * One native lifetime. Initialize/seal/join on the same host owner thread.
 * start() accepts JOINABLE attributes and follows positive pthread errno.
 * Other APIs return native negative errno. No detach, cancel, reset or timeout
 * workaround: a blocked join remains pending. Caller supplies a bounded
 * external observer and must preserve a still-running join.
 */
int ideck_joinable_guests_initialize(void);
int ideck_joinable_guest_start(pthread_t *thread,const pthread_attr_t *attributes,
                             void *(*entry)(void *),void *argument);
int ideck_joinable_guests_seal(void);
int ideck_joinable_guests_join(void);
struct ideck_joinable_guests_snapshot {
    unsigned slots,capacity,joined,sealed,joining;
    uint64_t rejected;
    int error,all_registered_children_joined;
};
int ideck_joinable_guests_snapshot(struct ideck_joinable_guests_snapshot *out);
#endif
