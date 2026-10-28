/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * Read-only VA snapshots around loading our source-built DLL. No Steam/auth.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include "owned-contract.h"

struct allocation { uintptr_t base; SIZE_T bytes; };
static struct allocation before[8192], after[8192];

static unsigned snapshot(struct allocation *items)
{
    SYSTEM_INFO system;
    MEMORY_BASIC_INFORMATION info;
    unsigned used = 0;
    uintptr_t cursor;
    GetSystemInfo(&system);
    cursor = (uintptr_t)system.lpMinimumApplicationAddress;
    while (cursor < (uintptr_t)system.lpMaximumApplicationAddress) {
        uintptr_t next;
        if (VirtualQuery((const void *)cursor, &info, sizeof(info)) != sizeof(info)) return 0;
        next = (uintptr_t)info.BaseAddress + info.RegionSize;
        if (next <= cursor) return 0;
        if (info.State != MEM_FREE && info.Type == MEM_PRIVATE) {
            uintptr_t base = (uintptr_t)info.AllocationBase;
            unsigned i;
            for (i = 0; i < used && items[i].base != base; ++i) {}
            if (i == used) {
                if (used == 8192) return 0;
                items[used].base = base;
                items[used++].bytes = 0;
            }
            if (items[i].bytes > SIZE_MAX - info.RegionSize) return 0;
            items[i].bytes += info.RegionSize;
        }
        cursor = next;
    }
    return used;
}

int wmain(int argc, wchar_t **argv)
{
    static const char *required[] = {
        "ClearReportsBetween_ExportThunk", "CrashForException_ExportThunk",
        "DumpHungProcessWithPtype_ExportThunk", "GetCrashReports_ExportThunk",
        "GetCrashpadDatabasePath_ExportThunk", "GetInstallDetailsPayload",
        "GetUserDataDirectoryThunk", "InjectDumpForHungInput_ExportThunk",
        "IsExtensionPointDisableSet", "IsThirdPartyInitialized",
        "RequestSingleCrashUpload_ExportThunk", "SetMetricsClientId",
        "SetUploadConsent_ExportThunk", "SignalChromeElf",
        "SignalInitializeCrashReporting"
    };
    const SIZE_T gib = (SIZE_T)1 << 30;
    HMODULE dll;
    unsigned n_before, n_after, small_pools = 0;
    setvbuf(stdout, NULL, _IONBF, 0);
    if (argc != 2) return 2;
    if (!wcscmp(argv[1], L"--owned-contract")) return cef64_owned_contract();
    n_before = snapshot(before);
    if (!n_before) return 3;
    puts("cef64-load-probe before-load");
    dll = LoadLibraryW(argv[1]);
    if (!dll) { printf("cef64-load-probe load-error=%lu\n", GetLastError()); return 4; }
    for (unsigned i = 0; i < sizeof(required)/sizeof(required[0]); ++i) {
        if (!GetProcAddress(dll, required[i])) {
            printf("cef64-load-probe missing-export=%s\n", required[i]);
            return 5;
        }
    }
    /* Public Chromium126 install_details.h Payload prefix; no account fields.
     * Matching this source-built object's version/size is only one ABI gate,
     * not proof that Valve's consumer or crash-reporting contracts work. */
    struct payload_prefix { SIZE_T size; const char *version; const SIZE_T *mode; };
    typedef const struct payload_prefix *(__cdecl *payload_function)(void);
    FARPROC payload_export = GetProcAddress(dll, "GetInstallDetailsPayload");
    payload_function payload_get;
    _Static_assert(sizeof(payload_get) == sizeof(payload_export), "Windows ABI pointer size");
    memcpy(&payload_get, &payload_export, sizeof(payload_get));
    const struct payload_prefix *payload = payload_get();
    if (!payload || payload->size != 80 || !payload->version || !payload->mode) return 9;
    const int version_match = !strcmp(payload->version, "126.0.6478.183");
    printf("cef64-load-probe install-payload-size=%zu version-match=%d mode-size=%zu\n",
           payload->size, version_match, *payload->mode);
    if (!version_match || !*payload->mode || *payload->mode > 4096) return 10;
    n_after = snapshot(after);
    if (!n_after) return 6;
    for (unsigned i = 0; i < n_after; ++i) {
        unsigned j;
        for (j = 0; j < n_before && before[j].base != after[i].base; ++j) {}
        if (j != n_before) continue;
        if (after[i].bytes >= (SIZE_T)16 * gib) {
            printf("cef64-load-probe FAIL new-large-reservation=%llu\n", (unsigned long long)after[i].bytes);
            return 7;
        }
        if (after[i].bytes >= gib && after[i].bytes <= gib + 65536) ++small_pools;
    }
    printf("cef64-load-probe required-exports=15 small-pools=%u\n", small_pools);
    if (small_pools < 2) return 8; /* Refuse to call an unexercised load a pass. */
    puts("cef64-load-probe PASS; not Steam or iOS validation");
    return 0;
}
