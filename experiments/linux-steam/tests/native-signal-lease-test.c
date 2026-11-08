/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Native OS signal-resource component controls; no Linux/Steam/Wine runtime. */
#include "NativeSignalLease.h"
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
static void previous_owner(int sig){(void)sig;}
static void runtime_owner(int sig){(void)sig;}
static void foreign_owner(int sig){(void)sig;}
static struct ideck_signal_quiescence complete={1,1,0,0,0};
static int same(const struct sigaction *a,const struct sigaction *b){
    if(a->sa_flags!=b->sa_flags||a->sa_handler!=b->sa_handler)return 0;
    for(int s=1;s<NSIG;s++)if(sigismember(&a->sa_mask,s)!=sigismember(&b->sa_mask,s))return 0;
    return 1;
}
static void read_pair(struct sigaction out[2]){assert(!sigaction(SIGUSR1,NULL,&out[0]));assert(!sigaction(SIGPIPE,NULL,&out[1]));}
static void check_unchanged(const struct sigaction before[2]){
    struct sigaction after[2];read_pair(after);assert(same(&before[0],&after[0])&&same(&before[1],&after[1]));
}
struct other_thread {struct ideck_signal_lease *lease;int release,claim,destroy;};
static void *wrong_owner(void *opaque){
    struct other_thread *p=opaque;p->release=ideck_signal_lease_release(p->lease,&complete);
    p->claim=ideck_signal_lease_claim(p->lease);p->destroy=ideck_signal_lease_destroy(p->lease);return NULL;
}
int main(int argc,char **argv){
    if(argc!=2)return 2;
    struct sigaction before[2],installed[2],action={0};
    action.sa_handler=previous_owner;action.sa_flags=SA_RESTART;
    sigemptyset(&action.sa_mask);sigaddset(&action.sa_mask,SIGUSR2);
    assert(!sigaction(SIGUSR1,&action,NULL)&&!sigaction(SIGPIPE,&action,NULL));read_pair(before);
    struct ideck_signal_lease *lease=ideck_signal_lease_capture(runtime_owner);assert(lease);
    assert(ideck_signal_lease_release(lease,&complete)==-EBUSY);
    assert(ideck_signal_lease_destroy(lease)==-EBUSY);check_unchanged(before);
    action.sa_handler=runtime_owner;action.sa_flags=0;sigemptyset(&action.sa_mask);sigaddset(&action.sa_mask,SIGUSR1);
    assert(!sigaction(SIGUSR1,&action,NULL));action.sa_handler=SIG_IGN;assert(!sigaction(SIGPIPE,&action,NULL));
    if(!strcmp(argv[1],"claim-conflict")){
        action.sa_handler=foreign_owner;assert(!sigaction(SIGUSR1,&action,NULL));read_pair(installed);
        assert(ideck_signal_lease_claim(lease)==-ESTALE);check_unchanged(installed);
        assert(ideck_signal_lease_release(lease,&complete)==-EBUSY);
        assert(!ideck_signal_lease_destroy(lease));puts("claim-conflict-preserved=PASS");return 0;
    }
    assert(!ideck_signal_lease_claim(lease));read_pair(installed);
    errno=0;assert(!ideck_signal_lease_capture(runtime_owner)&&errno==EBUSY);check_unchanged(installed);
    assert(ideck_signal_lease_claim(lease)==-EBUSY);
    struct other_thread other={.lease=lease};pthread_t thread;assert(!pthread_create(&thread,NULL,wrong_owner,&other));assert(!pthread_join(thread,NULL));
    assert(other.release==-EPERM&&other.claim==-EPERM&&other.destroy==-EPERM);check_unchanged(installed);
    assert(ideck_signal_lease_release(lease,NULL)==-EINVAL);check_unchanged(installed);
    for(unsigned field=0;field<5;field++)for(unsigned variant=0;variant<2;variant++){
        struct ideck_signal_quiescence proof=complete;
        int *value=field==0?&proof.runtime_call_returned:field==1?&proof.future_guest_starts_disabled:field==2?&proof.guest_tasks:field==3?&proof.native_guest_entries:&proof.other_native_workers;
        *value=field<2?(variant?2:0):(variant?1:-1);
        assert(ideck_signal_lease_release(lease,&proof)==-EAGAIN);check_unchanged(installed);
    }
    if(!strcmp(argv[1],"normal")){
        assert(!ideck_signal_lease_release(lease,&complete));check_unchanged(before);
        assert(ideck_signal_lease_release(lease,&complete)==-EBUSY);check_unchanged(before);
        assert(!ideck_signal_lease_destroy(lease));puts("exact-restore-and-gates=PASS");return 0;
    }
    if(!strcmp(argv[1],"foreign-handler"))action.sa_handler=foreign_owner;
    else if(!strcmp(argv[1],"foreign-mask"))sigaddset(&action.sa_mask,SIGUSR2);
    else if(!strcmp(argv[1],"foreign-flags"))action.sa_flags=SA_RESTART;
    else return 2;
    if(!strcmp(argv[1],"foreign-handler"))assert(!sigaction(SIGUSR1,&action,NULL));
    else { // Same Linux-owner pointer, changed mask/flags must also be refused.
        action.sa_handler=runtime_owner;assert(!sigaction(SIGUSR1,&action,NULL));
    }
    read_pair(installed);assert(ideck_signal_lease_release(lease,&complete)==-ESTALE);check_unchanged(installed);
    assert(ideck_signal_lease_release(lease,&complete)==-EBUSY);check_unchanged(installed);
    assert(!ideck_signal_lease_destroy(lease));puts("foreign-owner-preserved=PASS");return 0;
}
