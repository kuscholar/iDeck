/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST ONLY: real own unlinked file and real Darwin mappings, explicit refusal
 * injection tests contract/ownership, not actual iPad address-space capacity. */
#include "VAHeadroomProbe.h"
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
static const char *kind;static unsigned maps,unmaps,logs;static char last[512];
static void *owned_reservation,*owned_trial;static size_t trial_bytes;
void ideck_native_log_line(const char *s){assert(strlen(s)<sizeof last);strcpy(last,s);logs++;}
void *ideck_va_test_mmap(void *a,size_t n,int p,int f,int d,off_t o){
    assert(!a && !(f&MAP_FIXED));maps++;
    if(maps==1){assert(n==IDECK_VA_HEADROOM_BYTES&&p==PROT_NONE&&d==-1);
        if(!strcmp(kind,"prepare-fail")){errno=ENOMEM;return MAP_FAILED;}
    }else{assert(maps==2&&n==65536&&p==(PROT_READ|PROT_WRITE)&&f==MAP_SHARED&&d>=0&&o==0);
        if(!strcmp(kind,"trial-fail")){errno=ENOMEM;return MAP_FAILED;}
    }
    void *v=mmap(a,n,p,f,d,o);assert(v!=MAP_FAILED);
    if(maps==1)owned_reservation=v;else{owned_trial=v;trial_bytes=n;}return v;
}
int ideck_va_test_munmap(void *p,size_t n){
    unmaps++;
    if(unmaps==1){assert(p==owned_reservation&&n==IDECK_VA_HEADROOM_BYTES);
        if(!strcmp(kind,"release-fail")){errno=EINVAL;return -1;}
    }else{assert(unmaps==2&&p==owned_trial&&n==trial_bytes);
        if(!strcmp(kind,"cleanup-fail")){errno=EINVAL;return -1;}
    }
    return munmap(p,n);
}
static int fd;
static void *concurrent(void *x){(void)x;ideck_va_headroom_probe(fd,65536,0,PROT_READ|PROT_WRITE,MAP_SHARED,ENOMEM);return NULL;}
int main(int argc,char **argv){
    assert(argc==3);kind=argv[1];char file[1024];assert(snprintf(file,sizeof file,"%s/own-file",argv[2])<(int)sizeof file);
    fd=open(file,O_CREAT|O_EXCL|O_RDWR,0600);assert(fd>=0&&!unlink(file)&&!ftruncate(fd,65536));
    errno=EDOM;
    if(!strcmp(kind,"not-prepared")){
        concurrent(NULL);assert(!maps&&!unmaps&&!logs&&errno==EDOM);close(fd);return 0;
    }
    int r=ideck_va_headroom_prepare();assert(errno==EDOM&&maps==1&&logs==1);
    assert(ideck_va_headroom_prepare()==-EBUSY&&maps==1&&errno==EDOM);
    if(!strcmp(kind,"prepare-fail")){assert(r==-ENOMEM);concurrent(NULL);assert(maps==1&&!unmaps);close(fd);return 0;}
    assert(!r);unsigned pre=logs;
    ideck_va_headroom_probe(fd,65536,0,PROT_READ,MAP_SHARED,ENOMEM);
    ideck_va_headroom_probe(fd,65536,1,PROT_READ|PROT_WRITE,MAP_SHARED,ENOMEM);
    ideck_va_headroom_probe(fd,65536,0,PROT_READ|PROT_WRITE,MAP_PRIVATE,ENOMEM);
    ideck_va_headroom_probe(fd,IDECK_VA_HEADROOM_BYTES+1,0,PROT_READ|PROT_WRITE,MAP_SHARED,ENOMEM);
    ideck_va_headroom_probe(fd,0,0,PROT_READ|PROT_WRITE,MAP_SHARED,ENOMEM);
    ideck_va_headroom_probe(fd,65536,0,PROT_READ|PROT_WRITE,MAP_SHARED,EINVAL);
    ideck_va_headroom_probe(-1,65536,0,PROT_READ|PROT_WRITE,MAP_SHARED,ENOMEM);
    int pipes[2];assert(!pipe(pipes));
    ideck_va_headroom_probe(pipes[0],65536,0,PROT_READ|PROT_WRITE,MAP_SHARED,ENOMEM);
    close(pipes[0]);close(pipes[1]);
    int closed=dup(fd);assert(closed>=0);assert(!close(closed));
    ideck_va_headroom_probe(closed,65536,0,PROT_READ|PROT_WRITE,MAP_SHARED,ENOMEM);
    assert(errno==EDOM&&logs==pre&&maps==1&&!unmaps);
    if(!strcmp(kind,"shrunk")){assert(!ftruncate(fd,0));concurrent(NULL);assert(logs==pre&&maps==1&&!unmaps);assert(!munmap(owned_reservation,IDECK_VA_HEADROOM_BYTES));close(fd);return 0;}
    if(!strcmp(kind,"concurrent")){
        pthread_t threads[16];for(unsigned i=0;i<16;i++)assert(!pthread_create(&threads[i],NULL,concurrent,NULL));
        for(unsigned i=0;i<16;i++)assert(!pthread_join(threads[i],NULL));
    }else concurrent(NULL);
    assert(logs==2&&strstr(last,"original_result_preserved=1")&&strstr(last,"fixed_address=0"));
    unsigned m=maps,u=unmaps;concurrent(NULL);assert(maps==m&&unmaps==u&&logs==2&&errno==EDOM);
    if(!strcmp(kind,"release-fail")){assert(maps==1&&unmaps==1&&strstr(last,"reservation_released=0"));assert(!munmap(owned_reservation,IDECK_VA_HEADROOM_BYTES));}
    else if(!strcmp(kind,"trial-fail")){assert(maps==2&&unmaps==1&&strstr(last,"fresh_mapping=0"));}
    else{assert(maps==2&&unmaps==2&&strstr(last,"fresh_mapping=1"));
        if(!strcmp(kind,"cleanup-fail")){assert(strstr(last,"trial_released=0"));assert(!munmap(owned_trial,trial_bytes));}
        else assert(strstr(last,"trial_released=1"));
    }
    close(fd);puts("HOST owned PROT_NONE release/new OS-selected file mapping/once/error/refusal/concurrency PASS; NOT Air capacity proof");return 0;
}
