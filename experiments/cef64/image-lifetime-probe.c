/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see iDeck/LICENSE-EXCEPTION.md.
 * Own AMD64 loader discriminator. Uses existing private installed DLLs; no
 * DllMain, imports, Steam authentication or game entry point is executed.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <wchar.h>
_Static_assert(sizeof(void *) == 8, "AMD64 only");
static const wchar_t *paths[] = {
    L"C:\\Program Files\\Steam\\steamapps\\common\\Hot Roads\\UnityPlayer.dll",
    L"C:\\Program Files\\Steam\\bin\\cef\\cef.win64\\libcef.dll"
};
static unsigned check_image(unsigned which, unsigned round) {
    SetLastError(0);
    HMODULE module = LoadLibraryExW(paths[which], NULL, DONT_RESOLVE_DLL_REFERENCES);
    DWORD error = module ? 0 : GetLastError();
    printf("image-lifetime image=%u round=%u loaded=%u error=%lu\n",
           which, round, module != NULL, (unsigned long)error);
    if (!module) return 1;
    MEMORY_BASIC_INFORMATION info = {0};
    int ok = VirtualQuery(module, &info, sizeof(info)) == sizeof(info) &&
             info.AllocationBase == module && info.State == MEM_COMMIT && info.Type == MEM_IMAGE;
    IMAGE_DOS_HEADER *dos = (IMAGE_DOS_HEADER *)module;
    if (ok) ok = dos->e_magic == IMAGE_DOS_SIGNATURE && dos->e_lfanew >= 64 && dos->e_lfanew < 4096;
    if (ok) {
        IMAGE_NT_HEADERS64 *nt = (IMAGE_NT_HEADERS64 *)((unsigned char *)module + dos->e_lfanew);
        ok = nt->Signature == IMAGE_NT_SIGNATURE &&
             nt->FileHeader.Machine == IMAGE_FILE_MACHINE_AMD64 &&
             nt->OptionalHeader.Magic == IMAGE_NT_OPTIONAL_HDR64_MAGIC;
    }
    BOOL freed = FreeLibrary(module);
    printf("image-lifetime image=%u round=%u valid_AMD64_header=%u freed=%u\n", which, round, ok, !!freed);
    return !ok || !freed;
}
int wmain(int argc, wchar_t **argv) {
    setvbuf(stdout, NULL, _IONBF, 0);
    if (argc == 2 && !wcscmp(argv[1], L"--child")) {
        unsigned failed = 0;
        for (unsigned round = 0; round < 2; round++)
            for (unsigned image = 0; image < sizeof(paths) / sizeof(paths[0]); image++)
                failed += check_image(image, round);
        printf("image-lifetime child-result=%u\n", failed);
        return failed ? 1 : 0;
    }
    /* Madeira's existing component launcher supplies its fixed source-DLL
     * argument. Accept that exact value as parent mode, without using it as
     * an arbitrary load path. Child mode remains an exact private switch. */
    if (argc != 1 && !(argc == 2 && !wcscmp(argv[1], L"C:\\iDeckCEF64SourceProbe\\chrome_elf.dll"))) return 2;
    puts("image-lifetime begin no-DllMain no-import-resolution; not a Steam/game test");
    wchar_t path[1024], command[1100];
    DWORD length = GetModuleFileNameW(NULL, path, 1024);
    if (!length || length >= 1024) return 3;
    unsigned failures = 0;
    for (unsigned child = 0; child < 3; child++) {
        int count = swprintf(command, 1100, L"\"%ls\" --child", path);
        if (count < 0 || count >= 1100) return 4;
        STARTUPINFOW startup = {.cb = sizeof(startup)};
        PROCESS_INFORMATION process = {0};
        DWORD code = UINT32_C(0xffffffff);
        BOOL created = CreateProcessW(path, command, NULL, NULL, TRUE, 0, NULL, NULL, &startup, &process);
        DWORD error = created ? 0 : GetLastError();
        if (created) {
            if (WaitForSingleObject(process.hProcess, 30000) == WAIT_OBJECT_0)
                GetExitCodeProcess(process.hProcess, &code);
            else {
                TerminateProcess(process.hProcess, 5);
                WaitForSingleObject(process.hProcess, 5000);
            }
            CloseHandle(process.hThread);
            CloseHandle(process.hProcess);
        }
        printf("image-lifetime child=%u created=%u error=%lu exit=%lu\n",
               child, !!created, (unsigned long)error, (unsigned long)code);
        if (!created || code) failures++;
    }
    printf("image-lifetime result=%u; not native-CEF/game execution proof\n", failures);
    return failures ? 1 : 0;
}
