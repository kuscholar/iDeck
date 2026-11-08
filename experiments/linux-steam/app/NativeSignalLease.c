/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "NativeSignalLease.h"
#include <errno.h>
#include <pthread.h>
#include <signal.h>
#include <stdlib.h>

enum lease_state { CAPTURED, OWNED, RELEASED, POISONED };
struct ideck_signal_lease {
    pthread_t owner;
    enum lease_state state;
    void (*expected_usr1)(int);
    struct sigaction previous[2], owned[2];
};
static const int signals[2]={SIGUSR1,SIGPIPE};
static int same_action(const struct sigaction *a,const struct sigaction *b) {
    if(a->sa_flags!=b->sa_flags)return 0;
    if(a->sa_flags&SA_SIGINFO) {
        if(a->sa_sigaction!=b->sa_sigaction)return 0;
    } else if(a->sa_handler!=b->sa_handler)return 0;
    for(int sig=1;sig<NSIG;sig++)
        if(sigismember(&a->sa_mask,sig)!=sigismember(&b->sa_mask,sig))return 0;
    return 1;
}
static int owner(struct ideck_signal_lease *lease) {
    if(!lease)return -EINVAL;
    return pthread_equal(lease->owner,pthread_self())?0:-EPERM;
}
struct ideck_signal_lease *ideck_signal_lease_capture(void (*expected_usr1)(int)) {
    if(!expected_usr1||expected_usr1==SIG_IGN||expected_usr1==SIG_ERR){errno=EINVAL;return NULL;}
    struct ideck_signal_lease *lease=calloc(1,sizeof *lease);
    if(!lease)return NULL;
    lease->owner=pthread_self();lease->expected_usr1=expected_usr1;
    for(unsigned i=0;i<2;i++)if(sigaction(signals[i],NULL,&lease->previous[i])){
        int saved=errno;free(lease);errno=saved;return NULL;
    }
    if(!(lease->previous[0].sa_flags&SA_SIGINFO)&&lease->previous[0].sa_handler==expected_usr1){
        free(lease);errno=EBUSY;return NULL;
    }
    return lease;
}
int ideck_signal_lease_claim(struct ideck_signal_lease *lease) {
    int error=owner(lease);if(error)return error;
    if(lease->state!=CAPTURED)return -EBUSY;
    for(unsigned i=0;i<2;i++)if(sigaction(signals[i],NULL,&lease->owned[i])){
        lease->state=POISONED;return -errno;
    }
    if((lease->owned[0].sa_flags&SA_SIGINFO)||lease->owned[0].sa_handler!=lease->expected_usr1||
       (lease->owned[1].sa_flags&SA_SIGINFO)||lease->owned[1].sa_handler!=SIG_IGN){
        lease->state=POISONED;return -ESTALE;
    }
    lease->state=OWNED;return 0;
}
int ideck_signal_lease_release(struct ideck_signal_lease *lease,const struct ideck_signal_quiescence *proof) {
    int error=owner(lease);if(error)return error;
    if(lease->state!=OWNED)return -EBUSY;
    if(!proof)return -EINVAL;
    if(proof->runtime_call_returned!=1||proof->future_guest_starts_disabled!=1||
       proof->guest_tasks!=0||proof->native_guest_entries!=0||proof->other_native_workers!=0)return -EAGAIN;
    /* Read BOTH owners before changing either. A pointer match without mask/
     * flags comparison would miss a foreign policy using the same handler. */
    struct sigaction now[2];
    for(unsigned i=0;i<2;i++){
        if(sigaction(signals[i],NULL,&now[i])){lease->state=POISONED;return -errno;}
        if(!same_action(&now[i],&lease->owned[i])){lease->state=POISONED;return -ESTALE;}
    }
    /* No retry/forced overwrite after errors. Partial restoration poisons the
     * lease and can never grant a clean-handoff result. */
    for(unsigned i=0;i<2;i++)if(sigaction(signals[i],&lease->previous[i],NULL)){
        lease->state=POISONED;return -errno;
    }
    for(unsigned i=0;i<2;i++){
        if(sigaction(signals[i],NULL,&now[i])){lease->state=POISONED;return -errno;}
        if(!same_action(&now[i],&lease->previous[i])){lease->state=POISONED;return -ESTALE;}
    }
    lease->state=RELEASED;return 0;
}
int ideck_signal_lease_destroy(struct ideck_signal_lease *lease) {
    int error=owner(lease);if(error)return error;
    if(lease->state==CAPTURED||lease->state==OWNED)return -EBUSY;
    free(lease);return 0;
}
