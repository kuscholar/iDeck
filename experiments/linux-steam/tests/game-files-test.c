/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Native HOST fixtures only. PE identity bytes contain no executable program,
 * Valve code, credentials, licensing response or actual game. Nothing executes.
 */
#include "GameFiles.h"
#include "GameFilePolicy.h"
#include "LaunchProtocol.h"
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <assert.h>
#include <pthread.h>
#include <sys/wait.h>
static unsigned checks;
static void check(const char *name,int value){printf("%s=%s\n",name,value?"PASS":"FAIL");assert(value);checks++;}
static void path(char out[4096],const char *base,const char *name){int n=snprintf(out,4096,"%s/%s",base,name);assert(n>0&&n<4096);}
static void directory(const char *base,const char *name){char p[4096];path(p,base,name);assert(!mkdir(p,0700));}
static void fixture(const char *base,const char *name,unsigned machine,unsigned optional,unsigned attributes){
    char p[4096];path(p,base,name);unsigned char bytes[128]={0};bytes[0]='M';bytes[1]='Z';bytes[60]=64;
    memcpy(bytes+64,"PE\0\0",4);bytes[68]=machine&255;bytes[69]=(machine>>8)&255;bytes[70]=1;
    bytes[84]=2;bytes[86]=attributes&255;bytes[87]=(attributes>>8)&255;bytes[88]=optional&255;bytes[89]=(optional>>8)&255;
    int fd=open(p,O_WRONLY|O_CREAT|O_EXCL,0600);assert(fd>=0&&write(fd,bytes,sizeof bytes)==sizeof bytes&&!close(fd));
}
static struct ideck_launch_request request(const char *root,const char *game,const char *exe,const char *working){
    struct ideck_launch_request r={.magic=IDECK_LAUNCH_MAGIC,.version=IDECK_LAUNCH_VERSION,.appid=480,.verb=1,.argc=1};
    assert(snprintf(r.install,sizeof r.install,"%s%s",root,game)<(int)sizeof r.install);
    assert(snprintf(r.executable,sizeof r.executable,"%s/%s",r.install,exe)<(int)sizeof r.executable);
    if(working&&*working)assert(snprintf(r.working,sizeof r.working,"%s/%s",r.install,working)<(int)sizeof r.working);
    else strcpy(r.working,r.install);
    strcpy(r.arguments,r.executable);r.argument_bytes=(uint32_t)strlen(r.arguments)+1;return r;
}
static unsigned descriptors(void){unsigned n=0;for(int i=0;i<4096;i++)if(fcntl(i,F_GETFD)>=0)n++;return n;}
static void *inspect_requests(void *context){const struct ideck_launch_request *r=context;for(unsigned i=0;i<64;i++)ideck_game_file_policy_inspect(r);return NULL;}
int main(int argc,char **argv){
    if(argc!=2)return 2;setvbuf(stdout,NULL,_IONBF,0);char before_cwd[4096],after_cwd[4096];assert(getcwd(before_cwd,sizeof before_cwd));
    const char *base=argv[1];directory(base,"default");directory(base,"shared");directory(base,"outside");
    char standard[4096],shared[4096],outside[4096];path(standard,base,"default");path(shared,base,"shared");path(outside,base,"outside");
    directory(standard,"Control Game");directory(shared,"Control Game");char game[4096];path(game,standard,"Control Game");
    directory(game,"bin");directory(game,"assets");fixture(game,"bin/control.EXE",0x8664,0x20b,2);fixture(shared,"Control Game/control.exe",0x14c,0x10b,2);fixture(outside,"control.exe",0x8664,0x20b,2);
    struct ideck_library_caps caps={open(standard,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC),open(shared,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC)};assert(caps.default_common>=0&&caps.shared_common>=0);
    struct ideck_game_files *files=NULL;struct ideck_launch_request r=request(IDECK_LAUNCH_DEFAULT_ROOT,"Control Game","bin/control.EXE","assets");unsigned baseline=descriptors();
    check("default-library-real-directory-resolution",ideck_game_files_open(&caps,&r,sizeof r,&files)==0&&files);
    check("pe64-identity-and-appid",ideck_game_files_machine(files)==0x8664&&ideck_game_files_appid(files)==480&&ideck_game_files_library(files)==IDECK_LIBRARY_DEFAULT);
    struct stat actual,wanted;char p[4096];path(p,game,"assets");assert(!stat(p,&wanted));assert(!fstat(ideck_game_files_working(files),&actual));
    check("working-directory-is-selected-native-directory",actual.st_ino==wanted.st_ino&&actual.st_dev==wanted.st_dev&&S_ISDIR(actual.st_mode));
    check("borrowed-executable-readonly-and-cloexec",(fcntl(ideck_game_files_executable(files),F_GETFL)&O_ACCMODE)==O_RDONLY&&(fcntl(ideck_game_files_executable(files),F_GETFD)&FD_CLOEXEC));
    check("unchanged-file-revalidates",ideck_game_files_unchanged(files)==0);
    struct ideck_game_files *retained=files;check("busy-output-does-not-leak-or-overwrite",ideck_game_files_open(&caps,&r,sizeof r,&files)==-EBUSY&&files==retained);
    ideck_game_files_close(files);files=NULL;check("all-open-capabilities-closed",descriptors()==baseline);
    r=request(IDECK_LAUNCH_ROOT,"Control Game","control.exe",NULL);check("planned-shared-library-and-pe32",ideck_game_files_open(&caps,&r,sizeof r,&files)==0&&ideck_game_files_machine(files)==0x14c&&ideck_game_files_library(files)==IDECK_LIBRARY_SHARED);ideck_game_files_close(files);files=NULL;
    struct ideck_library_caps disabled=caps;disabled.shared_common=-1;
    check("missing-selected-library-does-not-fall-back",ideck_game_files_open(&disabled,&r,sizeof r,&files)==-ENODEV&&!files);

    char target[4096],alias[4096];path(target,outside,"control.exe");path(alias,game,"linked.exe");assert(!symlink(target,alias));
    r=request(IDECK_LAUNCH_DEFAULT_ROOT,"Control Game","linked.exe",NULL);check("executable-symlink-refused",ideck_game_files_open(&caps,&r,sizeof r,&files)<0&&!files);
    path(alias,standard,"Alias Game");assert(!symlink(outside,alias));r=request(IDECK_LAUNCH_DEFAULT_ROOT,"Alias Game","control.exe",NULL);check("installation-symlink-refused",ideck_game_files_open(&caps,&r,sizeof r,&files)<0&&!files);
    path(alias,game,"outside-bin");assert(!symlink(outside,alias));r=request(IDECK_LAUNCH_DEFAULT_ROOT,"Control Game","outside-bin/control.exe",NULL);check("nested-parent-symlink-refused",ideck_game_files_open(&caps,&r,sizeof r,&files)<0&&!files);
    r=request(IDECK_LAUNCH_DEFAULT_ROOT,"Control Game","bin/control.EXE","outside-bin");check("working-directory-symlink-refused",ideck_game_files_open(&caps,&r,sizeof r,&files)<0&&!files);
    path(alias,game,"hard.exe");assert(!link(target,alias));r=request(IDECK_LAUNCH_DEFAULT_ROOT,"Control Game","hard.exe",NULL);check("multiply-linked-executable-refused",ideck_game_files_open(&caps,&r,sizeof r,&files)==-EPERM&&!files);
    path(alias,game,"pipe.exe");assert(!mkfifo(alias,0600));r=request(IDECK_LAUNCH_DEFAULT_ROOT,"Control Game","pipe.exe",NULL);check("fifo-refused-without-blocking",ideck_game_files_open(&caps,&r,sizeof r,&files)==-EPERM&&!files);
    r=request(IDECK_LAUNCH_DEFAULT_ROOT,"Control Game","bin",NULL);check("directory-not-executable",ideck_game_files_open(&caps,&r,sizeof r,&files)<0&&!files);
    fixture(game,"arm.exe",0xaa64,0x20b,2);r=request(IDECK_LAUNCH_DEFAULT_ROOT,"Control Game","arm.exe",NULL);check("unsupported-machine-refused",ideck_game_files_open(&caps,&r,sizeof r,&files)==-ENOEXEC&&!files);
    fixture(game,"dll.exe",0x8664,0x20b,0x2002);r=request(IDECK_LAUNCH_DEFAULT_ROOT,"Control Game","dll.exe",NULL);check("dll-identity-refused",ideck_game_files_open(&caps,&r,sizeof r,&files)==-ENOEXEC&&!files);
    fixture(game,"wrong.exe",0x8664,0x10b,2);r=request(IDECK_LAUNCH_DEFAULT_ROOT,"Control Game","wrong.exe",NULL);check("machine-optional-header-mismatch-refused",ideck_game_files_open(&caps,&r,sizeof r,&files)==-ENOEXEC&&!files);
    fixture(game,"offset.exe",0x8664,0x20b,2);path(p,game,"offset.exe");int fd=open(p,O_WRONLY);unsigned char huge[4]={255,255,255,255};assert(fd>=0&&pwrite(fd,huge,4,60)==4&&!close(fd));r=request(IDECK_LAUNCH_DEFAULT_ROOT,"Control Game","offset.exe",NULL);check("pe-offset-beyond-file-refused",ideck_game_files_open(&caps,&r,sizeof r,&files)==-ENOEXEC&&!files);

    r=request(IDECK_LAUNCH_DEFAULT_ROOT,"Control Game","bin/control.EXE","assets");check("truncated-request-refused",ideck_game_files_open(&caps,&r,sizeof r-1,&files)==-EINVAL&&!files);
    strcpy(r.executable,"/Steam/steamapps/common/Control Game/../../outside.exe");check("parent-traversal-refused",ideck_game_files_open(&caps,&r,sizeof r,&files)==-EINVAL&&!files);
    r=request(IDECK_LAUNCH_DEFAULT_ROOT,"Control Game","bin/control.EXE","assets");r.appid=0;check("invalid-appid-refused",ideck_game_files_open(&caps,&r,sizeof r,&files)==-EINVAL&&!files);
    r=request(IDECK_LAUNCH_DEFAULT_ROOT,"Control Game","bin/control.EXE","assets");
    for(unsigned i=0;i<1000;i++){r.version++;assert(ideck_game_files_open(&caps,&r,sizeof r,&files)<0&&!files);r.version--;}
    check("rejected-requests-leave-no-descriptors",descriptors()==baseline);
    assert(ideck_game_files_open(&caps,&r,sizeof r,&files)==0);path(p,game,"bin/control.EXE");fd=open(p,O_WRONLY|O_APPEND);assert(fd>=0&&write(fd,"x",1)==1&&!close(fd));
    check("modified-file-detected",ideck_game_files_unchanged(files)==-ESTALE);ideck_game_files_close(files);files=NULL;

    fixture(game,"replaced.exe",0x8664,0x20b,2);fixture(game,"replacement.exe",0x14c,0x10b,2);r=request(IDECK_LAUNCH_DEFAULT_ROOT,"Control Game","replaced.exe",NULL);assert(!ideck_game_files_open(&caps,&r,sizeof r,&files));
    struct stat pinned;assert(!fstat(ideck_game_files_executable(files),&pinned));char old[4096],replacement[4096];path(old,game,"replaced.exe");path(replacement,game,"replacement.exe");assert(!rename(replacement,old));assert(!stat(old,&actual));
    check("path-replacement-detected",actual.st_ino!=pinned.st_ino&&ideck_game_files_unchanged(files)==-ESTALE);assert(!fstat(ideck_game_files_executable(files),&actual));check("retained-handle-pins-original-object",actual.st_ino==pinned.st_ino);ideck_game_files_close(files);files=NULL;

    directory(standard,"Move Game");fixture(standard,"Move Game/control.exe",0x8664,0x20b,2);r=request(IDECK_LAUNCH_DEFAULT_ROOT,"Move Game","control.exe",NULL);assert(!ideck_game_files_open(&caps,&r,sizeof r,&files));path(old,standard,"Move Game");path(replacement,standard,"Moved Game");assert(!rename(old,replacement));directory(standard,"Move Game");fixture(standard,"Move Game/control.exe",0x8664,0x20b,2);
    check("installation-directory-replacement-detected",ideck_game_files_unchanged(files)==-ESTALE);ideck_game_files_close(files);files=NULL;

    fixture(game,"stable.exe",0x8664,0x20b,2);r=request(IDECK_LAUNCH_DEFAULT_ROOT,"Control Game","stable.exe","assets");assert(!ideck_game_files_open(&caps,&r,sizeof r,&files));path(old,game,"assets");path(replacement,game,"moved-assets");assert(!rename(old,replacement));directory(game,"assets");
    check("working-directory-replacement-detected",ideck_game_files_unchanged(files)==-ESTALE);ideck_game_files_close(files);files=NULL;
    check("close-null-is-safe",ideck_game_files_executable(NULL)==-1&&ideck_game_files_working(NULL)==-1&&ideck_game_files_appid(NULL)==0&&ideck_game_files_unchanged(NULL)==-EINVAL);ideck_game_files_close(NULL);
    check("all-final-handles-closed",descriptors()==baseline);

    // Native embedding root: no library exists yet. Steam may create one
    // after startup without replacing the registered app-root capability.
    directory(base,"native-data");char data[4096];path(data,base,"native-data");int datafd=open(data,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);assert(datafd>=0);
    r=request(IDECK_LAUNCH_DEFAULT_ROOT,"Control Game","control.exe",NULL);
    check("data-root-missing-library-refused",ideck_game_files_from_data(datafd,&r,sizeof r,&files)==-ENOENT&&!files);
    directory(data,"Steam");directory(data,"Steam/steamapps");directory(data,"Steam/steamapps/common");directory(data,"Steam/steamapps/common/Control Game");fixture(data,"Steam/steamapps/common/Control Game/control.exe",0x8664,0x20b,2);
    check("library-created-after-root-registration-accepted",!ideck_game_files_from_data(datafd,&r,sizeof r,&files)&&files);ideck_game_files_close(files);files=NULL;
    struct ideck_launch_request shared_request=request(IDECK_LAUNCH_ROOT,"Control Game","control.exe",NULL);
    check("data-root-selected-missing-shared-no-fallback",ideck_game_files_from_data(datafd,&shared_request,sizeof shared_request,&files)==-ENOENT&&!files);
    directory(data,"mnt");directory(data,"mnt/ideck");directory(data,"mnt/ideck/SteamLibrary");directory(data,"mnt/ideck/SteamLibrary/steamapps");directory(data,"mnt/ideck/SteamLibrary/steamapps/common");directory(data,"mnt/ideck/SteamLibrary/steamapps/common/Control Game");fixture(data,"mnt/ideck/SteamLibrary/steamapps/common/Control Game/control.exe",0x14c,0x10b,2);
    check("data-root-shared-does-not-select-default",!ideck_game_files_from_data(datafd,&shared_request,sizeof shared_request,&files)&&ideck_game_files_machine(files)==0x14c);ideck_game_files_close(files);files=NULL;
    path(old,data,"Steam");path(replacement,data,"Steam-moved");assert(!rename(old,replacement)&&!symlink(replacement,old));
    check("fixed-library-prefix-symlink-refused",ideck_game_files_from_data(datafd,&r,sizeof r,&files)<0&&!files);assert(!unlink(old)&&!rename(replacement,old));
    check("data-root-truncated-frame-refused",ideck_game_files_from_data(datafd,&r,sizeof r-1,&files)==-EINVAL&&!files);
    check("data-root-invalid-native-capability-refused",ideck_game_files_from_data(-1,&r,sizeof r,&files)==-EBADF&&!files);
    struct ideck_game_file_observation observed;
    check("policy-uninitialized-is-not-success",ideck_game_file_policy_observation(&observed)==-ENODEV&&observed.submitted==0&&observed.status==-EAGAIN&&observed.library==-1);
    check("policy-invalid-capability-refused",ideck_game_file_policy_start(-1)==-EBADF);
    path(p,data,"Steam/steamapps/common/Control Game/control.exe");fd=open(p,O_RDONLY|O_CLOEXEC);assert(fd>=0);
    check("policy-regular-file-root-refused",ideck_game_file_policy_start(fd)==-EPERM);assert(!close(fd));
    check("policy-native-root-registered-once",!ideck_game_file_policy_start(datafd)&&ideck_game_file_policy_start(datafd)==-EBUSY);assert(!close(datafd));unsigned policy_descriptors=descriptors();
    ideck_game_file_policy_inspect(&r);assert(!ideck_game_file_policy_observation(&observed));
    check("policy-retains-duplicate-not-borrowed-root",observed.submitted==1&&observed.completed_sequence==1&&observed.status==0&&observed.machine==0x8664);
    pthread_t threads[8];for(unsigned i=0;i<8;i++)assert(!pthread_create(&threads[i],NULL,inspect_requests,&r));for(unsigned i=0;i<8;i++)assert(!pthread_join(threads[i],NULL));assert(!ideck_game_file_policy_observation(&observed));
    check("concurrent-policy-newest-completion-and-count",observed.submitted==513&&observed.completed_sequence==513&&observed.status==0&&observed.appid==480&&observed.machine==0x8664);
    struct ideck_launch_request malformed=r;malformed.version++;ideck_game_file_policy_inspect(&malformed);assert(!ideck_game_file_policy_observation(&observed));
    check("policy-malformed-snapshot-refused",observed.submitted==514&&observed.completed_sequence==514&&observed.status==-EINVAL&&observed.machine==0&&observed.library==-1);
    pid_t child=fork();assert(child>=0);
    if(!child){ideck_game_file_policy_inspect(&r);struct ideck_game_file_observation own;_exit(ideck_game_file_policy_observation(&own)==-EXDEV?0:1);}
    int child_status;assert(waitpid(child,&child_status,0)==child);
    check("policy-foreign-native-owner-refused",WIFEXITED(child_status)&&WEXITSTATUS(child_status)==0);
    check("policy-requests-leave-only-one-retained-root",descriptors()==policy_descriptors&&policy_descriptors==baseline+1);
    assert(!close(caps.default_common)&&!close(caps.shared_common));assert(getcwd(after_cwd,sizeof after_cwd));check("global-cwd-unchanged",!strcmp(before_cwd,after_cwd));
    printf("checks=%u scope=HOST_SYNTHETIC_NO_EXECUTION\n",checks);return 0;
}
