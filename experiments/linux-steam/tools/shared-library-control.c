/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST scratch fakefs + actual ARM64 ELF. No runtime-reuse/Wine permission. */
#include "SharedSteamLibrary.h"
#include "LabDeviceFS.h"
#include "kernel/init.h"
#include "kernel/calls.h"
#include "kernel/task.h"
#include "fs/real.h"
#include "fs/fake.h"
#include "fs/fd.h"
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <stdlib.h>
static struct task *guest;
static int status=-1;
void restore_termios(void) {}
static void observe(struct task *task,int result){if(task==guest)status=result;}
static void *execute(void *unused){(void)unused;current=guest;current->thread=pthread_self();task_run_current();return NULL;}
static int install_probe(const char *source){
 FILE *file=fopen(source,"rb");if(!file)return -1;
 struct fd *dest=generic_open("/probe",O_WRONLY_|O_CREAT_|O_TRUNC_,0700);
 if(IS_ERR(dest)){fclose(file);return (int)PTR_ERR(dest);}
 char bytes[4096];size_t size;int error=0;
 while((size=fread(bytes,1,sizeof bytes,file))){ssize_t n=dest->ops->write(dest,bytes,size);if(n!=(ssize_t)size){error=-1;break;}}
 if(ferror(file))error=-1;
 fclose(file);if(fd_close(dest)<0)error=-1;return error;
}
int main(int argc,char **argv){
 if(argc!=3)return 2;
 dup2(2,666);char fixture[4096],data[4096];
 int n=snprintf(fixture,sizeof fixture,"%s/fake-root",argv[1]);if(n<0||n>=(int)sizeof fixture)return 3;
 int error=lab_device_fs_prepare(fixture,data,sizeof data);if(error)return 4;
 if((error=mount_root(&fakefs,data))||(error=become_first_process())){fprintf(stderr,"fakefs/init=%d\n",error);return 5;}
 if((error=ideck_shared_steam_mount(argv[1]))){fprintf(stderr,"shared-mount=%d\n",error);return 6;}
 if(ideck_shared_steam_mount(argv[1])!=-16)return 7; // No duplicate native remount.
 if((error=install_probe(argv[2]))){fprintf(stderr,"install-probe=%d\n",error);return 8;}
 if((error=become_new_init_child()))return 9;
 guest=current;const char args[]="/probe\0",env[]="HOME=/\0";
 if((error=do_execve("/probe",1,args,env))){fprintf(stderr,"exec=%d\n",error);return 10;}
 exit_hook=observe;current=NULL;pthread_t thread;
 if(pthread_create(&thread,NULL,execute,NULL)||pthread_join(thread,NULL))return 11;
 printf("actual-ARM64-wait-status=%d\n",status);return status?12:0;
}
