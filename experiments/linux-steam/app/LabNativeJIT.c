/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#if !IDECK_LAB_NATIVE_JIT || !defined(ISH_JIT)
#error Optional Linux emitter and adapters must have matching layouts
#endif
#include "LabNativeJIT.h"
#include "NativeKernelLog.h"
#include "platform/native_fault.h"
#include "asbestos/guest-arm64/jit.h"
#include <stdatomic.h>
#include <stdio.h>
#include <unistd.h>
static atomic_int activation_status;
__attribute__((noinline)) int ideck_lab_native_jit_prepare_classic(void) {
    /* Actual Air74 self-check fault proves attach+classic protection results
     * insufficient. Never repeat that unsafe activation in this Lab. */
    atomic_store_explicit(&activation_status,-1,memory_order_release);
    ideck_native_log_line("IDECK_LINUX_CLASSIC_JIT_DISABLED_V1 actual_Air74_protection_fault=1 guest_started=0");
    return -1;
}
#if IDECK_LAB_DEBUGGER_PREPARED_JIT
/* Native debugger data only, before first guest. No guest IPC, path or text.
 * Publish word0 LAST, after all own RX-page writes were acknowledged. */
__attribute__((used)) volatile uint64_t ideck_lab_debugger_jit_offer[5];
static atomic_bool offer_consumed;
extern int ideck_linux_jit_adopt_debugger_region(void *,size_t);
__attribute__((noinline)) int ideck_lab_native_jit_prepare_debugger(void) {
    if(atomic_exchange_explicit(&offer_consumed,true,memory_order_acq_rel))return -1;
    uint64_t magic=ideck_lab_debugger_jit_offer[0],pid=ideck_lab_debugger_jit_offer[1];
    uint64_t rx=ideck_lab_debugger_jit_offer[2],bytes=ideck_lab_debugger_jit_offer[3],pages=ideck_lab_debugger_jit_offer[4];
    ideck_lab_debugger_jit_offer[0]=0;
    int result=-1;
    if(magic==IDECK_LAB_DEBUGGER_JIT_MAGIC && pid==(uint64_t)getpid() && rx && !(rx&16383) &&
       bytes==IDECK_LAB_DEBUGGER_JIT_BYTES && pages==IDECK_LAB_DEBUGGER_JIT_BYTES/16384 && rx<=UINTPTR_MAX-bytes){
        result=ideck_linux_jit_adopt_debugger_region((void *)(uintptr_t)rx,(size_t)bytes);
        if(result==0 && ish_app_native_fault_install()!=0)result=-2;
    }
    atomic_store_explicit(&activation_status,result==0?1:-1,memory_order_release);
    char line[160];snprintf(line,sizeof line,"IDECK_LINUX_DEBUGGER_REGION_V1 result=%d TXM_breakpoint_requested=0 guest_started=0",result);
    ideck_native_log_line(line);return result;
}
#endif
void ideck_lab_native_jit_read(struct ideck_lab_native_jit_stats *stats) {
    if(!stats)return;
    stats->activation_status=atomic_load_explicit(&activation_status,memory_order_acquire);
    jit_counters(&stats->blocks,&stats->segments,&stats->code_bytes);
}
