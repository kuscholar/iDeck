/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * Synthetic FLS lifecycle/process-isolation probe. No Steam or account data.
 */
#include <windows.h>
#include <stdio.h>
#include <wchar.h>
struct record { DWORD owner; volatile LONG calls; };
static struct record record;
static volatile LONG wrong_owner;
static VOID CALLBACK released(PVOID value) {
    struct record *r=value;
    if (r->owner!=GetCurrentProcessId()) InterlockedIncrement(&wrong_owner);
    InterlockedIncrement(&r->calls);
}
static void names(DWORD parent, wchar_t *ready, wchar_t *go) {
    swprintf(ready,80,L"Local\\MadeiraFlsReady_%lu",parent);
    swprintf(go,80,L"Local\\MadeiraFlsGo_%lu",parent);
}
static int child(DWORD parent) {
    wchar_t ready[80],go[80]; names(parent,ready,go);
    HANDLE r=OpenEventW(EVENT_MODIFY_STATE,FALSE,ready),g=OpenEventW(SYNCHRONIZE,FALSE,go);
    if (!r||!g) return 10;
    DWORD slot=FlsAlloc(released); if(slot==FLS_OUT_OF_INDEXES) return 11;
    record.owner=GetCurrentProcessId();
    if(FlsGetValue(slot)!=NULL || !FlsSetValue(slot,&record)) return 12;
    SetEvent(r);
    if(WaitForSingleObject(g,15000)!=WAIT_OBJECT_0) return 13;
    // Parent freeing its own slot must neither invoke nor clear our slot.
    if(record.calls || wrong_owner || FlsGetValue(slot)!=&record) return 14;
    if(!FlsFree(slot) || record.calls!=1 || wrong_owner) return 15;
    CloseHandle(r);CloseHandle(g);return 0;
}
static DWORD thread_slot;
static DWORD WINAPI worker(void *p) {
    return FlsSetValue(thread_slot,p)?0:20;
}
int wmain(int argc,wchar_t **argv) {
    setvbuf(stdout,NULL,_IONBF,0);
    if(argc==3 && !wcscmp(argv[1],L"--child")) return child(wcstoul(argv[2],NULL,10));
    record.owner=GetCurrentProcessId();
    // A thread-exit callback must run exactly once, before its join completes.
    thread_slot=FlsAlloc(released); if(thread_slot==FLS_OUT_OF_INDEXES) return 21;
    HANDLE t=CreateThread(NULL,0,worker,&record,0,NULL); if(!t)return 22;
    if(WaitForSingleObject(t,15000)!=WAIT_OBJECT_0)return 23;
    DWORD tc=99;GetExitCodeThread(t,&tc);CloseHandle(t);
    if(tc || record.calls!=1 || wrong_owner || !FlsFree(thread_slot) || record.calls!=1) return 24;
    puts("fls-probe thread-exit-once=PASS");
    record.calls=0;
    DWORD slot=FlsAlloc(released); if(slot==FLS_OUT_OF_INDEXES)return 25;
    if(!FlsSetValue(slot,&record))return 26;
    wchar_t ready[80],go[80],exe[32768],command[33000];names(GetCurrentProcessId(),ready,go);
    HANDLE r=CreateEventW(NULL,TRUE,FALSE,ready),g=CreateEventW(NULL,TRUE,FALSE,go);
    if(!r||!g||!GetModuleFileNameW(NULL,exe,32768))return 27;
    swprintf(command,33000,L"\"%ls\" --child %lu",exe,GetCurrentProcessId());
    STARTUPINFOW si={0};PROCESS_INFORMATION pi={0};si.cb=sizeof(si);
    if(!CreateProcessW(exe,command,NULL,NULL,FALSE,0,NULL,NULL,&si,&pi))return 28;
    HANDLE waits[2]={r,pi.hProcess};
    if(WaitForMultipleObjects(2,waits,FALSE,15000)!=WAIT_OBJECT_0)return 29;
    int parent_ok=FlsFree(slot) && record.calls==1 && !wrong_owner;
    SetEvent(g);
    DWORD wait=WaitForSingleObject(pi.hProcess,15000),code=99;
    if(wait==WAIT_OBJECT_0)GetExitCodeProcess(pi.hProcess,&code);
    printf("fls-probe parent_once=%d wrong_owner=%ld child_exit=%lu wait=%lu\n",parent_ok,wrong_owner,code,wait);
    CloseHandle(pi.hThread);CloseHandle(pi.hProcess);CloseHandle(r);CloseHandle(g);
    int pass=parent_ok && wait==WAIT_OBJECT_0 && code==0;
    printf("fls-probe result=%s\n",pass?"PASS":"FAIL");return pass?0:30;
}
