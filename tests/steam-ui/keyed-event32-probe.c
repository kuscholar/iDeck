/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * Isolated default-vs-explicit keyed event and contended InitOnce contract. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>

typedef LONG (NTAPI *key_op)(HANDLE,const void *,BOOLEAN,const LARGE_INTEGER *);
typedef LONG (NTAPI *key_create)(HANDLE *,ACCESS_MASK,void *,ULONG);
static INIT_ONCE once;
static volatile LONG callbacks;
static HANDLE gate;
static volatile LONG failures;
static BOOL CALLBACK initialize(PINIT_ONCE p,void *param,void **context) {
    (void)p;(void)param;
    InterlockedIncrement(&callbacks);
    Sleep(40);
    *context=(void *)0x12340000;
    return TRUE;
}
static DWORD WINAPI worker(void *p) {
    void *context=NULL;(void)p;
    if(WaitForSingleObject(gate,2000)!=WAIT_OBJECT_0 ||
       !InitOnceExecuteOnce(&once,initialize,NULL,&context) || context!=(void *)0x12340000)
        InterlockedIncrement(&failures);
    return 0;
}
int main(void) {
    FILE *out=fopen("C:\\madeira-keyed-event32-results.txt","w");
    HMODULE ntdll=GetModuleHandleA("ntdll.dll");
    key_op wait=(key_op)GetProcAddress(ntdll,"NtWaitForKeyedEvent");
    key_op release=(key_op)GetProcAddress(ntdll,"NtReleaseKeyedEvent");
    key_create create=(key_create)GetProcAddress(ntdll,"NtCreateKeyedEvent");
    LARGE_INTEGER zero;HANDLE explicit_event=NULL;static LONG key;
    LONG dw,dr,ew,er,cs;HANDLE threads[4];DWORD joined;int i;
    if(!out)return 90;
    fprintf(out,"keyed-event32 begin pid=%lu\n",GetCurrentProcessId());fflush(out);
    if(!wait||!release||!create){fprintf(out,"missing export\n");fclose(out);return 91;}
    zero.QuadPart=0;
    dw=wait(NULL,&key,FALSE,&zero);dr=release(NULL,&key,FALSE,&zero);
    cs=create(&explicit_event,GENERIC_READ|GENERIC_WRITE,NULL,0);
    ew=cs?cs:wait(explicit_event,&key,FALSE,&zero);
    er=cs?cs:release(explicit_event,&key,FALSE,&zero);
    fprintf(out,"default_wait=%08lx default_release=%08lx create=%08lx explicit_wait=%08lx explicit_release=%08lx\n",dw,dr,cs,ew,er);fflush(out);
    if(explicit_event)CloseHandle(explicit_event);
    if(dw!=0x102||dr!=0x102||cs||ew!=0x102||er!=0x102){fprintf(out,"FAIL keyed contract\n");fclose(out);return 70;}
    InitOnceInitialize(&once);gate=CreateEventW(NULL,TRUE,FALSE,NULL);
    if(!gate){fprintf(out,"FAIL gate\n");fclose(out);return 71;}
    for(i=0;i<4;i++) {
        threads[i]=CreateThread(NULL,0,worker,NULL,0,NULL);
        if(!threads[i]){fprintf(out,"FAIL thread\n");fclose(out);return 72;}
    }
    SetEvent(gate);joined=WaitForMultipleObjects(4,threads,TRUE,5000);
    fprintf(out,"joined=%08lx callbacks=%ld failures=%ld\n",joined,callbacks,failures);
    fprintf(out,"%s\n",joined==WAIT_OBJECT_0&&callbacks==1&&!failures?"PASS":"FAIL init-once contract");
    fclose(out);
    return joined==WAIT_OBJECT_0&&callbacks==1&&!failures?0:73;
}
