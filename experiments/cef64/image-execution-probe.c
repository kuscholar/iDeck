/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md.
 * Independent execution/ABI/lifetime discriminator; never launches Steam/game. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <wchar.h>
_Static_assert(sizeof(void *)==8,"AMD64 only");
typedef uint64_t (*tls_fn)(uint64_t);
typedef uint64_t (*step_fn)(uint64_t,uint64_t (*)(uint64_t));
static uint64_t callback(uint64_t value) { return value*UINT64_C(17)+UINT64_C(0x7654321); }
static DWORD WINAPI worker(void *arg)
{
    tls_fn fn=(tls_fn)arg;
    return fn(77)!=UINT64_C(0x123456789abcdef0) || fn(99)!=77;
}
static int round_trip(unsigned round)
{
    HMODULE module=LoadLibraryW(L"C:\\iDeckCEF64ImageProbe\\ideck-x64-image.dll");
    if (!module) { printf("image-execution load-error=%lu\n",(unsigned long)GetLastError());return 1; }
    tls_fn tls=(tls_fn)(void *)GetProcAddress(module,"image_tls");
    step_fn step=(step_fn)(void *)GetProcAddress(module,"image_step");
    int bad=!tls||!step;
    if (!bad)
    {
        bad=tls(123)!=UINT64_C(0x123456789abcdef0);
        for (uint64_t i=1;i<=32;i++)
        {
            uint64_t seed=i*257,expected=callback(seed)+i+(unsigned char)seed+(unsigned char)(seed>>8);
            if (step(seed,callback)!=expected) bad=1;
        }
        HANDLE thread=CreateThread(NULL,0,worker,(void *)tls,0,NULL);
        DWORD code=99;
        if (!thread || WaitForSingleObject(thread,15000)!=WAIT_OBJECT_0) ExitProcess(9);
        if (!GetExitCodeThread(thread,&code)||code||tls(456)!=123) bad=1;
        CloseHandle(thread);
    }
    printf("image-execution round=%u calls=32 callback-and-thread-TLS=%s\n",round,bad?"FAIL":"PASS");
    /* Final round deliberately leaves the image loaded at child exit. */
    if (!round && !FreeLibrary(module)) bad=1;
    return bad;
}
int wmain(int argc,wchar_t **argv)
{
    setvbuf(stdout,NULL,_IONBF,0);
    if (argc==2 && !wcscmp(argv[1],L"--child")) return round_trip(0)||round_trip(1);
    if (argc!=1 && !(argc==2 && !wcscmp(argv[1],L"C:\\iDeckCEF64SourceProbe\\chrome_elf.dll"))) return 2;
    wchar_t path[1024],command[1100];DWORD length=GetModuleFileNameW(NULL,path,1024);
    if (!length||length>=1024) return 3;
    unsigned bad=0;
    for (unsigned i=0;i<3;i++)
    {
        int n=swprintf(command,1100,L"\"%ls\" --child",path);if(n<0||n>=1100)return 4;
        STARTUPINFOW startup={.cb=sizeof(startup)};PROCESS_INFORMATION p={0};DWORD code=99;
        BOOL created=CreateProcessW(path,command,NULL,NULL,TRUE,0,NULL,NULL,&startup,&p);
        if (created)
        {
            if (WaitForSingleObject(p.hProcess,60000)==WAIT_OBJECT_0) GetExitCodeProcess(p.hProcess,&code);
            else { TerminateProcess(p.hProcess,8);WaitForSingleObject(p.hProcess,5000); }
            CloseHandle(p.hThread);CloseHandle(p.hProcess);
        }
        printf("image-execution child=%u created=%u exit=%lu\n",i,!!created,(unsigned long)code);
        if (!created||code)bad++;
    }
    printf("image-execution result=%u; owned ABI test, not Steam/game validation\n",bad);
    return bad?1:0;
}
