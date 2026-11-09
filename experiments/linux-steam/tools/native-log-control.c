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
    if(!strcmp(argv[1],"resources")){
        ideck_native_log_resources();size_t size;char *body=read_log(argv[2],&size);
        assert(strstr(body,"NATIVE_RESOURCE")&&strstr(body,"query_status=0 valid=1"));
        assert(strstr(body,"available_known=0")); // Host macOS API is deliberately unavailable.
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
        size_t size;char *body=read_log(argv[2],&size);
        assert(strstr(body,"HOST_RESOURCES:")&&strstr(body,"PROCESS_EVENT")&&strstr(body,"exec_committed"));
        assert(!strcmp(ideck_native_log_bridge_marker(),"IDECK_NATIVE_LOG_BRIDGE_V1"));free(body);
        puts("real-arm64-kernel-events-captured-with-fd666-closed=PASS");return 0;
    }
    return 2;
}
