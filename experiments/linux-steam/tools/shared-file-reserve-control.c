/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "SharedFileReserve.h"
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <pthread.h>
#include <stdatomic.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <sched.h>

static atomic_uint calls, fixed_calls, unmap_calls;
static atomic_int fail_prepare, fail_fixed, fail_reset, fail_drain;
static atomic_int hold_fixed, fixed_entered, fixed_continue;
void *ideck_file_reserve_test_map(void *address,size_t n,int prot,int flags,int fd,off_t offset) {
    atomic_fetch_add(&calls,1);
    if(flags&MAP_FIXED)atomic_fetch_add(&fixed_calls,1);
    if((flags&MAP_FIXED)&&prot!=PROT_NONE&&atomic_exchange(&hold_fixed,0)) {
        atomic_store(&fixed_entered,1);
        while(!atomic_load(&fixed_continue))sched_yield();
    }
    if((!address&&atomic_exchange(&fail_prepare,0))||
       ((flags&MAP_FIXED)&&prot!=PROT_NONE&&atomic_exchange(&fail_fixed,0))||
       ((flags&MAP_FIXED)&&prot==PROT_NONE&&atomic_exchange(&fail_reset,0))) {
        errno=ENOMEM;return MAP_FAILED;
    }
    return mmap(address,n,prot,flags,fd,offset);
}
int ideck_file_reserve_test_unmap(void *p,size_t n) {
    atomic_fetch_add(&unmap_calls,1);
    if(atomic_exchange(&fail_drain,0)){errno=EIO;return -1;}
    return munmap(p,n);
}
static int fixture(const char *directory,const char *name) {
    char path[4096];int n=snprintf(path,sizeof path,"%s/%s",directory,name);
    assert(n>0&&(size_t)n<sizeof path);
    int fd=open(path,O_RDWR|O_CREAT|O_EXCL,0600);assert(fd>=0);
    assert(!ftruncate(fd,IDECK_FILE_RESERVE_BYTES));return fd;
}
static struct ideck_file_reserve_stats snapshot(void) {
    struct ideck_file_reserve_stats s;assert(!ideck_file_reserve_snapshot(&s));return s;
}
static void *allocate(int fd,size_t n) {
    errno=EINTR;void *p=ideck_file_reserve_after_enomem(fd,n,0,PROT_READ|PROT_WRITE,MAP_SHARED,ENOMEM);
    assert(errno==EINTR);return p;
}
static void release(void *p,size_t n) {
    errno=ERANGE;assert(ideck_file_reserve_release(p,n)==1&&errno==ERANGE);
}
static void clean_drain(void) {
    struct ideck_file_reserve_stats s=snapshot();assert(!s.live&&!s.live_bytes&&!s.quarantined);
    errno=EINTR;assert(!ideck_file_reserve_drain()&&errno==EINTR);
    assert(ideck_file_reserve_prepare()==-EBUSY);
}
struct worker {int fd;unsigned index;size_t bytes;};
static void *one_allocation(void *arg) {
    struct worker *w=arg;void *p=allocate(w->fd,w->bytes);assert(p!=MAP_FAILED);
    release(p,w->bytes);return NULL;
}
static void *worker(void *arg) {
    struct worker *w=arg;
    for(unsigned n=0;n<100;n++) {
        uint64_t value=((uint64_t)w->index<<32)|n;
        uint64_t *p=allocate(w->fd,w->bytes);assert(p!=MAP_FAILED);
        *p=value;assert(p[w->bytes/sizeof(*p)-1]==0);
        uint64_t actual=0;assert(pread(w->fd,&actual,sizeof actual,0)==sizeof actual&&actual==value);
        release(p,w->bytes);
    }
    return NULL;
}
int main(int argc,char **argv) {
    assert(argc==3);const char *mode=argv[1];
    if(!strcmp(mode,"prepare-failure")) {
        atomic_store(&fail_prepare,1);errno=ERANGE;
        assert(ideck_file_reserve_prepare()==-ENOMEM&&errno==ERANGE);
        assert(ideck_file_reserve_prepare()==-EBUSY&&!atomic_load(&fixed_calls));
        puts("HOST prepare failure preserved/terminal PASS");return 0;
    }
    assert(ideck_file_reserve_snapshot(NULL)==-EINVAL);
    errno=ERANGE;assert(!ideck_file_reserve_prepare()&&errno==ERANGE);
    struct ideck_file_reserve_stats s=snapshot();size_t page=s.page_bytes;
    assert(s.slots*page==IDECK_FILE_RESERVE_BYTES&&page>=4096&&page<=65536);
    assert(ideck_file_reserve_prepare()==-EBUSY);
    int fd=fixture(argv[2],"data.bin");
    if(!strcmp(mode,"basic")||!strcmp(mode,"closed-fd")) {
        size_t n=262144;unsigned char *p=allocate(fd,n);assert(p!=MAP_FAILED);
        unsigned char *alias=mmap(NULL,n,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);assert(alias!=MAP_FAILED);
        memset(p,0x5a,n);assert(alias[0]==0x5a&&alias[n-1]==0x5a);
        alias[page]=0xc3;assert(p[page]==0xc3);
        if(!strcmp(mode,"closed-fd")){assert(!close(fd));fd=-1;}
        release(p,n);assert(alias[0]==0x5a&&alias[page]==0xc3&&alias[n-1]==0x5a);
        assert(!munmap(alias,n));s=snapshot();assert(s.mapped==1&&s.released==1&&s.peak_bytes==n);
    } else if(!strcmp(mode,"eligibility")) {
        unsigned before=atomic_load(&fixed_calls);size_t n=262144;
        assert(ideck_file_reserve_after_enomem(fd,n,0,3,MAP_SHARED,EACCES)==MAP_FAILED);
        assert(ideck_file_reserve_after_enomem(-1,n,0,3,MAP_SHARED,ENOMEM)==MAP_FAILED);
        assert(ideck_file_reserve_after_enomem(fd,0,0,3,MAP_SHARED,ENOMEM)==MAP_FAILED);
        assert(ideck_file_reserve_after_enomem(fd,IDECK_FILE_RESERVE_BYTES+page,0,3,MAP_SHARED,ENOMEM)==MAP_FAILED);
        assert(ideck_file_reserve_after_enomem(fd,n+1,0,3,MAP_SHARED,ENOMEM)==MAP_FAILED);
        assert(ideck_file_reserve_after_enomem(fd,n,(off_t)page,3,MAP_SHARED,ENOMEM)==MAP_FAILED);
        assert(ideck_file_reserve_after_enomem(fd,n,0,PROT_READ,MAP_SHARED,ENOMEM)==MAP_FAILED);
        assert(ideck_file_reserve_after_enomem(fd,n,0,3,MAP_PRIVATE,ENOMEM)==MAP_FAILED);
        assert(ideck_file_reserve_after_enomem(fd,n,0,3,MAP_SHARED|MAP_FIXED,ENOMEM)==MAP_FAILED);
        assert(!ftruncate(fd,page));assert(allocate(fd,n)==MAP_FAILED);
        int dir=open(argv[2],O_RDONLY|O_DIRECTORY);assert(dir>=0);
        assert(allocate(dir,page)==MAP_FAILED);assert(!close(dir));
        assert(atomic_load(&fixed_calls)==before&&!snapshot().live);
    } else if(!strcmp(mode,"capacity")) {
        void *all=allocate(fd,IDECK_FILE_RESERVE_BYTES);assert(all!=MAP_FAILED);
        assert(ideck_file_reserve_drain()==-EBUSY);unsigned before=atomic_load(&fixed_calls);
        assert(allocate(fd,page)==MAP_FAILED&&atomic_load(&fixed_calls)==before);
        assert(snapshot().capacity_refusals==1);release(all,IDECK_FILE_RESERVE_BYTES);
        void *again=allocate(fd,page);assert(again==all);release(again,page);
    } else if(!strcmp(mode,"wrong-release")) {
        unsigned char *p=allocate(fd,page*2);assert(p!=MAP_FAILED);p[0]=42;
        unsigned before=atomic_load(&fixed_calls);
        assert(ideck_file_reserve_release(p+1,page*2)==-EINVAL);
        assert(ideck_file_reserve_release(p+page,page)==-EINVAL);
        assert(ideck_file_reserve_release(p,page)==-EINVAL&&p[0]==42);
        assert(atomic_load(&fixed_calls)==before&&snapshot().live==1);
        release(p,page*2);assert(ideck_file_reserve_release(p,page*2)==-EINVAL);
        void *foreign=mmap(NULL,page,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
        assert(foreign!=MAP_FAILED&&ideck_file_reserve_release(foreign,page)==0);
        *(char *)foreign=7;assert(!munmap(foreign,page));
    } else if(!strcmp(mode,"suspend")) {
        uint64_t first=0, second=0;
        assert(ideck_file_reserve_suspend(NULL)==-EINVAL);
        assert(ideck_file_reserve_resume(0)==-EINVAL);
        void *p=allocate(fd,page);assert(p!=MAP_FAILED);
        assert(ideck_file_reserve_suspend(&first)==-EBUSY&&!first);
        release(p,page);
        unsigned writes=atomic_load(&fixed_calls), unmaps=atomic_load(&unmap_calls);
        assert(!ideck_file_reserve_suspend(&first)&&first);
        assert(ideck_file_reserve_suspend(&second)==-EBUSY&&!second);
        assert(allocate(fd,page)==MAP_FAILED);
        assert(ideck_file_reserve_drain()==-EBUSY&&ideck_file_reserve_prepare()==-EBUSY);
        assert(atomic_load(&fixed_calls)==writes&&atomic_load(&unmap_calls)==unmaps);
        assert(ideck_file_reserve_resume(first+1)==-ESTALE);
        assert(!ideck_file_reserve_resume(first)&&ideck_file_reserve_resume(first)==-EBUSY);
        assert(allocate(fd,page)==p);release(p,page);
        assert(!ideck_file_reserve_suspend(&second)&&second>first);
        assert(ideck_file_reserve_resume(first)==-ESTALE&&allocate(fd,page)==MAP_FAILED);
        assert(!ideck_file_reserve_resume(second));
        assert(allocate(fd,page)==p);release(p,page);
        s=snapshot();assert(!s.live&&s.mapped==3&&s.released==3);
    } else if(!strcmp(mode,"suspend-late-release")) {
        uint64_t token=0;
        void *p=allocate(fd,page);assert(p!=MAP_FAILED);
        release(p,page);
        unsigned writes=atomic_load(&fixed_calls), unmaps=atomic_load(&unmap_calls);
        assert(!ideck_file_reserve_suspend(&token)&&token);
        assert(ideck_file_reserve_release(p,page)==-EINVAL);
        assert(ideck_file_reserve_resume(token)==-EBUSY&&allocate(fd,page)==MAP_FAILED);
        assert(ideck_file_reserve_drain()==-EBUSY&&ideck_file_reserve_prepare()==-EBUSY);
        assert(atomic_load(&fixed_calls)==writes&&atomic_load(&unmap_calls)==unmaps);
        s=snapshot();assert(s.invalid_releases==1&&!s.live&&s.released==1);
        assert(!close(fd));
        puts("HOST late release poisons suspended reserve and prevents resume PASS");return 0;
    } else if(!strcmp(mode,"concurrency")) {
        pthread_t threads[8];struct worker args[8];
        for(unsigned i=0;i<8;i++) {
            char name[32];snprintf(name,sizeof name,"worker%u.bin",i);
            args[i]=(struct worker){fixture(argv[2],name),i,page*2};
            assert(!pthread_create(&threads[i],NULL,worker,&args[i]));
        }
        for(unsigned i=0;i<8;i++){assert(!pthread_join(threads[i],NULL));assert(!close(args[i].fd));}
        s=snapshot();assert(s.mapped==800&&s.released==800&&!s.live&&!s.quarantined);
    } else if(!strcmp(mode,"snapshot-busy")) {
        pthread_t thread;struct worker w={fd,0,page};atomic_store(&hold_fixed,1);
        assert(!pthread_create(&thread,NULL,one_allocation,&w));
        while(!atomic_load(&fixed_entered))sched_yield();
        struct ideck_file_reserve_stats busy;assert(ideck_file_reserve_snapshot(&busy)==-EBUSY);
        /* Unrelated native backings never wait for the reserve mutex. */
        char ordinary;assert(ideck_file_reserve_release(&ordinary,1)==0);
        atomic_store(&fixed_continue,1);assert(!pthread_join(thread,NULL));
    } else if(!strcmp(mode,"map-failure")) {
        atomic_store(&fail_fixed,1);assert(allocate(fd,page)==MAP_FAILED);
        unsigned before=atomic_load(&fixed_calls);assert(allocate(fd,page)==MAP_FAILED&&atomic_load(&fixed_calls)==before);
        s=snapshot();assert(s.map_failures==1&&s.quarantined==1&&!s.live);
        assert(ideck_file_reserve_drain()==-EBUSY&&!atomic_load(&unmap_calls));
        uint64_t token=42;assert(ideck_file_reserve_suspend(&token)==-EBUSY&&!token);
        puts("HOST failed mapping quarantined/no retry PASS");return 0;
    } else if(!strcmp(mode,"reset-failure")) {
        void *p=allocate(fd,page);assert(p!=MAP_FAILED);atomic_store(&fail_reset,1);
        assert(ideck_file_reserve_release(p,page)==-EIO);
        unsigned before=atomic_load(&fixed_calls);assert(allocate(fd,page)==MAP_FAILED&&atomic_load(&fixed_calls)==before);
        s=snapshot();assert(s.release_failures==1&&s.quarantined==1&&!s.live);
        assert(ideck_file_reserve_drain()==-EBUSY&&!atomic_load(&unmap_calls));
        uint64_t token=42;assert(ideck_file_reserve_suspend(&token)==-EBUSY&&!token);
        puts("HOST failed reset quarantined/no reuse PASS");return 0;
    } else if(!strcmp(mode,"drain-failure")) {
        atomic_store(&fail_drain,1);assert(ideck_file_reserve_drain()==-EIO);
        assert(ideck_file_reserve_drain()==-EBUSY&&ideck_file_reserve_prepare()==-EBUSY);
        puts("HOST failed drain terminal PASS");return 0;
    } else assert(!"unknown test");
    if(fd>=0)assert(!close(fd));clean_drain();
    puts("HOST real shared-file reserve ownership/semantics control PASS; NOT iOS fragmentation/UI proof");
    return 0;
}
