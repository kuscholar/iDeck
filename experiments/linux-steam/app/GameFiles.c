/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "GameFiles.h"
#include "LaunchProtocol.h"
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

struct ideck_game_files {
    int root,install,working,parent,executable;
    uint32_t appid;
    unsigned machine;
    enum ideck_library_kind library;
    struct stat install_stat,working_stat,parent_stat,executable_stat;
    char relative_install[1024],relative_working[1024],relative_parent[1024],leaf[NAME_MAX+1];
};
static int duplicate_directory(int descriptor) {
    int copy=fcntl(descriptor,F_DUPFD_CLOEXEC,3);if(copy<0)return -errno;
    struct stat st;
    if(fstat(copy,&st)){int error=-errno;close(copy);return error;}
    if(!S_ISDIR(st.st_mode)||st.st_uid!=geteuid()){close(copy);return -EPERM;}
    return copy;
}
static int directory_below(int root,const char *relative) {
    int current=duplicate_directory(root);if(current<0)return current;
    const char *cursor=relative;
    while(*cursor) {
        const char *slash=strchr(cursor,'/');size_t size=slash?(size_t)(slash-cursor):strlen(cursor);
        if(!size||size>NAME_MAX||(size==1&&cursor[0]=='.')||(size==2&&!memcmp(cursor,"..",2))){close(current);return -EINVAL;}
        char component[NAME_MAX+1];memcpy(component,cursor,size);component[size]=0;
        int next=openat(current,component,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
        if(next<0){int error=-errno;close(current);return error;}
        close(current);current=next;
        if(!slash)break;
        cursor=slash+1;if(!*cursor){close(current);return -EINVAL;}
    }
    return current;
}
static uint16_t le16(const unsigned char *p){return (uint16_t)p[0]|(uint16_t)p[1]<<8;}
static uint32_t le32(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static int read_at(int descriptor,void *buffer,size_t size,off_t offset) {
    size_t done=0;
    while(done<size){ssize_t n=pread(descriptor,(char *)buffer+done,size-done,offset+(off_t)done);if(n<0&&errno==EINTR)continue;if(n<0)return -errno;if(!n)return -ENOEXEC;done+=(size_t)n;}
    return 0;
}
static int pe_identity(int descriptor,const struct stat *st,unsigned *machine) {
    unsigned char dos[64],pe[26];
    if(st->st_size<90)return -ENOEXEC;
    int error=read_at(descriptor,dos,sizeof dos,0);if(error)return error;
    if(dos[0]!='M'||dos[1]!='Z')return -ENOEXEC;
    uint32_t offset=le32(dos+60);
    if(offset<sizeof dos||(uint64_t)offset+sizeof pe>(uint64_t)st->st_size)return -ENOEXEC;
    if((error=read_at(descriptor,pe,sizeof pe,(off_t)offset)))return error;
    unsigned architecture=le16(pe+4),optional=le16(pe+24),attributes=le16(pe+22),optional_bytes=le16(pe+20);
    if(memcmp(pe,"PE\0\0",4)||!le16(pe+6)||optional_bytes<2||
            (uint64_t)offset+24+optional_bytes>(uint64_t)st->st_size||
            !(attributes&2)||(attributes&0x2000)||
            !((architecture==0x14c&&optional==0x10b)||(architecture==0x8664&&optional==0x20b)))return -ENOEXEC;
    *machine=architecture;return 0;
}
static int same_object(const struct stat *a,const struct stat *b){return a->st_dev==b->st_dev&&a->st_ino==b->st_ino&&(a->st_mode&S_IFMT)==(b->st_mode&S_IFMT);}
static int same_file(const struct stat *a,const struct stat *b) {
    return same_object(a,b)&&S_ISREG(b->st_mode)&&b->st_nlink==1&&b->st_uid==a->st_uid&&b->st_size==a->st_size&&
        b->st_mtimespec.tv_sec==a->st_mtimespec.tv_sec&&b->st_mtimespec.tv_nsec==a->st_mtimespec.tv_nsec&&
        b->st_ctimespec.tv_sec==a->st_ctimespec.tv_sec&&b->st_ctimespec.tv_nsec==a->st_ctimespec.tv_nsec;
}
void ideck_game_files_close(struct ideck_game_files *files) {
    if(!files)return;
    int descriptors[]={files->executable,files->parent,files->working,files->install,files->root};
    for(unsigned i=0;i<sizeof descriptors/sizeof descriptors[0];i++)if(descriptors[i]>=0)close(descriptors[i]);
    free(files);
}
int ideck_game_files_open(const struct ideck_library_caps *libraries,const void *frame,size_t size,struct ideck_game_files **out) {
    if(!libraries||!frame||size!=sizeof(struct ideck_launch_request)||!out)return -EINVAL;
    if(*out)return -EBUSY;
    struct ideck_launch_request request;memcpy(&request,frame,sizeof request);
    if(ideck_launch_validate(&request,sizeof request))return -EINVAL;
    static const char *roots[]={IDECK_LAUNCH_DEFAULT_ROOT,IDECK_LAUNCH_ROOT};unsigned choice=2;
    for(unsigned i=0;i<2;i++)if(!strncmp(request.install,roots[i],strlen(roots[i]))){choice=i;break;}
    if(choice==2)return -EINVAL;
    int capability=choice==0?libraries->default_common:libraries->shared_common;if(capability<0)return -ENODEV;
    struct ideck_game_files *files=calloc(1,sizeof *files);if(!files)return -ENOMEM;
    files->root=files->install=files->working=files->parent=files->executable=-1;
    files->root=duplicate_directory(capability);int error=files->root;if(error<0)goto fail;
    files->library=(enum ideck_library_kind)choice;files->appid=request.appid;
    strcpy(files->relative_install,request.install+strlen(roots[choice]));
    files->install=directory_below(files->root,files->relative_install);error=files->install;if(error<0)goto fail;
    if(fstat(files->install,&files->install_stat)){error=-errno;goto fail;}
    size_t install_length=strlen(request.install);
    if(request.working[install_length])strcpy(files->relative_working,request.working+install_length+1);
    files->working=directory_below(files->install,files->relative_working);error=files->working;if(error<0)goto fail;
    if(fstat(files->working,&files->working_stat)){error=-errno;goto fail;}
    const char *relative=request.executable+install_length+1,*slash=strrchr(relative,'/'),*leaf=slash?slash+1:relative;
    size_t leaf_length=strlen(leaf);if(leaf_length>NAME_MAX||leaf_length<5||strcasecmp(leaf+leaf_length-4,".exe")){error=-ENOEXEC;goto fail;}
    strcpy(files->leaf,leaf);
    if(slash){size_t length=(size_t)(slash-relative);memcpy(files->relative_parent,relative,length);files->relative_parent[length]=0;}
    files->parent=directory_below(files->install,files->relative_parent);error=files->parent;if(error<0)goto fail;
    if(fstat(files->parent,&files->parent_stat)){error=-errno;goto fail;}
    files->executable=openat(files->parent,files->leaf,O_RDONLY|O_NONBLOCK|O_NOFOLLOW|O_CLOEXEC);
    if(files->executable<0){error=-errno;goto fail;}
    if(fstat(files->executable,&files->executable_stat)){error=-errno;goto fail;}
    if(!S_ISREG(files->executable_stat.st_mode)||files->executable_stat.st_nlink!=1||files->executable_stat.st_uid!=geteuid()){error=-EPERM;goto fail;}
    error=pe_identity(files->executable,&files->executable_stat,&files->machine);if(error)goto fail;
    struct stat after;
    if(fstat(files->executable,&after)||!same_file(&files->executable_stat,&after)){error=-ESTALE;goto fail;}
    *out=files;return 0;
fail:
    ideck_game_files_close(files);return error;
}
int ideck_game_files_executable(const struct ideck_game_files *files){return files?files->executable:-1;}
int ideck_game_files_from_data(int data_directory,const void *frame,size_t size,struct ideck_game_files **out) {
    if(!frame||size!=sizeof(struct ideck_launch_request)||!out)return -EINVAL;
    if(*out)return -EBUSY;
    struct ideck_launch_request request;memcpy(&request,frame,sizeof request);
    if(ideck_launch_validate(&request,sizeof request))return -EINVAL;
    int is_default=!strncmp(request.install,IDECK_LAUNCH_DEFAULT_ROOT,sizeof IDECK_LAUNCH_DEFAULT_ROOT-1);
    int common=directory_below(data_directory,is_default?"Steam/steamapps/common":"mnt/ideck/SteamLibrary/steamapps/common");
    if(common<0)return common;
    struct ideck_library_caps caps={.default_common=is_default?common:-1,.shared_common=is_default?-1:common};
    int result=ideck_game_files_open(&caps,&request,sizeof request,out);close(common);return result;
}
int ideck_game_files_working(const struct ideck_game_files *files){return files?files->working:-1;}
uint32_t ideck_game_files_appid(const struct ideck_game_files *files){return files?files->appid:0;}
unsigned ideck_game_files_machine(const struct ideck_game_files *files){return files?files->machine:0;}
enum ideck_library_kind ideck_game_files_library(const struct ideck_game_files *files){return files?files->library:(enum ideck_library_kind)-1;}
int ideck_game_files_unchanged(const struct ideck_game_files *files) {
    if(!files)return -EINVAL;
    struct stat st;int install=-1,working=-1,parent=-1,error=-ESTALE;
    if(fstat(files->executable,&st)||!same_file(&files->executable_stat,&st))return -ESTALE;
    install=directory_below(files->root,files->relative_install);if(install<0)goto done;
    if(fstat(install,&st)||!same_object(&files->install_stat,&st))goto done;
    working=directory_below(install,files->relative_working);if(working<0)goto done;
    if(fstat(working,&st)||!same_object(&files->working_stat,&st))goto done;
    parent=directory_below(install,files->relative_parent);if(parent<0)goto done;
    if(fstat(parent,&st)||!same_object(&files->parent_stat,&st))goto done;
    if(fstatat(parent,files->leaf,&st,AT_SYMLINK_NOFOLLOW)||!same_file(&files->executable_stat,&st))goto done;
    error=0;
done:
    if(parent>=0)close(parent);if(working>=0)close(working);if(install>=0)close(install);return error;
}
