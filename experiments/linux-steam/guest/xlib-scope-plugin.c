/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Own minimal plugin, dynamically loaded LOCAL/GLOBAL by the scope control.
 * Opaque Display and oversized output avoid relying on host X11 ABI headers.
 */
typedef unsigned long word;
extern void *XOpenDisplay(const char *);
extern word XDefaultRootWindow(void *);
extern word XCreateSimpleWindow(void *,word,int,int,unsigned,unsigned,unsigned,word,word);
extern int XGetWindowAttributes(void *,word,void *);
extern int XDestroyWindow(void *,word);
extern int XSync(void *,int);
extern int XCloseDisplay(void *);
int ideck_scope_query(void) {
    void *display=XOpenDisplay(0);if(!display)return 1;
    word window=XCreateSimpleWindow(display,XDefaultRootWindow(display),0,0,16,16,0,0,0);
    union {word align;char bytes[512];} attributes;
    int result=window&&XGetWindowAttributes(display,window,&attributes);
    if(window)XDestroyWindow(display,window);
    XSync(display,0);XCloseDisplay(display);return result?0:2;
}
