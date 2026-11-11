/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "NativeWorkerJoins.h"
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#if IDECK_LAB_WORKER_WAVES
static void *body(void *argument){return argument;}
static void *foreign(void *unused){(void)unused;assert(ideck_worker_joins_begin_next_wave()==-EPERM);return NULL;}
#endif
int main(void){
#if IDECK_LAB_WORKER_WAVES
    assert(ideck_worker_joins_begin_next_wave()==-ENODEV);
    assert(!ideck_worker_joins_initialize());
    for(unsigned wave=0;wave<20;wave++){
        assert(ideck_worker_joins_begin_next_wave()==-EBUSY);
        pthread_t a,b,other;void *result;
        assert(!ideck_worker_joins_start(IDECK_WORKER_TIMER,&a,NULL,body,NULL));
        assert(!ideck_worker_joins_start(IDECK_WORKER_FORWARD,&b,NULL,body,(void *)17));
        assert(!ideck_worker_joins_external(b,&result)&&result==(void *)17);
        assert(!ideck_worker_joins_seal());
        assert(ideck_worker_joins_begin_next_wave()==-EBUSY); /* Reaper not joined. */
        assert(!ideck_worker_joins_finish());
        struct ideck_worker_joins_snapshot s;assert(!ideck_worker_joins_snapshot(&s));
        assert(s.all_tracked_worker_threads_joined&&s.started==(wave+1)*2&&s.reaped==wave+1&&s.externally_joined==wave+1);
        assert(!pthread_create(&other,NULL,foreign,NULL)&&!pthread_join(other,NULL));
        if(wave<19)assert(!ideck_worker_joins_begin_next_wave());
    }
    puts("twenty-actual-worker-reaper-waves-history-and-gates=PASS");
#else
    assert(ideck_worker_joins_begin_next_wave()==-ENOTSUP);
    puts("default-worker-wave-reopen-refused=PASS");
#endif
    return 0;
}
