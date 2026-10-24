/* fileio — exercises CreateFile/WriteFile/ReadFile/CloseHandle/DeleteFile.
 *
 * Test path: write a known buffer to a file, close, re-open, read back, verify,
 * delete. All via Win32 file API → x86 → FEX → Wine → NtCreateFile/etc.
 *
 * Tests:
 *   - CreateFileA (opens for write, creates if missing)
 *   - WriteFile in 3 chunks (header / body / footer)
 *   - CloseHandle
 *   - CreateFileA (opens for read)
 *   - ReadFile total length
 *   - Byte-by-byte verify
 *   - DeleteFileA cleanup
 *
 * Path: C:\fexio_test.txt — at the Wine prefix root (drive_c symlinked from
 * Documents/wine). If that fails, falls back to current dir.
 */
#include <windows.h>
#include <string.h>

static HANDLE g_h;

static void put_str(const char *s, int len) {
    DWORD w = 0;
    WriteFile(g_h, s, (DWORD)len, &w, NULL);
}

static int strlen_c(const char *s) { int n = 0; while (s[n]) n++; return n; }

static int format_u64(char *buf, unsigned long long v) {
    char tmp[32];
    int n = 0;
    if (v == 0) { buf[0] = '0'; return 1; }
    while (v) { tmp[n++] = '0' + (char)(v % 10); v /= 10; }
    for (int i = 0; i < n; i++) buf[i] = tmp[n - 1 - i];
    return n;
}

static void put_label_u64(const char *label, unsigned long long v) {
    put_str(label, strlen_c(label));
    char buf[32];
    int len = format_u64(buf, v);
    put_str(buf, len);
    put_str("\n", 1);
}

static int passed = 0, failed = 0;
static void result(const char *label, int ok) {
    put_str(label, strlen_c(label));
    if (ok) { put_str(" PASS\n", 6); passed++; }
    else    { put_str(" FAIL\n", 6); failed++; }
}

#define TEST_PATH "C:\\fexio_test.txt"

static const char *part1 = "Hello from x86_64 PE under FEX on iOS! ";
static const char *part2 = "This is a file I/O test that writes, closes, ";
static const char *part3 = "reopens, and reads back to verify. END.\n";

static int do_write(void) {
    HANDLE f = CreateFileA(TEST_PATH,
                           GENERIC_WRITE,
                           0,
                           NULL,
                           CREATE_ALWAYS,
                           FILE_ATTRIBUTE_NORMAL,
                           NULL);
    if (f == INVALID_HANDLE_VALUE) {
        put_label_u64("  CreateFile(write) failed, GetLastError = ",
                      (unsigned long long)GetLastError());
        return 0;
    }
    DWORD wrote = 0;
    int ok = 1;
    int n1 = strlen_c(part1), n2 = strlen_c(part2), n3 = strlen_c(part3);
    if (!WriteFile(f, part1, n1, &wrote, NULL) || (int)wrote != n1) ok = 0;
    if (!WriteFile(f, part2, n2, &wrote, NULL) || (int)wrote != n2) ok = 0;
    if (!WriteFile(f, part3, n3, &wrote, NULL) || (int)wrote != n3) ok = 0;
    CloseHandle(f);
    return ok;
}

static int do_read_verify(void) {
    HANDLE f = CreateFileA(TEST_PATH,
                           GENERIC_READ,
                           FILE_SHARE_READ,
                           NULL,
                           OPEN_EXISTING,
                           FILE_ATTRIBUTE_NORMAL,
                           NULL);
    if (f == INVALID_HANDLE_VALUE) {
        put_label_u64("  CreateFile(read) failed, GetLastError = ",
                      (unsigned long long)GetLastError());
        return 0;
    }

    /* GetFileSize check. */
    int n1 = strlen_c(part1), n2 = strlen_c(part2), n3 = strlen_c(part3);
    int expected = n1 + n2 + n3;
    DWORD size_lo = GetFileSize(f, NULL);
    if ((int)size_lo != expected) {
        put_label_u64("  GetFileSize returned ", (unsigned long long)size_lo);
        put_label_u64("  expected = ", (unsigned long long)expected);
        CloseHandle(f);
        return 0;
    }

    /* Read all into a buffer. */
    char buf[512];
    if (expected > (int)sizeof(buf) - 1) { CloseHandle(f); return 0; }
    DWORD got = 0;
    if (!ReadFile(f, buf, expected, &got, NULL) || (int)got != expected) {
        put_label_u64("  ReadFile got ", (unsigned long long)got);
        CloseHandle(f);
        return 0;
    }
    CloseHandle(f);

    /* Verify content. */
    int p = 0;
    if (memcmp(buf + p, part1, n1) != 0) return 0; p += n1;
    if (memcmp(buf + p, part2, n2) != 0) return 0; p += n2;
    if (memcmp(buf + p, part3, n3) != 0) return 0;
    return 1;
}

static int do_delete(void) {
    if (!DeleteFileA(TEST_PATH)) {
        put_label_u64("  DeleteFile failed, GetLastError = ",
                      (unsigned long long)GetLastError());
        return 0;
    }
    /* Re-open should fail with ERROR_FILE_NOT_FOUND. */
    HANDLE f = CreateFileA(TEST_PATH,
                           GENERIC_READ,
                           FILE_SHARE_READ,
                           NULL,
                           OPEN_EXISTING,
                           FILE_ATTRIBUTE_NORMAL,
                           NULL);
    if (f != INVALID_HANDLE_VALUE) { CloseHandle(f); return 0; }
    return 1;
}

static int streq(const char *a, const char *b) {
    while (*a && *b && *a == *b) { a++; b++; }
    return *a == 0 && *b == 0;
}

int main(int argc, char **argv) {
    g_h = GetStdHandle(STD_OUTPUT_HANDLE);

    int keep = 0;
    for (int i = 1; i < argc; i++) {
        if (argv[i] && streq(argv[i], "--keep")) keep = 1;
    }

    put_str("== fileio test ==\n", 18);
    put_str("path: " TEST_PATH "\n", 6 + (int)sizeof(TEST_PATH) - 1 + 1);

    result("write 3 chunks                ", do_write());
    result("read back + verify content    ", do_read_verify());
    if (keep) {
        put_str("delete                         SKIPPED (--keep set)\n", 53);
    } else {
        result("delete + verify gone          ", do_delete());
    }

    put_label_u64("passed = ", (unsigned long long)passed);
    put_label_u64("failed = ", (unsigned long long)failed);

    return failed;
}
