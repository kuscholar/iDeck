/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#ifndef IDECK_JOINED_PROFILE_H
#define IDECK_JOINED_PROFILE_H
#include <stdint.h>
/* Explicit copied-archive prototype only. Same native serial owner as worker
 * joins, after actual initial call/child joins and closure of worker starts.
 * Stop request is not completion; release requires actual worker joins and no
 * remaining registered profiler producers. No reset/new profiling lifetime.
 */
int ideck_joined_profile_request_stop(void);
int ideck_joined_profile_release_buffers(void);
struct ideck_joined_profile_snapshot {
    unsigned stop_requested,sampler_started,sampler_completed,buffers_released;
    int retained_bytes_known;
    uint64_t logical_retained_bytes; /* allocations, NOT physical memory/FPS */
};
int ideck_joined_profile_snapshot(struct ideck_joined_profile_snapshot *);
#endif
