/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Native lock-order discriminator around an extracted REAL pinned CASP helper.
 * The memory-translation shim models the actual mm read->write CoW upgrade;
 * it is NOT the Linux MM implementation, ARM64 gadget or a device test.
 */
#include <assert.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint64_t addr_t;
typedef pthread_mutex_t lock_t;
#define LOCK_INITIALIZER PTHREAD_MUTEX_INITIALIZER
#define __no_instrument
struct tlb {int unused;};
static lock_t pair_atomic_lock=LOCK_INITIALIZER;
static pthread_rwlock_t mm=PTHREAD_RWLOCK_INITIALIZER;
static pthread_mutex_t schedule=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t changed=PTHREAD_COND_INITIALIZER;
static int model,lookup_started,peer_attempted,invalid;
static _Thread_local int participant,translated;
static _Alignas(16) unsigned char storage[16];
static void lock(lock_t *mutex){
    if(model&&participant==2){
        assert(!pthread_mutex_lock(&schedule));peer_attempted=1;
        puts("peer-attempts-pair-lock-while-mm-read-held");
        assert(!pthread_cond_broadcast(&changed));assert(!pthread_mutex_unlock(&schedule));
    }
    assert(!pthread_mutex_lock(mutex));
}
static void unlock(lock_t *mutex){assert(!pthread_mutex_unlock(mutex));}
static void *__tlb_write_ptr(struct tlb *tlb,addr_t address){
    (void)tlb;
    if(invalid||address<0x1000||address>=0x1010)return NULL;
    if(model&&participant==1&&!translated++){
        assert(!pthread_mutex_lock(&schedule));lookup_started=1;
        puts("cow-lookup-enters-with-mm-read-held");assert(!pthread_cond_broadcast(&changed));
        while(!peer_attempted)assert(!pthread_cond_wait(&changed,&schedule));
        assert(!pthread_mutex_unlock(&schedule));
        /* Match mem_ptr: drop current mm reader, acquire writer for CoW,
         * then reacquire reader before returning a host write pointer. */
        assert(!pthread_rwlock_unlock(&mm));puts("cow-upgrade-waits-for-mm-writer");
        assert(!pthread_rwlock_wrlock(&mm));assert(!pthread_rwlock_unlock(&mm));
        assert(!pthread_rwlock_rdlock(&mm));puts("cow-upgrade-returned");
    }
    return storage+(address-0x1000);
}
/* The builder inserts the complete exact function; do not mirror its logic. */
#include "CaspFunction.inc"
static uint64_t old[2][2];static int result[2];
static void *worker(void *argument){
    participant=(int)(intptr_t)argument;
    if(participant==2){
        assert(!pthread_mutex_lock(&schedule));
        while(!lookup_started)assert(!pthread_cond_wait(&changed,&schedule));
        assert(!pthread_mutex_unlock(&schedule));
    }
    assert(!pthread_rwlock_rdlock(&mm));
    struct tlb tlb={0};old[participant-1][0]=1;old[participant-1][1]=2;
    result[participant-1]=c_casp_pair(&tlb,0x1000,&old[participant-1][0],&old[participant-1][1],9,10,3);
    assert(!pthread_rwlock_unlock(&mm));return NULL;
}
static void semantics(void){
    struct tlb tlb={0};uint64_t pair[2]={1,2};memcpy(storage,pair,sizeof pair);
    uint64_t lo=1,hi=2;assert(!c_casp_pair(&tlb,0x1000,&lo,&hi,9,10,3));
    memcpy(pair,storage,sizeof pair);assert(lo==1&&hi==2&&pair[0]==9&&pair[1]==10);
    lo=1;hi=2;assert(!c_casp_pair(&tlb,0x1000,&lo,&hi,11,12,3));
    memcpy(pair,storage,sizeof pair);assert(lo==9&&hi==10&&pair[0]==9&&pair[1]==10);
    uint32_t short_pair[2]={21,22};memcpy(storage,short_pair,sizeof short_pair);
    lo=21;hi=22;assert(!c_casp_pair(&tlb,0x1000,&lo,&hi,31,32,2));
    memcpy(short_pair,storage,sizeof short_pair);assert(lo==21&&hi==22&&short_pair[0]==31&&short_pair[1]==32);
    lo=21;hi=22;assert(!c_casp_pair(&tlb,0x1000,&lo,&hi,41,42,2));
    memcpy(short_pair,storage,sizeof short_pair);assert(lo==31&&hi==32&&short_pair[0]==31&&short_pair[1]==32);
    invalid=1;assert(c_casp_pair(&tlb,0x1000,&lo,&hi,0,0,3)==-1);invalid=0;
    assert(c_casp_pair(&tlb,0x1001,&lo,&hi,0,0,3)==-1);
    assert(c_casp_pair(&tlb,0x1000,&lo,&hi,0,0,0)==-1);
    puts("serial-32-64-writeback-mismatch-fault-cases=PASS");
}
int main(int argc,char **argv){
    setbuf(stdout,NULL);if(argc!=2)return 2;
    if(!strcmp(argv[1],"semantics")){semantics();return 0;}
    if(strcmp(argv[1],"order"))return 2;
    model=1;uint64_t pair[2]={1,2};memcpy(storage,pair,sizeof pair);
    pthread_t a,b;assert(!pthread_create(&a,NULL,worker,(void *)(intptr_t)1));
    assert(!pthread_create(&b,NULL,worker,(void *)(intptr_t)2));
    assert(!pthread_join(a,NULL)&&!pthread_join(b,NULL));
    assert(!result[0]&&!result[1]);memcpy(pair,storage,sizeof pair);
    assert(pair[0]==9&&pair[1]==10&&old[0][0]==9&&old[0][1]==10&&old[1][0]==1&&old[1][1]==2);
    puts("native-lock-order-model=PASS");return 0;
}
