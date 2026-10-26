/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * Read-only Windows architecture contract, including Valve's own query.
 * No installation, authentication, registry edits or network requests. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdint.h>

typedef BOOL (WINAPI *wow2_fn)(HANDLE, USHORT *, USHORT *);
/* Valve's C++ bool returns in AL, not the Win32 BOOL/EAX ABI. */
typedef unsigned char (__cdecl *valve_wow_fn)(void);
typedef LONG (NTAPI *guest_supported_fn)(USHORT, unsigned char *);
typedef LONG (NTAPI *query_fn)(HANDLE, ULONG, void *, ULONG, ULONG *);
typedef LONG (NTAPI *system_ex_fn)(ULONG, void *, ULONG, void *, ULONG, ULONG *);
typedef HRESULT (WINAPI *machine_attributes_fn)(USHORT, DWORD *);

static FILE *out;
static void inspect(HANDLE process, const char *kind) {
    BOOL wow = FALSE, ok; USHORT guest = 0xffff, native = 0xffff;
    ULONG_PTR peb = 0; ULONG len = 0; LONG status;
    wow2_fn wow2 = (wow2_fn)(uintptr_t)GetProcAddress(GetModuleHandleW(L"kernel32.dll"), "IsWow64Process2");
    query_fn query = (query_fn)(uintptr_t)GetProcAddress(GetModuleHandleW(L"ntdll.dll"), "NtQueryInformationProcess");
    system_ex_fn ex = (system_ex_fn)(uintptr_t)GetProcAddress(GetModuleHandleW(L"ntdll.dll"), "NtQuerySystemInformationEx");
    ok = IsWow64Process(process, &wow);
    fprintf(out, "%s wow1_ok=%d wow1=%d\n", kind, ok, wow);
    if (wow2) {
        ok = wow2(process, &guest, &native);
        fprintf(out, "%s wow2_ok=%d guest=%04x native=%04x\n", kind, ok, guest, native);
    }
    if (query) {
        status = query(process, 26, &peb, sizeof(peb), &len);
        fprintf(out, "%s peb_status=%08lx peb_nonzero=%d length=%lu\n", kind, status, peb != 0, len);
    }
    if (ex) {
        DWORD entries[8] = {0};
        status = ex(181, &process, sizeof(process), entries, sizeof(entries), &len);
        fprintf(out, "%s architectures_status=%08lx length=%lu", kind, status, len);
        for (unsigned i = 0; i < 8; i++) fprintf(out, " %08lx", entries[i]);
        fputc('\n', out);
    }
    fflush(out);
}

int main(void) {
    SYSTEM_INFO system = {0}, native = {0}; HANDLE duplicate = NULL;
    out = fopen("C:\\madeira-platform32-results.txt", "w");
    if (!out) return 90;
    fprintf(out, "platform32 pointer_bits=%u\n", (unsigned)(sizeof(void *) * 8));
    inspect(GetCurrentProcess(), "current");
    if (DuplicateHandle(GetCurrentProcess(), GetCurrentProcess(), GetCurrentProcess(), &duplicate, 0, FALSE, DUPLICATE_SAME_ACCESS)) {
        inspect(duplicate, "duplicate"); CloseHandle(duplicate);
    }
    GetSystemInfo(&system); GetNativeSystemInfo(&native);
    fprintf(out, "system_arch=%u native_arch=%u\n", system.wProcessorArchitecture, native.wProcessorArchitecture);
    machine_attributes_fn attributes = (machine_attributes_fn)(uintptr_t)GetProcAddress(GetModuleHandleW(L"kernel32.dll"), "GetMachineTypeAttributes");
    if (attributes) {
        DWORD value = 0xffffffff;
        HRESULT status = attributes(0x8664, &value);
        fprintf(out, "amd64_machine_attributes_hr=%08lx value=%08lx\n", status, value);
    } else fprintf(out, "machine_attributes_export_missing\n");
    SetDllDirectoryW(L"C:\\Steam32BundleLab");
    HMODULE tier = LoadLibraryW(L"C:\\Steam32BundleLab\\tier0_s.dll");
    if (tier) {
        valve_wow_fn valve = (valve_wow_fn)(uintptr_t)GetProcAddress(tier, "Plat_IsWOW64");
        if (valve) fprintf(out, "valve_Plat_IsWOW64=%d\n", valve());
        else fprintf(out, "valve_export_missing\n");
        valve_wow_fn os64 = (valve_wow_fn)(uintptr_t)GetProcAddress(tier, "Is64BitOS");
        if (os64) fprintf(out, "valve_Is64BitOS=%d\n", os64());
    } else fprintf(out, "valve_load_error=%lu\n", GetLastError());
    guest_supported_fn supported = (guest_supported_fn)(uintptr_t)GetProcAddress(GetModuleHandleW(L"ntdll.dll"), "RtlWow64IsWowGuestMachineSupported");
    if (supported) {
        unsigned char yes = 0xff;
        LONG status = supported(0x8664, &yes);
        fprintf(out, "amd64_guest_supported_status=%08lx value=%u\n", status, yes);
    }
    fprintf(out, "complete\n"); fclose(out); return 0;
}
