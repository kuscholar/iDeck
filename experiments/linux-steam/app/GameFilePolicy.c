/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "GameFilePolicy.h"
#include "GameFiles.h"
#include "LaunchProtocol.h"
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <pthread.h>
static pthread_mutex_t lock=PTHREAD_MUTEX_INITIALIZER;
static int root=-1;
static pid_t native_owner;
static struct ideck_game_file_observation last={.status=-EAGAIN,.library=-1};
int ideck_game_file_policy_start(int descriptor) {
    pthread_mutex_lock(&lock);int result=0;
    if(root>=0){result=-EBUSY;goto done;}
    int copy=fcntl(descriptor,F_DUPFD_CLOEXEC,3);if(copy<0){result=-errno;goto done;}
    struct stat st;
    if(fstat(copy,&st)){result=-errno;close(copy);goto done;}
    if(!S_ISDIR(st.st_mode)||st.st_uid!=geteuid()){result=-EPERM;close(copy);goto done;}
    root=copy;native_owner=getpid();
done:
    pthread_mutex_unlock(&lock);return result;
}
void ideck_game_file_policy_inspect(const struct ideck_launch_request *request) {
    if(!request)return;
    struct ideck_launch_request owned=*request;
    pthread_mutex_lock(&lock);uint64_t sequence=++last.submitted;int descriptor=-1;
    int error=root<0?-ENODEV:native_owner!=getpid()?-EXDEV:0;
    if(!error){descriptor=fcntl(root,F_DUPFD_CLOEXEC,3);if(descriptor<0)error=-errno;}
    pthread_mutex_unlock(&lock);
    struct ideck_game_files *files=NULL;
    if(!error)error=ideck_game_files_from_data(descriptor,&owned,sizeof owned,&files);
    struct ideck_game_file_observation observation={.completed_sequence=sequence,.appid=owned.appid,.status=error,.library=-1};
    if(!error){observation.machine=ideck_game_files_machine(files);observation.library=(int)ideck_game_files_library(files);}
    ideck_game_files_close(files);if(descriptor>=0)close(descriptor);
    pthread_mutex_lock(&lock);
    if(sequence>last.completed_sequence){observation.submitted=last.submitted;last=observation;}
    pthread_mutex_unlock(&lock);
}
int ideck_game_file_policy_observation(struct ideck_game_file_observation *out) {
    if(!out)return -EINVAL;
    pthread_mutex_lock(&lock);*out=last;int result=root<0?-ENODEV:native_owner!=getpid()?-EXDEV:0;pthread_mutex_unlock(&lock);return result;
}
