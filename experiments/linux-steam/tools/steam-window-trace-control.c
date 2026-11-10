/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST ONLY. Invoke the actual app's fixed Steam frontend and trace installer
 * against a NEW unauthenticated private root. No command/credential interface.
 * A supervising observer owns this process; timeout is not a guest crash.
 */
#include "LinuxLabRuntime.h"
#include "ToolInstall.h"
#include "X11TraceInstall.h"
#include "NativeKernelLog.h"
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

extern const char *sock_tmp_prefix;
static void *payload(const char *bundle,const char *relative,size_t *size) {
    char path[4096];
    int length=snprintf(path,sizeof path,"%s/%s",bundle,relative);
    if(length<0||length>=(int)sizeof path)return NULL;
    int descriptor=open(path,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
    if(descriptor<0)return NULL;
    struct stat st;
    if(fstat(descriptor,&st)||!S_ISREG(st.st_mode)||st.st_size<=0||st.st_size>262144){close(descriptor);return NULL;}
    void *data=malloc((size_t)st.st_size);
    if(!data){close(descriptor);return NULL;}
    size_t copied=0;
    while(copied<(size_t)st.st_size){
        ssize_t count=read(descriptor,(char *)data+copied,(size_t)st.st_size-copied);
        if(count<0&&errno==EINTR)continue;
        if(count<=0){free(data);close(descriptor);return NULL;}
        copied+=(size_t)count;
    }
    close(descriptor);*size=copied;return data;
}
int main(int argc,char **argv) {
    if(argc!=4||argv[1][0]!='/'||argv[2][0]!='/'||argv[3][0]!='/')return 2;
    struct ideck_tool_payload tool={0};struct ideck_x11_trace_payload trace={0};
    tool.executable=payload(argv[3],"LabCompatibility/ideck-madeira",&tool.executable_size);
    tool.compatibility=payload(argv[3],"LabCompatibility/compatibilitytool.vdf",&tool.compatibility_size);
    tool.manifest=payload(argv[3],"LabCompatibility/toolmanifest.vdf",&tool.manifest_size);
    trace.bytes=payload(argv[3],"LabDiagnostics/xlib-window-trace.so",&trace.size);
    if(!tool.executable||!tool.compatibility||!tool.manifest||!trace.bytes)return 2;
    /* AF_UNIX has a small native path limit. Only transient socket names use
     * an owned short system-temp directory; all data/logs remain external.
     * Never reuse or clean a previous runtime's socket directory. */
    char socket_directory[]="/tmp/ideck-xtrace-XXXXXX";
    if(!mkdtemp(socket_directory))return 2;
    char prefix[128];int length=snprintf(prefix,sizeof prefix,"%s/sock",socket_directory);
    if(length<0||length>=(int)sizeof prefix)return 2;
    sock_tmp_prefix=prefix;
    if(ideck_native_log_start(argv[2]))return 2;
    puts("HOST_STEAM_TRACE requested=1 activation=unverified credentials=none");fflush(stdout);
    int status=ideck_linux_lab_steam_frontend_with_trace(argv[1],&tool,&trace);
    printf("HOST_STEAM_TRACE initial_wait_status=%d guest_UI=unverified\n",status);fflush(stdout);
    /* No reuse, Wine handoff or teardown certificate is claimed here. */
    if(status<0)return 1;
    return (status&127)?128+(status&127):(status>>8)&255;
}
