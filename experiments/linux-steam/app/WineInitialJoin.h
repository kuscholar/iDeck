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
enum ideck_wine_body_result_source {
    IDECK_WINE_BODY_RESULT_UNKNOWN,
    IDECK_WINE_BODY_NORMAL_RETURN,
    IDECK_WINE_BODY_LONGJMP
};
struct ideck_wine_initial_snapshot {
    uint64_t generation;
    unsigned phase,initial_created,initial_joined;
    int create_error,observer_error;
    unsigned body_result_source;
    uint32_t body_exit_code;
};
/* Private Lab replacement for ONE initial-thread create+detach pair only.
 * The original entry/attributes are retained. An owned observer joins that
 * thread including TLS destructors. Observer failure must not masquerade as
 * failure to create a game that actually started: create still returns zero.
 * No cancellation, Wine worker tracking, signal reset or return permission.
 */
int ideck_lab_wine_initial_create(pthread_t *,const pthread_attr_t *,void *(*)(void *),void *);
int ideck_lab_wine_initial_snapshot(struct ideck_wine_initial_snapshot *);
/* Only the actual initial pthread may report once, before its body returns.
 * UNKNOWN remains distinct from zero. This is the initial Wine body result,
 * NOT proof of child-game exit, licensing, all-worker teardown or safe return. */
int ideck_lab_wine_initial_report_result(unsigned source,uint32_t code);
/* Early refusal before Wine mutates prefix/socket state. Zero means only that
 * this initial-thread observer is idle, never full Wine/runtime readiness. */
int ideck_lab_wine_initial_ready(void);
#endif
