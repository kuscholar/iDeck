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
static int root=-1,shared=-1;
static pid_t native_owner;
static struct ideck_game_file_observation last={.status=-EAGAIN,.library=-1};
static struct ideck_launch_request pending;
static uint64_t pending_sequence;
#if IDECK_LAB_CAPTURE_LAUNCH
static uint64_t capture_reservation;
#endif
static int copy_directory(int descriptor) {
    int copy=fcntl(descriptor,F_DUPFD_CLOEXEC,3);if(copy<0)return -errno;
    struct stat st;if(fstat(copy,&st)){int e=-errno;close(copy);return e;}
    if(!S_ISDIR(st.st_mode)||st.st_uid!=geteuid()){close(copy);return -EPERM;}
    return copy;
}
int ideck_game_file_policy_start_shared(int descriptor,int shared_descriptor) {
    pthread_mutex_lock(&lock);int result=0;
    if(root>=0){result=-EBUSY;goto done;}
    int copy=copy_directory(descriptor);if(copy<0){result=copy;goto done;}
    int shared_copy=-1;
    if(shared_descriptor>=0){shared_copy=copy_directory(shared_descriptor);if(shared_copy<0){close(copy);result=shared_copy;goto done;}}
    root=copy;shared=shared_copy;native_owner=getpid();
done:
    pthread_mutex_unlock(&lock);return result;
}
int ideck_game_file_policy_start(int descriptor) {return ideck_game_file_policy_start_shared(descriptor,-1);}
void ideck_game_file_policy_inspect(const struct ideck_launch_request *request) {
    if(!request)return;
    struct ideck_launch_request owned=*request;
    pthread_mutex_lock(&lock);uint64_t sequence=++last.submitted;int descriptor=-1,shared_descriptor=-1;
    int error=root<0?-ENODEV:native_owner!=getpid()?-EXDEV:0;
#if IDECK_LAB_CAPTURE_LAUNCH
    if(!error){
        if(pending_sequence||capture_reservation)error=-EBUSY;
        else capture_reservation=sequence;
    }
#endif
    if(!error){descriptor=fcntl(root,F_DUPFD_CLOEXEC,3);if(descriptor<0)error=-errno;}
    if(!error&&shared>=0){shared_descriptor=fcntl(shared,F_DUPFD_CLOEXEC,3);if(shared_descriptor<0)error=-errno;}
    pthread_mutex_unlock(&lock);
    struct ideck_game_files *files=NULL;
    if(!error)error=ideck_game_files_from_roots(descriptor,shared_descriptor,&owned,sizeof owned,&files);
    struct ideck_game_file_observation observation={.completed_sequence=sequence,.appid=owned.appid,.status=error,.library=-1};
    if(!error){observation.machine=ideck_game_files_machine(files);observation.library=(int)ideck_game_files_library(files);}
    ideck_game_files_close(files);if(descriptor>=0)close(descriptor);if(shared_descriptor>=0)close(shared_descriptor);
    pthread_mutex_lock(&lock);
#if IDECK_LAB_CAPTURE_LAUNCH
    if(capture_reservation==sequence){
        capture_reservation=0;
        if(!error){pending=owned;pending_sequence=sequence;}
    }
#endif
    if(sequence>last.completed_sequence){observation.submitted=last.submitted;last=observation;}
    pthread_mutex_unlock(&lock);
}
int ideck_game_file_policy_observation(struct ideck_game_file_observation *out) {
    if(!out)return -EINVAL;
    pthread_mutex_lock(&lock);*out=last;int result=root<0?-ENODEV:native_owner!=getpid()?-EXDEV:0;pthread_mutex_unlock(&lock);return result;
}
int ideck_game_file_policy_pending(struct ideck_launch_request *out,uint64_t *sequence) {
    if(!out||!sequence)return -EINVAL;
    pthread_mutex_lock(&lock);
    int result=root<0?-ENODEV:native_owner!=getpid()?-EXDEV:pending_sequence?0:-EAGAIN;
    if(!result){*out=pending;*sequence=pending_sequence;}
    pthread_mutex_unlock(&lock);return result;
}
int ideck_game_file_policy_discard(uint64_t sequence) {
    pthread_mutex_lock(&lock);
    int result=native_owner!=getpid()?-EXDEV:!sequence||sequence!=pending_sequence?-ESTALE:0;
    if(!result){pending=(struct ideck_launch_request){0};pending_sequence=0;}
    pthread_mutex_unlock(&lock);return result;
}
