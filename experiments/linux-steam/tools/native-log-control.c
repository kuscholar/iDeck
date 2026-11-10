/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST ONLY private-sink/real-kernel controls, never Steam login or game data. */
#include "NativeKernelLog.h"
#include "LinuxLabRuntime.h"
#include <assert.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <stdatomic.h>
#include <sys/wait.h>
static size_t read_health(const char *directory,char body[4096]){
    char path[4096];assert(snprintf(path,sizeof path,"%s/%s",directory,ideck_native_health_name())<(int)sizeof path);
    int fd=open(path,O_RDONLY|O_NOFOLLOW);assert(fd>=0);struct stat st;assert(!fstat(fd,&st)&&S_ISREG(st.st_mode)&&!(st.st_mode&0077));
    ssize_t n=read(fd,body,4095);assert(n>0&&n<4095&&read(fd,body+n,1)==0);body[n]=0;assert(!close(fd));return (size_t)n;
}
static struct {const char *directory;atomic_int done;atomic_uint observations;} reader_state;
static void *health_reader(void *unused){
    (void)unused;char body[4096];
    while(!atomic_load(&reader_state.done)){
        size_t n=read_health(reader_state.directory,body);assert(body[0]=='{'&&body[n-2]=='}'&&body[n-1]=='\n');
        assert(strstr(body,"\"schema\":1")&&strstr(body,"\"native_log\":\"kernel-"));atomic_fetch_add(&reader_state.observations,1);
    }return NULL;
}
static char *read_log(const char *directory,size_t *size){
    char path[4096];assert(snprintf(path,sizeof path,"%s/%s",directory,ideck_native_log_name())<(int)sizeof path);
    FILE *file=fopen(path,"rb");assert(file);assert(!fseek(file,0,SEEK_END));long end=ftell(file);assert(end>=0&&end<=IDECK_NATIVE_LOG_LIMIT);rewind(file);
    char *body=calloc(1,(size_t)end+1);assert(body);assert(fread(body,1,(size_t)end,file)==(size_t)end);fclose(file);*size=(size_t)end;return body;
}
int main(int argc,char **argv){
    if(argc<3||argc>4)return 2;
    if(!strcmp(argv[1],"refuse")){
        assert(ideck_native_log_start(argv[2])<0);assert(!ideck_native_log_name());assert(ideck_native_log_bytes()==0);
        puts("nonprivate-or-symlink-directory-refused=PASS");return 0;
    }
    assert(!ideck_native_log_start(argv[2]));assert(ideck_native_log_name());assert(ideck_native_log_start(argv[2])==-EBUSY);
    if(!strcmp(argv[1],"health-collision")){
        char path[4096];snprintf(path,sizeof path,"%s/%s",argv[2],ideck_native_health_name());
        int fd=open(path,O_WRONLY|O_CREAT|O_EXCL,0600);assert(fd>=0&&write(fd,"unrelated",9)==9&&!close(fd));
        assert(ideck_native_health(25,"idle",0,0)==-EPERM);char body[4096];assert(read_health(argv[2],body)==9&&!strcmp(body,"unrelated"));
        puts("unrelated-first-health-collision-preserved=PASS");return 0;
    }
    if(!strcmp(argv[1],"health")){
        assert(!ideck_native_health(25,"guest-running",3,2));char first[4096],second[4096];read_health(argv[2],first);
        assert(strstr(first,"\"sequence\":1")&&strstr(first,"\"phase\":7")&&strstr(first,"\"initial_call_returned\":false"));
        char line[1024];memset(line,'a',sizeof line-1);line[sizeof line-1]=0;for(unsigned i=0;i<10000;i++)ideck_native_log_line(line);
        size_t capped=ideck_native_log_bytes();assert(!ideck_native_health(25,"guest-exited",0,0));read_health(argv[2],second);
        assert(strstr(second,"\"sequence\":2")&&strstr(second,"\"initial_call_returned\":true")&&strstr(second,"\"append_log_capped\":true"));
        assert(ideck_native_log_bytes()==capped&&strcmp(first,second));puts("fresh-private-health-after-append-log-cap=PASS");
        assert(ideck_native_health(0,"idle",0,0)==-EINVAL&&ideck_native_health(25,"password=DO_NOT_PERSIST",0,0)==-EINVAL&&ideck_native_health(25,"idle",-22,0)==-EINVAL);
        read_health(argv[2],first);assert(!strcmp(first,second)&&!strstr(first,"DO_NOT_PERSIST"));puts("invalid-health-payload-does-not-replace-current=PASS");
        char target[4096],temporary[4096];snprintf(target,sizeof target,"%s/%s",argv[2],ideck_native_health_name());snprintf(temporary,sizeof temporary,"%s/.%s-3.tmp",argv[2],ideck_native_health_name());
        int guard=open(temporary,O_WRONLY|O_CREAT|O_EXCL,0600);assert(guard>=0&&write(guard,"owned-fixture",13)==13&&!close(guard));
        assert(ideck_native_health(25,"idle",0,0)==-EEXIST);read_health(argv[2],first);assert(!strcmp(first,second)&&!access(temporary,F_OK));assert(!unlink(temporary));
        puts("temporary-collision-keeps-prior-health-and-unrelated-file=PASS");
        pid_t child=fork();assert(child>=0);if(!child)_exit(ideck_native_health(25,"idle",0,0)==-EXDEV?0:1);
        int status;assert(waitpid(child,&status,0)==child&&status==0);read_health(argv[2],first);assert(!strcmp(first,second));puts("foreign-native-process-health-refused=PASS");
        char guarded[4096];snprintf(guarded,sizeof guarded,"%s/guarded-own-fixture",argv[2]);guard=open(guarded,O_WRONLY|O_CREAT|O_EXCL,0600);assert(guard>=0&&write(guard,"retained",8)==8&&!close(guard));
        assert(!unlink(target)&&!symlink(guarded,target));assert(ideck_native_health(25,"idle",0,0)==-EPERM);guard=open(guarded,O_RDONLY);assert(guard>=0);char value[9]={0};assert(read(guard,value,9)==8&&!strcmp(value,"retained")&&!close(guard));assert(!unlink(target));
        assert(!ideck_native_health(25,"guest-running",-95,-1));read_health(argv[2],first);assert(strstr(first,"\"tracked_guest_entries\":-95")&&strstr(first,"\"tracked_linux_workers\":-1"));puts("symlink-refused-and-unknown-counts-remain-unknown=PASS");
        reader_state.directory=argv[2];pthread_t reader;assert(!pthread_create(&reader,NULL,health_reader,NULL));
        for(unsigned i=0;i<100;i++)assert(!ideck_native_health(25,i%2?"guest-running":"guest-exited",0,0));
        atomic_store(&reader_state.done,1);assert(!pthread_join(reader,NULL));assert(atomic_load(&reader_state.observations)>0);puts("atomic-health-updates-never-expose-partial-json=PASS");return 0;
    }
    if(!strcmp(argv[1],"resources")){
        ideck_native_log_resources();ideck_linux_lab_log_tasks();size_t size;char *body=read_log(argv[2],&size);
        assert(strstr(body,"NATIVE_RESOURCE")&&strstr(body,"query_status=0 valid=1"));
        assert(strstr(body,"available_known=0")); // Host macOS API is deliberately unavailable.
        assert(strstr(body,"cpu_valid=1")&&strstr(body,"LINUX_MEMORY_CLASSES"));
        assert(strstr(body,"anonymous_guest_pages=0")&&strstr(body,"translation_tables=0"));
        assert(strstr(body,"LINUX_TASK_SAMPLE unavailable=runtime_not_started"));
        free(body);puts("public-self-task-metrics-host-scope-only=PASS");return 0;
    }
    if(!strcmp(argv[1],"privacy-cap")){
        ideck_native_log_line("fixed-safe-native-event");
        ideck_native_log_line("PaSsWoRd=DO_NOT_PERSIST_FIXTURE");
        ideck_native_log_line("refresh_token=DO_NOT_PERSIST_FIXTURE");
        char oversized[5000];memset(oversized,'z',sizeof oversized-1);oversized[sizeof oversized-1]=0;ideck_native_log_line(oversized);
        char line[1024];memset(line,'a',sizeof line-1);line[sizeof line-1]=0;
        for(unsigned i=0;i<10000;i++)ideck_native_log_line(line);
        size_t size;char *body=read_log(argv[2],&size);assert(size==ideck_native_log_bytes()&&size<=IDECK_NATIVE_LOG_LIMIT);
        assert(strstr(body,"fixed-safe-native-event")&&strstr(body,"native_line_omitted sensitive")&&strstr(body,"native_line_omitted oversized"));
        assert(!strstr(body,"DO_NOT_PERSIST_FIXTURE")&&strstr(body,"native_log_capacity_reached"));
        size_t stopped=ideck_native_log_bytes();ideck_native_log_line("after-cap-event");assert(ideck_native_log_bytes()==stopped);
        struct stat st;char path[4096];snprintf(path,sizeof path,"%s/%s",argv[2],ideck_native_log_name());assert(!stat(path,&st)&&!(st.st_mode&0077));
        free(body);puts("private-bounded-and-sensitive-lines-omitted=PASS");return 0;
    }
    if(!strcmp(argv[1],"kernel")&&argc==4){
        errno=0;assert(fcntl(666,F_GETFD)==-1&&errno==EBADF);
        assert(ideck_linux_lab_run(argv[3])==0);assert(ideck_linux_lab_live_guest_threads()==0);
        ideck_linux_lab_log_tasks();
        size_t size;char *body=read_log(argv[2],&size);
        assert(strstr(body,"HOST_RESOURCES:")&&strstr(body,"PROCESS_EVENT")&&strstr(body,"exec_committed"));
        assert(!strcmp(ideck_native_log_bridge_marker(),"IDECK_NATIVE_LOG_BRIDGE_V1"));free(body);
        puts("real-arm64-kernel-events-captured-with-fd666-closed=PASS");return 0;
    }
    return 2;
}
