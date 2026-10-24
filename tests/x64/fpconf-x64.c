/* fpconf-x64.c — FEX float/SSE conformance test (ml539)
 *
 * WHY THIS EXISTS
 * ---------------
 * The Steam login window renders with intact ELEMENTS placed at WRONG POSITIONS:
 * the QR is a valid QR, the Steam logo is the logo, but panels are split and
 * displaced, and the QR's halo moves independently of the QR it surrounds.
 * Everything we own has been exonerated:
 *
 *   - the blit and present path      (Chromium's SOURCE bitmap is already corrupt)
 *   - the writers' own arithmetic    (row*stride + col*4 == destination, exactly)
 *   - the vector blitter/raster code (ml538: disabling AVX changed WHICH Skia
 *                                     routines ran — one writer vanished, the other
 *                                     two swapped magnitudes — and the corruption
 *                                     was byte-identical)
 *   - memory ordering                (ml512/ml513 vector+memcpy TSO: no effect)
 *
 * Intact content at wrong coordinates points at the COMPOSITOR's quad geometry:
 * 4x4 float transforms (SkM44 / gfx::Transform), point and rect mapping, and the
 * final float->int device-pixel conversion. That math is scalar and 128-bit SSE.
 * It has never been tested for correctness here — the TSO work was about memory
 * ORDERING, and the SIMD census was about misaligned STORES. Neither asks whether
 * a vector op computes the right VALUE.
 *
 * So: compute the same quantities two ways and compare.
 *   REF  — plain scalar C, one operation at a time, no vectorisation
 *   SSE  — the same math through __m128 intrinsics, the way Skia does it
 * Both run under FEX. If they disagree, FEX's vector path is wrong and we have the
 * bug isolated in a repro we control, with no Steam and no variance lottery.
 *
 * DISCIPLINE
 * ----------
 * This is a SELF-CALIBRATING test: it prints PASS lines as well as FAIL lines, and
 * a final census. "No FAIL output" is only meaningful if the PASS count is what we
 * expect — a test that silently ran zero cases would otherwise look like success,
 * which is the failure mode that has burned several probes in this port.
 *
 * The reference side is written to defeat auto-vectorisation (volatile
 * accumulators, no restrict) so that -O2 cannot quietly turn REF into the same SSE
 * code as the subject and make every comparison trivially pass.
 */

#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <math.h>
#include <emmintrin.h>   /* SSE2 */

static int g_pass, g_fail, g_cases;

/* Defeat constant folding. Every input here is a literal, so -O2 is entitled to
 * evaluate BOTH the reference and the SSE side at compile time and emit two
 * identical constants — the test would then pass without executing a single
 * float instruction under FEX. That is the "probe that cannot fire" failure
 * this port has hit repeatedly, and it looks exactly like success.
 *
 * Multiplying by a volatile 1.0f is exact for every finite float (no rounding,
 * no flush) but the optimiser cannot see through the volatile load. */
static volatile float g_one = 1.0f;
static float lf(float x) { return x * g_one; }
static void lf4(const float *src, float *dst)
{
    int i;
    for (i = 0; i < 4; i++) dst[i] = lf(src[i]);
}

/* Dual sink. stdout alone has burned probes in this port: writes from a guest
 * process can land in a console we never read, and "no output" then reads as
 * "no divergence". The file gives three DISTINGUISHABLE states:
 *   file missing        -> the test never ran / sink broken
 *   banner only         -> ran but executed no cases
 *   banner + DONE line  -> real result */
static HANDLE g_fh = INVALID_HANDLE_VALUE;

static void emit(const char *s)
{
    DWORD w;
    DWORD n = (DWORD)strlen(s);
    WriteFile(GetStdHandle(STD_OUTPUT_HANDLE), s, n, &w, NULL);
    if (g_fh != INVALID_HANDLE_VALUE) WriteFile(g_fh, s, n, &w, NULL);
}

static void logf_(const char *fmt, ...)
{
    char buf[512];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    emit(buf);
}

/* Exact bit comparison. Float equality is the right test here: both sides do the
 * same operations in the same order on the same inputs, so a correct translation
 * must produce bit-identical results. Tolerance would hide exactly the small
 * lane/rounding errors we are hunting. */
static int same_f(float a, float b) { return memcmp(&a, &b, 4) == 0; }

static void check4(const char *name, const float ref[4], const float got[4])
{
    int i, bad = 0;
    g_cases++;
    for (i = 0; i < 4; i++) if (!same_f(ref[i], got[i])) bad = 1;
    if (bad) {
        g_fail++;
        logf_("[fpconf] FAIL %-22s ref={%.9g,%.9g,%.9g,%.9g} got={%.9g,%.9g,%.9g,%.9g}\n",
              name, ref[0], ref[1], ref[2], ref[3], got[0], got[1], got[2], got[3]);
        for (i = 0; i < 4; i++)
            if (!same_f(ref[i], got[i]))
                logf_("[fpconf]      lane %d: ref bits %08X  got bits %08X\n",
                      i, *(unsigned *)&ref[i], *(unsigned *)&got[i]);
    } else {
        g_pass++;
        logf_("[fpconf] pass %-22s {%.9g,%.9g,%.9g,%.9g}\n",
              name, got[0], got[1], got[2], got[3]);
    }
}

static void check_i(const char *name, int ref, int got)
{
    g_cases++;
    if (ref != got) { g_fail++; logf_("[fpconf] FAIL %-22s ref=%d got=%d\n", name, ref, got); }
    else            { g_pass++; logf_("[fpconf] pass %-22s %d\n", name, got); }
}

/* ---------- reference: scalar, deliberately un-vectorisable ---------- */

static void ref_mat4_mul_vec(const float m[16], const float v[4], float out[4])
{
    int r;
    for (r = 0; r < 4; r++) {
        volatile float acc = 0.0f;      /* volatile: blocks auto-vectorisation */
        acc = acc + m[r * 4 + 0] * v[0];
        acc = acc + m[r * 4 + 1] * v[1];
        acc = acc + m[r * 4 + 2] * v[2];
        acc = acc + m[r * 4 + 3] * v[3];
        out[r] = acc;
    }
}

/* ---------- subject: the SSE form Skia/cc actually use ---------- */

static void sse_mat4_mul_vec(const float m[16], const float v[4], float out[4])
{
    /* column-combination form: r = c0*v.x + c1*v.y + c2*v.z + c3*v.w,
     * which is how SkM44::map and gfx::Transform::MapPoint are written. */
    __m128 c0 = _mm_set_ps(m[12], m[8],  m[4], m[0]);
    __m128 c1 = _mm_set_ps(m[13], m[9],  m[5], m[1]);
    __m128 c2 = _mm_set_ps(m[14], m[10], m[6], m[2]);
    __m128 c3 = _mm_set_ps(m[15], m[11], m[7], m[3]);
    __m128 r  = _mm_mul_ps(c0, _mm_set1_ps(v[0]));
    r = _mm_add_ps(r, _mm_mul_ps(c1, _mm_set1_ps(v[1])));
    r = _mm_add_ps(r, _mm_mul_ps(c2, _mm_set1_ps(v[2])));
    r = _mm_add_ps(r, _mm_mul_ps(c3, _mm_set1_ps(v[3])));
    _mm_storeu_ps(out, r);
}

int main(void)
{
    g_fh = CreateFileA("C:\\fpconf.log", GENERIC_WRITE, FILE_SHARE_READ, NULL,
                       CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    logf_("[fpconf] start rev=ml539 — FEX float/SSE conformance\n");

    /* A transform of the shape a compositor actually builds: scale, then a
     * LARGE translation. The translation column is the suspect — the corruption's
     * signature is a large constant positional offset (~-550,-97), which is what a
     * wrong translation element produces. Small rounding errors could not. */
    static const float M[16] = {
        2.0f, 0.0f, 0.0f, 162.0f,
        0.0f, 3.0f, 0.0f, 164.0f,
        0.0f, 0.0f, 1.0f,   0.0f,
        0.0f, 0.0f, 0.0f,   1.0f,
    };
    static const float pts[][4] = {
        { 0.0f,   0.0f,   0.0f, 1.0f },
        { 279.0f, 154.0f, 0.0f, 1.0f },   /* the exact quad origin seen on device */
        { 700.0f, 440.0f, 0.0f, 1.0f },   /* the buffer's far corner */
        { -550.0f, -97.0f, 0.0f, 1.0f },  /* the observed displacement, as an input */
        { 0.5f,   0.25f,  0.0f, 1.0f },
    };
    const int npts = (int)(sizeof(pts) / sizeof(pts[0]));
    int i;

    for (i = 0; i < npts; i++) {
        float r[4], g[4], m[16], v[4];
        char nm[40];
        int q;
        for (q = 0; q < 16; q++) m[q] = lf(M[q]);
        lf4(pts[i], v);
        ref_mat4_mul_vec(m, v, r);
        sse_mat4_mul_vec(m, v, g);
        snprintf(nm, sizeof(nm), "mat4*vec[%d]", i);
        check4(nm, r, g);
    }

    /* Lane-order sanity: a shuffle or set_ps lane mix-up is precisely the class
     * that would corrupt a translation column while leaving content intact. Use
     * four distinguishable values so ANY permutation shows up. */
    {
        float ref[4] = { 1.0f, 2.0f, 4.0f, 8.0f }, got[4];
        _mm_storeu_ps(got, _mm_set_ps(lf(8.0f), lf(4.0f), lf(2.0f), lf(1.0f)));  /* set_ps is reversed */
        check4("set_ps lane order", ref, got);
    }
    {
        static const float lit[4] = { 1.0f, 2.0f, 4.0f, 8.0f };
        float src[4];
        float ref[4] = { 4.0f, 8.0f, 1.0f, 2.0f }, got[4];
        __m128 v;
        lf4(lit, src);
        v = _mm_loadu_ps(src);
        _mm_storeu_ps(got, _mm_shuffle_ps(v, v, _MM_SHUFFLE(1, 0, 3, 2)));
        check4("shuffle 1032", ref, got);
    }
    {
        static const float la[4] = { 1.0f, 2.0f, 3.0f, 4.0f };
        static const float lb[4] = { 10.0f, 20.0f, 30.0f, 40.0f };
        float a[4], b[4];
        float ref[4] = { 1.0f, 10.0f, 2.0f, 20.0f }, got[4];
        lf4(la, a); lf4(lb, b);
        _mm_storeu_ps(got, _mm_unpacklo_ps(_mm_loadu_ps(a), _mm_loadu_ps(b)));
        check4("unpacklo", ref, got);
    }

    /* float -> int device pixel. cvttss2si truncates toward zero; cvtss2si uses
     * the MXCSR rounding mode (round-to-nearest-even by default). Getting either
     * wrong shifts geometry, and NEGATIVE inputs are where truncate-vs-floor
     * diverge — which matters because the displacement is negative. */
    {
        static const float fv[] = { 1.5f, 2.5f, -1.5f, -2.5f, 279.4f, 279.6f,
                                    -550.5f, -97.5f, 0.49999997f };
        static const int   trunc_ref[] = { 1, 2, -1, -2, 279, 279, -550, -97, 0 };
        static const int   near_ref[]  = { 2, 2, -2, -2, 279, 280, -550, -98, 0 };
        int k;
        for (k = 0; k < (int)(sizeof(fv) / sizeof(fv[0])); k++) {
            char nm[48];
            snprintf(nm, sizeof(nm), "cvttss2si %.7g", fv[k]);
            check_i(nm, trunc_ref[k], _mm_cvttss_si32(_mm_set_ss(lf(fv[k]))));
            snprintf(nm, sizeof(nm), "cvtss2si %.7g", fv[k]);
            check_i(nm, near_ref[k], _mm_cvtss_si32(_mm_set_ss(lf(fv[k]))));
        }
    }

    /* Packed truncate — cvttps2dq does four at once, which is how a rect's four
     * edges become device pixels in one op. A single bad lane here displaces one
     * edge of a quad and nothing else, which would look exactly like a panel
     * shifted while its neighbours are fine. */
    {
        static const float lin[4] = { 279.6f, -97.5f, 700.4f, -550.5f };
        float in[4];
        int ref[4]  = { 279, -97, 700, -550 };
        int got[4];
        lf4(lin, in);
        _mm_storeu_si128((__m128i *)got, _mm_cvttps_epi32(_mm_loadu_ps(in)));
        g_cases++;
        if (memcmp(ref, got, sizeof(ref))) {
            g_fail++;
            logf_("[fpconf] FAIL %-22s ref={%d,%d,%d,%d} got={%d,%d,%d,%d}\n",
                  "cvttps2dq packed", ref[0], ref[1], ref[2], ref[3],
                  got[0], got[1], got[2], got[3]);
        } else {
            g_pass++;
            logf_("[fpconf] pass %-22s {%d,%d,%d,%d}\n", "cvttps2dq packed",
                  got[0], got[1], got[2], got[3]);
        }
    }

    /* Unaligned 16-byte load/store straddling a page boundary. Matrices are
     * 64 bytes and are NOT always 16-aligned in Chromium's heaps; this port has a
     * documented history of misaligned-access bugs (#71, #83), and the Mach
     * handler EMULATES misaligned accesses — so a mistake there would silently
     * return wrong lanes rather than crashing. */
    {
        char *big = (char *)VirtualAlloc(NULL, 0x2000, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
        if (!big) { logf_("[fpconf] SKIP straddle — VirtualAlloc failed\n"); }
        else {
            static const float lr[4] = { 1.25f, -2.5f, 3.75f, -4.0f };
            float ref[4], got[4];
            char *p = big + 0x1000 - 8;          /* 8 bytes before the page edge */
            lf4(lr, ref);
            memcpy(p, ref, sizeof(ref));
            _mm_storeu_ps(got, _mm_loadu_ps((const float *)p));
            check4("loadu straddling page", ref, got);
            VirtualFree(big, 0, MEM_RELEASE);
        }
    }

    /* Self-calibration: 5 mat4 + set_ps + shuffle + unpacklo + 9*2 cvt + packed
     * + straddle = 28. A short count means a case was skipped, and "0 FAIL" from
     * a run that skipped cases is not a pass. */
    logf_("[fpconf] DONE cases=%d (expect 28) pass=%d fail=%d rev=ml539\n",
          g_cases, g_pass, g_fail);
    if (g_cases != 28)
        logf_("[fpconf] WARNING incomplete — %d cases missing, result NOT conclusive\n",
              28 - g_cases);
    logf_(g_fail ? "[fpconf] VERDICT: FEX FLOAT/SSE DIVERGES — bug isolated here\n"
                 : "[fpconf] VERDICT: no divergence in this set\n");
    if (g_fh != INVALID_HANDLE_VALUE) { FlushFileBuffers(g_fh); CloseHandle(g_fh); }
    return g_fail ? 1 : 0;
}
