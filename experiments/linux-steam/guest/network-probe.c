/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Glibc/libcurl ABI control; no account data or HTTP body is printed.
 */
#include <stddef.h>
typedef struct _IO_FILE FILE;
extern FILE *fopen(const char *, const char *);
extern int fprintf(FILE *, const char *, ...), fclose(FILE *);
extern int getaddrinfo(const char *, const char *, const void *, void **);
extern void freeaddrinfo(void *);
extern void *dlopen(const char *, int), *dlsym(void *, const char *);
extern int dlclose(void *);
static size_t discard(char *bytes, size_t size, size_t count, void *unused) {
    (void)bytes; (void)unused;
    return size * count;
}
int main(void) {
    FILE *report = fopen("/network-results.txt", "w");
    if (!report) return 90;
    void *addresses = NULL;
    int dns = getaddrinfo("client-update.steamstatic.com", "443", NULL, &addresses);
    fprintf(report, "dns-result=%d\n", dns);
    if (addresses) freeaddrinfo(addresses);
    void *curl = dlopen("/Steam/steamrtarm64/libs/libcurl.so", 2);
    fprintf(report, "curl-library-loaded=%d\n", curl != NULL);
    if (!curl) { fclose(report); return 1; }
    void *(*init)(void) = dlsym(curl, "curl_easy_init");
    int (*option)(void *, int, ...) = dlsym(curl, "curl_easy_setopt");
    int (*perform)(void *) = dlsym(curl, "curl_easy_perform");
    void (*cleanup)(void *) = dlsym(curl, "curl_easy_cleanup");
    if (!init || !option || !perform || !cleanup) { fclose(report); dlclose(curl); return 2; }
    void *easy = init();
    if (!easy) { fclose(report); dlclose(curl); return 3; }
    int setup = option(easy, 10002, "https://client-update.steamstatic.com/steam_client_steamdeck_stable_linuxarm64");
    setup |= option(easy, 20011, discard);
    setup |= option(easy, 78, 5L);
    setup |= option(easy, 13, 10L);
    setup |= option(easy, 99, 1L);
    setup |= option(easy, 10065, "/etc/ssl/certs/ca-certificates.crt");
    fprintf(report, "curl-setup=%d\n", setup);
    int result = setup ? -1 : perform(easy);
    fprintf(report, "curl-https-result=%d\n", result);
    cleanup(easy); dlclose(curl); fclose(report);
    return dns || result ? 1 : 0;
}
