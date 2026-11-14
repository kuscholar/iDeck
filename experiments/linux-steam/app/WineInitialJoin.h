/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_LAB_WINE_INITIAL_JOIN_H
#define IDECK_LAB_WINE_INITIAL_JOIN_H
#include <pthread.h>
#include <stdint.h>
enum ideck_wine_initial_phase {
    IDECK_WINE_INITIAL_UNUSED, IDECK_WINE_INITIAL_ACTIVE,
    IDECK_WINE_INITIAL_JOINED, IDECK_WINE_INITIAL_START_FAILED,
    IDECK_WINE_INITIAL_OBSERVER_FAILED
};
struct ideck_wine_initial_snapshot {
    uint64_t generation;
    unsigned phase,initial_created,initial_joined;
    int create_error,observer_error;
};
/* Private Lab replacement for ONE initial-thread create+detach pair only.
 * The original entry/attributes are retained. An owned observer joins that
 * thread including TLS destructors. Observer failure must not masquerade as
 * failure to create a game that actually started: create still returns zero.
 * No cancellation, Wine worker tracking, signal reset or return permission.
 */
int ideck_lab_wine_initial_create(pthread_t *,const pthread_attr_t *,void *(*)(void *),void *);
int ideck_lab_wine_initial_snapshot(struct ideck_wine_initial_snapshot *);
/* Early refusal before Wine mutates prefix/socket state. Zero means only that
 * this initial-thread observer is idle, never full Wine/runtime readiness. */
int ideck_lab_wine_initial_ready(void);
#endif
