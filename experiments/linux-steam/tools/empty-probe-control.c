/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "SharedSteamLibrary.h"
#include "LabDeviceFS.h"
#include "kernel/init.h"
#include "kernel/calls.h"
#include "kernel/task.h"
#include "fs/fake.h"
#include "fs/fd.h"
#include "fs/path.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
void restore_termios(void){}
static void check(int ok,const char *name){if(!ok){fprintf(stderr,"FAIL %s\n",name);exit(1);}}
static void directory(const char *path){check(!generic_mkdirat(AT_PWD,path,0700),"fixture directory");}
static void put(const char *path,const char *body){struct fd *fd=generic_open(path,O_WRONLY_|O_CREAT_|O_EXCL_,0600);check(!IS_ERR(fd),"own fixture open");check(fd->ops->write(fd,body,strlen(body))==(ssize_t)strlen(body)&&!fd_close(fd),"own fixture write");}
static void equals(const char *path,const char *body){struct fd *fd=generic_open(path,O_RDONLY_,0);check(!IS_ERR(fd),"retained file open");char data[64];ssize_t n=fd->ops->read(fd,data,sizeof data);check(n==(ssize_t)strlen(body)&&!memcmp(data,body,(size_t)n)&&!fd_close(fd),"retained bytes");}
int main(int argc,char **argv){
 if(argc!=4)return 2;dup2(2,666);char data[4096];check(!lab_device_fs_prepare(argv[1],data,sizeof data),"fakefs preparation");check(!mount_root(&fakefs,data)&&!become_first_process(),"fakefs/init");
 const char *mode=argv[2];int enabled=atoi(argv[3]);directory("/mnt");directory("/mnt/ideck");directory(IDECK_SHARED_STEAM_GUEST);
 if(strcmp(mode,"empty")){directory(IDECK_SHARED_STEAM_GUEST "/steamapps");directory(IDECK_SHARED_STEAM_GUEST "/steamapps/common");if(strcmp(mode,"partial"))directory(IDECK_SHARED_STEAM_GUEST "/steamapps/common/Control");}
 if(!strcmp(mode,"file"))put(IDECK_SHARED_STEAM_GUEST "/steamapps/common/Control/save.txt","preserve-save");
 if(!strcmp(mode,"other"))directory(IDECK_SHARED_STEAM_GUEST "/steamapps/common/Unrelated");
 int error=ideck_shared_steam_mount(argv[1]);int success=!strcmp(mode,"empty")||(enabled&&(!strcmp(mode,"legacy")||!strcmp(mode,"partial")));
 check(error==(success?0:-39),"exact expected mount result");
 if(!success){
  struct statbuf st;check(!generic_statat(AT_PWD,IDECK_SHARED_STEAM_GUEST "/steamapps/common/Control",&st,false)&&S_ISDIR(st.mode),"original probe directory retained on refusal");
  if(!strcmp(mode,"file"))equals(IDECK_SHARED_STEAM_GUEST "/steamapps/common/Control/save.txt","preserve-save");
  if(!strcmp(mode,"other"))check(!generic_statat(AT_PWD,IDECK_SHARED_STEAM_GUEST "/steamapps/common/Unrelated",&st,false),"unrelated empty directory retained");
 }else{
  equals(IDECK_SHARED_STEAM_GUEST "/native-sentinel","native-library");struct statbuf st;check(generic_statat(AT_PWD,IDECK_SHARED_STEAM_GUEST "/steamapps",&st,false)==-2,"mounted native source, no stale fixture");
 }
 printf("PASS enabled=%d case=%s result=%d; no file removal\n",enabled,mode,error);return 0;
}
