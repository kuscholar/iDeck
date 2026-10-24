/* Offline proof that the runtime's conversion request actually converts.
 *
 * Runs the SAME service the device uses, over the SAME argument struct, against
 * the SAME bytecode the tests embed. What it cannot check is Metal accepting the
 * result on a phone; what it does check is everything up to that, on a machine
 * where a failure costs seconds instead of a device round.
 *
 * It exists because the shader path changed from "load a library built at build
 * time" to "compile the application's bytecode now", and the failure modes of
 * the second are entirely different. */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdarg.h>
#include "madeira_ir_abi.h"

extern "C" int madeira_ir_convert_impl(struct madeira_ir_convert_args *a);

/* The same bytes the Windows tests embed, generated from the same .dxil. */
#include "tri_dxil.h"

static int fails = 0, checks = 0;
static void check(int ok, const char *fmt, ...) {
    va_list ap; va_start(ap, fmt);
    checks++;
    printf("  %-4s ", ok ? "ok" : "FAIL");
    vprintf(fmt, ap); printf("\n");
    va_end(ap);
    if (!ok) fails++;
}

/* A shader must be converted against the root signature it DECLARES. Converting
 * everything against a single root CBV made the textured pixel shaders fail to
 * compile, which looked like a shader fault and was really the harness binding
 * the wrong layout. Each entry now carries its own. */
static void layout_cbv_only(struct madeira_ir_root_param *p,
                            struct madeira_ir_root_range *r, unsigned *np, unsigned *nr) {
    memset(p, 0, sizeof *p);
    p[0].type = MADEIRA_IR_PARAM_CBV;
    p[0].visibility = MADEIRA_IR_VIS_ALL;
    (void)r;
    *np = 1; *nr = 0;
}

static void layout_textured(struct madeira_ir_root_param *p,
                            struct madeira_ir_root_range *r, unsigned *np, unsigned *nr) {
    memset(p, 0, sizeof *p * 3);
    memset(r, 0, sizeof *r * 2);
    p[0].type = MADEIRA_IR_PARAM_CBV;      p[0].visibility = MADEIRA_IR_VIS_ALL;
    p[1].type = MADEIRA_IR_PARAM_TABLE;    p[1].visibility = MADEIRA_IR_VIS_ALL;
    p[1].first_range = 0; p[1].num_ranges = 1;
    p[2].type = MADEIRA_IR_PARAM_TABLE;    p[2].visibility = MADEIRA_IR_VIS_ALL;
    p[2].first_range = 1; p[2].num_ranges = 1;
    r[0].range_type = MADEIRA_IR_RANGE_SRV;     r[0].num_descriptors = 1;
    r[1].range_type = MADEIRA_IR_RANGE_SAMPLER; r[1].num_descriptors = 1;
    *np = 3; *nr = 2;
}

typedef void (*layout_fn)(struct madeira_ir_root_param *, struct madeira_ir_root_range *,
                          unsigned *, unsigned *);

static int convert_rs(const unsigned char *dxil, size_t n, const char *entry,
                      uint32_t os, uint32_t family, const char *ver, layout_fn layout,
                      unsigned char **out, size_t *out_n, char *name) {
    struct madeira_ir_convert_args a;
    struct madeira_ir_root_param p[4];
    struct madeira_ir_root_range r[4];
    unsigned np = 0, nr = 0;
    (layout ? layout : layout_cbv_only)(p, r, &np, &nr);

    memset(&a, 0, sizeof a);
    a.dxil = (uint64_t)(uintptr_t)dxil; a.dxil_len = n;
    a.entry_point = (uint64_t)(uintptr_t)entry;
    a.params = (uint64_t)(uintptr_t)p; a.num_params = np;
    a.ranges = (uint64_t)(uintptr_t)r; a.num_ranges = nr;
    a.target_os = os; a.gpu_family = family;
    a.os_version = (uint64_t)(uintptr_t)ver;
    a.out_entry = (uint64_t)(uintptr_t)name;
    madeira_ir_convert_impl(&a);
    if (a.ret_status != MADEIRA_IR_BUFFER_TOO_SMALL && a.ret_status != MADEIRA_IR_OK)
        return (int)a.ret_status;

    size_t need = (size_t)a.ret_len;
    unsigned char *buf = (unsigned char *)malloc(need);
    memset(&a, 0, sizeof a);
    a.dxil = (uint64_t)(uintptr_t)dxil; a.dxil_len = n;
    a.entry_point = (uint64_t)(uintptr_t)entry;
    a.params = (uint64_t)(uintptr_t)p; a.num_params = np;
    a.ranges = (uint64_t)(uintptr_t)r; a.num_ranges = nr;
    a.target_os = os; a.gpu_family = family;
    a.os_version = (uint64_t)(uintptr_t)ver;
    a.out_buf = (uint64_t)(uintptr_t)buf; a.out_cap = need;
    a.out_entry = (uint64_t)(uintptr_t)name;
    madeira_ir_convert_impl(&a);
    if (a.ret_status != MADEIRA_IR_OK) { free(buf); return (int)a.ret_status; }
    *out = buf; *out_n = (size_t)a.ret_len;
    return MADEIRA_IR_OK;
}

/* From metal_irconverter.h. The first version of this test used 1007 for
 * Apple9, which is Apple7 -- a valid enum member, so it converted happily and
 * proved nothing about the family actually being requested. */
static int convert(const unsigned char *dxil, size_t n, const char *entry,
                   uint32_t os, uint32_t family, const char *ver,
                   unsigned char **out, size_t *out_n, char *name) {
    return convert_rs(dxil, n, entry, os, family, ver, layout_cbv_only, out, out_n, name);
}

#define IR_FAMILY_APPLE9 1009
#define IR_FAMILY_METAL3 5001

int main(void) {
    printf("madeira-d3d12 runtime conversion round trip\n");

    struct { const unsigned char *b; size_t n; const char *entry; const char *tag; layout_fn rs; } stages[] = {
        { cube_vs_dxil, sizeof cube_vs_dxil, "MainVS", "cube VS", layout_cbv_only },
        { cube_ps_dxil, sizeof cube_ps_dxil, "MainPS", "cube PS", layout_cbv_only },
        { tri_vs_dxil,  sizeof tri_vs_dxil,  "MainVS", "triangle VS", layout_cbv_only },
        { tri_ps_dxil,  sizeof tri_ps_dxil,  "MainPS", "triangle PS", layout_cbv_only },
        { tex_vs_dxil,  sizeof tex_vs_dxil,  "MainVS", "textured quad VS", layout_textured },
        { tex_ps_dxil,  sizeof tex_ps_dxil,  "MainPS", "textured quad PS", layout_textured },
        { texcube_vs_dxil, sizeof texcube_vs_dxil, "MainVS", "textured cube VS", layout_textured },
        { texcube_ps_dxil, sizeof texcube_ps_dxil, "MainPS", "textured cube PS", layout_textured },
    };
    struct { uint32_t os; uint32_t fam; const char *ver; const char *tag; } targets[] = {
        { MADEIRA_IR_OS_IOS,   IR_FAMILY_APPLE9, "17.0", "iOS/Apple9" },
        { MADEIRA_IR_OS_MACOS, IR_FAMILY_METAL3, "15.0", "macOS/Metal3" },
    };

    for (unsigned t = 0; t < 2; t++) {
        printf("\n-- target %s\n", targets[t].tag);
        for (unsigned i = 0; i < sizeof stages / sizeof stages[0]; i++) {
            unsigned char *out = NULL; size_t out_n = 0; char name[MADEIRA_IR_ENTRY_MAX] = {0};
            int rc = convert_rs(stages[i].b, stages[i].n, stages[i].entry,
                                targets[t].os, targets[t].fam, targets[t].ver, stages[i].rs,
                                &out, &out_n, name);
            check(rc == MADEIRA_IR_OK, "%s converted (status %d)", stages[i].tag, rc);
            if (rc != MADEIRA_IR_OK) continue;
            check(out_n > 0, "%s produced %zu bytes of metallib", stages[i].tag, out_n);
            /* A Metal library starts with MTLB. If this is wrong the backend
             * would reject it later, on a device, with far less to go on. */
            check(out_n > 4 && memcmp(out, "MTLB", 4) == 0,
                  "%s output is a Metal library (%.4s)", stages[i].tag, (const char *)out);
            check(name[0] != '\0', "%s reflected an entry point name ('%s')", stages[i].tag, name);
            free(out);
        }
    }

    /* The converter does NOT reject an unknown entry point; it compiles happily
     * and reports an empty reflected name. The service has to impose that bound
     * itself, so check that it does. */
    {
        unsigned char *out = NULL; size_t out_n = 0; char name[MADEIRA_IR_ENTRY_MAX] = {0};
        int rc = convert(cube_vs_dxil, sizeof cube_vs_dxil, "NoSuchEntryPoint",
                         MADEIRA_IR_OS_IOS, IR_FAMILY_APPLE9, "17.0", &out, &out_n, name);
        check(rc == MADEIRA_IR_EMPTY_ENTRY,
              "a missing entry point is refused rather than yielding an empty library (status %d)", rc);
        free(out);
    }

    /* Bytecode that is not DXIL must fail, not silently produce something. */
    {
        unsigned char junk[64]; memset(junk, 0, sizeof junk); memcpy(junk, "DXBC", 4);
        unsigned char *out = NULL; size_t out_n = 0; char name[MADEIRA_IR_ENTRY_MAX] = {0};
        int rc = convert(junk, sizeof junk, "MainVS",
                         MADEIRA_IR_OS_IOS, IR_FAMILY_APPLE9, "17.0", &out, &out_n, name);
        check(rc != MADEIRA_IR_OK, "junk bytecode fails conversion (status %d)", rc);
        free(out);
    }

    /* Does the converter find the entry point itself? D3D12 never tells the
     * runtime a name: the bytecode is already compiled for one. If NULL works,
     * the hard-coded "MainVS"/"MainPS" can go. */
    {
        unsigned char *out = NULL; size_t out_n = 0; char name[MADEIRA_IR_ENTRY_MAX] = {0};
        int rc = convert(cube_vs_dxil, sizeof cube_vs_dxil, NULL,
                         MADEIRA_IR_OS_IOS, IR_FAMILY_APPLE9, "17.0", &out, &out_n, name);
        check(rc == MADEIRA_IR_OK && name[0],
              "no entry point name supplied: the converter uses the one in the bytecode ('%s')", name);
        free(out);
    }

    printf("\n%d checks, %d failures\n", checks, fails);
    return fails != 0;
}
