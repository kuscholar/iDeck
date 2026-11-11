/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_RETAINED_FRONTEND_H
#define IDECK_RETAINED_FRONTEND_H
#include "ToolInstall.h"
enum ideck_frontend_phase { IDECK_FRONTEND_UNUSED,IDECK_FRONTEND_PREPARING,
    IDECK_FRONTEND_RUNNING,IDECK_FRONTEND_DRAINING,IDECK_FRONTEND_DORMANT,IDECK_FRONTEND_POISONED };
struct ideck_frontend_result {unsigned wave,reaped;int guest_status,error,phase;};
struct ideck_frontend_transport_boundary {
    int embedded; /* 0: no in-process viewer. 1: mandatory drain callback. */
    int (*drain)(void *context,int guest_status);
    void *context;
};
/* Explicit prototype only. All calls to run belong to ONE native pthread for
 * this process lifetime. Root must match after first claim. No reset/remount or
 * cross-thread retry. Nonzero native error poisons the lifetime; no forced join.
 * DORMANT means tracked backend threads joined/PIDs reaped/signals restored,
 * NOT native viewer/GPU/storage/Wine permission. Caller coordinates those.
 */
/* Embedded viewer drain runs on owner after guest/native joins/reap, BEFORE
 * signal restoration. It must wait for actual transport completion without
 * blocking main. Failure poisons the lifetime. Bind the same boundary on every
 * wave; do not substitute a counter or timeout for its native completion. */
int ideck_retained_frontend_run(const char *root,const struct ideck_tool_payload *,
    const struct ideck_frontend_transport_boundary *,struct ideck_frontend_result *);
int ideck_retained_frontend_snapshot(struct ideck_frontend_result *);
#endif
