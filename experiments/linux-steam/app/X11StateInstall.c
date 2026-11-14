/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "X11StateInstall.h"
#include "kernel/calls.h"
#include "kernel/task.h"
#include "fs/fd.h"
#include "fs/path.h"
#include <stdint.h>
#include <stdlib.h>
#include <stdatomic.h>
#include <string.h>
static void *owned_bytes;
static size_t owned_size;
static _Atomic int prepared;
static int valid(const void *bytes,size_t size){
    if(!bytes||size<64||size>262144)return 0;
    const unsigned char *e=bytes;
    return !memcmp(e,"\177ELF",4)&&e[4]==2&&e[5]==1&&e[6]==1&&e[16]==2&&e[17]==0&&e[18]==183&&e[19]==0;
}
int ideck_x11_state_configure(const void *bytes,size_t size){
    if(!valid(bytes,size))return -22;
    void *copy=malloc(size);if(!copy)return -12;memcpy(copy,bytes,size);
    int expected=0;
    if(!atomic_compare_exchange_strong(&prepared,&expected,1)){free(copy);return -16;}
    owned_bytes=copy;owned_size=size;atomic_store_explicit(&prepared,2,memory_order_release);return 0;
}
static int matches(const char *path){
    struct statbuf st;int result=generic_statat(AT_PWD,path,&st,false);
    if(result<0||!S_ISREG(st.mode)||(uint64_t)st.size!=owned_size||(st.mode&0777)!=0700)return -17;
    struct fd *fd=generic_open(path,O_RDONLY_|O_NOFOLLOW_,0);if(IS_ERR(fd))return -17;
    unsigned char buffer[4096];size_t offset=0;int error=0;
    while(offset<owned_size){size_t size=owned_size-offset;if(size>sizeof buffer)size=sizeof buffer;
        ssize_t n=fd->ops->read(fd,buffer,size);if(n<=0||(size_t)n>size||memcmp(buffer,(char *)owned_bytes+offset,(size_t)n)){error=-17;break;}offset+=(size_t)n;}
    int closed=fd_close(fd);return error?error:closed<0?closed:0;
}
static int install(void){
    struct statbuf st;int result=generic_statat(AT_PWD,IDECK_X11_STATE_BASE,&st,false);
    if(result==-2){result=generic_mkdirat(AT_PWD,IDECK_X11_STATE_BASE,0755);if(result<0)return result;result=generic_statat(AT_PWD,IDECK_X11_STATE_BASE,&st,false);}
    if(result<0)return result;if(!S_ISDIR(st.mode))return -20;
    result=generic_statat(AT_PWD,IDECK_X11_STATE_STAGE,&st,false);if(!result)return -17;if(result!=-2)return result;
    result=generic_statat(AT_PWD,IDECK_X11_STATE_FILE,&st,false);if(!result)return matches(IDECK_X11_STATE_FILE);if(result!=-2)return result;
    struct fd *fd=generic_open(IDECK_X11_STATE_STAGE,O_WRONLY_|O_CREAT_|O_EXCL_|O_NOFOLLOW_,0600);
    if(IS_ERR(fd))return (int)PTR_ERR(fd);
    size_t offset=0;int error=0;
    while(offset<owned_size){ssize_t n=fd->ops->write(fd,(char *)owned_bytes+offset,owned_size-offset);
        if(n<=0||(size_t)n>owned_size-offset){error=n<0?(int)n:-5;break;}offset+=(size_t)n;}
    int closed=fd_close(fd);if(!error&&closed<0)error=closed;
    if(!error)error=generic_setattrat(AT_PWD,IDECK_X11_STATE_STAGE,make_attr(mode,S_IFREG|0700),false);
    if(!error)error=matches(IDECK_X11_STATE_STAGE);
    if(!error)error=generic_linkat(AT_PWD,IDECK_X11_STATE_STAGE,AT_PWD,IDECK_X11_STATE_FILE);
    int removed=generic_unlinkat(AT_PWD,IDECK_X11_STATE_STAGE);if(!error&&removed<0)error=removed;
    return error?error:matches(IDECK_X11_STATE_FILE);
}
int ideck_x11_state_install_prepared(void){
    if(!current||current->pid!=1)return -16;
    int expected=2;
    if(!atomic_compare_exchange_strong_explicit(&prepared,&expected,3,memory_order_acq_rel,memory_order_acquire))return -22;
    int result=install();free(owned_bytes);owned_bytes=NULL;owned_size=0;return result;
}
