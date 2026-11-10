/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Appended ONLY to an explicitly selected COPY of pinned guest_profile.c.
 * Original profiler buffers are visible in this translation unit. No guest
 * strings, profile contents/addresses or paths are logged by these APIs.
 */
static int ideck_profile_guest_boundary(void) {
    int error=ideck_worker_joins_owner_check();if(error)return error;
    if(strcmp(ideck_linux_lab_stage(),"guest-exited")||ideck_linux_lab_live_guest_threads()!=0)return -EAGAIN;
    struct ideck_joinable_guests_snapshot guests;
    error=ideck_joinable_guests_snapshot(&guests);if(error)return error;
    if(!guests.all_registered_children_joined)return -EAGAIN;
    struct ideck_worker_joins_snapshot workers;
    error=ideck_worker_joins_snapshot(&workers);if(error)return error;
    return workers.sealed?0:-EAGAIN;
}
int ideck_joined_profile_request_stop(void) {
    int error=ideck_profile_guest_boundary();if(error)return error;
    atomic_store_explicit(&ideck_profile_stopping,1,memory_order_release);
    return 0;
}
int ideck_joined_profile_release_buffers(void) {
    int error=ideck_profile_guest_boundary();if(error)return error;
    struct ideck_worker_joins_snapshot workers;
    error=ideck_worker_joins_snapshot(&workers);if(error)return error;
    if(!workers.all_tracked_worker_threads_joined||!atomic_load_explicit(&ideck_profile_stopping,memory_order_acquire))return -EAGAIN;
    if(atomic_load(&ideck_profile_started)&&!atomic_load(&ideck_profile_completed))return -EAGAIN;
    pthread_mutex_lock(&profile_lock);
    /* Do not hide a producer leak by disabling registration first. */
    for(unsigned i=0;i<PROFILE_SLOTS;i++)if(slots[i].tlb){pthread_mutex_unlock(&profile_lock);return -EBUSY;}
    guest_profile_enabled=false;
    free(table);table=NULL;
    for(unsigned i=0;i<PROFILE_PIDS;i++){free(maps_cache[i]);maps_cache[i]=NULL;maps_size[i]=0;seen_pids[i]=0;}
    seen_count=0;profile_path=NULL;
    atomic_store_explicit(&ideck_profile_released,1,memory_order_release);
    pthread_mutex_unlock(&profile_lock);return 0;
}
int ideck_joined_profile_snapshot(struct ideck_joined_profile_snapshot *out) {
    if(!out)return -EINVAL;
    int error=ideck_worker_joins_owner_check();if(error)return error;
    *out=(struct ideck_joined_profile_snapshot){.stop_requested=atomic_load(&ideck_profile_stopping),.sampler_started=atomic_load(&ideck_profile_started),
        .sampler_completed=atomic_load(&ideck_profile_completed),.buffers_released=atomic_load(&ideck_profile_released)};
    struct ideck_worker_joins_snapshot workers;
    error=ideck_worker_joins_snapshot(&workers);if(error)return error;
    /* dump() writes maps_cache outside profile_lock. Read allocations ONLY
     * after real worker/TLS completion, never from the completed flag alone. */
    if(workers.all_tracked_worker_threads_joined){
        uint64_t bytes=table?(uint64_t)sizeof *table*PROFILE_TABLE:0;
        for(unsigned i=0;i<PROFILE_PIDS;i++)if(maps_cache[i]){
            if(UINT64_MAX-bytes<maps_size[i])return -EOVERFLOW;bytes+=maps_size[i];
        }
        out->logical_retained_bytes=bytes;out->retained_bytes_known=1;
    }
    return 0;
}
