/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "SharedSteamLibrary.h"
#include "kernel/fs.h"
#include "kernel/errno.h"
#include "fs/real.h"
#include "fs/fd.h"
#include "fs/path.h"
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#if IDECK_LAB_RETIRE_EMPTY_PROBE
#if !IDECK_LAB_DOCK_STORAGE
#error Empty old-probe retirement requires the explicit Dock storage experiment
#endif
#if IDECK_LAB_NATIVE_LOG
#include "NativeKernelLog.h"
#endif
/* Only the old owned compatibility probe's exact EMPTY directory chain. This
 * uses fakefs APIs, never host rmdir behind meta.db. Any file, other name or
 * symlink stops preparation. Each rmdir independently requires emptiness. */
static int only_directory_child(const char *path,const char *expected,int *found) {
    *found=0;struct fd *fd=generic_openat(AT_PWD,path,O_RDONLY_|O_DIRECTORY_,0);
    if(IS_ERR(fd))return PTR_ERR(fd);
    int error=0;struct dir_entry entry;
    if(!fd->ops->readdir){fd_close(fd);return _ENOTDIR;}
    for(unsigned count=0;;count++) {
        int next=fd->ops->readdir(fd,&entry);if(next<=0){error=next;break;}
        if(!strcmp(entry.name,".")||!strcmp(entry.name,"..")){if(count>=8){error=_EIO;break;}continue;}
        if(!expected||strcmp(entry.name,expected)||*found){error=_ENOTEMPTY;break;}
        *found=1;
    }
    int closed=fd_close(fd);return error?error:closed;
}
static int retire_empty_probe(void) {
    const char *paths[]={IDECK_SHARED_STEAM_GUEST,IDECK_SHARED_STEAM_GUEST "/steamapps",IDECK_SHARED_STEAM_GUEST "/steamapps/common",IDECK_SHARED_STEAM_GUEST "/steamapps/common/Control"};
    const char *children[]={"steamapps","common","Control",NULL};unsigned depth=0;
    for(unsigned i=0;i<4;i++) {
        int found=0,error=only_directory_child(paths[i],children[i],&found);if(error)return error;
        if(!found)break;
        struct statbuf st;error=generic_statat(AT_PWD,paths[i+1],&st,false);if(error)return error;
        if(!S_ISDIR(st.mode))return _ENOTDIR;depth++;
    }
    unsigned retired=0;
    while(depth){int error=generic_rmdirat(AT_PWD,paths[depth]);if(error)return error;depth--;retired++;}
#if IDECK_LAB_NATIVE_LOG
    if(retired){char line[128];snprintf(line,sizeof line,"IDECK_EMPTY_LAB_PROBE_RETIRED_V1 directories=%u files_deleted=0",retired);ideck_native_log_line(line);}
#else
    (void)retired;
#endif
    return 0;
}
#endif
static int mounted;
static int guest_directory(const char *path) {
    int e=generic_mkdirat(AT_PWD,path,0700);
    if(e!=_EEXIST)return e;
    struct statbuf st;
    e=generic_statat(AT_PWD,path,&st,false);
    return e?e:S_ISDIR(st.mode)?0:_ENOTDIR;
}
static int empty_mountpoint(void) {
    struct fd *fd=generic_openat(AT_PWD,IDECK_SHARED_STEAM_GUEST,O_RDONLY_|O_DIRECTORY_,0);
    if(IS_ERR(fd))return PTR_ERR(fd);
    int error=0;struct dir_entry entry;
    if(!fd->ops->readdir){fd_close(fd);return _ENOTDIR;}
    for(unsigned i=0;;i++) {
        int next=fd->ops->readdir(fd,&entry);
        if(next<=0){error=next;break;}
        if(strcmp(entry.name,".")&&strcmp(entry.name,"..")){error=_ENOTEMPTY;break;}
        if(i>=4){error=_EIO;break;}
    }
    fd_close(fd);return error;
}
static int native_directory(const char *root_directory,char source[4096]) {
    if(!root_directory||root_directory[0]!='/')return _EINVAL;
#if IDECK_LAB_DOCK_STORAGE
    // Explicit new layout only. Never silently hide/migrate the older shared source.
    char previous[4096];int old=snprintf(previous,sizeof previous,"%s/SharedSteamLibrary",root_directory);
    if(old<0||(size_t)old>=sizeof previous)return _ENAMETOOLONG;
    struct stat prior;if(!lstat(previous,&prior))return _EEXIST;
    if(errno!=ENOENT)return -errno;
    const char *parts[]={"MadeiraPrefix","MadeiraPrefix/drive_c"};
    for(unsigned i=0;i<2;i++) {
        int count=snprintf(source,4096,"%s/%s",root_directory,parts[i]);
        if(count<0||count>=4096)return _ENAMETOOLONG;
        if(mkdir(source,0700)&&errno!=EEXIST)return -errno;
        struct stat node;if(lstat(source,&node))return -errno;
        if(!S_ISDIR(node.st_mode))return _ENOTDIR;
    }
    int n=snprintf(source,4096,"%s/MadeiraPrefix/drive_c/SteamLibrary",root_directory);
#else
    int n=snprintf(source,4096,"%s/SharedSteamLibrary",root_directory);
#endif
    if(n<0||(size_t)n>=4096)return _ENAMETOOLONG;
    if(mkdir(source,0700)&&errno!=EEXIST)return -errno;
    struct stat st;if(lstat(source,&st))return -errno;
    return S_ISDIR(st.st_mode)?0:_ENOTDIR;
}
int ideck_shared_steam_prepare(const char *root_directory) {
    char source[4096];int error=native_directory(root_directory,source);if(error)return error;
    int fd=open(source,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    return fd<0?-errno:fd;
}
int ideck_shared_steam_mount(const char *root_directory) {
    if(mounted)return _EBUSY;
    char source[4096];int error=native_directory(root_directory,source);if(error)return error;
    const char *dirs[]={"/mnt","/mnt/ideck",IDECK_SHARED_STEAM_GUEST};
    for(unsigned i=0;i<sizeof dirs/sizeof dirs[0];i++){int e=guest_directory(dirs[i]);if(e)return e;}
#if IDECK_LAB_RETIRE_EMPTY_PROBE
    error=retire_empty_probe();if(error)return error;
#endif
    error=empty_mountpoint();if(error)return error; // Never hide existing files.
    error=do_mount(&realfs,source,IDECK_SHARED_STEAM_GUEST,"",0);
    if(!error)mounted=1;
    return error;
}
