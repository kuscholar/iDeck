/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "SharedLibraryConfig.h"
#include "SharedSteamLibrary.h"
#include "LabDeviceFS.h"
#include "kernel/init.h"
#include "kernel/calls.h"
#include "kernel/task.h"
#include "fs/fake.h"
#include "fs/fd.h"
#include "fs/path.h"
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static struct task *guest;static int status=-1;
void restore_termios(void){}
static void check(int ok,const char *name){if(!ok){fprintf(stderr,"FAIL %s\n",name);exit(1);}}
static void observe(struct task *task,int result){if(task==guest)status=result;}
static void *execute(void *unused){(void)unused;current=guest;current->thread=pthread_self();task_run_current();return NULL;}
static void metadata_checks(void){
 const char *already[]={"\"libraryfolders\" { \"0\" \"/mnt/ideck/SteamLibrary\" }","\xef\xbb\xbf\"LibraryFolders\" { \"7\" { \"Path\" \"/mnt/ideck/SteamLibrary\" } } // tail }"};
 char out[2048];size_t written=99;int changed=99;
 for(unsigned i=0;i<2;i++)check(!ideck_shared_library_plan(already[i],strlen(already[i]),out,sizeof out,&written,&changed)&&!written&&!changed,"existing modern/legacy/BOM/key-case registration unchanged");
 const char duplicate[]="\"libraryfolders\" { \"0\" { \"path\" \"/mnt/ideck/SteamLibrary\" \"path\" \"/Steam\" } }";
 check(!ideck_shared_library_plan(duplicate,sizeof duplicate-1,out,sizeof out,&written,&changed)&&changed,"last duplicate path follows existing KV reader semantics");
 const char partial[]="\"libraryfolders\" { \"0\" { \"path\" \"/Steam\" }";
 check(ideck_shared_library_plan(partial,sizeof partial-1,out,sizeof out,&written,&changed)==-22&&!written&&!changed,"incomplete metadata not published");
 check(ideck_shared_library_plan(NULL,0,out,1,&written,&changed)==-7&&!written&&!changed,"bounded output");
}
static void put(const char *path,const char *bytes,size_t size){struct fd *f=generic_open(path,O_WRONLY_|O_CREAT_|O_EXCL_,0700);check(!IS_ERR(f),"fixture create");check(f->ops->write(f,bytes,size)==(ssize_t)size,"fixture write");check(!fd_close(f),"fixture close");}
static size_t get(const char *path,char *bytes,size_t size){struct fd *f=generic_open(path,O_RDONLY_,0);check(!IS_ERR(f),"read VFS file");ssize_t n=f->ops->read(f,bytes,size);check(n>=0&&!fd_close(f),"read/close VFS file");return (size_t)n;}
int main(int argc,char **argv){
 if(argc!=5)return 2;metadata_checks();dup2(2,666);char data[4096];
 check(!lab_device_fs_prepare(argv[1],data,sizeof data),"scratch fakefs");check(!mount_root(&fakefs,data)&&!become_first_process(),"mount/init");
#if IDECK_LAB_RETIRE_EMPTY_PROBE
 const char *legacy[]={"/mnt","/mnt/ideck",IDECK_SHARED_STEAM_GUEST,IDECK_SHARED_STEAM_GUEST "/steamapps",IDECK_SHARED_STEAM_GUEST "/steamapps/common",IDECK_SHARED_STEAM_GUEST "/steamapps/common/Control"};
 for(unsigned i=0;i<sizeof legacy/sizeof legacy[0];i++)check(!generic_mkdirat(AT_PWD,legacy[i],0700),"known empty legacy probe fixture");
#endif
 check(!ideck_shared_steam_mount(argv[1]),"actual shared mount");check(!generic_mkdirat(AT_PWD,"/Steam",0700),"Steam dir");check(!generic_mkdirat(AT_PWD,"/Steam/steamapps",0700),"steamapps dir");
 const char old[]="// retained comment with }\n\"libraryfolders\"\n{\n\"0\" { \"path\" \"/Steam\" \"label\" \"braces { } and \\\"quote\\\"\" \"apps\" { \"123\" \"45\" } }\n\"2\" { \"path\" \"/Other Library\" \"unknown\" \"keep me\" }\n}\n// tail retained\n";
 int fresh=!strcmp(argv[3],"fresh"),conflict=!strcmp(argv[3],"interrupted");
 if(!fresh){put(IDECK_LIBRARY_CONFIG_PATH,old,sizeof old-1);check(!generic_setattrat(AT_PWD,IDECK_LIBRARY_CONFIG_PATH,make_attr(mode,S_IFREG|0640),false),"original metadata mode");}
 if(conflict)put(IDECK_LIBRARY_CONFIG_STAGE,"previous-stage",14);
 int changed=-1,error=ideck_shared_library_register(&changed);char bytes[4096],backup[4096];
 if(conflict){check(error==-17&&!changed,"interrupted stage retained");size_t n=get(IDECK_LIBRARY_CONFIG_PATH,bytes,sizeof bytes);check(n==sizeof old-1&&!memcmp(bytes,old,n),"original retained on interrupted publication");check(get(IDECK_LIBRARY_CONFIG_STAGE,bytes,sizeof bytes)==14&&!memcmp(bytes,"previous-stage",14),"prior stage retained");puts("PASS interrupted publication retains original and earlier stage; no guest started");return 0;}
 check(!error&&changed,"register library");size_t n=get(IDECK_LIBRARY_CONFIG_PATH,bytes,sizeof bytes);
 if(!fresh){size_t b=get(IDECK_LIBRARY_CONFIG_BACKUP,backup,sizeof backup);check(b==sizeof old-1&&!memcmp(backup,old,b),"exact original backup");struct statbuf st;check(!generic_statat(AT_PWD,IDECK_LIBRARY_CONFIG_PATH,&st,false)&&(st.mode&0777)==0640,"original config mode retained");}
 check(!ideck_shared_library_register(&changed)&&!changed,"idempotent registration");size_t b=get(IDECK_LIBRARY_CONFIG_PATH,backup,sizeof backup);check(b==n&&!memcmp(bytes,backup,n),"repeat preserves bytes");
 FILE *output=fopen(argv[4],"wb");check(output!=NULL,"private fixture readback");check(fwrite(bytes,1,n,output)==n&&!fclose(output),"private output close");
 FILE *probe=fopen(argv[2],"rb");check(probe!=NULL,"probe input");b=fread(backup,1,sizeof backup,probe);check(b>0&&feof(probe)&&!fclose(probe),"own ELF read");put("/probe",backup,b);
 check(!become_new_init_child(),"guest child");check(ideck_shared_library_register(&changed)==-16,"guest cannot register while running");guest=current;
 const char args[]="/probe\0",env[]="HOME=/\0";check(!do_execve("/probe",1,args,env),"exec actual ARM64 ELF");exit_hook=observe;current=NULL;pthread_t thread;
 check(!pthread_create(&thread,NULL,execute,NULL)&&!pthread_join(thread,NULL),"guest native join");check(!status,"guest reads registered library through Linux syscalls");
 printf("PASS %s exact backup/idempotence; actual ARM64 guest status=%d\n",argv[3],status);return 0;
}
