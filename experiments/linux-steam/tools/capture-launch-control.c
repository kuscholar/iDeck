/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "GameFilePolicy.h"
#include "GameFiles.h"
#include "SharedSteamLibrary.h"
#include "WindowsLaunchMap.h"
#include <errno.h>
#include "LaunchProtocol.h"
#include "LinuxLabRuntime.h"
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <stdatomic.h>
#include <sched.h>
#include <sys/stat.h>
#if IDECK_LAB_CAPTURE_LAUNCH
static atomic_bool begin;
static void *inspect_concurrent(void *request){
 while(!atomic_load_explicit(&begin,memory_order_acquire))sched_yield();
 ideck_game_file_policy_inspect(request);return NULL;
}
#endif
static int check_default_routes(const char *root){
 char path[4096];snprintf(path,sizeof path,"%s/data",root);int data=open(path,O_RDONLY|O_DIRECTORY|O_CLOEXEC);
 int shared=ideck_shared_steam_prepare(root);
 if(data<0||shared<0)return 1;
 struct ideck_launch_request r={.magic=IDECK_LAUNCH_MAGIC,.version=IDECK_LAUNCH_VERSION,.appid=0x70000002,.verb=1,.argc=1};
 snprintf(r.install,sizeof r.install,"%sDefault Probe",IDECK_LAUNCH_DEFAULT_ROOT);
 snprintf(r.working,sizeof r.working,"%s",r.install);
 snprintf(r.executable,sizeof r.executable,"%sDefault Probe/probe.exe",IDECK_LAUNCH_DEFAULT_ROOT);
 snprintf(r.arguments,sizeof r.arguments,"%s",r.executable);r.argument_bytes=(unsigned)strlen(r.arguments)+1;
 struct ideck_game_files *files=NULL;
 int e=ideck_game_files_from_data(data,&r,sizeof r,&files);
 if(!e&&(ideck_game_files_machine(files)!=0x8664||ideck_game_files_library(files)!=IDECK_LIBRARY_DEFAULT))e=1;
 ideck_game_files_close(files);files=NULL;
 if(!e)e=ideck_game_files_from_roots(data,shared,&r,sizeof r,&files);
 if(!e&&ideck_game_files_library(files)!=IDECK_LIBRARY_DEFAULT)e=1;
 ideck_game_files_close(files);close(data);close(shared);return e;
}
int main(int argc,char **argv){
 if(argc!=2)return 2;
 char path[4096];snprintf(path,sizeof path,"%s/data",argv[1]);int data=open(path,O_RDONLY|O_DIRECTORY|O_CLOEXEC);
#if IDECK_LAB_DOCK_STORAGE
 char prior[4096],oldsource[4096],prefix[4096];
 snprintf(prior,sizeof prior,"%s/prior-layout-control",argv[1]);if(mkdir(prior,0700))return 23;
 snprintf(oldsource,sizeof oldsource,"%s/SharedSteamLibrary",prior);if(mkdir(oldsource,0700))return 24;
 snprintf(prefix,sizeof prefix,"%s/MadeiraPrefix",prior);
 if(ideck_shared_steam_prepare(prior)!=-EEXIST||access(prefix,F_OK)==0||access(oldsource,F_OK))return 25;
#endif
 int shared=ideck_shared_steam_prepare(argv[1]);
 if(data<0||shared<0||ideck_game_file_policy_start_shared(data,shared))return 3;
 close(data);close(shared);
 if(check_default_routes(argv[1]))return 19;
 int wait=ideck_linux_lab_run(argv[1]);if(wait){printf("guest-wait=%d\n",wait);return 4;}
#if !IDECK_LAB_CAPTURE_LAUNCH
 struct ideck_launch_request ignored;uint64_t ignored_seq;
 if(ideck_game_file_policy_pending(&ignored,&ignored_seq)!=-EAGAIN)return 17;
 struct ideck_game_file_observation observed;
 if(ideck_game_file_policy_observation(&observed)||observed.status||observed.machine!=0x8664)return 18;
 puts("PASS actual ARM64 IPC observation with request capture OFF; response125; no Windows execution");return 0;
#else
 struct ideck_launch_request r;uint64_t seq=0;
 if(ideck_game_file_policy_pending(&r,&seq)||seq!=1||r.appid!=0x70000001||r.argc!=3||strcmp(r.install,IDECK_LAUNCH_ROOT "Bridge Probe"))return 5;
 struct ideck_game_file_observation observation;
 if(ideck_game_file_policy_observation(&observation)||observation.status||observation.library!=1||observation.machine!=0x8664)return 6;
 struct ideck_launch_request original=r;
#if IDECK_LAB_DOCK_STORAGE
 struct ideck_windows_launch_map mapped;
 if(ideck_windows_launch_map(&r,&mapped)||mapped.appid!=r.appid||mapped.argc!=3)return 20;
 if(strcmp(mapped.executable,"C:\\SteamLibrary\\steamapps\\common\\Bridge Probe\\probe.exe"))return 21;
 const char *option=mapped.arguments+strlen(mapped.arguments)+1;
 if(strcmp(mapped.arguments,mapped.executable)||strcmp(option,"--level")||strcmp(option+strlen(option)+1,"1 2"))return 22;
#endif
 r.appid++;ideck_game_file_policy_inspect(&r);
 if(ideck_game_file_policy_pending(&r,&seq)||memcmp(&r,&original,sizeof r))return 7;
 if(ideck_game_file_policy_discard(seq))return 8;
 ideck_game_file_policy_inspect(&original);
 if(ideck_game_file_policy_pending(&r,&seq)||seq!=3||memcmp(&r,&original,sizeof r))return 9;
 if(ideck_game_file_policy_discard(seq))return 10;
 struct ideck_launch_request pair[2]={original,original};pair[0].appid=0x70000020;pair[1].appid=0x70000021;
 pthread_t threads[2];
 for(unsigned i=0;i<2;i++)if(pthread_create(&threads[i],NULL,inspect_concurrent,&pair[i]))return 11;
 atomic_store_explicit(&begin,1,memory_order_release);
 for(unsigned i=0;i<2;i++)if(pthread_join(threads[i],NULL))return 12;
 if(ideck_game_file_policy_pending(&r,&seq)||(r.appid!=pair[0].appid&&r.appid!=pair[1].appid))return 13;
 if(ideck_game_file_policy_observation(&observation)||observation.submitted!=5||observation.completed_sequence!=5)return 14;
 if(ideck_game_file_policy_discard(seq))return 15;
 ideck_game_file_policy_inspect(&original);
 if(ideck_game_file_policy_pending(&r,&seq)||seq!=6||memcmp(&r,&original,sizeof r))return 16;
 printf("PASS actual ARM64 IPC -> separate native shared files -> one owned request; busy retains first; two concurrent native requests yield one slot; native discard permits next; response125; Windows game NOT executed\n");return 0;
#endif
}
