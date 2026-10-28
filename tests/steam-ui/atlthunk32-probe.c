/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * Exercise public ATL thunk allocation, executable callback and free. The
 * observer records only our own stage/offsets and NEVER handles an exception.
 */
#include <windows.h>
#include <stdio.h>
#include <stdint.h>

typedef void *(WINAPI *Allocate)(void);
typedef void (WINAPI *Init)(void *, void *, SIZE_T);
typedef WNDPROC (WINAPI *Code)(void *);
typedef void (WINAPI *Free)(void *);
static FILE *output;
static unsigned stage;
static uintptr_t own_base;
static Free window_release;
struct callback_context { void *data; HWND window; unsigned freed; };

static void note(const char *name, unsigned value)
{
    if (output) { fprintf(output,"atl-probe-v1 stage=%u event=%s value=%u\n",stage,name,value); fflush(output); }
}
static LONG CALLBACK observe(EXCEPTION_POINTERS *info)
{
    note("exception-code",info->ExceptionRecord->ExceptionCode);
    if (info->ExceptionRecord->ExceptionCode==EXCEPTION_ACCESS_VIOLATION &&
        info->ExceptionRecord->NumberParameters>=2) {
        uintptr_t addr=info->ExceptionRecord->ExceptionInformation[1];
        note("access-kind",(unsigned)info->ExceptionRecord->ExceptionInformation[0]);
        if(own_base && addr>=own_base && addr-own_base<0x10000) note("own-pool-offset",(unsigned)(addr-own_base));
    }
    return EXCEPTION_CONTINUE_SEARCH;
}
static LRESULT CALLBACK target(HWND window,UINT msg,WPARAM wp,LPARAM lp)
{
    return (LRESULT)((uintptr_t)window ^ msg ^ wp ^ (uintptr_t)lp);
}
static LRESULT CALLBACK window_target(HWND argument,UINT msg,WPARAM wp,LPARAM lp)
{
    struct callback_context *ctx=(struct callback_context *)argument;
    if(msg==WM_APP+73)return 0x1357^msg^(LRESULT)wp^lp;
    if(msg==WM_NCDESTROY && ctx->data) {
        window_release(ctx->data); /* same API while inside a USER callback */
        ctx->data=NULL;ctx->freed++;
    }
    return DefWindowProcW(ctx->window,msg,wp,lp);
}
int main(void)
{
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);
    output=fopen("C:\\madeira-atlthunk-results.txt","w");
    if(!output)return 2;
    note("pointer-bits",sizeof(void *)*8);
    PVOID observer=AddVectoredExceptionHandler(1,observe);
    HMODULE module=LoadLibraryW(L"atlthunk.dll");
    if(!module){note("load-error",GetLastError());return 3;}
    Allocate allocate=(Allocate)(void *)GetProcAddress(module,"AtlThunk_AllocateData");
    Init init=(Init)(void *)GetProcAddress(module,"AtlThunk_InitData");
    Code code=(Code)(void *)GetProcAddress(module,"AtlThunk_DataToCode");
    Free release=(Free)(void *)GetProcAddress(module,"AtlThunk_FreeData");
    if(!allocate||!init||!code||!release){note("missing-export",1);return 4;}
    for(unsigned n=0;n<64;n++) {
        stage=n*10+1;note("before-allocate",n);
        void *data=allocate();if(!data){note("null-allocation",GetLastError());return 5;}
        stage=n*10+2;init(data,(void *)target,0x1357);
        WNDPROC thunk=code(data);
        MEMORY_BASIC_INFORMATION ci={0},di={0};
        if(!VirtualQuery((void *)thunk,&ci,sizeof(ci))||!VirtualQuery(data,&di,sizeof(di)))return 6;
        own_base=(uintptr_t)ci.AllocationBase;
        note("same-native-16k-page",((uintptr_t)thunk>>14)==((uintptr_t)data>>14));
        note("data-offset",(unsigned)((uintptr_t)data-own_base));
        note("code-protect",ci.Protect);note("data-protect",di.Protect);
        stage=n*10+3;note("before-callback",n);
        LRESULT result=thunk(NULL,3,5,7);
        if(result!=(LRESULT)(0x1357^3^5^7)){note("callback-mismatch",1);return 7;}
        stage=n*10+4;note("before-free",n);
        release(data);
        stage=n*10+5;note("after-free",n);
    }
    window_release=release;
    WNDCLASSW wc={0};wc.lpfnWndProc=DefWindowProcW;
    wc.hInstance=GetModuleHandleW(NULL);wc.lpszClassName=L"IDeckATLProbe";
    if(!RegisterClassW(&wc)){note("class-error",GetLastError());return 8;}
    for(unsigned n=0;n<64;n++) {
        struct callback_context ctx={0};stage=1000+n*10;
        ctx.window=CreateWindowExW(0,wc.lpszClassName,L"ATL diagnostic",WS_POPUP,
                                  0,0,16,16,NULL,NULL,wc.hInstance,NULL);
        if(!ctx.window){note("window-error",GetLastError());return 9;}
        ctx.data=allocate();if(!ctx.data)return 10;
        init(ctx.data,(void *)window_target,(SIZE_T)&ctx);
        SetLastError(0);
        if(!SetWindowLongPtrW(ctx.window,GWLP_WNDPROC,(LONG_PTR)code(ctx.data)) && GetLastError())return 11;
        stage=1001+n*10;
        if(SendMessageW(ctx.window,WM_APP+73,5,7)!=(LRESULT)(0x1357^(WM_APP+73)^5^7))return 12;
        stage=1002+n*10;note("before-destroy-callback-free",n);
        if(!DestroyWindow(ctx.window)||ctx.freed!=1){note("destroy-failed",1);return 13;}
        stage=1003+n*10;note("after-destroy-callback-free",n);
    }
    UnregisterClassW(wc.lpszClassName,wc.hInstance);
    FreeLibrary(module);
    if(observer)RemoveVectoredExceptionHandler(observer);
    note("PASS",128);fclose(output);return 0;
}
