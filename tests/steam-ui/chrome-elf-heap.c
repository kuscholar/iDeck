/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * Loads the user's matching official chrome_elf through the PE import table.
 * Exercises Win32 heap and thread teardown; no Steam client, network or auth.
 * This is not a PartitionAlloc unit test and does not bypass any check.
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
__declspec(dllimport) void *GetHandleVerifier(void);
static volatile LONG failures;
static DWORD WINAPI worker(void *unused) {
    (void)unused;
    if (!GetHandleVerifier()) InterlockedIncrement(&failures);
    for (unsigned i=0;i<2000;i++) {
        SIZE_T size=16+(i%257)*16;
        unsigned char *p=HeapAlloc(GetProcessHeap(),0,size);
        if (!p) { InterlockedIncrement(&failures); break; }
        for (SIZE_T j=0;j<size;j++) p[j]=(unsigned char)(i+j);
        for (SIZE_T j=0;j<size;j++) if (p[j]!=(unsigned char)(i+j)) { InterlockedIncrement(&failures); break; }
        if (!HeapFree(GetProcessHeap(),0,p)) InterlockedIncrement(&failures);
        p=malloc(size);
        if (!p) { InterlockedIncrement(&failures); break; }
        for (SIZE_T j=0;j<size;j++) p[j]=(unsigned char)(i^j);
        free(p);
    }
    return 0;
}
int main(void) {
    setvbuf(stdout,NULL,_IONBF,0);
    puts("elf-probe import-entry-reached");
    if (!GetHandleVerifier()) { puts("elf-probe verifier-unavailable"); return 10; }
    puts("elf-probe verifier-ready");
    for (unsigned round=0;round<4;round++) {
        HANDLE threads[4];
        for (unsigned i=0;i<4;i++) {
            threads[i]=CreateThread(NULL,0,worker,NULL,0,NULL);
            if (!threads[i]) { puts("elf-probe thread-create-failed"); return 11; }
        }
        if (WaitForMultipleObjects(4,threads,TRUE,30000)!=WAIT_OBJECT_0) {
            puts("elf-probe join-failed-or-timeout"); return 12;
        }
        for (unsigned i=0;i<4;i++) CloseHandle(threads[i]);
        printf("elf-probe thread-round=%u completed failures=%ld\n",round+1,failures);
    }
    printf("elf-probe result=%s\n",failures?"FAIL":"PASS");
    return failures?13:0;
}
