/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * Isolated-prefix experiment: preserve one CEF config through Steam's rewrite.
 * No Valve executable, authentication, URL, crash key or report is modified.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>

static const wchar_t config[] = L"C:\\Program Files\\Steam\\bin\\cef\\cef.win64\\crash_reporter.cfg";
static const wchar_t marker[] = L"C:\\iDeckCEF64Crashpad\\config-original-attributes.bin";

static int restore(void) {
    DWORD original = 0, bytes = 0;
    HANDLE file = CreateFileW(marker, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
    if (file == INVALID_HANDLE_VALUE) {
        if (GetLastError() != ERROR_FILE_NOT_FOUND) return 10;
        puts("config-attributes-no-pending-marker=PASS");
        return 0;
    }
    BOOL read = ReadFile(file, &original, sizeof(original), &bytes, NULL);
    DWORD size = GetFileSize(file, NULL);
    CloseHandle(file);
    if (!read || bytes != sizeof(original) || size != sizeof(original) || original == INVALID_FILE_ATTRIBUTES || (original & FILE_ATTRIBUTE_DIRECTORY)) return 11;
    if (!SetFileAttributesW(config, original)) return 12;
    DWORD actual = GetFileAttributesW(config);
    if (actual == INVALID_FILE_ATTRIBUTES || (actual & FILE_ATTRIBUTE_READONLY) != (original & FILE_ATTRIBUTE_READONLY)) return 13;
    if (!DeleteFileW(marker)) return 14;
    puts("config-original-attributes-restored=PASS");
    return 0;
}

static int protect(void) {
    char data[65537]; DWORD count = 0;
    const char expected[] = "ExternalHandler=C:\\iDeckCEF64Crashpad\\crashpad_handler.exe";
    HANDLE file = CreateFileW(config, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, 0, NULL);
    if (file == INVALID_HANDLE_VALUE) return 2;
    DWORD size = GetFileSize(file, NULL);
    BOOL read = size <= 65536 && ReadFile(file, data, size, &count, NULL);
    CloseHandle(file);
    if (!read || count != size || !size) return 3;
    data[count] = 0;
    unsigned matches = 0;
    for (const char *at = data; (at = strstr(at, expected)) != NULL; ++at) {
        char end = at[sizeof(expected)-1];
        if ((at == data || at[-1] == '\n') && (end == '\r' || end == '\n' || !end)) ++matches;
    }
    if (matches != 1 || GetFileAttributesW(marker) != INVALID_FILE_ATTRIBUTES) return 4;
    DWORD original = GetFileAttributesW(config);
    if (original == INVALID_FILE_ATTRIBUTES || (original & FILE_ATTRIBUTE_DIRECTORY)) return 5;
    file = CreateFileW(marker, GENERIC_WRITE, 0, NULL, CREATE_NEW, 0, NULL);
    if (file == INVALID_HANDLE_VALUE) return 6;
    BOOL saved = WriteFile(file, &original, sizeof(original), &count, NULL);
    CloseHandle(file);
    if (!saved || count != sizeof(original)) { DeleteFileW(marker); return 7; }
    if (!SetFileAttributesW(config, original | FILE_ATTRIBUTE_READONLY)) { restore(); return 8; }
    /* OPEN_EXISTING does not truncate or write if the contract is broken. */
    file = CreateFileW(config, GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE, NULL, OPEN_EXISTING, 0, NULL);
    DWORD error = GetLastError();
    if (file != INVALID_HANDLE_VALUE) { CloseHandle(file); restore(); return 9; }
    if (error != ERROR_ACCESS_DENIED) { restore(); return 15; }
    puts("config-readonly=PASS write-denied=5");
    return 0;
}

int wmain(int argc, wchar_t **argv) {
    setvbuf(stdout, NULL, _IONBF, 0);
    if (argc != 2) return 1;
    if (!wcscmp(argv[1], L"--protect")) return protect();
    if (!wcscmp(argv[1], L"--restore")) return restore();
    return 1;
}
