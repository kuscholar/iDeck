/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Real pinned fakefs/VFS and own installer. No Steam/account/device data. */
#include "X11StateInstall.h"
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
static int put(const char *path,const void *body,size_t size){struct fd *f=generic_open(path,O_WRONLY_|O_CREAT_|O_EXCL_|O_NOFOLLOW_,0600);if(IS_ERR(f))return 0;ssize_t n=f->ops->write(f,body,size);int r=fd_close(f);return n==(ssize_t)size&&r>=0;}
static int equals(const char *path,const void *bytes,size_t size){
    struct fd *f=generic_open(path,O_RDONLY_|O_NOFOLLOW_,0);if(IS_ERR(f))return 0;
    unsigned char buffer[4096];size_t offset=0;int same=1;
    while(offset<size){size_t n=size-offset;if(n>sizeof buffer)n=sizeof buffer;ssize_t got=f->ops->read(f,buffer,n);if(got<=0||(size_t)got>n||memcmp(buffer,(const char *)bytes+offset,(size_t)got)){same=0;break;}offset+=(size_t)got;}
    unsigned char extra;ssize_t tail=f->ops->read(f,&extra,1);fd_close(f);return same&&offset==size&&tail==0;
}
int main(int argc,char **argv){
    if(argc!=4)return 2;int asset=open(argv[2],O_RDONLY|O_NOFOLLOW);struct stat info;if(asset<0||fstat(asset,&info)||info.st_size<64||info.st_size>262144)return 3;
    size_t size=(size_t)info.st_size;unsigned char *bytes=malloc(size);if(!bytes)return 3;
    size_t offset=0;while(offset<size){ssize_t n=read(asset,bytes+offset,size-offset);if(n<=0)return 3;offset+=(size_t)n;}close(asset);
    char root[4096];if(lab_device_fs_prepare(argv[1],root,sizeof root)||mount_root(&fakefs,root)||become_first_process())return 4;
    struct statbuf st;const char *mode=argv[3];
    if(!strcmp(mode,"invalid")){
        check("null-refused",ideck_x11_state_configure(NULL,size)==-22);
        check("short-refused",ideck_x11_state_configure(bytes,63)==-22);
        check("large-refused",ideck_x11_state_configure(bytes,262145)==-22);
        bytes[18]=62;check("wrong-machine-refused",ideck_x11_state_configure(bytes,size)==-22);bytes[18]=183;
        bytes[16]=3;check("shared-object-refused",ideck_x11_state_configure(bytes,size)==-22);bytes[16]=2;
        check("unprepared-refused",ideck_x11_state_install_prepared()==-22);
        check("no-directory-change",generic_statat(AT_PWD,IDECK_X11_STATE_BASE,&st,false)==-2);
        free(bytes);return failures?1:0;
    }
    check("immutable-payload-copied",!ideck_x11_state_configure(bytes,size));
    check("second-configure-refused",ideck_x11_state_configure(bytes,size)==-16);
    if(!strcmp(mode,"positive")){
        unsigned char first=bytes[0];bytes[0]=0;
        check("owned-copy-install",!ideck_x11_state_install_prepared());bytes[0]=first;
        check("published-exact",equals(IDECK_X11_STATE_FILE,bytes,size));
        check("published-regular-executable",!generic_statat(AT_PWD,IDECK_X11_STATE_FILE,&st,false)&&S_ISREG(st.mode)&&st.nlink==1&&(st.mode&0777)==0700);
        check("owned-stage-gone",generic_statat(AT_PWD,IDECK_X11_STATE_STAGE,&st,false)==-2);
        check("same-lifetime-consumed",ideck_x11_state_install_prepared()==-22);
    }else if(!strcmp(mode,"identical")){
        if(generic_mkdirat(AT_PWD,IDECK_X11_STATE_BASE,0755)||!put(IDECK_X11_STATE_FILE,bytes,size)||generic_setattrat(AT_PWD,IDECK_X11_STATE_FILE,make_attr(mode,S_IFREG|0700),false))return 5;
        check("matching-published-reused",!ideck_x11_state_install_prepared());check("existing-bytes-preserved",equals(IDECK_X11_STATE_FILE,bytes,size));
    }else if(!strcmp(mode,"conflict")){
        if(generic_mkdirat(AT_PWD,IDECK_X11_STATE_BASE,0755)||!put(IDECK_X11_STATE_FILE,"foreign",7)||!put(IDECK_X11_STATE_BASE "/note","keep",4))return 5;
        check("foreign-target-refused",ideck_x11_state_install_prepared()==-17);check("foreign-preserved",equals(IDECK_X11_STATE_FILE,"foreign",7));check("note-preserved",equals(IDECK_X11_STATE_BASE "/note","keep",4));
    }else if(!strcmp(mode,"base-link")){
        if(generic_mkdirat(AT_PWD,"/foreign",0700)||!put("/foreign/note","keep",4)||generic_symlinkat("/foreign",AT_PWD,IDECK_X11_STATE_BASE))return 5;
        check("base-symlink-refused",ideck_x11_state_install_prepared()==-20);check("referent-preserved",equals("/foreign/note","keep",4));
    }else if(!strcmp(mode,"target-link")){
        if(generic_mkdirat(AT_PWD,IDECK_X11_STATE_BASE,0755)||!put("/foreign",bytes,size)||generic_symlinkat("/foreign",AT_PWD,IDECK_X11_STATE_FILE))return 5;
        check("target-symlink-refused",ideck_x11_state_install_prepared()==-17);check("referent-preserved",equals("/foreign",bytes,size));
    }else if(!strcmp(mode,"stale")){
        if(generic_mkdirat(AT_PWD,IDECK_X11_STATE_BASE,0755)||!put(IDECK_X11_STATE_STAGE,"keep",4))return 5;
        check("stale-refused",ideck_x11_state_install_prepared()==-17);check("stale-preserved",equals(IDECK_X11_STATE_STAGE,"keep",4));check("no-target",generic_statat(AT_PWD,IDECK_X11_STATE_FILE,&st,false)==-2);
    }else if(!strcmp(mode,"noninit")){
        if(become_new_init_child())return 5;check("guest-install-refused",ideck_x11_state_install_prepared()==-16);check("no-directory-change",generic_statat(AT_PWD,IDECK_X11_STATE_BASE,&st,false)==-2);
    }else return 2;
    free(bytes);return failures?1:0;
}
