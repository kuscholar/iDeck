/* SPDX-License-Identifier: GPL-3.0-or-later
 * Madeira Converter Exception: see LICENSE-EXCEPTION.md
 * Bounded public HTTP/TLS and process-exit discriminator. No account requests,
 * response payload logging, proxy changes or certificate-validation exceptions.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <winhttp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

static int child_exit(int direct, unsigned long long nonce)
{
    FILE *out = fopen("C:\\madeira-cef64-network-child.txt", "w");
    if (!out) return 9;
    fprintf(out, "nonce=%llu intended=7 direct=%d\n", nonce, direct);
    if (fclose(out)) return 10;
    if (direct) ExitProcess(7);
    return 7;
}

static int check_child(int direct)
{
    WCHAR self[2048], command[2200];
    STARTUPINFOW startup = {.cb = sizeof(startup)};
    PROCESS_INFORMATION child = {0};
    unsigned long long nonce = GetTickCount64();
    char expected[100], actual[100] = {0};
    DWORD code = 0xffffffff, wait = WAIT_FAILED;
    int got = 0, fresh = 0;
    DWORD error = 0;
    DWORD n = GetModuleFileNameW(NULL, self, 2048);
    if (!n || n == 2048) return 0;
    int length = swprintf(command, 2200, L"\"%ls\" --child-%ls %llu", self,
                          direct ? L"direct" : L"crt", nonce);
    if (length < 0 || length >= 2200) return 0;
    FILE *out = fopen("C:\\madeira-cef64-network-child.txt", "w");
    if (!out) return 0;
    fputs("pending\n", out);
    if (fclose(out)) return 0;
    int created = CreateProcessW(NULL, command, NULL, NULL, FALSE, 0, NULL, NULL, &startup, &child);
    if (created) {
        wait = WaitForSingleObject(child.hProcess, 10000);
        if (wait == WAIT_OBJECT_0) {
            got = GetExitCodeProcess(child.hProcess, &code);
            if (!got) error = GetLastError();
        } else {
            TerminateProcess(child.hProcess, 124);
            WaitForSingleObject(child.hProcess, 5000);
        }
        CloseHandle(child.hThread);
        CloseHandle(child.hProcess);
    } else error = GetLastError();
    out = fopen("C:\\madeira-cef64-network-child.txt", "r");
    if (out) {
        int read = fgets(actual, sizeof(actual), out) != NULL;
        int eof = fgetc(out) == EOF;
        fclose(out);
        snprintf(expected, sizeof(expected), "nonce=%llu intended=7 direct=%d\n", nonce, direct);
        fresh = read && eof && !strcmp(expected, actual);
    }
    printf("network-child direct=%d created=%d wait=%lu get-code=%d code=%lu error=%lu fresh-result=%d\n",
           direct, created, wait, got, code, error, fresh);
    return created && wait == WAIT_OBJECT_0 && got && code == 7 && fresh;
}

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

int wmain(int argc, WCHAR **argv)
{
    setvbuf(stdout, NULL, _IONBF, 0);
    if (argc == 3 && (!wcscmp(argv[1], L"--child-crt") || !wcscmp(argv[1], L"--child-direct"))) {
        WCHAR *end;
        unsigned long long nonce = wcstoull(argv[2], &end, 10);
        if (*end) return 2;
        return child_exit(!wcscmp(argv[1], L"--child-direct"), nonce);
    }
    if (argc != 1) return 2;
    char option[8] = {0};
    DWORD count = GetEnvironmentVariableA("MADEIRA_X64_IMAGE_NOCOPY", option, sizeof(option));
    printf("network-probe begin x64-image-data=%d; public endpoints and numeric states only\n",
           count == 1 && option[0] == '1');
    int crt = check_child(0), direct = check_child(1);
    int http = fetch(1, L"example.com", 80, L"/", 0);
    int neutral = fetch(2, L"example.com", 443, L"/", WINHTTP_FLAG_SECURE);
    int steam = fetch(3, L"api.steampowered.com", 443,
                      L"/ISteamWebAPIUtil/GetServerInfo/v1/", WINHTTP_FLAG_SECURE);
    int directory = fetch(4, L"api.steampowered.com", 443,
                          L"/ISteamDirectory/GetCMListForConnect/v1/?cellid=83&qoslevel=3", WINHTTP_FLAG_SECURE);
    /* Steam's categorical log omits an API version here. Test that URL form
     * separately; the log is NOT proof of the URI actually sent on the wire. */
    int client_path = fetch(5, L"api.steampowered.com", 443,
                            L"/ISteamDirectory/GetCMListForConnect/?cellid=83&qoslevel=3", WINHTTP_FLAG_SECURE);
    int ok = crt && direct && http && neutral && steam && directory && client_path;
    printf("network-probe result=%d crt=%d direct=%d http=%d https-neutral=%d steam-time=%d steam-directory=%d unversioned-form=%d; not Steam authentication or observed wire URI\n",
           ok ? 0 : 1, crt, direct, http, neutral, steam, directory, client_path);
    return ok ? 0 : 1;
}
