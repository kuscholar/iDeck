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
enum ideck_wine_server_join_state {
    IDECK_WINE_SERVER_JOIN_UNKNOWN, IDECK_WINE_SERVER_NO_HANDLE,
    IDECK_WINE_SERVER_JOINED, IDECK_WINE_SERVER_JOIN_FAILED
};
enum ideck_wine_server_main_outcome {
    IDECK_WINE_SERVER_MAIN_UNKNOWN,
    IDECK_WINE_SERVER_MAIN_RETURNED_ZERO,
    IDECK_WINE_SERVER_MAIN_RETURNED_NONZERO
};
struct ideck_wine_report_identity {
    uint64_t capture_sequence;
    char report_token[37];
};
int ideck_lab_wine_report_identity(struct ideck_wine_report_identity *,uint64_t,const char *);
int ideck_lab_wine_process_start_for_report(const char *,uint64_t,const char *);
struct ideck_wine_initial_snapshot {
    uint64_t generation;
    struct ideck_wine_report_identity report;
    unsigned phase,initial_created,initial_joined;
    int create_error,observer_error;
    unsigned body_result_source;
    uint32_t body_exit_code;
    unsigned server_join_state;
    int server_join_error;
    unsigned server_main_outcome;
};
/* Private Lab replacement for ONE initial-thread create+detach pair only.
 * The original entry/attributes are retained. An owned observer joins that
 * thread including TLS destructors. Observer failure must not masquerade as
 * failure to create a game that actually started: create still returns zero.
 * No cancellation, Wine worker tracking, signal reset or return permission.
 */
int ideck_lab_wine_initial_create(pthread_t *,const pthread_attr_t *,void *(*)(void *),void *,
                                 const struct ideck_wine_report_identity *);
int ideck_lab_wine_initial_snapshot(struct ideck_wine_initial_snapshot *);
/* Only the actual initial pthread may report once, before its body returns.
 * UNKNOWN remains distinct from zero. This is the initial Wine body result,
 * NOT proof of child-game exit, licensing, all-worker teardown or safe return. */
int ideck_lab_wine_initial_report_result(unsigned source,uint32_t code);
/* Records one observed server stop outcome from the current initial Wine
 * thread. A successful join only reports a known main result if the
 * server returned the corresponding token through pthread_join. */
int ideck_lab_wine_initial_report_server_join(int attempted,int join_error,unsigned main_outcome);
struct ideck_wine_thread_census {
    unsigned baseline_count;
    unsigned current_count;
    unsigned started_since_baseline;
};
/* Compare process-local Darwin thread IDs with the sample immediately before
 * Wine starts. Excludes the initial-thread join observer itself. ENODEV,
 * ESTALE, EBUSY or a sampling error leave no counts. Zero new threads is not
 * proof of Wine worker teardown or permission to start the Linux frontend. */
int ideck_lab_wine_thread_census(uint64_t generation, struct ideck_wine_thread_census *);
/* Early refusal before Wine mutates prefix/socket state. Zero means only that
 * this initial-thread observer is idle, never full Wine/runtime readiness. */
int ideck_lab_wine_initial_ready(void);
#endif
