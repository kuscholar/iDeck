#!/usr/bin/env python3
"""Check graphics pin policy with Wine's real handle, refcount and detach code."""
from pathlib import Path
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
wine = Path(os.environ.get("WINE_SRC", root / "wine"))
source = (root / "madeira-d3d12/src/pe/madeira_d3d12.c").read_text()
loader = (wine / "dlls/ntdll/loader.c").read_text()
kernelbase = (wine / "dlls/kernelbase/loader.c").read_text()


def function(text, signature):
    start = text.index(signature)
    return text[start:text.index('\n}', start) + 2] + '\n'


helper = source[source.index("/* madeira graphics pin begin */"):
                source.index("/* madeira graphics pin end */")]
direct = function(source, "__declspec(dllexport) HRESULT WINAPI MadeiraD3D12CreateDevice(")
standard = function(source, "HRESULT WINAPI D3D12CreateDevice(")
main = function(source, "BOOL WINAPI DllMain(")
assert "mad_pin_graphics_dlls" not in main, "must not call the loader from DllMain"
assert direct.index("mad_pin_graphics_dlls();") < direct.index("build_vtables();")
assert "if (!device) {\n        mad_pin_graphics_dlls();" in standard
assert "return MadeiraD3D12CreateDevice(adapter, min_level, riid, device);" in standard
assert "LoadLibrary" not in helper, "pinning must not load another module"
assert "FreeLibrary" not in helper and "ios_jit" not in helper

code = r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "windows.h"
#include "winternl.h"
#include "ntstatus.h"
#define TRACE(...) ((void)0)
#define FIXME(...) ((void)0)
typedef struct { LDR_DATA_TABLE_ENTRY ldr; } WINE_MODREF;
struct file_id { ULONGLONG dev, ino; };
static const WCHAR *const names[] = {L"D3D12.dll", L"madeira_d3d12.dll", L"d3d12core.dll",
                                    L"DXGI.DLL", L"winemetal.dll", L"libcef.dll"};
static WINE_MODREF mods[ARRAY_SIZE(names)];
static LDR_DDAG_NODE nodes[ARRAY_SIZE(names)];
static unsigned dependency_releases, unload_traces, detaches, queries, handle_queries, logs;
static unsigned lock_depth;
static unsigned missing_mask, fail_mask;
static int process_detaching;
static const char *option_value;
static DWORD last_error;
static RTL_CRITICAL_SECTION loader_section;
static PEB_LDR_DATA loader_data;
static PEB peb;
static TEB teb;
#undef NtCurrentTeb
#define NtCurrentTeb() (&teb)
static int same_name(const WCHAR *a, const WCHAR *b)
{
    for (; *a && *b; a++, b++)
    {
        WCHAR x = *a, y = *b;
        if (x >= 'A' && x <= 'Z') x += 'a' - 'A';
        if (y >= 'A' && y <= 'Z') y += 'a' - 'A';
        if (x != y) return 0;
    }
    return *a == *b;
}
DWORD WINAPI GetLastError(void) { return last_error; }
void WINAPI SetLastError(DWORD error) { last_error = error; }
HANDLE WINAPI GetProcessHeap(void) { return peb.ProcessHeap; }
DWORD WINAPI GetEnvironmentVariableA(LPCSTR name, LPSTR value, DWORD capacity)
{
    queries++;
    assert(!strcmp(name, "MADEIRA_PIN_GRAPHICS_DLLS") && capacity == 2);
    if (!option_value) { SetLastError(ERROR_ENVVAR_NOT_FOUND); return 0; }
    size_t n = strlen(option_value);
    if (n >= capacity) return n + 1;
    memcpy(value, option_value, n + 1);
    return n;
}
NTSTATUS WINAPI RtlEnterCriticalSection(RTL_CRITICAL_SECTION *section)
{ assert(section == &loader_section); lock_depth++; return STATUS_SUCCESS; }
NTSTATUS WINAPI RtlLeaveCriticalSection(RTL_CRITICAL_SECTION *section)
{ assert(section == &loader_section && lock_depth); lock_depth--; return STATUS_SUCCESS; }
void WINAPI RtlInitUnicodeString(UNICODE_STRING *string, const WCHAR *name)
{
    unsigned n = 0; while (name[n]) n++;
    string->Buffer = (WCHAR *)name; string->Length = n * sizeof(WCHAR);
    string->MaximumLength = (n + 1) * sizeof(WCHAR);
}
void WINAPI RtlFreeUnicodeString(UNICODE_STRING *string) { assert(!string->Buffer); }
BOOLEAN WINAPI RtlFreeHeap(HANDLE heap, ULONG flags, void *pointer)
{ (void)heap; assert(!flags && !pointer); return TRUE; }
NTSTATUS WINAPI NtClose(HANDLE handle) { (void)handle; assert(0); return STATUS_SUCCESS; }
void *WINAPI RtlPcToFileHeader(void *pc, void **base)
{ (void)pc; (void)base; assert(0); return NULL; }
ULONG WINAPI RtlNtStatusToDosError(NTSTATUS status)
{ return status == STATUS_DLL_NOT_FOUND ? ERROR_MOD_NOT_FOUND : ERROR_NOT_ENOUGH_MEMORY; }
static BOOL set_ntstatus(NTSTATUS status)
{ if (status) SetLastError(RtlNtStatusToDosError(status)); return !status; }
static WCHAR *append_dll_ext(const WCHAR *name) { (void)name; return NULL; }
static NTSTATUS find_dll_file(LPCWSTR path, const WCHAR *name, UNICODE_STRING *nt_name,
                             WINE_MODREF **wm, HANDLE *mapping, SECTION_IMAGE_INFORMATION *image,
                             struct file_id *id, BOOL *redirected, BOOL find_loaded)
{
    (void)mapping; (void)image; (void)id; (void)redirected;
    assert(!path && find_loaded && lock_depth);
    memset(nt_name, 0, sizeof *nt_name); *wm = NULL; handle_queries++;
    for (unsigned i = 0; i < ARRAY_SIZE(names); i++)
        if (same_name(name, names[i]))
        {
            if (missing_mask & (1u << i)) return STATUS_DLL_NOT_FOUND;
            if (fail_mask & (1u << i)) { fail_mask &= ~(1u << i); return STATUS_NO_MEMORY; }
            *wm = &mods[i]; return STATUS_SUCCESS;
        }
    return STATUS_DLL_NOT_FOUND;
}
static WINE_MODREF *get_modref(HMODULE module)
{
    assert(lock_depth);
    for (unsigned i = 0; i < ARRAY_SIZE(names); i++)
        if (module == mods[i].ldr.DllBase) return &mods[i];
    return NULL;
}
static NTSTATUS walk_node_dependencies(LDR_DDAG_NODE *node, void *context,
                                      NTSTATUS (*callback)(LDR_DDAG_NODE *, void *))
{ (void)node; (void)context; (void)callback; dependency_releases++; return STATUS_SUCCESS; }
static void module_push_unload_trace(WINE_MODREF *wm) { (void)wm; unload_traces++; }
static NTSTATUS MODULE_InitDLL(WINE_MODREF *wm, UINT reason, LPVOID reserved)
{ (void)wm; (void)reserved; assert(reason == DLL_PROCESS_DETACH); detaches++; return STATUS_SUCCESS; }
static void call_ldr_notifications(ULONG reason, LDR_DATA_TABLE_ENTRY *ldr)
{ (void)ldr; assert(reason == LDR_DLL_NOTIFICATION_REASON_UNLOADED); }
static void d3d12_log(const char *format, ...)
{ assert(strstr(format, "[graphics-pin]")); logs++; SetLastError(555); }
'''
# The actual existing Wine API and lifetime routines, with only external
# environment/name lookup/notification functions stubbed by the fixture above.
code += function(loader, "NTSTATUS WINAPI LdrAddRefDll(")
code += function(loader, "NTSTATUS WINAPI LdrGetDllHandleEx(")
code += function(kernelbase, "BOOL WINAPI DECLSPEC_HOTPATCH GetModuleHandleExW(")
code += function(loader, "static NTSTATUS MODULE_DecRefCount(")
code += function(loader, "static void process_detach(void)")
code += helper
code += r'''
static void initialize(void)
{
    LIST_ENTRY *head = &loader_data.InInitializationOrderModuleList;
    head->Flink = head->Blink = head;
    memset(mods, 0, sizeof mods); memset(nodes, 0, sizeof nodes);
    for (unsigned i = 0; i < ARRAY_SIZE(names); i++)
    {
        RtlInitUnicodeString(&mods[i].ldr.BaseDllName, names[i]);
        mods[i].ldr.DllBase = (HMODULE)&mods[i];
        mods[i].ldr.LoadCount = 1;
        mods[i].ldr.Flags = LDR_PROCESS_ATTACHED;
        mods[i].ldr.DdagNode = &nodes[i];
        LIST_ENTRY *entry = &mods[i].ldr.InInitializationOrderLinks;
        entry->Flink = head; entry->Blink = head->Blink;
        head->Blink->Flink = entry; head->Blink = entry;
        LIST_ENTRY *module = &mods[i].ldr.NodeModuleLink;
        nodes[i].Modules.Flink = nodes[i].Modules.Blink = module;
        module->Flink = module->Blink = &nodes[i].Modules;
    }
    peb.LdrData = &loader_data; teb.Peb = &peb;
    dependency_releases = unload_traces = detaches = handle_queries = 0;
    missing_mask = fail_mask = 0; process_detaching = 0;
    assert(!lock_depth);
}
static void run_pin(void)
{
    SetLastError(1234);
    mad_pin_graphics_dlls();
    assert(GetLastError() == 1234 && !lock_depth);
}
int main(void)
{
    assert(sizeof(WCHAR) == 2);
    static const char *const invalid[] = {NULL, "", "0", "yes", "11", "1 ", "10"};
    initialize();
    for (unsigned i = 0; i < ARRAY_SIZE(invalid); i++)
    {
        option_value = invalid[i]; run_pin();
        for (unsigned j = 0; j < ARRAY_SIZE(names); j++) assert(mods[j].ldr.LoadCount == 1);
        assert(!handle_queries && !logs);
    }
    option_value = "1";
    missing_mask = 1u << 2; // d3d12core has not loaded yet: no LoadLibrary side effect.
    fail_mask = 1u << 3;    // A failed pin lookup must be retried on another probe.
    run_pin();
    assert(mods[2].ldr.LoadCount == 1 && mods[3].ldr.LoadCount == 1);
    assert(mods[0].ldr.LoadCount == -1 && mods[1].ldr.LoadCount == -1 && mods[4].ldr.LoadCount == -1);
    assert(mods[5].ldr.LoadCount == 1 && logs == 3);
    missing_mask = 0;
    run_pin();
    assert(logs == 5);
    for (unsigned i = 0; i < 5; i++) assert(mods[i].ldr.LoadCount == -1);
    for (unsigned probe = 0; probe < 100; probe++)
    {
        run_pin();
        for (unsigned i = 0; i < 5; i++) assert(!MODULE_DecRefCount(&nodes[i], NULL));
        process_detach();
    }
    assert(!dependency_releases && !unload_traces && !detaches && logs == 5);
    for (unsigned i = 0; i < 5; i++) assert(mods[i].ldr.Flags & LDR_PROCESS_ATTACHED);
    // Unrelated modules retain normal unload behavior while graphics are pinned.
    assert(!MODULE_DecRefCount(&nodes[5], NULL));
    process_detach();
    assert(mods[5].ldr.LoadCount == 0 && dependency_releases == 1 && unload_traces == 1 && detaches == 1);
    // Normal process termination still detaches every pinned module exactly once.
    process_detaching = 1;
    process_detach(); process_detach();
    assert(detaches == 6);
    for (unsigned i = 0; i < ARRAY_SIZE(names); i++) assert(!(mods[i].ldr.Flags & LDR_PROCESS_ATTACHED));
    // Current environment is consulted again; a new process without the flag
    // retains the original loader refcount/unload behavior.
    initialize(); option_value = NULL; run_pin();
    for (unsigned i = 0; i < ARRAY_SIZE(names); i++)
    {
        assert(mods[i].ldr.LoadCount == 1);
        assert(!MODULE_DecRefCount(&nodes[i], NULL));
    }
    process_detach();
    assert(dependency_releases == 6 && unload_traces == 6 && detaches == 6);
    assert(!handle_queries && queries == ARRAY_SIZE(invalid) + 103);
    puts("PASS: opt-in pin, absent-module/retry, last-error preservation, repeated release and normal teardown");
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix="madeira-graphics-pin-") as temp:
    folder = Path(temp)
    path = folder / "check.c"
    path.write_text(code)
    executable = folder / "check"
    flags = ['-std=gnu11', '-D__WINESRC__', '-DWINE_UNIX_LIB', '-fshort-wchar',
             '-Wall', '-Wextra', '-Werror', '-g', '-fsanitize=address,undefined',
             '-fno-sanitize-recover=all', '-I', str(wine / 'include')]
    subprocess.run([os.environ.get('CC', 'cc'), *flags, str(path), '-o', str(executable)], check=True)
    subprocess.run([str(executable)], check=True)
assert (wine / "dlls/ntdll/loader.c").read_text() == loader
assert (wine / "dlls/kernelbase/loader.c").read_text() == kernelbase
print("PASS: both D3D12 entry points, existing Wine pin APIs, submodule unchanged")
