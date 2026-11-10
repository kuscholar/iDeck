/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "X11TraceInstall.h"
#include "kernel/calls.h"
#include "kernel/task.h"
#include "fs/fd.h"
#include "fs/path.h"
#include <stdint.h>
#include <string.h>
static int valid(const struct ideck_x11_trace_payload *p){
    if(!p||!p->bytes||p->size<64||p->size>262144)return 0;
    const unsigned char *e=p->bytes;
    return !memcmp(e,"\177ELF",4)&&e[4]==2&&e[5]==1&&e[6]==1&&e[16]==3&&e[17]==0&&e[18]==183&&e[19]==0;
}
static int matches(const char *path,const struct ideck_x11_trace_payload *p){
    struct statbuf st;int result=generic_statat(AT_PWD,path,&st,false);
    if(result<0||!S_ISREG(st.mode)||(uint64_t)st.size!=p->size)return -17;
    struct fd *fd=generic_open(path,O_RDONLY_|O_NOFOLLOW_,0);if(IS_ERR(fd))return -17;
    unsigned char buffer[4096];size_t offset=0;int error=0;
    while(offset<p->size){size_t size=p->size-offset;if(size>sizeof buffer)size=sizeof buffer;
        ssize_t n=fd->ops->read(fd,buffer,size);if(n<=0||(size_t)n>size||memcmp(buffer,(const char *)p->bytes+offset,(size_t)n)){error=-17;break;}offset+=(size_t)n;}
    int closed=fd_close(fd);return error?error:closed<0?closed:0;
}
int ideck_x11_trace_install(const struct ideck_x11_trace_payload *p,int *created){
    if(created)*created=0;if(!created||!valid(p)||!current)return -22;
    if(current->pid!=1)return -16;
    struct statbuf st;int result=generic_statat(AT_PWD,IDECK_X11_TRACE_BASE,&st,false);
    if(result==-2){result=generic_mkdirat(AT_PWD,IDECK_X11_TRACE_BASE,0755);if(result<0)return result;result=generic_statat(AT_PWD,IDECK_X11_TRACE_BASE,&st,false);}
    if(result<0)return result;if(!S_ISDIR(st.mode))return -20;
    result=generic_statat(AT_PWD,IDECK_X11_TRACE_STAGE,&st,false);if(!result)return -17;if(result!=-2)return result;
    result=generic_statat(AT_PWD,IDECK_X11_TRACE_FILE,&st,false);
    if(!result)return matches(IDECK_X11_TRACE_FILE,p);if(result!=-2)return result;
    struct fd *fd=generic_open(IDECK_X11_TRACE_STAGE,O_WRONLY_|O_CREAT_|O_EXCL_|O_NOFOLLOW_,0600);
    if(IS_ERR(fd))return (int)PTR_ERR(fd);
    size_t offset=0;int error=0;
    while(offset<p->size){ssize_t n=fd->ops->write(fd,(const char *)p->bytes+offset,p->size-offset);
        if(n<=0||(size_t)n>p->size-offset){error=n<0?(int)n:-5;break;}offset+=(size_t)n;}
    int closed=fd_close(fd);if(!error&&closed<0)error=closed;
    if(!error)error=generic_setattrat(AT_PWD,IDECK_X11_TRACE_STAGE,make_attr(mode,S_IFREG|0644),false);
    if(!error)error=matches(IDECK_X11_TRACE_STAGE,p);
    // linkat atomically refuses an existing destination; generic renameat
    // could replace a target that appeared after the preflight check.
    if(!error)error=generic_linkat(AT_PWD,IDECK_X11_TRACE_STAGE,AT_PWD,IDECK_X11_TRACE_FILE);
    int removed=generic_unlinkat(AT_PWD,IDECK_X11_TRACE_STAGE);if(!error&&removed<0)error=removed;
    if(error)return error;
    if((error=matches(IDECK_X11_TRACE_FILE,p))<0)return error;
    *created=1;return 0;
}
