/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Actual pinned fakefs/VFS control, no mock Steam UI or account resources. */
#include "ToolInstall.h"
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
static int failures;
void restore_termios(void){}
static void check(const char *name,int ok){printf("%s=%s\n",name,ok?"PASS":"FAIL");if(!ok)failures++;}
static void *asset(const char *base,const char *name,size_t *size){char path[4096];int n=snprintf(path,sizeof path,"%s/%s",base,name);if(n<0||n>=(int)sizeof path)return NULL;int fd=open(path,O_RDONLY|O_NOFOLLOW);struct stat st;if(fd<0)return NULL;if(fstat(fd,&st)||!S_ISREG(st.st_mode)||st.st_size<1||st.st_size>262144){close(fd);return NULL;}void *b=malloc((size_t)st.st_size);if(!b){close(fd);return NULL;}size_t done=0;while(done<(size_t)st.st_size){ssize_t got=read(fd,(char *)b+done,(size_t)st.st_size-done);if(got<=0){free(b);close(fd);return NULL;}done+=(size_t)got;}close(fd);*size=done;return b;}
static int put(const char *path,const char *text){struct fd *f=generic_open(path,O_WRONLY_|O_CREAT_|O_TRUNC_,0600);if(IS_ERR(f))return 0;ssize_t n=f->ops->write(f,text,strlen(text));int r=fd_close(f);return n==(ssize_t)strlen(text)&&r>=0;}
static int equals(const char *path,const void *bytes,size_t size){struct fd *f=generic_open(path,O_RDONLY_|O_NOFOLLOW_,0);if(IS_ERR(f))return 0;unsigned char b[4096];size_t pos=0;int ok=1;while(pos<size){size_t count=size-pos;if(count>sizeof b)count=sizeof b;ssize_t n=f->ops->read(f,b,count);if(n<=0||(size_t)n>count||memcmp(b,(const char *)bytes+pos,(size_t)n)){ok=0;break;}pos+=(size_t)n;}char extra;ssize_t eof=f->ops->read(f,&extra,1);fd_close(f);return ok&&pos==size&&eof==0;}
int main(int argc,char **argv){
    if(argc!=4)return 2;struct ideck_tool_payload p={0};p.executable=asset(argv[2],"ideck-madeira",&p.executable_size);p.compatibility=asset(argv[2],"compatibilitytool.vdf",&p.compatibility_size);p.manifest=asset(argv[2],"toolmanifest.vdf",&p.manifest_size);if(!p.executable||!p.compatibility||!p.manifest)return 3;
    char root[4096];if(lab_device_fs_prepare(argv[1],root,sizeof root))return 4;if(mount_root(&fakefs,root)||become_first_process())return 5;
    if(generic_mkdirat(AT_PWD,"/Steam",0700))return 6;
    struct statbuf st;int created=-1;
    if(!strcmp(argv[3],"positive")){
        check("complete-install",ideck_tool_install(&p,&created)==0&&created==1);
        check("helper-bytes-exact",equals(IDECK_COMPAT_TOOL_EXE,p.executable,p.executable_size));
        check("tool-executable-mode",!generic_statat(AT_PWD,IDECK_COMPAT_TOOL_EXE,&st,false)&&S_ISREG(st.mode)&&(st.mode&0111));
        check("discovery-vdf-bytes-exact",equals(IDECK_COMPAT_TOOL_DIR "/compatibilitytool.vdf",p.compatibility,p.compatibility_size));
        check("manifest-bytes-exact",equals(IDECK_COMPAT_TOOL_DIR "/toolmanifest.vdf",p.manifest,p.manifest_size));
        check("stage-published-and-gone",generic_statat(AT_PWD,IDECK_COMPAT_TOOL_STAGE,&st,false)==-2);
        check("matching-install-reused",ideck_tool_install(&p,&created)==0&&created==0);
    }else if(!strcmp(argv[3],"conflict")){
        check("fixture-installed",ideck_tool_install(&p,&created)==0);
        check("foreign-change-written",put(IDECK_COMPAT_TOOL_DIR "/toolmanifest.vdf","foreign")&&put(IDECK_COMPAT_TOOL_DIR "/user-note","keep"));
        check("modified-target-refused",ideck_tool_install(&p,&created)==-17&&created==0);
        check("modified-file-preserved",equals(IDECK_COMPAT_TOOL_DIR "/toolmanifest.vdf","foreign",7));
        check("unrelated-note-preserved",equals(IDECK_COMPAT_TOOL_DIR "/user-note","keep",4));
    }else if(!strcmp(argv[3],"symlink")){
        if(generic_mkdirat(AT_PWD,"/foreign",0700)||!put("/foreign/sentinel","keep")||generic_symlinkat("/foreign",AT_PWD,"/Steam/compatibilitytools.d"))return 7;
        check("symlink-parent-refused",ideck_tool_install(&p,&created)==-20&&created==0);
        check("symlink-target-preserved",equals("/foreign/sentinel","keep",4));
        check("nothing-installed-through-symlink",generic_statat(AT_PWD,"/foreign/ideck-madeira-lab-v1",&st,false)==-2);
    }else if(!strcmp(argv[3],"stale")){
        if(generic_mkdirat(AT_PWD,"/Steam/compatibilitytools.d",0700)||generic_mkdirat(AT_PWD,IDECK_COMPAT_TOOL_STAGE,0700)||!put(IDECK_COMPAT_TOOL_STAGE "/user-note","keep"))return 8;
        check("preexisting-stage-refused",ideck_tool_install(&p,&created)==-17&&created==0);
        check("preexisting-stage-preserved",equals(IDECK_COMPAT_TOOL_STAGE "/user-note","keep",4));
        check("no-incomplete-publication",generic_statat(AT_PWD,IDECK_COMPAT_TOOL_DIR,&st,false)==-2);
    }else if(!strcmp(argv[3],"noninit")){
        if(become_new_init_child())return 9;
        check("non-init-installer-refused",ideck_tool_install(&p,&created)==-16);
        check("non-init-no-namespace-change",generic_statat(AT_PWD,"/Steam/compatibilitytools.d",&st,false)==-2);
    }else if(!strcmp(argv[3],"invalid")){
        ((unsigned char *)p.executable)[18]=62;
        check("wrong-elf-architecture-refused",ideck_tool_install(&p,&created)==-22);
        check("invalid-payload-no-parent-created",generic_statat(AT_PWD,"/Steam/compatibilitytools.d",&st,false)==-2);
        ((unsigned char *)p.executable)[18]=183;((char *)p.manifest)[0]=0;
        check("embedded-nul-vdf-refused",ideck_tool_install(&p,&created)==-22);
        check("invalid-vdf-no-parent-created",generic_statat(AT_PWD,"/Steam/compatibilitytools.d",&st,false)==-2);
    }else return 2;
    free((void *)p.executable);free((void *)p.compatibility);free((void *)p.manifest);
    return failures?1:0;
}
