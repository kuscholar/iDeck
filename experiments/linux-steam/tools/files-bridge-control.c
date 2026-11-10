/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "LinuxLabRuntime.h"
#include "GameFilePolicy.h"
#include "NativeKernelLog.h"
#include <sys/stat.h>
#include <assert.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
extern unsigned ideck_lab_bridge_requests(void);
int main(int argc,char **argv){
    if(argc!=3||(strcmp(argv[2],"default")&&strcmp(argv[2],"shared")&&strcmp(argv[2],"symlink")))return 2;
    char logs[4096];int length=snprintf(logs,sizeof logs,"%s/NativeDiagnostics",argv[1]);assert(length>0&&length<(int)sizeof logs);
    assert(!mkdir(logs,0700)&&!ideck_native_log_start(logs));
    int descriptor=open(argv[1],O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);assert(descriptor>=0);
    assert(!ideck_game_file_policy_start(descriptor));assert(ideck_game_file_policy_start(descriptor)<0);assert(!close(descriptor));
    int status=ideck_linux_lab_run(argv[1]);assert(status==(125<<8));assert(ideck_lab_bridge_requests()==1);
    struct ideck_game_file_observation observed;assert(!ideck_game_file_policy_observation(&observed));assert(observed.submitted==1&&observed.completed_sequence==1&&observed.appid==480);
    if(!strcmp(argv[2],"symlink"))assert(observed.status<0&&observed.machine==0&&observed.library==-1);
    else assert(observed.status==0&&observed.machine==0x8664&&observed.library==!strcmp(argv[2],"shared"));
    assert(!ideck_native_health(26,"guest-exited",-95,-95));
    printf("actual-arm64-helper-to-native-file-policy=PASS\npolicy_status=%d library=%d wrapper_exit=125 game_launched=NO\n",observed.status,observed.library);return 0;
}
