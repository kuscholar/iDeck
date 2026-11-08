/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "ToolInstall.h"
#include "kernel/calls.h"
#include "kernel/task.h"
#include "fs/fd.h"
#include "fs/path.h"
#include <stdint.h>
#include <string.h>
#include <stdio.h>
static const char *names[]={"ideck-madeira","compatibilitytool.vdf","toolmanifest.vdf"};
static int text(const void *data,size_t size) {
    if(!data||!size||size>4096)return 0;
    const unsigned char *p=data;
    for(size_t i=0;i<size;i++)if((p[i]<32&&p[i]!='\n'&&p[i]!='\r'&&p[i]!='\t')||p[i]>126)return 0;
    return 1;
}
static int valid(const struct ideck_tool_payload *p) {
    if(!p||!p->executable||p->executable_size<64||p->executable_size>262144)return 0;
    const unsigned char *e=p->executable;
    return !memcmp(e,"\177ELF",4)&&e[4]==2&&e[5]==1&&e[6]==1&&
        (e[16]==2||e[16]==3)&&e[17]==0&&e[18]==183&&e[19]==0&&
        text(p->compatibility,p->compatibility_size)&&text(p->manifest,p->manifest_size);
}
static int directory(const char *path,int create) {
    struct statbuf st;int r=generic_statat(AT_PWD,path,&st,false);
    if(r==-2&&create){r=generic_mkdirat(AT_PWD,path,0700);if(r<0)return r;r=generic_statat(AT_PWD,path,&st,false);}
    if(r<0)return r;return S_ISDIR(st.mode)?0:-20;
}
static int location(char *out,size_t size,const char *base,unsigned index) {
    int n=snprintf(out,size,"%s/%s",base,names[index]);return n<0||(size_t)n>=size?-36:0;
}
static int matches(const char *path,const void *data,size_t size,int executable) {
    struct statbuf st;int r=generic_statat(AT_PWD,path,&st,false);
    if(r<0||!S_ISREG(st.mode)||(uint64_t)st.size!=(uint64_t)size||(executable&&!(st.mode&0111)))return -17;
    struct fd *fd=generic_open(path,O_RDONLY_|O_NOFOLLOW_,0);if(IS_ERR(fd))return -17;
    unsigned char buffer[4096];size_t offset=0;int equal=1;
    while(offset<size){size_t count=size-offset;if(count>sizeof buffer)count=sizeof buffer;
        ssize_t n=fd->ops->read(fd,buffer,count);if(n<=0||(size_t)n>count||memcmp(buffer,(const char *)data+offset,(size_t)n)){equal=0;break;}offset+=(size_t)n;}
    int closed=fd_close(fd);return equal&&offset==size&&closed>=0?0:-17;
}
static int write_new(const char *path,const void *data,size_t size,int executable,int *created) {
    *created=0;struct fd *fd=generic_open(path,O_WRONLY_|O_CREAT_|O_EXCL_|O_NOFOLLOW_,0600);
    if(IS_ERR(fd))return (int)PTR_ERR(fd);*created=1;size_t offset=0;int error=0;
    while(offset<size){ssize_t n=fd->ops->write(fd,(const char *)data+offset,size-offset);
        if(n<0){error=(int)n;break;}if(!n||(size_t)n>size-offset){error=-5;break;}offset+=(size_t)n;}
    int closed=fd_close(fd);if(!error&&closed<0)error=closed;
    if(!error)error=generic_setattrat(AT_PWD,path,make_attr(mode,S_IFREG|(executable?0755:0644)),false);
    return error;
}
int ideck_tool_install(const struct ideck_tool_payload *p,int *created) {
    if(created)*created=0;if(!created||!current||!valid(p))return -22;
    if(current->pid!=1)return -16;
    int r=directory("/Steam",0);if(r<0)return r;
    r=directory("/Steam/compatibilitytools.d",1);if(r<0)return r;
    const void *data[]={p->executable,p->compatibility,p->manifest};
    size_t sizes[]={p->executable_size,p->compatibility_size,p->manifest_size};char path[256];
    struct statbuf st;r=generic_statat(AT_PWD,IDECK_COMPAT_TOOL_DIR,&st,false);
    if(!r){if(!S_ISDIR(st.mode))return -17;
        for(unsigned i=0;i<3;i++){if(location(path,sizeof path,IDECK_COMPAT_TOOL_DIR,i)||matches(path,data[i],sizes[i],i==0))return -17;}return 0;}
    if(r!=-2)return r;
    r=generic_mkdirat(AT_PWD,IDECK_COMPAT_TOOL_STAGE,0700);if(r<0)return r; // Never remove a pre-existing stage.
    unsigned owned=0;
    for(unsigned i=0;i<3;i++){
        r=location(path,sizeof path,IDECK_COMPAT_TOOL_STAGE,i);if(r<0)break;
        int made=0;r=write_new(path,data[i],sizes[i],i==0,&made);if(made)owned|=1u<<i;
        if(!r)r=matches(path,data[i],sizes[i],i==0);if(r<0)break;
    }
    if(!r)r=generic_renameat(AT_PWD,IDECK_COMPAT_TOOL_STAGE,AT_PWD,IDECK_COMPAT_TOOL_DIR);
    if(!r){*created=1;return 0;}
    for(unsigned i=0;i<3;i++)if((owned&(1u<<i))&&!location(path,sizeof path,IDECK_COMPAT_TOOL_STAGE,i))generic_unlinkat(AT_PWD,path);
    generic_rmdirat(AT_PWD,IDECK_COMPAT_TOOL_STAGE);return r;
}
