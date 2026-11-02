/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * Own bounded concurrent-process public TLS discriminator. Not Steam's actual
 * HTTP implementation, authentication, or proof of wire request equivalence.
 * No payload logging, credential access, proxy or TLS verification changes.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <winhttp.h>
#include <wincrypt.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

static int fetch(unsigned stage, const WCHAR *host, INTERNET_PORT port,
                 const WCHAR *path, DWORD flags)
{
    HINTERNET session = NULL, connection = NULL, request = NULL;
    DWORD status = 0, bytes = sizeof(status), error = 0;
    unsigned total = 0;
    int ok = 0;
    const char *phase = "open";
    ULONGLONG start = GetTickCount64();
    printf("network stage=%u begin tls=%u\n", stage, !!(flags & WINHTTP_FLAG_SECURE));
    session = WinHttpOpen(L"iDeck-Isolated-Network-Probe/1.0", WINHTTP_ACCESS_TYPE_NO_PROXY,
                          WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);
    if (!session) goto done;
    phase = "timeouts";
    if (!WinHttpSetTimeouts(session, 5000, 5000, 5000, 5000)) goto done;
    phase = "connect";
    connection = WinHttpConnect(session, host, port, 0);
    if (!connection) goto done;
    phase = "request";
    request = WinHttpOpenRequest(connection, L"GET", path, NULL, WINHTTP_NO_REFERER,
                                 WINHTTP_DEFAULT_ACCEPT_TYPES, flags);
    if (!request) goto done;
    phase = "send";
    if (!WinHttpSendRequest(request, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
                            WINHTTP_NO_REQUEST_DATA, 0, 0, 0)) goto done;
    phase = "receive";
    if (!WinHttpReceiveResponse(request, NULL)) goto done;
    phase = "headers";
    if (!WinHttpQueryHeaders(request, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
                             WINHTTP_HEADER_NAME_BY_INDEX, &status, &bytes, WINHTTP_NO_HEADER_INDEX)) goto done;
    phase = "read";
    for (;;) {
        char buffer[4096];
        DWORD got = 0;
        if (!WinHttpReadData(request, buffer, sizeof(buffer), &got)) goto done;
        if (!got) { ok = status == 200 && total != 0; break; }
        total += got;
        if (total > 262144 || GetTickCount64() - start > 20000) {
            phase = "body-limit";
            error = ERROR_TIMEOUT;
            goto done;
        }
    }
done:
    if (!ok && !error) error = GetLastError();
    printf("network stage=%u phase=%s status=%lu bytes=%u ok=%d error=%lu elapsed-ms=%llu\n",
           stage, phase, status, total, ok, error, (unsigned long long)(GetTickCount64() - start));
    if (request) WinHttpCloseHandle(request);
    if (connection) WinHttpCloseHandle(connection);
    if (session) WinHttpCloseHandle(session);
    return ok;
}

static unsigned root_count(void)
{
    HCERTSTORE store=CertOpenSystemStoreW(0,L"ROOT");PCCERT_CONTEXT cert=NULL;unsigned n=0;
    if(store){while((cert=CertEnumCertificatesInStore(store,cert)))++n;CertCloseStore(store,0);}
    printf("concurrent-root-store count=%u error=%lu\n",n,store?0:GetLastError());
    return n;
}
static DWORD WINAPI worker(void *opaque)
{
    unsigned lane=(unsigned)(uintptr_t)opaque;
    int ok=1;
    for (unsigned i=0;i<2;++i)
        if (!fetch(lane*10+i,L"api.steampowered.com",443,
                   L"/ISteamDirectory/GetCMListForConnect/v1/?cellid=83&qoslevel=3",WINHTTP_FLAG_SECURE)) ok=0;
    return ok ? 7 : 8;
}
static int lanes(void)
{
    HANDLE t[2]={0};DWORD code[2]={0},wait=WAIT_FAILED;
    t[0]=CreateThread(NULL,0,worker,(void *)(uintptr_t)1,0,NULL);
    t[1]=CreateThread(NULL,0,worker,(void *)(uintptr_t)2,0,NULL);
    if(t[0]&&t[1])wait=WaitForMultipleObjects(2,t,TRUE,45000);
    if(wait!=WAIT_OBJECT_0){printf("concurrent-worker-deadline wait=%lu; isolated process exits124\n",wait);fflush(stdout);ExitProcess(124);}
    int ok=1;
    for(unsigned i=0;i<2;++i){
        if(t[i]){
            if(!GetExitCodeThread(t[i],&code[i]) || code[i]!=7)ok=0;
            CloseHandle(t[i]);
        }else ok=0;
    }
    printf("concurrent-threads wait=%lu result=%d codes=%lu,%lu\n",wait,ok,code[0],code[1]);
    return ok;
}
int wmain(int argc,WCHAR **argv)
{
    setvbuf(stdout,NULL,_IONBF,0);
    if(argc==4 && !wcscmp(argv[1],L"--child")){
        WCHAR *end=NULL;unsigned long long nonce=wcstoull(argv[2],&end,10);
        if(!end||*end||!nonce)return 2;
        unsigned slot=(unsigned)wcstoul(argv[3],&end,10);
        if(!end||*end||slot<1||slot>2)return 2;
        char path[100];snprintf(path,sizeof(path),"C:\\madeira-net-parallel-%llu-%u.txt",nonce,slot);
        if(!freopen(path,"w",stdout))return 2;setvbuf(stdout,NULL,_IONBF,0);
        WCHAR event[100];swprintf(event,100,L"Local\\iDeckNetParallel-%llu",nonce);
        HANDLE gate=OpenEventW(SYNCHRONIZE,FALSE,event);
        DWORD gate_error=gate?0:GetLastError();
        HINTERNET preload=WinHttpOpen(L"iDeck-Concurrent-Test/1.0",WINHTTP_ACCESS_TYPE_NO_PROXY,
            WINHTTP_NO_PROXY_NAME,WINHTTP_NO_PROXY_BYPASS,0);
        DWORD preload_error=preload?0:GetLastError();
        DWORD wait=gate?WaitForSingleObject(gate,10000):WAIT_FAILED;
        printf("concurrent-child-start nonce=%llu slot=%u gate=%d gate-error=%lu preload=%d preload-error=%lu wait=%lu\n",nonce,slot,gate!=NULL,gate_error,preload!=NULL,preload_error,wait);
        if(gate)CloseHandle(gate);
        unsigned roots=root_count();
        int ok=preload && roots && wait==WAIT_OBJECT_0 && lanes();
        if(preload)WinHttpCloseHandle(preload);
        printf("concurrent-child nonce=%llu slot=%u result=%d\n",nonce,slot,ok?0:1);
        fflush(stdout);ExitProcess(ok?7:8);
    }
    if(argc!=1)return 2;
    unsigned long long nonce=GetTickCount64();WCHAR event[100],self[2048];
    swprintf(event,100,L"Local\\iDeckNetParallel-%llu",nonce);
    HANDLE gate=CreateEventW(NULL,TRUE,FALSE,event);
    DWORD n=GetModuleFileNameW(NULL,self,2048);
    printf("concurrent-parent begin nonce=%llu; public HTTPS numeric states only\n",nonce);
    HINTERNET preload=WinHttpOpen(L"iDeck-Concurrent-Test/1.0",WINHTTP_ACCESS_TYPE_NO_PROXY,
        WINHTTP_NO_PROXY_NAME,WINHTTP_NO_PROXY_BYPASS,0);
    if(!gate||!preload||!n||n==2048)return 2;
    if(!root_count())return 2;
    PROCESS_INFORMATION child[2]={{0}};int created[2]={0};
    for(unsigned i=0;i<2;++i){
        WCHAR command[2200];STARTUPINFOW si={.cb=sizeof(si)};
        int count=swprintf(command,2200,L"\"%ls\" --child %llu %u",self,nonce,i+1);
        if(count>=0&&count<2200)created[i]=CreateProcessW(NULL,command,NULL,NULL,FALSE,0,NULL,NULL,&si,&child[i]);
        printf("concurrent-spawn slot=%u created=%d error=%lu\n",i+1,created[i],created[i]?0:GetLastError());
    }
    int ok=created[0]&&created[1]&&SetEvent(gate)&&lanes();
    for(unsigned i=0;i<2;++i){
        DWORD wait=WAIT_FAILED,code=0xffffffff;int fresh=0;
        if(created[i]){
            wait=WaitForSingleObject(child[i].hProcess,45000);
            if(wait==WAIT_OBJECT_0)GetExitCodeProcess(child[i].hProcess,&code);
            else{TerminateProcess(child[i].hProcess,124);WaitForSingleObject(child[i].hProcess,5000);}
            char path[100],expected[120],line[512];
            snprintf(path,sizeof(path),"C:\\madeira-net-parallel-%llu-%u.txt",nonce,i+1);
            snprintf(expected,sizeof(expected),"concurrent-child nonce=%llu slot=%u result=0",nonce,i+1);
            FILE *f=fopen(path,"r");if(f){while(fgets(line,sizeof(line),f))if(strstr(line,expected))fresh=1;fclose(f);}
            CloseHandle(child[i].hThread);CloseHandle(child[i].hProcess);
        }
        if(wait!=WAIT_OBJECT_0||code!=7||!fresh)ok=0;
        printf("concurrent-child-status slot=%u wait=%lu code=%lu fresh=%d\n",i+1,wait,code,fresh);
    }
    WinHttpCloseHandle(preload);CloseHandle(gate);
    printf("concurrent-network result=%d; not actual Steam authentication or equivalent HTTP stack\n",ok?0:1);
    return ok?0:1;
}
