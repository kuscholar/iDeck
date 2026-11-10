/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Actual fakefs/VFS; synthetic private roots, no Steam/account data. */
#include "X11TraceInstall.h"
#include "LabDeviceFS.h"
#include "kernel/init.h"
#include "kernel/calls.h"
#include "fs/real.h"
#include "fs/path.h"
#include "fs/fd.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
void restore_termios(void){}
static int failures;
static void check(const char *name,int pass){printf("%s=%s\n",name,pass?"PASS":"FAIL");if(!pass)failures++;}
static int put(const char *path,const void *body,size_t size){struct fd *f=generic_open(path,O_WRONLY_|O_CREAT_|O_TRUNC_|O_NOFOLLOW_,0600);if(IS_ERR(f))return 0;ssize_t n=f->ops->write(f,body,size);int r=fd_close(f);return n==(ssize_t)size&&r>=0;}
static int equals(const char *path,const void *bytes,size_t size){
    struct fd *f=generic_open(path,O_RDONLY_|O_NOFOLLOW_,0);if(IS_ERR(f))return 0;
    unsigned char buffer[4096];size_t offset=0;int same=1;
    while(offset<size){size_t n=size-offset;if(n>sizeof buffer)n=sizeof buffer;ssize_t got=f->ops->read(f,buffer,n);if(got<=0||(size_t)got>n||memcmp(buffer,(const char *)bytes+offset,(size_t)got)){same=0;break;}offset+=(size_t)got;}
    unsigned char extra;ssize_t tail=f->ops->read(f,&extra,1);fd_close(f);return same&&offset==size&&tail==0;
}
int main(int argc,char **argv){
    if(argc!=4)return 2;int asset=open(argv[2],O_RDONLY|O_NOFOLLOW);struct stat info;if(asset<0||fstat(asset,&info)||info.st_size<64||info.st_size>262144)return 3;
    size_t size=(size_t)info.st_size;unsigned char *bytes=malloc(size);if(!bytes)return 3;
    size_t offset=0;while(offset<size){ssize_t got=read(asset,bytes+offset,size-offset);if(got<=0)return 3;offset+=(size_t)got;}close(asset);
    struct ideck_x11_trace_payload payload={bytes,size};char root[4096];if(lab_device_fs_prepare(argv[1],root,sizeof root)||mount_root(&fakefs,root)||become_first_process())return 4;
    int created=-1;struct statbuf st;
    if(!strcmp(argv[3],"positive")){
        check("complete-trace-install",!ideck_x11_trace_install(&payload,&created)&&created==1);
        check("published-bytes-exact",equals(IDECK_X11_TRACE_FILE,bytes,size));
        check("published-one-link-readable-mode",!generic_statat(AT_PWD,IDECK_X11_TRACE_FILE,&st,false)&&S_ISREG(st.mode)&&st.nlink==1&&(st.mode&0777)==0644);
        check("owned-stage-gone",generic_statat(AT_PWD,IDECK_X11_TRACE_STAGE,&st,false)==-2);
        check("identical-existing-resource-reused",!ideck_x11_trace_install(&payload,&created)&&created==0);
    }else if(!strcmp(argv[3],"conflict")){
        if(ideck_x11_trace_install(&payload,&created)||!put(IDECK_X11_TRACE_FILE,"foreign",7)||!put(IDECK_X11_TRACE_BASE "/user-note","keep",4))return 5;
        check("existing-different-resource-refused",ideck_x11_trace_install(&payload,&created)==-17&&created==0);
        check("existing-resource-preserved",equals(IDECK_X11_TRACE_FILE,"foreign",7));check("unrelated-note-preserved",equals(IDECK_X11_TRACE_BASE "/user-note","keep",4));
    }else if(!strcmp(argv[3],"symlink")){
        if(generic_mkdirat(AT_PWD,"/foreign",0700)||!put("/foreign/note","keep",4)||generic_symlinkat("/foreign",AT_PWD,IDECK_X11_TRACE_BASE))return 5;
        check("symlink-base-refused",ideck_x11_trace_install(&payload,&created)==-20&&created==0);check("alias-target-preserved",equals("/foreign/note","keep",4));
    }else if(!strcmp(argv[3],"target-symlink")){
        if(generic_mkdirat(AT_PWD,IDECK_X11_TRACE_BASE,0755)||!put("/foreign-payload",bytes,size)||generic_symlinkat("/foreign-payload",AT_PWD,IDECK_X11_TRACE_FILE))return 5;
        check("symlink-target-refused-even-matching-bytes",ideck_x11_trace_install(&payload,&created)==-17&&created==0);check("alias-payload-preserved",equals("/foreign-payload",bytes,size));
    }else if(!strcmp(argv[3],"stale")){
        if(generic_mkdirat(AT_PWD,IDECK_X11_TRACE_BASE,0755)||!put(IDECK_X11_TRACE_STAGE,"keep",4))return 5;
        check("preexisting-stage-refused",ideck_x11_trace_install(&payload,&created)==-17&&created==0);check("stage-preserved",equals(IDECK_X11_TRACE_STAGE,"keep",4));check("no-partial-target",generic_statat(AT_PWD,IDECK_X11_TRACE_FILE,&st,false)==-2);
    }else if(!strcmp(argv[3],"published-stage")){
        if(ideck_x11_trace_install(&payload,&created)||generic_linkat(AT_PWD,IDECK_X11_TRACE_FILE,AT_PWD,IDECK_X11_TRACE_STAGE))return 5;
        check("matching-target-with-stale-alias-refused",ideck_x11_trace_install(&payload,&created)==-17&&created==0);check("both-existing-aliases-preserved",equals(IDECK_X11_TRACE_FILE,bytes,size)&&equals(IDECK_X11_TRACE_STAGE,bytes,size));
    }else if(!strcmp(argv[3],"noninit")){
        if(become_new_init_child())return 5;check("guest-context-refused",ideck_x11_trace_install(&payload,&created)==-16&&created==0);check("no-namespace-change",generic_statat(AT_PWD,IDECK_X11_TRACE_BASE,&st,false)==-2);
    }else if(!strcmp(argv[3],"invalid")){
        payload.size=63;check("short-elf-refused",ideck_x11_trace_install(&payload,&created)==-22);payload.size=size;bytes[18]=62;check("wrong-machine-refused",ideck_x11_trace_install(&payload,&created)==-22);bytes[18]=183;bytes[16]=2;check("nonshared-elf-refused",ideck_x11_trace_install(&payload,&created)==-22);check("invalid-input-no-namespace-change",generic_statat(AT_PWD,IDECK_X11_TRACE_BASE,&st,false)==-2);
    }else return 2;
    free(bytes);return failures?1:0;
}
