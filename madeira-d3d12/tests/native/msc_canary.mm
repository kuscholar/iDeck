/*  M1 canary: DXIL -> Metal shader converter -> MTLLibrary -> pipeline -> pixels.
 *
 *  This is the gate the design puts before any COM work: if a converted shader
 *  cannot read a root CBV through the top-level argument buffer and produce the
 *  colour we put in it, there is no point implementing D3D12 objects on top.
 *
 *  What it proves, in order:
 *
 *    1. The converter loads and its API matches the pinned package headers.
 *    2. An explicitly constructed root signature (not the one embedded in the
 *       DXIL) drives the generated argument-buffer layout.
 *    3. The emitted metallib loads on the executing Metal device.
 *    4. Two different constant-buffer states produce two different, exactly
 *       predicted images. A wrong argument-buffer offset or bind point yields a
 *       wrong colour rather than a plausible one, which is the whole point.
 *    5. Recompiling the same inputs reproduces identical bytecode, which is what
 *       makes a shader cache safe to key.
 *    6. Bad inputs fail with bounded, named errors instead of crashing.
 *
 *  Binding ABI is taken from the package's own runtime header, not assumed:
 *  the top-level argument buffer binds at index kIRArgumentBufferBindPoint, and
 *  a root CBV appears there as a 64-bit GPU address at offset 0 because this
 *  root signature declares no root constants ahead of it.
 */

#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <dlfcn.h>
#include <mach/mach.h>
#include <mach/mach_time.h>
#include <mach/task_info.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "metal_irconverter/metal_irconverter.h"
#include "metal_irconverter_runtime/metal_irconverter_runtime.h"

/* Convert for the platform this binary runs on. A library built for macOS is
 * not loadable by an iOS device and vice versa, which is why the design keeps
 * target OS in the cache key and forbids reusing a macOS entry on iOS. */
#if TARGET_OS_IPHONE
#  define CANARY_OS        IROperatingSystem_iOS
#  define CANARY_OS_NAME   "iOS"
#  define CANARY_OS_VER    "17.0"
#  define CANARY_OS_VER_ALT "16.0"
#else
#  define CANARY_OS        IROperatingSystem_macOS
#  define CANARY_OS_NAME   "macOS"
#  define CANARY_OS_VER    "15.0"
#  define CANARY_OS_VER_ALT "14.0"
#endif

#define IR_FUNC_LIST(X) \
    X(IRObjectCreateFromDXIL) \
    X(IRObjectDestroy) \
    X(IRObjectGetMetalIRShaderStage) \
    X(IRObjectGetMetalLibBinary) \
    X(IRObjectGetReflection) \
    X(IRCompilerCreate) \
    X(IRCompilerDestroy) \
    X(IRCompilerSetGlobalRootSignature) \
    X(IRCompilerSetEntryPointName) \
    X(IRCompilerSetMinimumDeploymentTarget) \
    X(IRCompilerSetMinimumGPUFamily) \
    X(IRCompilerAllocCompileAndLink) \
    X(IRRootSignatureCreateFromDescriptor) \
    X(IRRootSignatureDestroy) \
    X(IRMetalLibBinaryCreate) \
    X(IRMetalLibBinaryDestroy) \
    X(IRMetalLibGetBytecodeSize) \
    X(IRMetalLibGetBytecode) \
    X(IRShaderReflectionCreate) \
    X(IRShaderReflectionDestroy) \
    X(IRShaderReflectionGetEntryPointFunctionName) \
    X(IRErrorGetCode) \
    X(IRErrorDestroy)

/* ---- converter loaded at RUNTIME -------------------------------------------
 *
 * A real D3D12 runtime cannot link the converter at build time and then fail to
 * start when it is absent; and "does the iOS dylib load inside our process" is
 * precisely the question the in-app gate has to answer. So every entry point is
 * resolved through dlopen/dlsym, and a missing one is named rather than turning
 * into a launch-time dyld abort. */
struct IRFns {
    void *handle;
#define IR_DECL(f) decltype(&::f) f;
    IR_FUNC_LIST(IR_DECL)
#undef IR_DECL
};
static IRFns ir;

static const char *ir_load(const char *path) {
    static char errbuf[512];
    ir.handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    if (!ir.handle) {
        snprintf(errbuf, sizeof errbuf, "dlopen failed: %s", dlerror());
        return errbuf;
    }
#define IR_BIND(f)                                                              \
    ir.f = (decltype(&::f))dlsym(ir.handle, #f);                                \
    if (!ir.f) { snprintf(errbuf, sizeof errbuf, "missing symbol %s", #f); return errbuf; }
    IR_FUNC_LIST(IR_BIND)
#undef IR_BIND
    return NULL;
}

static int g_checks, g_fails;

/* One output path for both callers: stdout when run standalone over SSH, and
 * Madeira's log when the app drives it, so the two runs are comparable line for
 * line instead of being two different tests that happen to share a name. */
static void (*g_sink)(const char *) = NULL;
/* In-app, stderr is not captured until the Wine log is wired up later in
 * startup, so the verdict reached the log but the 27 individual results did
 * not. A transcript file does not depend on that ordering. */
static FILE *g_log = NULL;
static void cout_(const char *fmt, ...) {
    char buf[1024];
    va_list ap; va_start(ap, fmt);
    vsnprintf(buf, sizeof buf, fmt, ap);
    va_end(ap);
    if (g_sink) g_sink(buf); else fputs(buf, stderr);
    if (g_log) { fputs(buf, g_log); fflush(g_log); }
}
#define CHECK(cond, ...) do {                                                  \
    g_checks++;                                                                \
    if (!(cond)) { g_fails++; cout_("  FAIL  " __VA_ARGS__); cout_("\n"); }   \
    else         { cout_("  ok    " __VA_ARGS__); cout_("\n"); }             \
} while (0)

static double now_ms(void) {
    static mach_timebase_info_data_t tb;
    if (!tb.denom) mach_timebase_info(&tb);
    return (double)mach_absolute_time() * tb.numer / tb.denom / 1.0e6;
}

static size_t footprint_kb(void) {
    task_vm_info_data_t info; mach_msg_type_number_t n = TASK_VM_INFO_COUNT;
    if (task_info(mach_task_self(), TASK_VM_INFO, (task_info_t)&info, &n) != KERN_SUCCESS) return 0;
    return (size_t)(info.phys_footprint >> 10);
}

static uint8_t *load_file(const char *path, size_t *out_len) {
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET);
    uint8_t *p = (uint8_t *)malloc((size_t)n);
    if (p && fread(p, 1, (size_t)n, f) != (size_t)n) { free(p); p = NULL; }
    fclose(f);
    if (p) *out_len = (size_t)n;
    return p;
}

/* The canary's root signature, built through the converter's own descriptor API
 * rather than relying on the RTS0 blob the compiler embedded. The design calls
 * for the explicit path from the start: a real D3D12 runtime receives a root
 * signature from the application and must be able to impose it. */
/* Root constants (four 32-bit values at b0) followed by a root CBV at b1.
 * The manual's layout rule puts the constants at bytes 0..15 and the CBV's
 * 64-bit address at byte 16; the layout fixture checks that empirically rather
 * than trusting the arithmetic. */
static IRRootSignature *make_root_signature_constants_then_cbv(IRError **err) {
    IRRootParameter1 params[2];
    memset(params, 0, sizeof params);

    params[0].ParameterType = IRRootParameterType32BitConstants;
    params[0].Constants.ShaderRegister = 0;
    params[0].Constants.RegisterSpace = 0;
    params[0].Constants.Num32BitValues = 4;
    params[0].ShaderVisibility = IRShaderVisibilityAll;

    params[1].ParameterType = IRRootParameterTypeCBV;
    params[1].Descriptor.ShaderRegister = 1;
    params[1].Descriptor.RegisterSpace = 0;
    params[1].Descriptor.Flags = IRRootDescriptorFlagNone;
    params[1].ShaderVisibility = IRShaderVisibilityAll;

    IRVersionedRootSignatureDescriptor desc;
    memset(&desc, 0, sizeof desc);
    desc.version = IRRootSignatureVersion_1_1;
    desc.desc_1_1.NumParameters = 2;
    desc.desc_1_1.pParameters = params;
    desc.desc_1_1.Flags = IRRootSignatureFlagNone;
    return ir.IRRootSignatureCreateFromDescriptor(&desc, err);
}

static IRRootSignature *make_root_signature(IRError **err) {
    IRRootParameter1 param;
    memset(&param, 0, sizeof param);
    param.ParameterType = IRRootParameterTypeCBV;
    param.Descriptor.ShaderRegister = 0;
    param.Descriptor.RegisterSpace = 0;
    param.Descriptor.Flags = IRRootDescriptorFlagNone;
    param.ShaderVisibility = IRShaderVisibilityAll;

    IRVersionedRootSignatureDescriptor desc;
    memset(&desc, 0, sizeof desc);
    desc.version = IRRootSignatureVersion_1_1;
    desc.desc_1_1.NumParameters = 1;
    desc.desc_1_1.pParameters = &param;
    desc.desc_1_1.NumStaticSamplers = 0;
    desc.desc_1_1.pStaticSamplers = NULL;
    desc.desc_1_1.Flags = IRRootSignatureFlagNone;
    return ir.IRRootSignatureCreateFromDescriptor(&desc, err);
}

typedef struct {
    uint8_t *bytes;
    size_t   len;
    char     entry[256];
} ConvertedShader;

/* Convert one DXIL blob for one stage. Returns 0 on success. Any converter
 * object created here is destroyed here; the caller receives copied bytes, so
 * nothing converter-owned escapes, which the design requires explicitly. */
static int convert(const uint8_t *dxil, size_t dxil_len, const char *entry_point,
                   IRShaderStage *out_stage, ConvertedShader *out, double *out_ms,
                   const char *os_version, IRGPUFamily family, int quiet,
                   IRRootSignature *(*rs_builder)(IRError **),
                   IROperatingSystem target_os = CANARY_OS) {
    double t0 = now_ms();
    int rc = -1;
    IRError *err = NULL;
    IRObject *input = NULL, *output = NULL;
    IRCompiler *compiler = NULL;
    IRRootSignature *rs = NULL;
    IRMetalLibBinary *lib = NULL;
    IRShaderReflection *refl = NULL;
    /* Declared before the first goto: C++ forbids jumping over initialisations. */
    IRShaderStage stage = IRShaderStageInvalid;
    size_t n = 0;
    const char *nm = NULL;

    input = ir.IRObjectCreateFromDXIL(dxil, dxil_len, IRBytecodeOwnershipNone);
    if (!input) { if (!quiet) cout_("        IRObjectCreateFromDXIL returned NULL\n"); goto done; }

    rs = (rs_builder ? rs_builder : make_root_signature)(&err);
    if (!rs) {
        if (!quiet) cout_("        root signature error code %u\n", err ? ir.IRErrorGetCode(err) : 0);
        goto done;
    }

    compiler = ir.IRCompilerCreate();
    if (!compiler) goto done;
    ir.IRCompilerSetGlobalRootSignature(compiler, rs);
    ir.IRCompilerSetEntryPointName(compiler, entry_point);
    ir.IRCompilerSetMinimumDeploymentTarget(compiler, target_os, os_version);
    ir.IRCompilerSetMinimumGPUFamily(compiler, family);

    output = ir.IRCompilerAllocCompileAndLink(compiler, entry_point, input, &err);
    if (!output) {
        if (!quiet) cout_("        compile/link error code %u\n", err ? ir.IRErrorGetCode(err) : 0);
        goto done;
    }

    stage = ir.IRObjectGetMetalIRShaderStage(output);
    lib = ir.IRMetalLibBinaryCreate();
    if (!ir.IRObjectGetMetalLibBinary(output, stage, lib)) {
        if (!quiet) cout_("        IRObjectGetMetalLibBinary failed for stage %d\n", (int)stage);
        goto done;
    }

    n = ir.IRMetalLibGetBytecodeSize(lib);
    if (!n) goto done;
    out->bytes = (uint8_t *)malloc(n);
    if (!out->bytes) goto done;
    out->len = ir.IRMetalLibGetBytecode(lib, out->bytes);

    /* The converter renames entry points; ask reflection rather than guessing. */
    out->entry[0] = '\0';
    refl = ir.IRShaderReflectionCreate();
    if (refl && ir.IRObjectGetReflection(output, stage, refl)) {
        nm = ir.IRShaderReflectionGetEntryPointFunctionName(refl);
        if (nm) snprintf(out->entry, sizeof out->entry, "%s", nm);
    }
    /* The converter does NOT reject an unknown entry point: measured, it compiles
     * and links happily and reports an EMPTY entry-point function name. The
     * failure would otherwise surface much later as a missing MTLFunction. A
     * D3D12 runtime has to impose this bound itself, so the canary treats an
     * empty reflected name as the error it is. */
    if (!out->entry[0]) {
        if (!quiet) cout_("        reflection returned an empty entry-point name for '%s'\n", entry_point);
        free(out->bytes); out->bytes = NULL; out->len = 0;
        rc = -1;
        goto done;
    }

    if (out_stage) *out_stage = stage;
    rc = 0;
done:
    if (refl) ir.IRShaderReflectionDestroy(refl);
    if (lib) ir.IRMetalLibBinaryDestroy(lib);
    if (output) ir.IRObjectDestroy(output);
    if (compiler) ir.IRCompilerDestroy(compiler);
    if (rs) ir.IRRootSignatureDestroy(rs);
    if (input) ir.IRObjectDestroy(input);
    if (err) ir.IRErrorDestroy(err);
    if (out_ms) *out_ms = now_ms() - t0;
    return rc;
}

static id<MTLFunction> make_function(id<MTLDevice> dev, const ConvertedShader *sh, NSError **e) {
    dispatch_data_t d = dispatch_data_create(sh->bytes, sh->len, NULL,
                                             DISPATCH_DATA_DESTRUCTOR_DEFAULT);
    id<MTLLibrary> lib = [dev newLibraryWithData:d error:e];
    if (!lib) return nil;
    id<MTLFunction> fn = [lib newFunctionWithName:[NSString stringWithUTF8String:sh->entry]];
    if (!fn) {
        /* Name the alternatives rather than failing blind. */
        cout_("        entry '%s' not in library; available: %s\n", sh->entry,
               [[lib.functionNames componentsJoinedByString:@", "] UTF8String]);
    }
    return fn;
}

/* Render the full-screen triangle into a 64x64 target with `colour` in the root
 * CBV, and return the centre pixel. */
/* Render with a caller-built top-level argument buffer, so the layout under test
 * is the thing being varied rather than something this helper decides. */
static int render_with_argbuf(id<MTLDevice> dev, id<MTLCommandQueue> q,
                              id<MTLRenderPipelineState> pso,
                              id<MTLBuffer> argbuf, NSArray<id<MTLBuffer>> *resident,
                              uint8_t out_rgba[4]) {
    const NSUInteger W = 64, H = 64;

    MTLTextureDescriptor *td =
        [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm
                                                           width:W height:H mipmapped:NO];
    td.usage = MTLTextureUsageRenderTarget | MTLTextureUsageShaderRead;
    td.storageMode = MTLStorageModeShared;
    id<MTLTexture> target = [dev newTextureWithDescriptor:td];

    MTLRenderPassDescriptor *rp = [MTLRenderPassDescriptor renderPassDescriptor];
    rp.colorAttachments[0].texture = target;
    rp.colorAttachments[0].loadAction = MTLLoadActionClear;
    rp.colorAttachments[0].storeAction = MTLStoreActionStore;
    rp.colorAttachments[0].clearColor = MTLClearColorMake(0, 0, 0, 1);

    id<MTLCommandBuffer> cb = [q commandBuffer];
    id<MTLRenderCommandEncoder> enc = [cb renderCommandEncoderWithDescriptor:rp];
    [enc setRenderPipelineState:pso];
    [enc setVertexBuffer:argbuf offset:0 atIndex:kIRArgumentBufferBindPoint];
    [enc setFragmentBuffer:argbuf offset:0 atIndex:kIRArgumentBufferBindPoint];
    /* The CBV is reached indirectly through the argument buffer, so it must be
     * made resident explicitly; Metal cannot infer it from the encoder. */
    for (id<MTLBuffer> r in resident)
        [enc useResource:r usage:MTLResourceUsageRead
                  stages:MTLRenderStageVertex | MTLRenderStageFragment];
    [enc drawPrimitives:MTLPrimitiveTypeTriangle vertexStart:0 vertexCount:3];
    [enc endEncoding];
    [cb commit];
    [cb waitUntilCompleted];

    if (cb.status == MTLCommandBufferStatusError) {
        cout_("        GPU error: %s\n", [[cb.error description] UTF8String]);
        return -1;
    }
    uint8_t px[4];
    [target getBytes:px bytesPerRow:4 fromRegion:MTLRegionMake2D(W / 2, H / 2, 1, 1) mipmapLevel:0];
    memcpy(out_rgba, px, 4);
    return 0;
}

/* The original single-root-CBV case: one 64-bit address at offset 0. */
static int render_once(id<MTLDevice> dev, id<MTLCommandQueue> q,
                       id<MTLRenderPipelineState> pso, const float colour[4],
                       uint8_t out_rgba[4]) {
    id<MTLBuffer> cbv = [dev newBufferWithBytes:colour length:16
                                        options:MTLResourceStorageModeShared];
    uint64_t gpuAddress = cbv.gpuAddress;
    id<MTLBuffer> argbuf = [dev newBufferWithBytes:&gpuAddress length:sizeof gpuAddress
                                           options:MTLResourceStorageModeShared];
    return render_with_argbuf(dev, q, pso, argbuf, @[cbv], out_rgba);
}

/* Returns the number of failed checks; 0 means the gate passed. */
extern "C" int madeira_d3d12_canary_run_log(const char *fixture_dir, const char *dylib_path,
                                            void (*sink)(const char *), const char *log_path,
                                            const char *build_id);

extern "C" int madeira_d3d12_canary_run(const char *fixture_dir, const char *dylib_path,
                                        void (*sink)(const char *)) {
    return madeira_d3d12_canary_run_log(fixture_dir, dylib_path, sink, NULL, NULL);
}

extern "C" int madeira_d3d12_canary_run_log(const char *fixture_dir, const char *dylib_path,
                                            void (*sink)(const char *), const char *log_path,
                                            const char *build_id) {
    @autoreleasepool {
        g_sink = sink; g_checks = 0; g_fails = 0;
        g_log = (log_path && *log_path) ? fopen(log_path, "w") : NULL;
        char vsbuf[1100], psbuf[1100];
        if (!fixture_dir || !*fixture_dir) fixture_dir = "madeira-d3d12/shaders";
        snprintf(vsbuf, sizeof vsbuf, "%s/canary_vs.dxil", fixture_dir);
        snprintf(psbuf, sizeof psbuf, "%s/canary_ps.dxil", fixture_dir);
        const char *vs_path = vsbuf, *ps_path = psbuf;

        cout_("madeira-d3d12 M1 canary: DXIL -> Metal shader converter -> pipeline -> pixels\n");
        /* Compile stamp identifies this exact canary object without anyone
         * having to remember to bump a revision string. */
        cout_("  canary built %s %s | host build %s\n", __DATE__, __TIME__,
              build_id ? build_id : "(unset)");
        cout_("  fixtures %s\n", fixture_dir);
        cout_("  converter version %d.%d.%d, targeting %s %s\n",
               IR_VERSION_MAJOR, IR_VERSION_MINOR, IR_VERSION_PATCH, CANARY_OS_NAME, CANARY_OS_VER);
        cout_("  argument buffer bind point %llu, descriptor heap %llu, sampler heap %llu\n\n",
               (unsigned long long)kIRArgumentBufferBindPoint,
               (unsigned long long)kIRDescriptorHeapBindPoint,
               (unsigned long long)kIRSamplerHeapBindPoint);

        /* Resolve the converter first: everything below depends on it, and a
         * missing dylib should say so rather than abort in dyld at launch. */
        const char *ir_path = dylib_path && *dylib_path ? dylib_path : getenv("MADEIRA_MSC_DYLIB");
        if (!ir_path) ir_path = "@rpath/libmetalirconverter.dylib";
        const char *ir_err = ir_load(ir_path);
        CHECK(ir_err == NULL, "converter loaded from %s%s%s",
              ir_path, ir_err ? " -- " : "", ir_err ? ir_err : "");
        if (ir_err) return g_fails ? g_fails : 1;

        size_t vs_len = 0, ps_len = 0;
        uint8_t *vs = load_file(vs_path, &vs_len);
        uint8_t *ps = load_file(ps_path, &ps_len);
        CHECK(vs && ps, "DXIL fixtures loaded (%zu + %zu bytes)", vs_len, ps_len);
        if (!vs || !ps) return g_fails ? g_fails : 1;

        id<MTLDevice> dev = MTLCreateSystemDefaultDevice();
        CHECK(dev != nil, "Metal device: %s", dev ? [dev.name UTF8String] : "none");
        if (!dev) return g_fails ? g_fails : 1;
        /* MTLArgumentBuffersTier1 == 0, so the reported tier is the raw value + 1.
         * Printing the raw enum reads as one tier lower than reality. */
        cout_("        argument buffers tier %ld\n", (long)dev.argumentBuffersSupport + 1);
        CHECK(dev.argumentBuffersSupport >= MTLArgumentBuffersTier2,
              "argument buffers tier 2 (required by converted libraries)");

        size_t base_kb = footprint_kb();

        /* ---- 1. conversion ---- */
        ConvertedShader cvs = {}, cps = {};
        IRShaderStage vstage = IRShaderStageInvalid, pstage = IRShaderStageInvalid;
        double vms = 0, pms = 0;
        int rc_v = convert(vs, vs_len, "MainVS", &vstage, &cvs, &vms, CANARY_OS_VER, IRGPUFamilyMetal3, 0, NULL);
        int rc_p = convert(ps, ps_len, "MainPS", &pstage, &cps, &pms, CANARY_OS_VER, IRGPUFamilyMetal3, 0, NULL);
        CHECK(rc_v == 0, "vertex DXIL converted (%zu bytes, entry '%s', %.1f ms)", cvs.len, cvs.entry, vms);
        CHECK(rc_p == 0, "pixel DXIL converted (%zu bytes, entry '%s', %.1f ms)", cps.len, cps.entry, pms);
        if (rc_v || rc_p) return g_fails ? g_fails : 1;
        CHECK(vstage == IRShaderStageVertex, "vertex stage reported as vertex (%d)", (int)vstage);
        CHECK(pstage == IRShaderStageFragment, "pixel stage reported as fragment (%d)", (int)pstage);

        /* ---- 2. determinism: same inputs must yield identical bytes ---- */
        ConvertedShader again = {}; double ams = 0;
        int rc_a = convert(vs, vs_len, "MainVS", NULL, &again, &ams, CANARY_OS_VER, IRGPUFamilyMetal3, 1, NULL);
        CHECK(rc_a == 0 && again.len == cvs.len && memcmp(again.bytes, cvs.bytes, cvs.len) == 0,
              "recompile is byte-identical (%.1f ms) -- repeatability, which is neither "
              "necessary nor sufficient for cache safety", ams);

        /* ---- 3. pipeline ---- */
        NSError *e = nil;
        id<MTLFunction> fvs = make_function(dev, &cvs, &e);
        CHECK(fvs != nil, "vertex MTLFunction created");
        id<MTLFunction> fps = make_function(dev, &cps, &e);
        CHECK(fps != nil, "fragment MTLFunction created");
        if (!fvs || !fps) return g_fails ? g_fails : 1;

        MTLRenderPipelineDescriptor *pd = [MTLRenderPipelineDescriptor new];
        pd.vertexFunction = fvs;
        pd.fragmentFunction = fps;
        pd.colorAttachments[0].pixelFormat = MTLPixelFormatRGBA8Unorm;
        id<MTLRenderPipelineState> pso = [dev newRenderPipelineStateWithDescriptor:pd error:&e];
        CHECK(pso != nil, "render pipeline state built%s%s",
              pso ? "" : ": ", pso ? "" : [[e localizedDescription] UTF8String]);
        if (!pso) return g_fails ? g_fails : 1;

        /* ---- 4. two constant-buffer states, exact expected pixels ---- */
        id<MTLCommandQueue> q = [dev newCommandQueue];
        const float stateA[4] = {1.0f, 0.0f, 0.0f, 1.0f};   /* red   */
        const float stateB[4] = {0.0f, 0.25f, 1.0f, 1.0f};  /* blue  */
        uint8_t pa[4] = {0}, pb[4] = {0};
        int ra = render_once(dev, q, pso, stateA, pa);
        int rb = render_once(dev, q, pso, stateB, pb);
        CHECK(ra == 0 && rb == 0, "both offscreen renders completed without GPU error");
        CHECK(pa[0] == 255 && pa[1] == 0 && pa[2] == 0 && pa[3] == 255,
              "state A read back as (%u,%u,%u,%u), expected (255,0,0,255)", pa[0], pa[1], pa[2], pa[3]);
        CHECK(pb[0] == 0 && pb[1] == 64 && pb[2] == 255 && pb[3] == 255,
              "state B read back as (%u,%u,%u,%u), expected (0,64,255,255)", pb[0], pb[1], pb[2], pb[3]);
        CHECK(memcmp(pa, pb, 4) != 0, "the two states are distinguishable");

        /* ---- 5. argument-buffer LAYOUT with a real multi-parameter signature ----
         *
         * One root CBV at offset 0 is the trivial case. This checks the manual's
         * actual packing rule: four 32-bit root constants occupy bytes 0..15 and
         * the root CBV's address lands at byte 16. Red and green come from the
         * constants, blue from the CBV, so a mistake on either side is visible. */
        cout_("\n  argument-buffer layout: root constants + root CBV\n");
        /* Look for the layout fixtures beside the ones we were given, so the
         * same binary works from the repo root and from a device directory. */
        char ldir[1024]; snprintf(ldir, sizeof ldir, "%s", vs_path);
        char *slash = strrchr(ldir, '/');
        if (slash) *slash = '\0'; else snprintf(ldir, sizeof ldir, ".");
        char lvs_path[1100], lps_path[1100];
        snprintf(lvs_path, sizeof lvs_path, "%s/canary_layout_vs.dxil", ldir);
        snprintf(lps_path, sizeof lps_path, "%s/canary_layout_ps.dxil", ldir);
        size_t lvs_len = 0, lps_len = 0;
        uint8_t *lvs = load_file(lvs_path, &lvs_len);
        uint8_t *lps = load_file(lps_path, &lps_len);
        CHECK(lvs && lps, "layout fixtures loaded from %s (%zu + %zu bytes)", ldir, lvs_len, lps_len);
        if (lvs && lps) {
            ConvertedShader lcv = {}, lcp = {};
            int lrv = convert(lvs, lvs_len, "MainVS", NULL, &lcv, NULL, "15.0",
                              IRGPUFamilyMetal3, 0, make_root_signature_constants_then_cbv);
            int lrp = convert(lps, lps_len, "MainPS", NULL, &lcp, NULL, "15.0",
                              IRGPUFamilyMetal3, 0, make_root_signature_constants_then_cbv);
            CHECK(lrv == 0 && lrp == 0, "two-parameter root signature converted");

            /* Converting the SAME shader under the single-CBV signature must not
             * silently succeed: the root signature is part of the compile, which
             * is exactly why it belongs in the cache key. */
            ConvertedShader mism = {};
            int mismrc = convert(lps, lps_len, "MainPS", NULL, &mism, NULL, "15.0",
                                 IRGPUFamilyMetal3, 1, make_root_signature);
            CHECK(mismrc != 0 || mism.len != lcp.len || memcmp(mism.bytes, lcp.bytes, lcp.len) != 0,
                  "a different root signature changes or rejects the compile");

            if (lrv == 0 && lrp == 0) {
                NSError *le = nil;
                id<MTLFunction> lfv = make_function(dev, &lcv, &le);
                id<MTLFunction> lfp = make_function(dev, &lcp, &le);
                MTLRenderPipelineDescriptor *lpd = [MTLRenderPipelineDescriptor new];
                lpd.vertexFunction = lfv; lpd.fragmentFunction = lfp;
                lpd.colorAttachments[0].pixelFormat = MTLPixelFormatRGBA8Unorm;
                id<MTLRenderPipelineState> lpso =
                    [dev newRenderPipelineStateWithDescriptor:lpd error:&le];
                CHECK(lpso != nil, "layout pipeline built");
                if (lpso) {
                    const float cbvColour[4] = {0.0f, 0.0f, 1.0f, 1.0f};
                    id<MTLBuffer> lcbv = [dev newBufferWithBytes:cbvColour length:16
                                                         options:MTLResourceStorageModeShared];
                    uint8_t ab[24] = {0};
                    uint32_t consts[4] = {200, 100, 0, 0};
                    memcpy(ab, consts, sizeof consts);          /* bytes 0..15  */
                    uint64_t addr = lcbv.gpuAddress;
                    memcpy(ab + 16, &addr, sizeof addr);        /* byte 16      */
                    id<MTLBuffer> largs = [dev newBufferWithBytes:ab length:sizeof ab
                                                          options:MTLResourceStorageModeShared];
                    uint8_t lp[4] = {0};
                    int lr = render_with_argbuf(dev, q, lpso, largs, @[lcbv], lp);
                    CHECK(lr == 0, "layout render completed");
                    CHECK(lp[0] == 200 && lp[1] == 100 && lp[2] == 255 && lp[3] == 255,
                          "constants at 0 and CBV at 16 read back as (%u,%u,%u,%u), expected (200,100,255,255)",
                          lp[0], lp[1], lp[2], lp[3]);
                }
            }
        }

        /* ---- 6. cache-key differentiation ----
         *
         * Byte-identical recompilation only shows repeatability. What makes a
         * cache safe is that every input in the key actually changes the output,
         * so a stale entry cannot be served for different inputs. */
        cout_("\n  cache-key differentiation\n");
        ConvertedShader os_variant = {}, gpu_variant = {};
        int rc_os = convert(vs, vs_len, "MainVS", NULL, &os_variant, NULL, CANARY_OS_VER_ALT,
                            IRGPUFamilyMetal3, 1, NULL);
        CHECK(rc_os == 0 && (os_variant.len != cvs.len ||
                             memcmp(os_variant.bytes, cvs.bytes, cvs.len) != 0),
              "minimum deployment target changes the output (%s vs %s)", CANARY_OS_VER_ALT, CANARY_OS_VER);
        int rc_gpu = convert(vs, vs_len, "MainVS", NULL, &gpu_variant, NULL, "15.0",
                             IRGPUFamilyApple9, 1, NULL);
        int gpu_differs = rc_gpu == 0 && (gpu_variant.len != cvs.len ||
                                          memcmp(gpu_variant.bytes, cvs.bytes, cvs.len) != 0);
        CHECK(rc_gpu == 0, "minimum GPU family Apple9 also converts");
        /* Measured: for a shader this simple the minimum GPU family does NOT
         * change a single byte. That is a fact about this shader, not a licence
         * to drop the family from the cache key -- a shader using family-gated
         * features would diverge, and serving it an entry compiled for a
         * different minimum family would be wrong. The key is decided by what
         * the compiler is ALLOWED to vary on, not by what it happened to vary
         * on for one trivial input. */
        cout_("        Apple9 vs Metal3 output: %s (trivial shader; family stays in the key regardless)\n",
               gpu_differs ? "differs" : "identical");

        /* ---- 7. negative tests: bounded, named failures ---- */
        cout_("\n  negative tests\n");
        ConvertedShader junk = {};
        uint8_t garbage[256]; memset(garbage, 0xA5, sizeof garbage);
        CHECK(convert(garbage, sizeof garbage, "MainVS", NULL, &junk, NULL, CANARY_OS_VER, IRGPUFamilyMetal3, 1, NULL) != 0,
              "invalid DXIL rejected");
        ConvertedShader badentry = {};
        CHECK(convert(vs, vs_len, "NoSuchEntryPoint", NULL, &badentry, NULL, CANARY_OS_VER, IRGPUFamilyMetal3, 1, NULL) != 0,
              "unknown entry point rejected (by our empty-reflection check, not by the converter)");
        ConvertedShader truncated = {};
        CHECK(convert(vs, vs_len / 2, "MainVS", NULL, &truncated, NULL, CANARY_OS_VER, IRGPUFamilyMetal3, 1, NULL) != 0,
              "truncated DXIL rejected");

        cout_("\n  peak footprint delta %zu KB over baseline\n", footprint_kb() - base_kb);
        /* ---- 8. cross-target emission ----
         *
         * The design's cross-target gate: can the converter hosted HERE emit a
         * library the OTHER platform's device will accept? On the VM the guest
         * runs iOS while rendering happens on a macOS host, so a macOS-targeted
         * library compiled on the device is what the remote backend needs. This
         * writes it out; loading it is the other machine's job, and a library
         * that merely compiles is not yet a library that loads. */
        const char *cross_out = getenv("MADEIRA_MSC_CROSS_OUT");
        if (cross_out && *cross_out) {
            IROperatingSystem other = (CANARY_OS == IROperatingSystem_iOS)
                                    ? IROperatingSystem_macOS : IROperatingSystem_iOS;
            const char *other_name = (other == IROperatingSystem_macOS) ? "macOS" : "iOS";
            const char *other_ver  = (other == IROperatingSystem_macOS) ? "15.0" : "17.0";
            cout_("\n  cross-target emission for %s %s\n", other_name, other_ver);
            struct { const uint8_t *b; size_t n; const char *entry; const char *tag; } jobs[] = {
                { vs, vs_len, "MainVS", "vs" }, { ps, ps_len, "MainPS", "ps" },
            };
            for (int i = 0; i < 2; i++) {
                ConvertedShader x = {};
                int rc = convert(jobs[i].b, jobs[i].n, jobs[i].entry, NULL, &x, NULL,
                                 other_ver, IRGPUFamilyMetal3, 0, NULL, other);
                CHECK(rc == 0, "%s converted for %s (%zu bytes)", jobs[i].tag, other_name, x.len);
                if (rc == 0) {
                    char path[1200];
                    snprintf(path, sizeof path, "%s/cross_%s.metallib", cross_out, jobs[i].tag);
                    FILE *f = fopen(path, "wb");
                    if (f) { fwrite(x.bytes, 1, x.len, f); fclose(f); }
                    CHECK(f != NULL, "wrote %s", path);
                }
            }
        }

        cout_("\n%d checks, %d failures\n", g_checks, g_fails);
        if (g_log) { fclose(g_log); g_log = NULL; }
        return g_fails;
    }
}

#ifdef CANARY_STANDALONE
int main(int argc, const char **argv) {
    const char *dir = argc > 1 ? argv[1] : NULL;
    return madeira_d3d12_canary_run(dir, argc > 2 ? argv[2] : NULL, NULL) != 0;
}
#endif
