/* asmconf-x64.c — run FEX's own ASM conformance suite under OUR FEX build.
 *
 * See gen_asmconf.py for why this exists. Short version: FEX ships 2,239
 * golden-value instruction tests, but its runner is a Linux tool. This re-hosts
 * the test bodies in a Windows PE so they execute through the configuration we
 * actually ship — our FEX fork, ARM64EC/xtajit64, jitless — which upstream CI
 * never exercises.
 *
 * SELF-CALIBRATION (this port has been burned repeatedly by probes that could
 * not fire and therefore always "passed"):
 *   - the scratch region at 0xe0000000 is REQUIRED by 867 of the tests. If the
 *     reservation fails we say so and refuse to report a clean result.
 *   - every test is announced to the log BEFORE it runs and the file is flushed,
 *     so a test that kills the process names itself instead of leaving a gap.
 *   - the final census prints the expected test count. A short run cannot look
 *     like a clean one.
 */

#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>

#include "asmconf_tests.h"

/* Capture buffer filled by each test's epilogue: 16 GPRs, then 16 XMMs. */
extern unsigned char asmconf_regs[128 + 16 * 16];
extern unsigned char asmconf_save[16 * 8];

#define SCRATCH_BASE ((void *)(uintptr_t)0xe0000000)
/* Tests use 0xe0000000..0xe0004000 for data AND set rsp to 0xe8000000, which
 * grows DOWN. One region must cover both or a `call` after the rsp switch pushes
 * onto unmapped memory -- and with rsp invalid the SEH machinery cannot push an
 * exception frame either, so it HANGS rather than faulting (CALL.asm, ml541). */
#define SCRATCH_SIZE (0x8100000u)          /* 0xe0000000 .. 0xe8100000, 129 MB */

static HANDLE g_fh = INVALID_HANDLE_VALUE;
static int g_pass, g_fail, g_ran, g_crash;

static void emit(const char *s)
{
    DWORD w, n = (DWORD)strlen(s);
    WriteFile(GetStdHandle(STD_OUTPUT_HANDLE), s, n, &w, NULL);
    if (g_fh != INVALID_HANDLE_VALUE) { WriteFile(g_fh, s, n, &w, NULL); FlushFileBuffers(g_fh); }
}

static void lg(const char *fmt, ...)
{
    char buf[1024];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    emit(buf);
}

static const char *REGNAME[16] = { "RAX","RBX","RCX","RDX","RSI","RDI","RBP","RSP",
                                   "R8","R9","R10","R11","R12","R13","R14","R15" };

static unsigned long long captured(int reg, int lane)
{
    if (reg < 16) return ((unsigned long long *)asmconf_regs)[reg];
    return *(unsigned long long *)(asmconf_regs + 128 + (reg - 16) * 16 + lane * 8);
}

static void regname(int reg, int lane, char *out, size_t n)
{
    if (reg < 16) snprintf(out, n, "%s", REGNAME[reg]);
    else          snprintf(out, n, "XMM%d[%d]", reg - 16, lane);
}

/* Resumable sweep.
 *
 * Some tests repoint rsp and then fault, and a fault on a stack we do not own is
 * NOT catchable by __try -- the process dies outright. That is fatal on device,
 * where every Windows "process" is a pseudo-process in ONE Mach process and any
 * faulting helper kills the whole app.
 *
 * So: record the next index before running it. If we are killed, the next launch
 * resumes PAST the offender and marks it fatal. Sweeping on the Mac this way
 * produces a skip list, and the device build ships only harness-safe tests. */
static int load_start(void)
{
    char buf[32] = {0}; DWORD got = 0; int v = 0;
    HANDLE h = CreateFileA("C:\\asmconf_next.txt", GENERIC_READ, FILE_SHARE_READ, NULL,
                           OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) return 0;
    ReadFile(h, buf, sizeof(buf) - 1, &got, NULL);
    CloseHandle(h);
    v = atoi(buf);
    return v < 0 ? 0 : v;
}

static void save_next(int idx)
{
    char buf[32]; DWORD w;
    HANDLE h = CreateFileA("C:\\asmconf_next.txt", GENERIC_WRITE, 0, NULL,
                           CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (h == INVALID_HANDLE_VALUE) return;
    snprintf(buf, sizeof(buf), "%d", idx);
    WriteFile(h, buf, (DWORD)strlen(buf), &w, NULL);
    FlushFileBuffers(h); CloseHandle(h);
}

int main(void)
{
    unsigned i;
    int start;
    void *scratch;

    start = load_start();
    g_fh = CreateFileA("C:\\asmconf.log", GENERIC_WRITE, FILE_SHARE_READ, NULL,
                       start ? OPEN_ALWAYS : CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (start) SetFilePointer(g_fh, 0, NULL, FILE_END);
    lg("[asmconf] start rev=ml541  tests=%d expected-values=%d\n",
       ASMCONF_NTESTS, ASMCONF_NEXPECT);

    /* The tests write through absolute pointers into 0xe0000000. Without this
     * mapping they fault instead of running, so a failure here invalidates the
     * whole run and must not be quietly tolerated. */
    scratch = VirtualAlloc(SCRATCH_BASE, SCRATCH_SIZE, MEM_RESERVE | MEM_COMMIT,
                           PAGE_EXECUTE_READWRITE);
    if (scratch != SCRATCH_BASE) {
        lg("[asmconf] FATAL scratch reservation at 0xe0000000 FAILED (got %p, err=%lu)\n"
           "[asmconf] VERDICT: INVALID RUN — 867 tests need that address; not reporting passes\n",
           scratch, (unsigned long)GetLastError());
        if (g_fh != INVALID_HANDLE_VALUE) CloseHandle(g_fh);
        return 2;
    }
    /* No memset: VirtualAlloc already zero-fills, and touching all 129 MB would
     * dirty every page -- costly on a device with a 4096 MB jetsam ceiling. */
    lg("[asmconf] scratch 0x%p +%u MB OK (data 0xe0000000, test stacks 0xe8000000)\n",
       scratch, SCRATCH_SIZE / (1024 * 1024));

    if (start) lg("[asmconf] RESUME at %d — test %d killed the process (uncatchable fault)\n",
                  start, start - 1);
    for (i = (unsigned)start; i < ASMCONF_NTESTS; i++) {
        int j, bad = 0;
        /* Announce BEFORE running: if this test takes the process down, the log
         * ends with its name rather than an anonymous gap. */
        save_next((int)i + 1);   /* survive our own death: next launch skips this one */
        lg("[asmconf] >> %u/%d %s\n", i + 1, ASMCONF_NTESTS, asmconf_tests[i].name);
        memset(asmconf_regs, 0, sizeof(asmconf_regs));

        __try {
            asmconf_tests[i].fn();
            g_ran++;
        }
        __except (EXCEPTION_EXECUTE_HANDLER) {
            g_crash++; g_fail++;
            lg("[asmconf] CRASH %-44s exception=0x%08lX\n",
               asmconf_tests[i].name, (unsigned long)GetExceptionCode());
            continue;
        }

        for (j = 0; j < asmconf_tests[i].n_exp; j++) {
            const asmconf_exp *e = &asmconf_expected[asmconf_tests[i].first_exp + j];
            unsigned long long got = captured(e->reg, e->lane);
            if (got != e->val) {
                char rn[24];
                regname(e->reg, e->lane, rn, sizeof(rn));
                if (!bad) lg("[asmconf] FAIL %s\n", asmconf_tests[i].name);
                bad = 1;
                lg("[asmconf]      %-12s expected 0x%016llX  got 0x%016llX\n", rn, e->val, got);
            }
        }
        if (bad) g_fail++; else g_pass++;
    }

    save_next(-1);
    lg("[asmconf] DONE ran=%d/%d pass=%d fail=%d crash=%d rev=ml541\n",
       g_ran + g_crash, ASMCONF_NTESTS, g_pass, g_fail, g_crash);
    if (g_ran + g_crash != ASMCONF_NTESTS)
        lg("[asmconf] WARNING incomplete — %d tests never ran; result NOT conclusive\n",
           ASMCONF_NTESTS - (g_ran + g_crash));
    lg(g_fail ? "[asmconf] VERDICT: DIVERGENCE FOUND — see FAIL/CRASH lines above\n"
              : "[asmconf] VERDICT: no divergence across the suite\n");
    if (g_fh != INVALID_HANDLE_VALUE) { FlushFileBuffers(g_fh); CloseHandle(g_fh); }
    return g_fail ? 1 : 0;
}
