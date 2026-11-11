/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST actual shared backend on one dedicated owner pthread. No UI imitation,
 * credentials, simulator, Wine/game or App success claim.
 */
#include "RetainedFrontend.h"
#include "NativeKernelLog.h"
#include "LinuxLabRuntime.h"
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include <signal.h>
extern const char *sock_tmp_prefix;
extern void sigusr1_handler(int);
struct context {const char *root;struct ideck_tool_payload tool;struct ideck_frontend_transport_boundary transport;int result;unsigned drains;};
static int drain_empty_host_transport(void *argument,int status){
    struct context *c=argument;struct ideck_frontend_result state;
    assert(!status&&!ideck_retained_frontend_snapshot(&state)&&state.phase==IDECK_FRONTEND_DRAINING);
    assert(!ideck_linux_lab_live_guest_threads()&&!ideck_linux_lab_native_worker_entries());
    struct sigaction action;assert(!sigaction(SIGUSR1,NULL,&action)&&action.sa_handler==sigusr1_handler);
    /* No embedded viewer exists in this C host fixture (RFB observer is a
     * different process). Hold the empty-set boundary to test ordering only. */
    usleep(100000);c->drains++;
    printf("HOST_EMPTY_TRANSPORT_BOUNDARY wave=%u before_signal_restore=1\n",state.wave);fflush(stdout);return 0;
}
static void *read_payload(const char *bundle,const char *name,size_t *size){
    char path[4096];int n=snprintf(path,sizeof path,"%s/LabCompatibility/%s",bundle,name);
    if(n<0||n>=(int)sizeof path)return NULL;
    int fd=open(path,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);if(fd<0)return NULL;
    struct stat st;if(fstat(fd,&st)||!S_ISREG(st.st_mode)||st.st_size<1||st.st_size>262144){close(fd);return NULL;}
    void *data=malloc(st.st_size);assert(data);size_t copied=0;
    while(copied<(size_t)st.st_size){ssize_t n=read(fd,(char *)data+copied,st.st_size-copied);if(n<0&&errno==EINTR)continue;assert(n>0);copied+=n;}
    close(fd);*size=copied;return data;
}
static void *run_owner(void *argument){
    struct context *c=argument;struct ideck_frontend_result result;
    assert(ideck_retained_frontend_run("relative",&c->tool,&c->transport,&result)==-EINVAL);
    for(unsigned wave=1;wave<=2;wave++){
        printf("DEDICATED_FRONTEND begin=%u\n",wave);fflush(stdout);
        int error=ideck_retained_frontend_run(c->root,&c->tool,&c->transport,&result);
        printf("DEDICATED_FRONTEND returned=%u native_error=%d guest_status=%d phase=%d reaped=%u\n",result.wave,error,result.guest_status,result.phase,result.reaped);fflush(stdout);
        if(error||result.guest_status||result.phase!=IDECK_FRONTEND_DORMANT){c->result=1;return NULL;}
        struct ideck_frontend_result snapshot;assert(!ideck_retained_frontend_snapshot(&snapshot));
        assert(snapshot.wave==wave&&snapshot.phase==IDECK_FRONTEND_DORMANT);
        assert(ideck_retained_frontend_run("/different-private-root",&c->tool,&c->transport,&snapshot)==-EXDEV);
        struct ideck_frontend_transport_boundary different={0};
        assert(ideck_retained_frontend_run(c->root,&c->tool,&different,&snapshot)==-EXDEV);
        ideck_native_log_resources();
    }
    return NULL;
}
int main(int argc,char **argv){
    if(argc!=4)return 2;
    struct context c={.root=argv[1]};
    c.transport=(struct ideck_frontend_transport_boundary){1,drain_empty_host_transport,&c};
    c.tool.executable=read_payload(argv[3],"ideck-madeira",&c.tool.executable_size);
    c.tool.compatibility=read_payload(argv[3],"compatibilitytool.vdf",&c.tool.compatibility_size);
    c.tool.manifest=read_payload(argv[3],"toolmanifest.vdf",&c.tool.manifest_size);
    if(!c.tool.executable||!c.tool.compatibility||!c.tool.manifest)return 2;
    char directory[]="/tmp/ideck-backend-XXXXXX",prefix[128];assert(mkdtemp(directory));
    assert(snprintf(prefix,sizeof prefix,"%s/sock",directory)<(int)sizeof prefix);sock_tmp_prefix=prefix;
    assert(!ideck_native_log_start(argv[2]));ideck_native_log_resources();
    pthread_t thread;assert(!pthread_create(&thread,NULL,run_owner,&c));
    /* Snapshot establishes that the worker has claimed this backend before
     * attempting a forbidden foreign-thread call; no actual second launch. */
    struct ideck_frontend_result s;
    for(unsigned i=0;i<5000;i++){assert(!ideck_retained_frontend_snapshot(&s));if(s.wave)break;usleep(1000);}
    assert(s.wave);
    assert(ideck_retained_frontend_run(c.root,&c.tool,&c.transport,&s)==-EPERM);
    assert(!pthread_join(thread,NULL));
    assert(c.result||c.drains==2);
    puts("scope=HOST_SHARED_BACKEND_DEDICATED_OWNER_ONLY_NOT_IPAD_WINE_GAME_OR_FULL_HANDOFF");
    return c.result;
}
