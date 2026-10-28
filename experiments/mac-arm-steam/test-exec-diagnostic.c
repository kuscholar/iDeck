// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Mock the exact resolver boundary. Never spawn, exec or fork a host process.
#define dlsym test_symbol
#define dladdr test_address
#define execv test_execv
#define execvp test_execvp
#define fork test_fork
#define posix_spawn test_spawn
#include "exec-diagnostic.c"
#undef dlsym
#undef dladdr
#undef execv
#undef execvp
#undef fork
#undef posix_spawn
#include <assert.h>
#include <stdlib.h>
static char Path[]="/private/account-name/unknown-program";
static char *Args[]={Path,"-bigpicture","private-password",NULL};
static char *Env[]={"TOKEN=private",NULL};
static int Calls,Missing;
static int fake_exec(const char *p,char *const a[]){assert(p==Path && a==Args && errno==EDOM);++Calls;errno=EACCES;return -1;}
static pid_t fake_fork(void){assert(errno==EDOM);++Calls;errno=EPERM;return -1;}
static int fake_spawn(pid_t *p,const char *s,const posix_spawn_file_actions_t *a,const posix_spawnattr_t *b,char *const av[],char *const ev[]){assert(p && *p==99 && s==Path && !a && !b && av==Args && ev==Env && errno==EDOM);++Calls;errno=EBUSY;return EPERM;}
void *test_symbol(void *h,const char *name){assert(h==RTLD_NEXT);errno=EINVAL;if(Missing)return NULL;if(!strcmp(name,"fork"))return(void *)fake_fork;if(!strcmp(name,"posix_spawn"))return(void *)fake_spawn;assert(!strcmp(name,"execv")||!strcmp(name,"execvp"));return(void *)fake_exec;}
int test_address(const void *p,Dl_info *info){(void)p;(void)info;errno=ENOENT;return 0;}
int main(void){
    char *text=NULL;size_t n=0;FILE *stream=open_memstream(&text,&n);assert(stream);FILE *old=stderr;stderr=stream;
    errno=EDOM;assert(test_execv(Path,Args)==-1 && errno==EACCES);
    errno=EDOM;assert(test_execvp(Path,Args)==-1 && errno==EACCES);
    errno=EDOM;assert(test_fork()==-1 && errno==EPERM);
    pid_t pid=99;errno=EDOM;assert(test_spawn(&pid,Path,NULL,NULL,Args,Env)==EPERM && errno==EBUSY && pid==99);
    assert(Calls==4);Missing=1;errno=EDOM;assert(test_spawn(&pid,Path,NULL,NULL,Args,Env)==ENOSYS && errno==EDOM);
    fclose(stream);stderr=old;assert(!strstr(text,"account-name") && !strstr(text,"unknown-program") && !strstr(text,"private-password") && !strstr(text,"TOKEN"));assert(strstr(text,"other-redacted"));free(text);
    puts("exec observers PASS: exact arguments/results/incoming-outgoing errno; no unknown names/secret values; no host process calls");
}
