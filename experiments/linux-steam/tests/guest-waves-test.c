/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "JoinableGuests.h"
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <time.h>
#if IDECK_LAB_GUEST_WAVES
static pthread_key_t key;
static pthread_mutex_t mutex=PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t changed=PTHREAD_COND_INITIALIZER;
static int tls_entered,release_tls;
static void destructor(void *unused){
    (void)unused;pthread_mutex_lock(&mutex);tls_entered=1;
    pthread_cond_broadcast(&changed);
    while(!release_tls)pthread_cond_wait(&changed,&mutex);
    pthread_mutex_unlock(&mutex);
}
static void *entry(void *unused){(void)unused;assert(!pthread_setspecific(key,(void *)1));return NULL;}
static void *foreign(void *unused){
    (void)unused;assert(ideck_joinable_guests_begin_next_wave()==-EPERM);return NULL;
}
static void *unblock(void *unused){
    (void)unused;struct ideck_joinable_guests_snapshot s;
    for(;;){
        assert(!ideck_joinable_guests_snapshot(&s));
        if(s.joining){
            assert(s.sealed&&!s.joined&&!s.all_registered_children_joined);
            pthread_mutex_lock(&mutex);assert(tls_entered);release_tls=1;
            pthread_cond_broadcast(&changed);pthread_mutex_unlock(&mutex);return NULL;
        }
        struct timespec delay={0,1000000};nanosleep(&delay,NULL);
    }
}
#endif
int main(void){
#if !IDECK_LAB_GUEST_WAVES
    assert(ideck_joinable_guests_begin_next_wave()==-ENOTSUP);
    puts("default-wave-reopen-refused=PASS");return 0;
#else
    assert(ideck_joinable_guests_begin_next_wave()==-ENODEV);
    assert(!ideck_joinable_guests_initialize());
    assert(ideck_joinable_guests_begin_next_wave()==-EBUSY);
    assert(!pthread_key_create(&key,destructor));pthread_t child,helper;
    assert(!ideck_joinable_guest_start(&child,NULL,entry,NULL));
    pthread_mutex_lock(&mutex);while(!tls_entered)pthread_cond_wait(&changed,&mutex);pthread_mutex_unlock(&mutex);
    assert(!ideck_joinable_guests_seal());
    assert(ideck_joinable_guests_begin_next_wave()==-EBUSY);
    assert(!pthread_create(&helper,NULL,foreign,NULL)&&!pthread_join(helper,NULL));
    assert(!pthread_create(&helper,NULL,unblock,NULL));
    assert(!ideck_joinable_guests_join()&&!pthread_join(helper,NULL));
    assert(!ideck_joinable_guests_begin_next_wave());
    struct ideck_joinable_guests_snapshot s;
    assert(!ideck_joinable_guests_snapshot(&s)&&s.slots==1&&s.joined==1&&!s.sealed);
    assert(!ideck_joinable_guest_start(&child,NULL,entry,NULL));
    assert(!ideck_joinable_guests_seal()&&!ideck_joinable_guests_join());
    assert(!ideck_joinable_guests_snapshot(&s)&&s.slots==2&&s.joined==2&&s.all_registered_children_joined);
    assert(s.capacity==2&&ideck_joinable_guests_begin_next_wave()==-ENOSPC);
    assert(!pthread_key_delete(key));
    puts("wave-reopen-owner-TLS-unjoined-gates-and-cumulative-capacity=PASS");return 0;
#endif
}
