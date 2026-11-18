/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "LinuxLabRuntime.h"
#include "NativeKernelLog.h"
#include "CowBackingBroker.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
extern uint64_t ideck_private_discard_count(void);
int main(int argc,char **argv){
    assert(argc==3&&!ideck_native_log_start(argv[2]));
    int result=ideck_linux_lab_run(argv[1]);
    struct ideck_cow_broker_stats s;ideck_cow_broker_read_stats(&s);
    uint64_t discards=ideck_private_discard_count();
    printf("HOST translated guest wait=%d exclusive_discards=%llu broker_alloc=%llu release=%llu native_advice=%llu live_slots=%llu\n",result,(unsigned long long)discards,(unsigned long long)s.allocation_calls,(unsigned long long)s.release_calls,(unsigned long long)s.advice_calls,(unsigned long long)s.live_slots);
    assert(!result&&s.allocation_calls>=16&&s.release_calls>=16&&s.advice_calls>0);
#if !IDECK_METADATA_PURE_SPIN
    assert(discards>0);
#endif
    assert(ideck_linux_lab_run(argv[1])==-16);return 0;
}
