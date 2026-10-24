/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * Keep implicit keyed events local to each isolated Wine pseudo-process.
 * Original Wine source retains its own copyright/licensing through inclusion. */
#define NtWaitForKeyedEvent ios_original_NtWaitForKeyedEvent
#define NtReleaseKeyedEvent ios_original_NtReleaseKeyedEvent
#include "../../wine/dlls/ntdll/unix/sync.c"
#undef NtWaitForKeyedEvent
#undef NtReleaseKeyedEvent
#include <pthread.h>

/* Native globals are shared by iOS pseudo-processes, but server handles are
 * process-local. Never pass the main process default handle into a child.
 * Entries live for this bounded lab session; Wine closes handles on process
 * exit. Do not reuse entries for other identities or fall back on exhaustion. */
static pthread_mutex_t ios_keyed_lock = PTHREAD_MUTEX_INITIALIZER;
static struct { PEB *peb; HANDLE pid, event; } ios_keyed_processes[128];
static NTSTATUS ios_keyed_resolve(HANDLE *handle)
{
    const char *lab = getenv("MADEIRA_STEAM_UI_SESSION");
    TEB *teb; unsigned i; NTSTATUS status=STATUS_NO_MEMORY;
    if (*handle || !lab || strcmp(lab,"1")) return STATUS_SUCCESS;
    teb=NtCurrentTeb();
    pthread_mutex_lock(&ios_keyed_lock);
    for(i=0;i<128;i++) {
        if(ios_keyed_processes[i].peb==teb->Peb &&
           ios_keyed_processes[i].pid==teb->ClientId.UniqueProcess) {
            *handle=ios_keyed_processes[i].event;status=STATUS_SUCCESS;break;
        }
        if(!ios_keyed_processes[i].peb) {
            status=NtCreateKeyedEvent(handle,GENERIC_READ|GENERIC_WRITE,NULL,0);
            if(!status) {
                ios_keyed_processes[i].peb=teb->Peb;
                ios_keyed_processes[i].pid=teb->ClientId.UniqueProcess;
                ios_keyed_processes[i].event=*handle;
                dprintf(2,"[steam-ui-keyed-event-local] pid=%04x ready\n",
                        (unsigned)(ULONG_PTR)teb->ClientId.UniqueProcess);
            }
            break;
        }
    }
    pthread_mutex_unlock(&ios_keyed_lock);
    return status;
}

static void ios_keyed_observe(HANDLE requested, NTSTATUS status, const char *operation)
{
    const char *lab = getenv("MADEIRA_STEAM_UI_SESSION");
    static unsigned samples;
    if (!requested && (status & 0x80000000U) && lab && !strcmp(lab,"1") &&
        __atomic_fetch_add(&samples,1,__ATOMIC_RELAXED)<32)
        dprintf(2,"[steam-ui-keyed-event] op=%s status=%08x pid=%04x default_handle=%p\n",
                operation,(unsigned)status,(unsigned)(ULONG_PTR)NtCurrentTeb()->ClientId.UniqueProcess,keyed_event);
}
NTSTATUS WINAPI NtWaitForKeyedEvent(HANDLE h,const void *key,BOOLEAN alertable,const LARGE_INTEGER *timeout)
{
    HANDLE requested=h;
    NTSTATUS status=ios_keyed_resolve(&h);
    if(!status) status=ios_original_NtWaitForKeyedEvent(h,key,alertable,timeout);
    ios_keyed_observe(requested,status,"wait");return status;
}
NTSTATUS WINAPI NtReleaseKeyedEvent(HANDLE h,const void *key,BOOLEAN alertable,const LARGE_INTEGER *timeout)
{
    HANDLE requested=h;
    NTSTATUS status=ios_keyed_resolve(&h);
    if(!status) status=ios_original_NtReleaseKeyedEvent(h,key,alertable,timeout);
    ios_keyed_observe(requested,status,"release");return status;
}
