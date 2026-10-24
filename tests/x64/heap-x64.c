/* heap — exercises malloc/free/realloc on x86_64 PE under FEX on iOS.
 *
 * Tests:
 *   - malloc / free (ucrtbase → HeapAlloc → RtlAllocateHeap → NtAllocateVirtualMemory)
 *   - Multiple small allocations + verify each
 *   - One big allocation + verify
 *   - Linked-list build + walk (heap pointer chasing)
 *   - realloc with both grow and shrink
 *   - free in reverse order to stress freelist
 *
 * Output: one line per phase with PASS/FAIL. Exit code = number of failures.
 */
#include <windows.h>
#include <stdlib.h>
#include <string.h>

static HANDLE g_h;

static void put_str(const char *s, int len) {
    DWORD w = 0;
    WriteFile(g_h, s, (DWORD)len, &w, NULL);
}

static int strlen_c(const char *s) {
    int n = 0;
    while (s[n]) n++;
    return n;
}

static int format_u64(char *buf, unsigned long long v) {
    char tmp[32];
    int n = 0;
    if (v == 0) { buf[0] = '0'; return 1; }
    while (v) { tmp[n++] = '0' + (char)(v % 10); v /= 10; }
    for (int i = 0; i < n; i++) buf[i] = tmp[n - 1 - i];
    return n;
}

static int passed = 0, failed = 0;

static void result(const char *label, int ok) {
    int len = strlen_c(label);
    put_str(label, len);
    if (ok) {
        put_str(" PASS\n", 6);
        passed++;
    } else {
        put_str(" FAIL\n", 6);
        failed++;
    }
}

static void put_label_u64(const char *prefix, unsigned long long v) {
    int p = strlen_c(prefix);
    put_str(prefix, p);
    char buf[32];
    int len = format_u64(buf, v);
    put_str(buf, len);
    put_str("\n", 1);
}

/* Test 1: many small allocations, write known pattern, verify, free. */
static int test_small_allocs(void) {
    const int N = 1000;
    char *blocks[1000];
    for (int i = 0; i < N; i++) {
        blocks[i] = (char *)malloc(64);
        if (!blocks[i]) return 0;
        /* Fill with i (low byte) so we can verify. */
        memset(blocks[i], i & 0xFF, 64);
    }
    /* Verify each. */
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < 64; j++) {
            if (blocks[i][j] != (char)(i & 0xFF)) return 0;
        }
    }
    /* Free in REVERSE order — stresses freelist coalescing. */
    for (int i = N - 1; i >= 0; i--) free(blocks[i]);
    return 1;
}

/* Test 2: one big allocation. */
static int test_big_alloc(void) {
    const size_t SZ = 1024 * 1024;  /* 1 MiB */
    unsigned char *buf = (unsigned char *)malloc(SZ);
    if (!buf) return 0;
    /* Write a deterministic pattern. */
    for (size_t i = 0; i < SZ; i++) buf[i] = (unsigned char)(i & 0xFF);
    /* Verify. */
    for (size_t i = 0; i < SZ; i++) {
        if (buf[i] != (unsigned char)(i & 0xFF)) { free(buf); return 0; }
    }
    free(buf);
    return 1;
}

/* Test 3: linked list with malloc'd nodes. */
typedef struct Node {
    struct Node *next;
    unsigned long long value;
} Node;

static int test_linked_list(unsigned long long *sum_out) {
    const int N = 500;
    Node *head = NULL;
    /* Build list: head -> N-1 -> N-2 -> ... -> 0. */
    for (int i = 0; i < N; i++) {
        Node *n = (Node *)malloc(sizeof(Node));
        if (!n) return 0;
        n->value = (unsigned long long)i;
        n->next = head;
        head = n;
    }
    /* Walk and sum. */
    unsigned long long sum = 0;
    int count = 0;
    for (Node *p = head; p; p = p->next) {
        sum += p->value;
        count++;
    }
    if (count != N) return 0;
    /* Sum 0..N-1 = N*(N-1)/2. */
    if (sum != (unsigned long long)N * (N - 1) / 2) return 0;
    *sum_out = sum;
    /* Free. */
    while (head) { Node *next = head->next; free(head); head = next; }
    return 1;
}

/* Test 4: realloc grow + shrink. */
static int test_realloc(void) {
    char *p = (char *)malloc(16);
    if (!p) return 0;
    memset(p, 'A', 16);

    /* Grow. */
    p = (char *)realloc(p, 1024);
    if (!p) return 0;
    /* First 16 bytes must still be 'A'. */
    for (int i = 0; i < 16; i++) if (p[i] != 'A') { free(p); return 0; }
    /* Fill the rest. */
    memset(p + 16, 'B', 1024 - 16);

    /* Shrink. */
    p = (char *)realloc(p, 32);
    if (!p) return 0;
    /* First 16 still 'A', next 16 still 'B'. */
    for (int i = 0; i < 16; i++) if (p[i] != 'A') { free(p); return 0; }
    for (int i = 16; i < 32; i++) if (p[i] != 'B') { free(p); return 0; }

    free(p);
    return 1;
}

int main(void) {
    g_h = GetStdHandle(STD_OUTPUT_HANDLE);

    put_str("== heap test ==\n", 16);

    result("test_small_allocs (1000 x 64B)", test_small_allocs());
    result("test_big_alloc (1 MiB)        ", test_big_alloc());

    unsigned long long ll_sum = 0;
    int ll_ok = test_linked_list(&ll_sum);
    result("test_linked_list (500 nodes)  ", ll_ok);
    if (ll_ok) put_label_u64("  sum = ", ll_sum);

    result("test_realloc (grow + shrink)  ", test_realloc());

    put_label_u64("passed = ", (unsigned long long)passed);
    put_label_u64("failed = ", (unsigned long long)failed);

    return failed;
}
