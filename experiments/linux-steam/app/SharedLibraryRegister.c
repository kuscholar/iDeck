/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "SharedLibraryConfig.h"
#include "SharedSteamLibrary.h"
#include "kernel/task.h"
#include "kernel/calls.h"
#include "fs/fd.h"
#include "fs/path.h"
#include <stdlib.h>
#include <string.h>
static int read_file(const char *path,char *bytes,size_t capacity,size_t *size) {
    *size=0;struct statbuf st;int e=generic_statat(AT_PWD,path,&st,false);
    if(e)return e;
    if(!S_ISREG(st.mode)||st.size<0||(uint64_t)st.size>capacity)return -22;
    struct fd *fd=generic_open(path,O_RDONLY_|O_NOFOLLOW_,0);if(IS_ERR(fd))return (int)PTR_ERR(fd);
    while(*size<capacity){ssize_t n=fd->ops->read(fd,bytes+*size,capacity-*size);if(n<0){e=(int)n;break;}if(!n)break;*size+=(size_t)n;}
    if(!e&&*size!=(size_t)st.size)e=-11;
    int closed=fd_close(fd);return e?e:closed;
}
static int write_new(const char *path,const char *bytes,size_t size,int *owned) {
    *owned=0;struct fd *fd=generic_open(path,O_WRONLY_|O_CREAT_|O_EXCL_|O_NOFOLLOW_,0600);
    if(IS_ERR(fd))return (int)PTR_ERR(fd);*owned=1;size_t used=0;int error=0;
    while(used<size){ssize_t n=fd->ops->write(fd,bytes+used,size-used);if(n<=0){error=n<0?(int)n:-5;break;}used+=(size_t)n;}
    int closed=fd_close(fd);return error?error:closed;
}
int ideck_shared_library_register(int *changed) {
    if(changed)*changed=0;if(!changed||!current)return -22;
    if(current->pid!=1)return -16;
    struct statbuf st;int error=generic_statat(AT_PWD,IDECK_SHARED_STEAM_GUEST,&st,false);
    if(error||!S_ISDIR(st.mode))return error?error:-20;
    error=generic_mkdirat(AT_PWD,"/Steam/steamapps",0700);if(error&&error!=-17)return error;
    char *old=malloc(IDECK_LIBRARY_CONFIG_MAX),*planned=malloc(IDECK_LIBRARY_CONFIG_MAX+512),*check=malloc(IDECK_LIBRARY_CONFIG_MAX+512);
    if(!old||!planned||!check){free(old);free(planned);free(check);return -12;}
    size_t size=0,length=0;int present=1,made=0,owned=0;
    error=read_file(IDECK_LIBRARY_CONFIG_PATH,old,IDECK_LIBRARY_CONFIG_MAX,&size);
    if(error==-2){present=0;error=0;}if(error)goto done;
    error=ideck_shared_library_plan(old,size,planned,IDECK_LIBRARY_CONFIG_MAX+512,&length,&made);
    if(error||!made)goto done;
    struct statbuf original={0};
    if(present){
        error=generic_statat(AT_PWD,IDECK_LIBRARY_CONFIG_PATH,&original,false);if(error)goto done;
        int backup=0;error=write_new(IDECK_LIBRARY_CONFIG_BACKUP,old,size,&backup);if(error)goto done;
    }
    error=write_new(IDECK_LIBRARY_CONFIG_STAGE,planned,length,&owned);if(error)goto done;
    if(present){error=generic_setattrat(AT_PWD,IDECK_LIBRARY_CONFIG_STAGE,make_attr(mode,S_IFREG|(original.mode&0777)),false);if(error)goto done;}
    size_t checked=0;error=read_file(IDECK_LIBRARY_CONFIG_STAGE,check,IDECK_LIBRARY_CONFIG_MAX+512,&checked);
    if(!error&&(checked!=length||memcmp(check,planned,length)))error=-5;
    if(error)goto done;
    error=read_file(IDECK_LIBRARY_CONFIG_PATH,check,IDECK_LIBRARY_CONFIG_MAX,&checked);
    if(present){if(!error&&(checked!=size||memcmp(check,old,size)))error=-11;}
    else if(error==-2)error=0;else if(!error)error=-17;
    if(error)goto done;
    error=generic_renameat(AT_PWD,IDECK_LIBRARY_CONFIG_STAGE,AT_PWD,IDECK_LIBRARY_CONFIG_PATH);
    if(!error){owned=0;*changed=1;}
done:
    if(owned)generic_unlinkat(AT_PWD,IDECK_LIBRARY_CONFIG_STAGE);
    free(old);free(planned);free(check);return error;
}
