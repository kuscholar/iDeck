/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * Synthetic guest probe: no Steam files, network, credentials or game content.
 */
#include <windows.h>
#include <stdio.h>
#include <wchar.h>
#define VALUE 0x43454631
int wmain(int argc, wchar_t **argv) {
    if (argc == 3 && !wcscmp(argv[1], L"--child")) {
        HANDLE m = OpenFileMappingW(FILE_MAP_WRITE, FALSE, argv[2]);
        if (!m) return 11;
        volatile LONG *p = MapViewOfFile(m, FILE_MAP_WRITE, 0, 0, sizeof(LONG));
        if (!p) { CloseHandle(m); return 12; }
        InterlockedExchange(p, VALUE);
        UnmapViewOfFile((const void *)p); CloseHandle(m); return 0;
    }
    wchar_t name[80], exe[32768], command[33000];
    swprintf(name, 80, L"Local\\MadeiraSteamUIProbe_%lu", GetCurrentProcessId());
    if (!GetModuleFileNameW(NULL, exe, 32768)) return 20;
    HANDLE m = CreateFileMappingW(INVALID_HANDLE_VALUE, NULL, PAGE_READWRITE, 0, sizeof(LONG), name);
    if (!m) return 21;
    volatile LONG *p = MapViewOfFile(m, FILE_MAP_WRITE | FILE_MAP_READ, 0, 0, sizeof(LONG));
    if (!p) { CloseHandle(m); return 22; }
    *p = 0;
    swprintf(command, 33000, L"\"%ls\" --child %ls", exe, name);
    STARTUPINFOW si = {0}; PROCESS_INFORMATION pi = {0}; si.cb = sizeof(si);
    if (!CreateProcessW(exe, command, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) {
        UnmapViewOfFile((const void *)p); CloseHandle(m); return 23;
    }
    DWORD wait = WaitForSingleObject(pi.hProcess, 15000), code = 99;
    BOOL exited = wait == WAIT_OBJECT_0 && GetExitCodeProcess(pi.hProcess, &code);
    BOOL pass = exited && code == 0 && *p == VALUE;
    printf("steam-ui-process-probe wait=%lu child_exit=%lu shared_match=%d\n", wait, code, *p == VALUE);
    CloseHandle(pi.hThread); CloseHandle(pi.hProcess);
    UnmapViewOfFile((const void *)p); CloseHandle(m);
    /* No forced child termination on timeout; use only in an isolated session. */
    return pass ? 0 : 24;
}
