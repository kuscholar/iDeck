/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Actual distribution libX11/glibc ABI control; no Valve code/credentials.
 * Public Xlib ABI reference: https://www.x.org/releases/current/doc/libX11/libX11/libX11.html
 * Its own error handler admits ONLY the deliberately destroyed test window.
 * No error handler is installed in Steam or any other process.
 */
typedef unsigned long word;
#ifndef X11_EXTRA_ATTRIBUTE_QUERIES
#define X11_EXTRA_ATTRIBUTE_QUERIES 0
#endif
struct attributes {
    int x,y,width,height,border_width,depth;
    void *visual;
    word root;
    int window_class,bit_gravity,win_gravity,backing_store;
    word backing_planes,backing_pixel;
    int save_under;
    word colormap;
    int map_installed,map_state;
    long all_event_masks,your_event_mask,do_not_propagate_mask;
    int override_redirect;
    void *screen;
};
struct xerror {int type;void *display;word resource,serial;unsigned char error,request,minor;};
_Static_assert(sizeof(struct attributes)==136,"Linux ARM64 XWindowAttributes ABI");
_Static_assert(sizeof(struct xerror)==40,"Linux ARM64 XErrorEvent ABI");
extern int XInitThreads(void);
extern void *XOpenDisplay(const char *);
extern word XDefaultRootWindow(void *);
extern word XCreateSimpleWindow(void *,word,int,int,unsigned,unsigned,unsigned,word,word);
extern int XGetWindowAttributes(void *,word,struct attributes *);
extern int XMapWindow(void *,word);
extern int XDestroyWindow(void *,word);
extern int XCloseDisplay(void *);
extern void *XGetImage(void *,word,int,int,unsigned,unsigned,word,int);
extern word XGetPixel(void *,int,int);
extern int XDestroyImage(void *);
extern int (*XSetErrorHandler(int (*)(void *,struct xerror *)))(void *,struct xerror *);
extern int fork(void);
extern int waitpid(int,int *,int);
extern int open(const char *,int,...);
extern long write(int,const void *,word);
extern int close(int);
extern int snprintf(char *,word,const char *,...);
static word expected_missing;
static unsigned stage,unexpected_errors,bad_windows,live_attributes,images,extra_attributes;
static word image_bytes,pixel_checks;
static unsigned hash=2166136261U;
static int error_handler(void *display,struct xerror *event){
    (void)display;
    if(expected_missing&&event->resource==expected_missing&&event->error==3&&event->request==3)bad_windows++;
    else unexpected_errors++;
    return 0;
}
static int worker(unsigned role){
    stage=1;void *display=XOpenDisplay(":97");if(!display)return 1;
    XSetErrorHandler(error_handler);word root=XDefaultRootWindow(display),color=role?0x327ac4:0x194e83;
    for(unsigned i=0;i<16;i++){
        stage=2;word window=XCreateSimpleWindow(display,root,role?128:16,16,64,32,0,0,color);if(!window)return 1;
        struct attributes attr;
        stage=3;if(!XGetWindowAttributes(display,window,&attr)||attr.width!=64||attr.height!=32||attr.map_state!=0)return 1;live_attributes++;
        stage=4;XMapWindow(display,window);if(!XGetWindowAttributes(display,window,&attr)||attr.map_state!=2)return 1;live_attributes++;
        if(i==0)for(unsigned query=0;query<X11_EXTRA_ATTRIBUTE_QUERIES;query++){
            if(!XGetWindowAttributes(display,window,&attr)||attr.map_state!=2)return 1;extra_attributes++;
        }
        stage=5;void *image=XGetImage(display,window,0,0,64,32,~0UL,2);if(!image)return 1;
        for(int y=0;y<32;y++)for(int x=0;x<64;x++){
            word pixel=XGetPixel(image,x,y)&0xffffff;if(pixel!=color)return 1;pixel_checks++;
            for(unsigned byte=0;byte<4;byte++){hash^=(unsigned)((pixel>>(byte*8))&255);hash*=16777619U;}
        }
        XDestroyImage(image);images++;image_bytes+=64*32*4;
        stage=6;XDestroyWindow(display,window);expected_missing=window;
        if(XGetWindowAttributes(display,window,&attr)!=0||bad_windows!=i+1)return 1;
        expected_missing=0;if(unexpected_errors)return 1;
    }
    stage=7;XCloseDisplay(display);stage=0;return 0;
}
int main(void){
    if(!XInitThreads())return 80;
    // Warm a real Xlib call BEFORE fork. An enabled logger must safely discard
    // its inherited parent fd/lock state in the child, not mix process files.
    void *warm=XOpenDisplay(":97");struct attributes attr;
    if(!warm||!XGetWindowAttributes(warm,XDefaultRootWindow(warm),&attr))return 79;
    XCloseDisplay(warm);int child=fork();if(child<0)return 81;
    unsigned role=child==0;int status=worker(role);
    if(!role){int result=-1;if(waitpid(child,&result,0)!=child||result){stage=8;status=1;}}
    char report[1024];int n=snprintf(report,sizeof report,
        "status=%d\nfailure_stage=%u\nwire_error=%u\nlive_attributes=%u\nexpected_bad_windows=%u\nimages=%u\nimage_bytes=%lu\npixel_comparisons=%lu\nframebuffer_fnv1a32=%u\nextra_attributes=%u\nscope=real_ARM64_libX11_own_windows_not_Steam_or_iPad_success\n",
        status,stage,unexpected_errors,live_attributes,bad_windows,images,image_bytes,pixel_checks,hash,extra_attributes);
    if(n<0||n>=(int)sizeof report)return 82;
    int fd=open(role?"/x11-window-child.txt":"/x11-window-parent.txt",0x241,0600);if(fd<0)return 83;
    if(write(fd,report,(word)n)!=n)status=84;close(fd);return status;
}
