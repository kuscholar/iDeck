/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Genuine distro Xlib client creating ONLY its own :99 control windows. The
 * separate static wire observer must report real map/unmap/remap/focus/destroy
 * transitions. Never run this fixture on the Steam display or an active root.
 */
typedef unsigned long word;
extern void *XOpenDisplay(const char *);
extern word XDefaultRootWindow(void *);
extern word XCreateSimpleWindow(void *,word,int,int,unsigned,unsigned,unsigned,word,word);
extern int XMapWindow(void *,word);
extern int XUnmapWindow(void *,word);
extern int XSetInputFocus(void *,word,int,word);
extern int XSync(void *,int);
extern int XDestroyWindow(void *,word);
extern int XCloseDisplay(void *);
extern int fork(void);
extern int waitpid(int,int *,int);
extern int open(const char *,int,...);
extern long write(int,const void *,word);
extern long read(int,void *,word);
extern int dup2(int,int);
extern int close(int);
extern int execl(const char *,const char *,...);
extern void _exit(int);
extern int snprintf(char *,word,const char *,...);
#if X11_STATE_WATCH_CONTROL
extern int kill(int,int);
struct timespec {long sec,nsec;};
extern int clock_gettime(int,struct timespec *);
extern int nanosleep(const struct timespec *,struct timespec *);
static long now_ms(void){struct timespec t;if(clock_gettime(1,&t))return -1;return t.sec*1000+t.nsec/1000000;}
static int pause_short(void){struct timespec t={0,100000000};return nanosleep(&t,(void *)0);}
static int wait_lines(unsigned wanted,long timeout_ms){
    long start=now_ms();if(start<0)return 87;
    for(;;){
        int fd=open("/x11-state-watch.jsonl",0);unsigned lines=0;char bytes[65536];
        if(fd>=0){long n=read(fd,bytes,sizeof bytes);close(fd);if(n<0||n==(long)sizeof bytes)return 88;for(long i=0;i<n;i++)lines+=bytes[i]=='\n';}
        if(lines>=wanted)return 0;
        long current=now_ms();if(current<0||current-start>timeout_ms)return 89;
        if(pause_short())return 90;
    }
}
static int watch_control(void *display,word a,word b){
    int child=fork();if(child<0)return 81;
    if(!child){
        int fd=open("/x11-state-watch.jsonl",0x2c1,0600);if(fd<0||dup2(fd,1)!=1)_exit(82);
        close(fd);execl("/x11-window-state","x11-window-state",(char *)0);_exit(83);
    }
    int stage=wait_lines(1,20000);
    if(!stage){XUnmapWindow(display,a);XSetInputFocus(display,b,1,0);XSync(display,0);stage=wait_lines(2,45000);}
    /* This is OUR synthetic child, not an observer timeout or device process.
     * Test deliberate SIGTERM delivery/reaping. Never escalate to SIGKILL or
     * target a guessed/reused PID. WNOHANG bounds the wait on this exact child. */
    int sent=kill(child,15),status=-1,reaped=0;long start=now_ms();
    while(start>=0){
        int result=waitpid(child,&status,1);if(result==child){reaped=1;break;}if(result<0)break;
        long current=now_ms();if(current<0||current-start>20000||pause_short())break;
    }
    char report[256];int n=snprintf(report,sizeof report,"{\"fixture_stage\":%d,\"child\":%d,\"sigterm_result\":%d,\"reaped\":%d,\"wait_status\":%d}\n",stage,child,sent,reaped,status);
    if(n<0||n>=(int)sizeof report)return 91;
    int fd=open("/x11-state-watch-child.json",0x2c1,0600);if(fd<0||write(fd,report,(word)n)!=n)return 92;close(fd);
    return stage?stage:sent||!reaped||status!=15?93:0;
}
#else
static int observe(unsigned number){
    char path[64];int n=snprintf(path,sizeof path,"/x11-state-%u.json",number);if(n<0||n>=(int)sizeof path)return 80;
    int child=fork();if(child<0)return 81;
    if(!child){
        int fd=open(path,0x2c1,0600);if(fd<0||dup2(fd,1)!=1)_exit(82);
        close(fd);execl("/x11-window-state","x11-window-state",(char *)0);_exit(83);
    }
    int status=-1;if(waitpid(child,&status,0)!=child||status)return 84;return 0;
}
#endif
int main(void){
    void *display=XOpenDisplay(":99");if(!display)return 70;
    word root=XDefaultRootWindow(display);
    word a=XCreateSimpleWindow(display,root,19,23,64,32,0,0,0x194e83);
    word b=XCreateSimpleWindow(display,root,119,123,160,90,0,0,0x327ac4);
    word c=XCreateSimpleWindow(display,root,-9,8,45,27,0,0,0x444444);
    if(!a||!b||!c)return 71;
    XMapWindow(display,a);XMapWindow(display,b);XSetInputFocus(display,a,1,0);XSync(display,0);
#if X11_STATE_WATCH_CONTROL
    int result=watch_control(display,a,b);if(result)return result;
#else
    int result=observe(0);if(result)return result;
    XUnmapWindow(display,a);XSetInputFocus(display,b,1,0);XSync(display,0);
    if((result=observe(1)))return result;
    XMapWindow(display,a);XSetInputFocus(display,a,1,0);XSync(display,0);
    if((result=observe(2)))return result;
    XDestroyWindow(display,b);XSync(display,0);
    if((result=observe(3)))return result;
#endif
    char ids[256];int n=snprintf(ids,sizeof ids,"{\"root\":%lu,\"a\":%lu,\"b\":%lu,\"c\":%lu}\n",root,a,b,c);
    if(n<0||n>=(int)sizeof ids)return 85;
    int fd=open("/x11-state-ids.json",0x2c1,0600);if(fd<0||write(fd,ids,(word)n)!=n)return 86;
    close(fd);XDestroyWindow(display,a);XDestroyWindow(display,c);
#if X11_STATE_WATCH_CONTROL
    XDestroyWindow(display,b);
#endif
    XCloseDisplay(display);return 0;
}
