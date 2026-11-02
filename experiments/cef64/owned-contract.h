/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * Isolated Windows API discriminator, no Valve module or network activity.
 */
#ifndef IDECK_CEF64_OWNED_CONTRACT_H
#define IDECK_CEF64_OWNED_CONTRACT_H
#include <string.h>
static int cef64_owned_child_pools(void)
{
    FILE *out=fopen("C:\\madeira-cef64-child-results.txt", "w");
    const SIZE_T sizes[2]={UINT64_C(0x40000000),UINT64_C(0x40010000)};
    const uintptr_t bases[2]={UINT64_C(0x7780000000),UINT64_C(0x773fff0000)};
    void *held[2]={0};int result=0;
    if(!out)return 80;
    for(unsigned i=0;i<2;i++) {
        MEMORY_BASIC_INFORMATION info;
        held[i]=VirtualAlloc(NULL,sizes[i],MEM_RESERVE,PAGE_NOACCESS);
        int ok=(uintptr_t)held[i]==bases[i] && VirtualQuery(held[i],&info,sizeof(info))==sizeof(info) &&
            info.AllocationBase==held[i] && info.RegionSize==sizes[i] && info.State==MEM_RESERVE;
        if(ok) {
            unsigned char *page=(unsigned char *)held[i]+(i?0x10000:0);
            ok=VirtualAlloc(page,0x4000,MEM_COMMIT,PAGE_READWRITE)==page;
            if(ok){for(unsigned j=0;j<0x4000;j++)if(page[j])ok=0;
                memset(page,0x69,0x4000);ok=ok&&page[0]==0x69&&page[0x3fff]==0x69;}
        }
        fprintf(out,"cef64-child allocation=%u reserve-query-zero-write-read=%d\n",i,ok);
        if(!ok){result=81+i;break;}
    }
    for(unsigned i=0;i<2;i++)if(held[i]&&!VirtualFree(held[i],0,MEM_RELEASE))result=85;
    fprintf(out,"cef64-child result=%d\n",result);fclose(out);return result;
}
static int cef64_owned_contract(int split)
{
    const SIZE_T sizes[] = {UINT64_C(0x40000000), UINT64_C(0x40010000),
        UINT64_C(0x400000000), UINT64_C(0x400010000), UINT64_C(0x200000000),
        UINT64_C(0x100000000), UINT64_C(0x20000000), UINT64_C(0x20000000)};
    uintptr_t expected[] = {UINT64_C(0x7100000000), UINT64_C(0x717fff0000),
        UINT64_C(0x7c00000000), UINT64_C(0x77ffff0000), UINT64_C(0x7200000000),
        UINT64_C(0x7600000000), UINT64_C(0x7700000000), UINT64_C(0x7700000000)};
    unsigned char *owned[8] = {0};
    const unsigned count = split >= 2 ? 8 : split ? 7 : 5;
    char layout[2] = {0};
    int standalone = GetEnvironmentVariableA("MADEIRA_CEF64_STANDALONE_LAYOUT", layout, sizeof(layout)) == 1 && layout[0] == '1';
    if (split >= 2) expected[6] = UINT64_C(0x70a0000000);
    if (standalone) {
        expected[5] = UINT64_C(0x7400000000);
        expected[7] = UINT64_C(0x7140000000);
    }
    char compact_flag[2]={0};
    int compact=standalone && GetEnvironmentVariableA("MADEIRA_CEF64_COMPACT_SOURCE_POOLS",compact_flag,sizeof(compact_flag))==1 && compact_flag[0]=='1';
    if(compact){expected[0]=UINT64_C(0x7140000000);expected[1]=UINT64_C(0x70ffff0000);expected[7]=UINT64_C(0x7180000000);}
    int result = 0;
    setvbuf(stdout, NULL, _IONBF, 0);
    puts("cef64-owned-contract begin; exact reserved ownership, not CEF startup");
    for (unsigned i = 0; i < count; ++i) {
        MEMORY_BASIC_INFORMATION info;
        if (split >= 2 && i == 7) {
            typedef void *(WINAPI *alloc2_fn)(HANDLE, void *, SIZE_T, ULONG, ULONG, MEM_EXTENDED_PARAMETER *, ULONG);
            alloc2_fn alloc2 = (alloc2_fn)(uintptr_t)GetProcAddress(GetModuleHandleW(L"kernelbase.dll"), "VirtualAlloc2");
            owned[i] = alloc2 ? alloc2(NULL, NULL, sizes[i], MEM_RESERVE | MEM_RESERVE_PLACEHOLDER, PAGE_NOACCESS, NULL, 0) : NULL;
        } else owned[i] = VirtualAlloc(NULL, sizes[i], MEM_RESERVE, PAGE_NOACCESS);
        printf("cef64-owned-contract allocation=%u exact=%u error=%lu\n", i,
            (uintptr_t)owned[i] == expected[i], owned[i] ? 0ul : GetLastError());
        if ((uintptr_t)owned[i] != expected[i]) { result = 10 + i; break; }
        if (VirtualQuery(owned[i], &info, sizeof(info)) != sizeof(info) ||
            info.AllocationBase != owned[i] || info.State != MEM_RESERVE || info.RegionSize != sizes[i]) {
            result = 20 + i; break;
        }
        if (split >= 2 && i == 7) {
            printf("cef64-owned-contract allocation=%u placeholder-reserved=1\n", i);
            continue;
        }
        const SIZE_T offsets[] = {(i == 1 || i == 3) ? 0x10000 : 0, sizes[i] - 0x4000};
        for (unsigned edge = 0; edge < 2; ++edge) {
            unsigned char *page = owned[i] + offsets[edge];
            if (VirtualAlloc(page, 0x4000, MEM_COMMIT, PAGE_READWRITE) != page) { result = 30 + i; break; }
            for (unsigned j = 0; j < 0x4000; ++j) if (page[j]) { result = 40 + i; break; }
            if (result) break;
            const unsigned char value = (unsigned char)(0x31 + i * 2 + edge);
            memset(page, value, 0x4000);
            for (unsigned j = 0; j < 0x4000; ++j) if (page[j] != value) { result = 50 + i; break; }
            if (result) break;
            printf("cef64-owned-contract allocation=%u edge=%u committed-zero-write-read=1\n", i, edge);
        }
        if (result) break;
    }
    if (!result) {
        void *foreign = VirtualAlloc((void *)(uintptr_t)(split ? UINT64_C(0x7500000000) : UINT64_C(0x7600000000)),
                                    UINT64_C(0x100000000), MEM_RESERVE, PAGE_NOACCESS);
        printf("cef64-owned-contract generic-fex-jumbo-refused=%u error=%lu\n",
               !foreign, foreign ? 0ul : GetLastError());
        if (foreign) { VirtualFree(foreign, 0, MEM_RELEASE); result = 61; }
    }
    if (!result) {
        void *duplicate = VirtualAlloc(NULL, sizes[0], MEM_RESERVE, PAGE_NOACCESS);
        printf("cef64-owned-contract duplicate-refused=%u error=%lu\n", !duplicate, duplicate ? 0ul : GetLastError());
        if (duplicate) { VirtualFree(duplicate, 0, MEM_RELEASE); result = 60; }
    }
    if (!result && split == 2) {
        /* Actual90 child: free an over-reservation then reserve its aligned
         * subrange. The pool-like size must not be routed into a used lease. */
        void *outer = VirtualAlloc((void *)(uintptr_t)UINT64_C(0x7760000000),
                                  UINT64_C(0x7fff0000), MEM_RESERVE, PAGE_NOACCESS);
        int ok = outer == (void *)(uintptr_t)UINT64_C(0x7760000000);
        if (outer) ok = VirtualFree(outer, 0, MEM_RELEASE) && ok;
        void *inner = ok ? VirtualAlloc((void *)(uintptr_t)UINT64_C(0x7780000000),
                              UINT64_C(0x40000000), MEM_RESERVE, PAGE_NOACCESS) : NULL;
        ok = ok && inner == (void *)(uintptr_t)UINT64_C(0x7780000000);
        if (inner) {
            void *data = VirtualAlloc(inner, 0x4000, MEM_COMMIT, PAGE_READWRITE);
            ok = ok && data == inner;
            if (data) { memset(data, 0x5a, 0x4000); ok = ok && *(unsigned char *)data == 0x5a; }
            ok = VirtualFree(inner, 0, MEM_RELEASE) && ok;
        }
        printf("cef64-owned-contract realigned-foreign-fixed=%d\n", ok);
        if (!ok) result = 62;
    }
    if (!result && split == 3) {
        /* V8 reserves more than one external-entity subspace. Splitting a
         * placeholder preserves its ownership; it is not a full release. */
        typedef void *(WINAPI *alloc2_fn)(HANDLE, void *, SIZE_T, ULONG, ULONG, MEM_EXTENDED_PARAMETER *, ULONG);
        alloc2_fn alloc2 = (alloc2_fn)(uintptr_t)GetProcAddress(GetModuleHandleW(L"kernelbase.dll"), "VirtualAlloc2");
        MEMORY_BASIC_INFORMATION info;
        int divided = VirtualFree(owned[7], 0x10000, MEM_RELEASE | MEM_PRESERVE_PLACEHOLDER);
        unsigned char *segment = divided && alloc2 ? alloc2(NULL, owned[7], 0x10000,
            MEM_RESERVE | MEM_COMMIT | MEM_REPLACE_PLACEHOLDER, PAGE_READWRITE, NULL, 0) : NULL;
        int backed = segment == owned[7];
        if (backed) {
            for (unsigned n = 0; n < 0x10000; ++n) if (segment[n]) backed = 0;
            memset(segment, 0x6b, 0x10000);
            backed = backed && segment[0] == 0x6b && segment[0xffff] == 0x6b;
        }
        int remains = VirtualQuery(owned[7] + 0x10000, &info, sizeof(info)) == sizeof(info) &&
            info.State == MEM_RESERVE && info.RegionSize == sizes[7] - 0x10000;
        printf("cef64-placeholder split-preserve=%d replace-zero-write-read=%d remaining-owned=%d\n", divided, backed, remains);
        if (!divided || !backed || !remains) result = 87;
        if (segment && !VirtualFree(segment, 0x10000, MEM_RELEASE | MEM_PRESERVE_PLACEHOLDER)) result = 88;
        if (divided && !VirtualFree(owned[7], sizes[7], MEM_RELEASE | MEM_COALESCE_PLACEHOLDERS)) result = 89;
        if (!result) {
            char four[2]={0};
            unsigned extra_count=standalone && GetEnvironmentVariableA("MADEIRA_CEF64_FOUR_TABLES",four,sizeof(four))==1 && four[0]=='1' ? 3 : 2;
            char six[2]={0};
            if(extra_count==3 && GetEnvironmentVariableA("MADEIRA_CEF64_SIX_TABLES",six,sizeof(six))==1 && six[0]=='1')extra_count=5;
            char seven[2]={0};
            if(extra_count==5 && GetEnvironmentVariableA("MADEIRA_CEF64_SEVENTH_TABLE",seven,sizeof(seven))==1 && seven[0]=='1')extra_count=6;
            char eight[2]={0};
            if(extra_count==6 && GetEnvironmentVariableA("MADEIRA_CEF64_EIGHTH_TABLE",eight,sizeof(eight))==1 && eight[0]=='1')extra_count=7;
            char nine[2]={0};
            int tail_nine=GetEnvironmentVariableA("MADEIRA_CEF64_NINTH_TAIL_TABLE",nine,sizeof(nine))==1 && nine[0]=='1';
            if(extra_count==7 && (compact || tail_nine))extra_count=8;
            char twelve[2]={0};
            if(extra_count==8 && tail_nine && GetEnvironmentVariableA("MADEIRA_CEF64_TWELVE_TABLES",twelve,sizeof(twelve))==1 && twelve[0]=='1')extra_count=11;
            void *extra[11] = {0};
            for (unsigned n = 0; n < extra_count; ++n) {
                extra[n] = alloc2(NULL, NULL, sizes[7], MEM_RESERVE | MEM_RESERVE_PLACEHOLDER,
                                  PAGE_NOACCESS, NULL, 0);
                DWORD error = extra[n] ? 0 : GetLastError();
                int distinct = extra[n] && extra[n] != owned[7];
                for(unsigned old=0;old<n;old++)if(extra[n]==extra[old])distinct=0;
                printf("cef64-placeholder extra-index=%u independent=%d distinct=%d error=%lu\n",
                    n + 1, !!extra[n], distinct, error);
                if (!distinct) { result = 90; break; }
            }
            for (unsigned n = 0; n < extra_count; ++n)
                if (extra[n] && !VirtualFree(extra[n], 0, MEM_RELEASE)) result = 91;
        }
    }
    if (!result && split == 3 && !standalone) {
        STARTUPINFOW startup={.cb=sizeof(startup)};PROCESS_INFORMATION child={0};
        WCHAR command[]=L"C:\\steam64-cef-load-probe.exe --child-pools --type=crashpad-handler";
        DWORD exit_code=UINT32_C(0xffffffff);
        int created=CreateProcessW(NULL,command,NULL,NULL,FALSE,0,NULL,NULL,&startup,&child);
        if(created) {
            if(WaitForSingleObject(child.hProcess,30000)==WAIT_OBJECT_0)
                GetExitCodeProcess(child.hProcess,&exit_code);
            else { TerminateProcess(child.hProcess,86); WaitForSingleObject(child.hProcess,5000); }
            CloseHandle(child.hThread);CloseHandle(child.hProcess);
        }
        printf("cef64-owned-contract child-created=%d child-exit=%lu\n",created,(unsigned long)exit_code);
        if(!created||exit_code)result=86;
    }
    if (split == 3 && standalone)
        puts("cef64-owned-contract legacy child pools absent by design; genuine standalone Crashpad requires separate IPC/minidump test");
    for (unsigned i = 0; i < count; ++i) if (owned[i]) {
        BOOL freed = VirtualFree(owned[i], 0, MEM_RELEASE);
        printf("cef64-owned-contract release=%u result=%u\n", i, !!freed);
        if (!freed && !result) result = 70 + i;
    }
    printf("cef64-owned-contract result=%d; no CEF/login/game claim\n", result);
    return result;
}
#endif
