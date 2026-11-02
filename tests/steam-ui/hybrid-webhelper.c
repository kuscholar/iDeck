/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * Private architecture discriminator, NOT a distributable Steam replacement.
 * The AMD64 Steam process launches this AMD64 shim; it delegates unchanged
 * arguments to an unmodified official i386 browser in sibling cef.win7.
 * No command lines, credentials, account identifiers or object payloads logged.
 */
#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#include <windows.h>
#include <wchar.h>
#include <stdlib.h>
#include <stdio.h>
#include "hybrid-webhelper-args.h"
#if !defined(__x86_64__)
#error This discriminator must be built as AMD64, matching current Steam.
#endif
_Static_assert(sizeof(void *) == 8, "AMD64 wrapper required");

static void record(const char *stage, DWORD value)
{
    FILE *f = _wfopen(L"C:\\madeira-steam64-hybrid-results.txt", L"a");
    if (f) {
        fprintf(f, "hybrid-v2 pid=%lu stage=%s value=%lu\n",
                GetCurrentProcessId(), stage, value);
        fclose(f);
    }
}

int wmain(void)
{
    wchar_t gate[2], path[32768];
    if (GetEnvironmentVariableW(L"MADEIRA_STEAM64_HYBRID", gate, 2) != 1 || gate[0] != L'1')
        return ERROR_ACCESS_DENIED;
    record("begin-amd64", sizeof(void *) * 8);
    record("cwd-has-steam", GetFileAttributesW(L"steam.exe") != INVALID_FILE_ATTRIBUTES);
    DWORD n = GetModuleFileNameW(NULL, path, 32768);
    if (!n || n >= 32768) return ERROR_BAD_PATHNAME;
    wchar_t *slash = wcsrchr(path, L'\\');
    if (!slash) return ERROR_BAD_PATHNAME;
    *slash = 0; /* cef.win64 */
    slash = wcsrchr(path, L'\\');
    if (!slash) return ERROR_BAD_PATHNAME;
    *slash = 0; /* cef */
    const wchar_t suffix[] = L"\\cef.win7\\steamwebhelper.exe";
    if (wcslen(path) + wcslen(suffix) >= 32768) return ERROR_BAD_PATHNAME;
    wcscat(path, suffix);
    const wchar_t *tail = hybrid_args_tail(GetCommandLineW());
    size_t cap = wcslen(path) + wcslen(tail) + 4;
    if (cap > 32767) return ERROR_BAD_ARGUMENTS;
    wchar_t *cmd = calloc(cap, sizeof(wchar_t));
    if (!cmd) return ERROR_NOT_ENOUGH_MEMORY;
    if (swprintf(cmd, cap, L"\"%ls\" %ls", path, tail) < 0) {
        free(cmd);
        return ERROR_BAD_ARGUMENTS;
    }
    STARTUPINFOW si = {0};
    PROCESS_INFORMATION pi = {0};
    si.cb = sizeof(si);
    /* Inherit Steam's original working directory. The loader searches the
     * real EXE directory for its DLLs independently of the working directory. */
    if (!CreateProcessW(path, cmd, NULL, NULL, TRUE, 0, NULL, NULL, &si, &pi)) {
        DWORD error = GetLastError();
        record("spawn-failed", error);
        free(cmd);
        return (int)error;
    }
    free(cmd);
    record("child-i386-created", pi.dwProcessId);
    CloseHandle(pi.hThread);
    DWORD wait = WaitForSingleObject(pi.hProcess, INFINITE), code = ERROR_PROCESS_ABORTED;
    if (wait == WAIT_OBJECT_0) {
        if (!GetExitCodeProcess(pi.hProcess, &code)) code = GetLastError();
        record("child-exit", code);
    } else {
        code = GetLastError();
        record("wait-failed", code);
    }
    CloseHandle(pi.hProcess);
    return (int)code;
}
