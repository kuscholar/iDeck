/* winhttp_get.c — Steam S0 smoke test for the iOS network+TLS stack.
 *
 * Stage 1: plain HTTP GET http://example.com/
 *   exercises ws2_32 unixlib (DNS + sockets via wineserver/afd) and
 *   winhttp's request core, with no crypto involved.
 * Stage 2: HTTPS GET https://api.steampowered.com/ISteamWebAPIUtil/GetServerInfo/v1/
 *   exercises secur32/schannel (GnuTLS handshake), bcrypt (crypto
 *   primitives), and crypt32 (cert chain verification against the
 *   bundled Mozilla roots).
 *
 * Success looks like: both stages print "status=200" and a body
 * snippet; stage 2's body is Steam's servertime JSON. Exit code 0 only
 * if both stages succeed.
 */
#include <windows.h>
#include <winhttp.h>
#include <stdio.h>

static void out(const char *fmt, ...)
{
    char buf[2048];
    va_list ap;
    DWORD written;
    int len;
    va_start(ap, fmt);
    len = vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    /* WriteFile straight to the std handle: atomic, interleaves cleanly
     * with ntdll traces (see feedback_stderr_interleaving). */
    WriteFile(GetStdHandle(STD_OUTPUT_HANDLE), buf, len, &written, NULL);
}

static int fetch(const WCHAR *host, INTERNET_PORT port, const WCHAR *path, DWORD secure)
{
    HINTERNET ses = NULL, con = NULL, req = NULL;
    DWORD status = 0, size = sizeof(status), avail, got;
    char buf[513];
    int ok = 0, total = 0;

    out("[net-test] %S:%u %S %s\n", host, port, path, secure ? "(TLS)" : "(plain)");

    ses = WinHttpOpen(L"Madeira-S0-Test/1.0", WINHTTP_ACCESS_TYPE_NO_PROXY,
                      WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);
    if (!ses) { out("[net-test] WinHttpOpen FAILED err=%lu\n", GetLastError()); goto done; }

    /* Generous timeouts: TCP connect to far CDN edges (Akamai/Steam) can
     * be slower than a nearby host; the iOS poll loop adds ~1ms grain.
     * resolve, connect, send, receive (ms). */
    WinHttpSetTimeouts(ses, 30000, 30000, 30000, 30000);

    con = WinHttpConnect(ses, host, port, 0);
    if (!con) { out("[net-test] WinHttpConnect FAILED err=%lu\n", GetLastError()); goto done; }

    req = WinHttpOpenRequest(con, L"GET", path, NULL, WINHTTP_NO_REFERER,
                             WINHTTP_DEFAULT_ACCEPT_TYPES, secure);
    if (!req) { out("[net-test] WinHttpOpenRequest FAILED err=%lu\n", GetLastError()); goto done; }

    if (!WinHttpSendRequest(req, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
                            WINHTTP_NO_REQUEST_DATA, 0, 0, 0))
    { out("[net-test] WinHttpSendRequest FAILED err=%lu\n", GetLastError()); goto done; }

    if (!WinHttpReceiveResponse(req, NULL))
    { out("[net-test] WinHttpReceiveResponse FAILED err=%lu\n", GetLastError()); goto done; }

    if (!WinHttpQueryHeaders(req, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
                             WINHTTP_HEADER_NAME_BY_INDEX, &status, &size, WINHTTP_NO_HEADER_INDEX))
    { out("[net-test] QueryHeaders FAILED err=%lu\n", GetLastError()); goto done; }

    out("[net-test] status=%lu\n", status);

    while (WinHttpQueryDataAvailable(req, &avail) && avail)
    {
        if (avail > sizeof(buf) - 1) avail = sizeof(buf) - 1;
        if (!WinHttpReadData(req, buf, avail, &got) || !got) break;
        buf[got] = 0;
        if (total < 512) out("[net-test] body: %s\n", buf);
        total += got;
    }
    out("[net-test] read %d bytes total\n", total);
    ok = (status == 200 && total > 0);

done:
    if (req) WinHttpCloseHandle(req);
    if (con) WinHttpCloseHandle(con);
    if (ses) WinHttpCloseHandle(ses);
    return ok;
}

int main(void)
{
    int http_ok, https_ok;

    out("[net-test] === Madeira S0 network/TLS smoke test ===\n");

    http_ok = fetch(L"example.com", INTERNET_DEFAULT_HTTP_PORT, L"/", 0);
    out("[net-test] STAGE 1 (plain HTTP): %s\n", http_ok ? "PASS" : "FAIL");

    /* Stage 2a: HTTPS to a boring, nearby host — isolates "TLS stack
     * works at all" from anything Steam/Akamai-specific. */
    {
        int neutral_ok = fetch(L"example.com", INTERNET_DEFAULT_HTTPS_PORT, L"/", WINHTTP_FLAG_SECURE);
        out("[net-test] STAGE 2a (HTTPS neutral host): %s\n", neutral_ok ? "PASS" : "FAIL");
    }

    /* VPN-switch gate: the JIT debugger (StikDebug) needs a loopback
     * VPN, which conflicts with the user's real VPN. By this point both
     * TLS stages ran, so every code path the Steam stage needs is
     * already JIT-compiled — safe to detach the debugger and switch
     * VPNs. We wait for C:\madeira-continue.flag, written by the app's
     * "Continue Net Test" button, deleting it first so a stale flag
     * can't skip the pause. Waiting uses only already-compiled code
     * (CreateFileA probe + Sleep). 10-minute cap. */
    {
        const char *flag = "C:\\madeira-continue.flag";
        int waited;
        DeleteFileA(flag);
        out("[net-test] === PAUSED: detach JIT debugger + switch VPN now; tap 'Continue Net Test' ===\n");
        for (waited = 0; waited < 600; waited++)
        {
            HANDLE h = CreateFileA(flag, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                                   NULL, OPEN_EXISTING, 0, NULL);
            if (h != INVALID_HANDLE_VALUE) { CloseHandle(h); break; }
            Sleep(1000);
        }
        DeleteFileA(flag);
        out("[net-test] === CONTINUING (waited %ds) ===\n", waited);
    }

    /* Retry the HTTPS stage: connect to far CDN edges is intermittent on
     * flaky mobile links, and we care about exercising the TLS layer at
     * least once — the crypto path is deterministic once connected. */
    https_ok = 0;
    for (int attempt = 1; attempt <= 3 && !https_ok; attempt++)
    {
        out("[net-test] HTTPS attempt %d/3\n", attempt);
        https_ok = fetch(L"api.steampowered.com", INTERNET_DEFAULT_HTTPS_PORT,
                         L"/ISteamWebAPIUtil/GetServerInfo/v1/", WINHTTP_FLAG_SECURE);
    }
    out("[net-test] STAGE 2 (HTTPS + certs): %s\n", https_ok ? "PASS" : "FAIL");

    out("[net-test] === RESULT: %s ===\n", (http_ok && https_ok) ? "ALL PASS" : "FAILURES");
    return (http_ok && https_ok) ? 0 : 1;
}
