/*  ml1980: root signature deserializer round trip, run natively on x86-64 Windows.
 *
 *  The runtime is an ARM64EC DLL that needs winemetal, so this test does not
 *  load it. Instead it compiles the runtime's own RTS0 reader, serializer and
 *  deserializer -- the regions of src/pe/madeira_d3d12.c between the
 *  "rsdeser-test:begin" and "rsdeser-test:end" markers -- on their own, so the
 *  code under test is the shipped code, not a copy.
 *
 *  Build (from madeira-d3d12, with the llvm-mingw toolchain):
 *    awk '/rsdeser-test:begin/{on=1} on{print} /rsdeser-test:end/{on=0}' \
 *        src/pe/madeira_d3d12.c > /tmp/rsdeser/rsdeser_extract.inc
 *    x86_64-w64-mingw32-clang -O1 -Wall -I/tmp/rsdeser -Isrc \
 *        tests/windows/rsdeser_test.c -o rsdeser_test.exe -luuid
 *  Run rsdeser_test.exe; run it again with MADEIRA_D3D12_RS_DESERIALIZER=0 to
 *  check the rollback path returns E_NOTIMPL.
 */

#define COBJMACROS
#define INITGUID
#include <initguid.h>
#include <windows.h>
#include <d3d12.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "madeira_ir_abi.h"

/* What the extracted regions expect from the rest of the runtime. The bounds
 * must match the runtime's (MAD_ROOT_PARAM_MAX / MAD_ROOT_RANGE_SANE). */
#define MAD_ROOT_PARAM_MAX 32
#define MAD_ROOT_RANGE_SANE 8192
static int g_quiet;
static void d3d12_log(const char *fmt, ...) {
    va_list ap;
    if (g_quiet) return;
    va_start(ap, fmt);
    printf("    log: ");
    vprintf(fmt, ap);
    va_end(ap);
}

#include "rsdeser_extract.inc"

static int checks, fails;
#define CHECK(cond, ...) do {                                                  \
    checks++;                                                                  \
    if (!(cond)) { fails++; printf("  FAIL  " __VA_ARGS__); printf("  (%s:%d)\n", __FILE__, __LINE__); } \
} while (0)

/* ---- a 1.1 description exercising every parameter kind ------------------ */
static D3D12_DESCRIPTOR_RANGE1 g_tab0[3], g_tab1[1];
static D3D12_ROOT_PARAMETER1 g_params[6];
static D3D12_STATIC_SAMPLER_DESC g_samplers[2];
static D3D12_ROOT_SIGNATURE_DESC1 g_desc;

static void build_desc(void) {
    memset(g_params, 0, sizeof g_params);
    g_params[0].ParameterType = D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS;
    g_params[0].ShaderVisibility = D3D12_SHADER_VISIBILITY_VERTEX;
    g_params[0].Constants.ShaderRegister = 3; g_params[0].Constants.RegisterSpace = 1;
    g_params[0].Constants.Num32BitValues = 16;

    g_params[1].ParameterType = D3D12_ROOT_PARAMETER_TYPE_CBV;
    g_params[1].ShaderVisibility = D3D12_SHADER_VISIBILITY_ALL;
    g_params[1].Descriptor.ShaderRegister = 0; g_params[1].Descriptor.RegisterSpace = 0;
    g_params[1].Descriptor.Flags = D3D12_ROOT_DESCRIPTOR_FLAG_DATA_STATIC;

    g_params[2].ParameterType = D3D12_ROOT_PARAMETER_TYPE_SRV;
    g_params[2].ShaderVisibility = D3D12_SHADER_VISIBILITY_PIXEL;
    g_params[2].Descriptor.ShaderRegister = 7; g_params[2].Descriptor.RegisterSpace = 2;
    g_params[2].Descriptor.Flags = D3D12_ROOT_DESCRIPTOR_FLAG_NONE;

    g_params[3].ParameterType = D3D12_ROOT_PARAMETER_TYPE_UAV;
    g_params[3].ShaderVisibility = D3D12_SHADER_VISIBILITY_ALL;
    g_params[3].Descriptor.ShaderRegister = 1; g_params[3].Descriptor.RegisterSpace = 0;
    g_params[3].Descriptor.Flags = D3D12_ROOT_DESCRIPTOR_FLAG_DATA_VOLATILE;

    memset(g_tab0, 0, sizeof g_tab0);
    g_tab0[0].RangeType = D3D12_DESCRIPTOR_RANGE_TYPE_SRV; g_tab0[0].NumDescriptors = 8;
    g_tab0[0].BaseShaderRegister = 1; g_tab0[0].RegisterSpace = 0;
    g_tab0[0].Flags = D3D12_DESCRIPTOR_RANGE_FLAG_DESCRIPTORS_VOLATILE;
    g_tab0[0].OffsetInDescriptorsFromTableStart = 0;
    g_tab0[1].RangeType = D3D12_DESCRIPTOR_RANGE_TYPE_CBV; g_tab0[1].NumDescriptors = 2;
    g_tab0[1].BaseShaderRegister = 4; g_tab0[1].RegisterSpace = 3;
    g_tab0[1].Flags = D3D12_DESCRIPTOR_RANGE_FLAG_DATA_STATIC_WHILE_SET_AT_EXECUTE;
    g_tab0[1].OffsetInDescriptorsFromTableStart = D3D12_DESCRIPTOR_RANGE_OFFSET_APPEND;
    g_tab0[2].RangeType = D3D12_DESCRIPTOR_RANGE_TYPE_UAV; g_tab0[2].NumDescriptors = UINT_MAX;  /* unbounded */
    g_tab0[2].BaseShaderRegister = 0; g_tab0[2].RegisterSpace = 5;
    g_tab0[2].Flags = D3D12_DESCRIPTOR_RANGE_FLAG_DESCRIPTORS_VOLATILE | D3D12_DESCRIPTOR_RANGE_FLAG_DATA_VOLATILE;
    g_tab0[2].OffsetInDescriptorsFromTableStart = 10;
    g_params[4].ParameterType = D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE;
    g_params[4].ShaderVisibility = D3D12_SHADER_VISIBILITY_ALL;
    g_params[4].DescriptorTable.NumDescriptorRanges = 3;
    g_params[4].DescriptorTable.pDescriptorRanges = g_tab0;

    memset(g_tab1, 0, sizeof g_tab1);
    g_tab1[0].RangeType = D3D12_DESCRIPTOR_RANGE_TYPE_SAMPLER; g_tab1[0].NumDescriptors = 4;
    g_tab1[0].BaseShaderRegister = 2; g_tab1[0].RegisterSpace = 0;
    g_tab1[0].Flags = D3D12_DESCRIPTOR_RANGE_FLAG_NONE;
    g_tab1[0].OffsetInDescriptorsFromTableStart = 0;
    g_params[5].ParameterType = D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE;
    g_params[5].ShaderVisibility = D3D12_SHADER_VISIBILITY_PIXEL;
    g_params[5].DescriptorTable.NumDescriptorRanges = 1;
    g_params[5].DescriptorTable.pDescriptorRanges = g_tab1;

    memset(g_samplers, 0, sizeof g_samplers);
    g_samplers[0].Filter = D3D12_FILTER_ANISOTROPIC;
    g_samplers[0].AddressU = D3D12_TEXTURE_ADDRESS_MODE_WRAP;
    g_samplers[0].AddressV = D3D12_TEXTURE_ADDRESS_MODE_CLAMP;
    g_samplers[0].AddressW = D3D12_TEXTURE_ADDRESS_MODE_MIRROR;
    g_samplers[0].MipLODBias = -0.5f; g_samplers[0].MaxAnisotropy = 16;
    g_samplers[0].ComparisonFunc = D3D12_COMPARISON_FUNC_LESS_EQUAL;
    g_samplers[0].BorderColor = D3D12_STATIC_BORDER_COLOR_OPAQUE_WHITE;
    g_samplers[0].MinLOD = 1.25f; g_samplers[0].MaxLOD = D3D12_FLOAT32_MAX;
    g_samplers[0].ShaderRegister = 9; g_samplers[0].RegisterSpace = 4;
    g_samplers[0].ShaderVisibility = D3D12_SHADER_VISIBILITY_PIXEL;
    g_samplers[1] = g_samplers[0];
    g_samplers[1].Filter = D3D12_FILTER_COMPARISON_MIN_MAG_MIP_LINEAR;
    g_samplers[1].ShaderRegister = 10; g_samplers[1].MipLODBias = 2.0f;
    g_samplers[1].ShaderVisibility = D3D12_SHADER_VISIBILITY_ALL;

    memset(&g_desc, 0, sizeof g_desc);
    g_desc.NumParameters = 6; g_desc.pParameters = g_params;
    g_desc.NumStaticSamplers = 2; g_desc.pStaticSamplers = g_samplers;
    g_desc.Flags = D3D12_ROOT_SIGNATURE_FLAG_ALLOW_INPUT_ASSEMBLER_INPUT_LAYOUT |
                   D3D12_ROOT_SIGNATURE_FLAG_DENY_HULL_SHADER_ROOT_ACCESS;
}

static unsigned char *serialize(const D3D12_ROOT_SIGNATURE_DESC1 *d, SIZE_T *len) {
    SIZE_T n = 0; unsigned char *b;
    if (MadeiraD3D12SerializeRootSignature(d, NULL, &n) != S_OK || !n) return NULL;
    b = malloc(n);
    if (MadeiraD3D12SerializeRootSignature(d, b, &n) != S_OK) { free(b); return NULL; }
    *len = n;
    return b;
}

/* The same container in the 1.0 layout: root descriptors are two words and
 * ranges five, which is what a 1.0 serializer emits. */
static unsigned char *serialize_v10(const D3D12_ROOT_SIGNATURE_DESC1 *d, SIZE_T *len) {
    UINT32 np = d->NumParameters, nr = 0, i, j, bodies = 0;
    for (i = 0; i < np; i++) {
        const D3D12_ROOT_PARAMETER1 *rp = &d->pParameters[i];
        if (rp->ParameterType == D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE) {
            nr += rp->DescriptorTable.NumDescriptorRanges; bodies += 8;
        } else bodies += rp->ParameterType == D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS ? 12 : 8;
    }
    UINT32 sampler_at = 24 + 12 * np + bodies + 20 * nr;
    UINT32 chunk = sampler_at + 52 * d->NumStaticSamplers;
    UINT32 total = 36 + 8 + chunk;
    unsigned char *out = calloc(1, total), *p;
    memcpy(out, "DXBC", 4);
    rs_wr(out, 20, 1); rs_wr(out, 24, total); rs_wr(out, 28, 1); rs_wr(out, 32, 36);
    memcpy(out + 36, "RTS0", 4); rs_wr(out, 40, chunk);
    p = out + 44;
    rs_wr(p, 0, 1); rs_wr(p, 4, np); rs_wr(p, 8, 24);
    rs_wr(p, 12, d->NumStaticSamplers); rs_wr(p, 16, sampler_at); rs_wr(p, 20, d->Flags);
    for (i = 0; i < d->NumStaticSamplers; i++) memcpy(p + sampler_at + 52 * i, &d->pStaticSamplers[i], 52);
    UINT32 body = 24 + 12 * np, range_at = 24 + 12 * np + bodies;
    for (i = 0; i < np; i++) {
        const D3D12_ROOT_PARAMETER1 *rp = &d->pParameters[i];
        rs_wr(p, 24 + 12 * i, rp->ParameterType); rs_wr(p, 24 + 12 * i + 4, rp->ShaderVisibility);
        rs_wr(p, 24 + 12 * i + 8, body);
        if (rp->ParameterType == D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS) {
            rs_wr(p, body, rp->Constants.ShaderRegister); rs_wr(p, body + 4, rp->Constants.RegisterSpace);
            rs_wr(p, body + 8, rp->Constants.Num32BitValues); body += 12;
        } else if (rp->ParameterType == D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE) {
            rs_wr(p, body, rp->DescriptorTable.NumDescriptorRanges); rs_wr(p, body + 4, range_at);
            for (j = 0; j < rp->DescriptorTable.NumDescriptorRanges; j++) {
                const D3D12_DESCRIPTOR_RANGE1 *dr = &rp->DescriptorTable.pDescriptorRanges[j];
                rs_wr(p, range_at, dr->RangeType); rs_wr(p, range_at + 4, dr->NumDescriptors);
                rs_wr(p, range_at + 8, dr->BaseShaderRegister); rs_wr(p, range_at + 12, dr->RegisterSpace);
                rs_wr(p, range_at + 16, dr->OffsetInDescriptorsFromTableStart);
                range_at += 20;
            }
            body += 8;
        } else {
            rs_wr(p, body, rp->Descriptor.ShaderRegister); rs_wr(p, body + 4, rp->Descriptor.RegisterSpace);
            body += 8;
        }
    }
    *len = total;
    return out;
}

/* Wraps an RTS0-bearing container in a two-chunk container with a dummy chunk
 * first, the way a shader's bytecode carries an embedded root signature. */
static unsigned char *wrap_two_chunks(const unsigned char *one, SIZE_T one_len, SIZE_T *len) {
    UINT32 rts_sz = rs_rd(one, one_len, 40, &(int){0});
    UINT32 dummy = 16;
    UINT32 total = 32 + 8 + (8 + dummy) + (8 + rts_sz);
    unsigned char *out = calloc(1, total);
    memcpy(out, "DXBC", 4);
    rs_wr(out, 20, 1); rs_wr(out, 24, total); rs_wr(out, 28, 2);
    rs_wr(out, 32, 40); rs_wr(out, 36, 40 + 8 + dummy);
    memcpy(out + 40, "SFI0", 4); rs_wr(out, 44, dummy); memset(out + 48, 0xAB, dummy);
    memcpy(out + 40 + 8 + dummy, one + 36, 8 + rts_sz);
    *len = total;
    return out;
}

static int same_sampler(const D3D12_STATIC_SAMPLER_DESC *a, const D3D12_STATIC_SAMPLER_DESC *b) {
    return memcmp(a, b, sizeof *a) == 0;
}

/* Compares a 1.1 description to the original, optionally expecting the flags
 * a 1.0 blob converts to instead of the original flags. */
static void check_v11(const char *tag, const D3D12_ROOT_SIGNATURE_DESC1 *got, int from_v10) {
    UINT32 i, j;
    CHECK(got->NumParameters == g_desc.NumParameters, "%s: parameter count %u", tag, got->NumParameters);
    CHECK(got->NumStaticSamplers == g_desc.NumStaticSamplers, "%s: sampler count", tag);
    CHECK(got->Flags == g_desc.Flags, "%s: root signature flags %#x", tag, (unsigned)got->Flags);
    if (got->NumParameters != g_desc.NumParameters) return;
    for (i = 0; i < g_desc.NumParameters; i++) {
        const D3D12_ROOT_PARAMETER1 *a = &g_desc.pParameters[i], *b = &got->pParameters[i];
        CHECK(a->ParameterType == b->ParameterType, "%s: param %u type", tag, i);
        CHECK(a->ShaderVisibility == b->ShaderVisibility, "%s: param %u visibility", tag, i);
        if (a->ParameterType != b->ParameterType) continue;
        switch (a->ParameterType) {
        case D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS:
            CHECK(!memcmp(&a->Constants, &b->Constants, sizeof a->Constants), "%s: param %u constants", tag, i);
            break;
        case D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE:
            CHECK(a->DescriptorTable.NumDescriptorRanges == b->DescriptorTable.NumDescriptorRanges,
                  "%s: param %u range count", tag, i);
            if (a->DescriptorTable.NumDescriptorRanges != b->DescriptorTable.NumDescriptorRanges) break;
            for (j = 0; j < a->DescriptorTable.NumDescriptorRanges; j++) {
                const D3D12_DESCRIPTOR_RANGE1 *x = &a->DescriptorTable.pDescriptorRanges[j];
                const D3D12_DESCRIPTOR_RANGE1 *y = &b->DescriptorTable.pDescriptorRanges[j];
                D3D12_DESCRIPTOR_RANGE_FLAGS want = from_v10
                    ? (x->RangeType == D3D12_DESCRIPTOR_RANGE_TYPE_SAMPLER
                        ? D3D12_DESCRIPTOR_RANGE_FLAG_DESCRIPTORS_VOLATILE
                        : D3D12_DESCRIPTOR_RANGE_FLAG_DESCRIPTORS_VOLATILE | D3D12_DESCRIPTOR_RANGE_FLAG_DATA_VOLATILE)
                    : x->Flags;
                CHECK(x->RangeType == y->RangeType && x->NumDescriptors == y->NumDescriptors &&
                      x->BaseShaderRegister == y->BaseShaderRegister && x->RegisterSpace == y->RegisterSpace &&
                      x->OffsetInDescriptorsFromTableStart == y->OffsetInDescriptorsFromTableStart,
                      "%s: param %u range %u fields", tag, i, j);
                CHECK(y->Flags == want, "%s: param %u range %u flags %#x want %#x", tag, i, j,
                      (unsigned)y->Flags, (unsigned)want);
            }
            break;
        default: {
            D3D12_ROOT_DESCRIPTOR_FLAGS want = from_v10 ? D3D12_ROOT_DESCRIPTOR_FLAG_DATA_VOLATILE : a->Descriptor.Flags;
            CHECK(a->Descriptor.ShaderRegister == b->Descriptor.ShaderRegister &&
                  a->Descriptor.RegisterSpace == b->Descriptor.RegisterSpace, "%s: param %u descriptor", tag, i);
            CHECK(b->Descriptor.Flags == want, "%s: param %u descriptor flags %#x", tag, i, (unsigned)b->Descriptor.Flags);
            break;
        }
        }
    }
    for (i = 0; i < g_desc.NumStaticSamplers && i < got->NumStaticSamplers; i++)
        CHECK(same_sampler(&g_desc.pStaticSamplers[i], &got->pStaticSamplers[i]), "%s: sampler %u", tag, i);
}

static void check_v10(const char *tag, const D3D12_ROOT_SIGNATURE_DESC *got) {
    UINT32 i, j;
    CHECK(got->NumParameters == g_desc.NumParameters, "%s: parameter count", tag);
    CHECK(got->NumStaticSamplers == g_desc.NumStaticSamplers, "%s: sampler count", tag);
    CHECK(got->Flags == g_desc.Flags, "%s: flags", tag);
    if (got->NumParameters != g_desc.NumParameters) return;
    for (i = 0; i < g_desc.NumParameters; i++) {
        const D3D12_ROOT_PARAMETER1 *a = &g_desc.pParameters[i];
        const D3D12_ROOT_PARAMETER *b = &got->pParameters[i];
        CHECK(a->ParameterType == b->ParameterType && a->ShaderVisibility == b->ShaderVisibility,
              "%s: param %u header", tag, i);
        switch (a->ParameterType) {
        case D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS:
            CHECK(!memcmp(&a->Constants, &b->Constants, sizeof a->Constants), "%s: param %u constants", tag, i);
            break;
        case D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE:
            CHECK(a->DescriptorTable.NumDescriptorRanges == b->DescriptorTable.NumDescriptorRanges,
                  "%s: param %u range count", tag, i);
            for (j = 0; j < a->DescriptorTable.NumDescriptorRanges && j < b->DescriptorTable.NumDescriptorRanges; j++) {
                const D3D12_DESCRIPTOR_RANGE1 *x = &a->DescriptorTable.pDescriptorRanges[j];
                const D3D12_DESCRIPTOR_RANGE *y = &b->DescriptorTable.pDescriptorRanges[j];
                CHECK(x->RangeType == y->RangeType && x->NumDescriptors == y->NumDescriptors &&
                      x->BaseShaderRegister == y->BaseShaderRegister && x->RegisterSpace == y->RegisterSpace &&
                      x->OffsetInDescriptorsFromTableStart == y->OffsetInDescriptorsFromTableStart,
                      "%s: param %u range %u", tag, i, j);
            }
            break;
        default:
            CHECK(a->Descriptor.ShaderRegister == b->Descriptor.ShaderRegister &&
                  a->Descriptor.RegisterSpace == b->Descriptor.RegisterSpace, "%s: param %u descriptor", tag, i);
            break;
        }
    }
    for (i = 0; i < g_desc.NumStaticSamplers && i < got->NumStaticSamplers; i++)
        CHECK(same_sampler(&g_desc.pStaticSamplers[i], &got->pStaticSamplers[i]), "%s: sampler %u", tag, i);
}

static void check_blob(const char *tag, const unsigned char *blob, SIZE_T len, int is_v10) {
    ID3D12VersionedRootSignatureDeserializer *vd = NULL;
    ID3D12RootSignatureDeserializer *pd = NULL;
    const D3D12_VERSIONED_ROOT_SIGNATURE_DESC *un, *at10, *at11, *again;
    HRESULT hr;
    void *unk = NULL;

    hr = mad_rsd_create(blob, len, &IID_ID3D12VersionedRootSignatureDeserializer, (void **)&vd, 1);
    CHECK(hr == S_OK && vd, "%s: versioned create hr=%#lx", tag, (unsigned long)hr);
    if (vd) {
        un = ID3D12VersionedRootSignatureDeserializer_GetUnconvertedRootSignatureDesc(vd);
        CHECK(un && un->Version == (is_v10 ? D3D_ROOT_SIGNATURE_VERSION_1_0 : D3D_ROOT_SIGNATURE_VERSION_1_1),
              "%s: unconverted version", tag);
        hr = ID3D12VersionedRootSignatureDeserializer_GetRootSignatureDescAtVersion(vd, D3D_ROOT_SIGNATURE_VERSION_1_1, &at11);
        CHECK(hr == S_OK && at11 && at11->Version == D3D_ROOT_SIGNATURE_VERSION_1_1, "%s: at 1.1", tag);
        if (hr == S_OK) check_v11(tag, &at11->Desc_1_1, is_v10);
        hr = ID3D12VersionedRootSignatureDeserializer_GetRootSignatureDescAtVersion(vd, D3D_ROOT_SIGNATURE_VERSION_1_0, &at10);
        CHECK(hr == S_OK && at10 && at10->Version == D3D_ROOT_SIGNATURE_VERSION_1_0, "%s: at 1.0", tag);
        if (hr == S_OK) check_v10(tag, &at10->Desc_1_0);
        CHECK(un == (is_v10 ? at10 : at11), "%s: unconverted is the native view", tag);
        hr = ID3D12VersionedRootSignatureDeserializer_GetRootSignatureDescAtVersion(vd, D3D_ROOT_SIGNATURE_VERSION_1_1, &again);
        CHECK(hr == S_OK && again == at11, "%s: cached 1.1 pointer is stable", tag);
        again = (const void *)1;
        hr = ID3D12VersionedRootSignatureDeserializer_GetRootSignatureDescAtVersion(vd, (D3D_ROOT_SIGNATURE_VERSION)3, &again);
        CHECK(hr == E_INVALIDARG && !again, "%s: 1.2 conversion refused", tag);
        CHECK(ID3D12VersionedRootSignatureDeserializer_GetRootSignatureDescAtVersion(vd, D3D_ROOT_SIGNATURE_VERSION_1_1, NULL)
              == E_INVALIDARG, "%s: NULL desc out", tag);
        hr = ID3D12VersionedRootSignatureDeserializer_QueryInterface(vd, &IID_IUnknown, &unk);
        CHECK(hr == S_OK && unk == vd, "%s: QI IUnknown", tag);
        if (unk) CHECK(IUnknown_Release((IUnknown *)unk) == 1, "%s: refcount after QI release", tag);
        unk = (void *)1;
        hr = ID3D12VersionedRootSignatureDeserializer_QueryInterface(vd, &IID_ID3D12RootSignatureDeserializer, &unk);
        CHECK(hr == E_NOINTERFACE && !unk, "%s: QI other interface refused", tag);
        CHECK(ID3D12VersionedRootSignatureDeserializer_AddRef(vd) == 2, "%s: AddRef", tag);
        CHECK(ID3D12VersionedRootSignatureDeserializer_Release(vd) == 1, "%s: Release", tag);
        CHECK(ID3D12VersionedRootSignatureDeserializer_Release(vd) == 0, "%s: final Release", tag);
    }

    hr = mad_rsd_create(blob, len, &IID_ID3D12RootSignatureDeserializer, (void **)&pd, 0);
    CHECK(hr == S_OK && pd, "%s: plain create hr=%#lx", tag, (unsigned long)hr);
    if (pd) {
        const D3D12_ROOT_SIGNATURE_DESC *d = ID3D12RootSignatureDeserializer_GetRootSignatureDesc(pd);
        CHECK(d != NULL, "%s: plain desc", tag);
        if (d) check_v10(tag, d);
        CHECK(ID3D12RootSignatureDeserializer_GetRootSignatureDesc(pd) == d, "%s: plain desc stable", tag);
        unk = (void *)1;
        hr = ID3D12RootSignatureDeserializer_QueryInterface(pd, &IID_ID3D12VersionedRootSignatureDeserializer, &unk);
        CHECK(hr == E_NOINTERFACE && !unk, "%s: plain QI versioned refused", tag);
        CHECK(ID3D12RootSignatureDeserializer_Release(pd) == 0, "%s: plain final Release", tag);
    }
    pd = (void *)1;
    hr = mad_rsd_create(blob, len, &IID_ID3D12Device, (void **)&pd, 0);
    CHECK(hr == E_NOINTERFACE && !pd, "%s: create with a foreign riid", tag);
}

int main(void) {
    char env[4] = {0};
    SIZE_T n11 = 0, n10 = 0, n2 = 0, i;
    unsigned char *b11, *b10, *b2, *bad;
    void *out;
    HRESULT hr;
    (void)rs_vis;

    build_desc();
    b11 = serialize(&g_desc, &n11);
    b10 = serialize_v10(&g_desc, &n10);
    CHECK(b11 && b10, "serialize");
    if (!b11 || !b10) goto done;

    if (GetEnvironmentVariableA("MADEIRA_D3D12_RS_DESERIALIZER", env, sizeof env) == 1 && env[0] == '0') {
        out = (void *)1;
        hr = mad_rsd_create(b11, n11, &IID_ID3D12RootSignatureDeserializer, &out, 0);
        CHECK(hr == E_NOTIMPL && !out, "rollback returns E_NOTIMPL");
        goto done;
    }

    printf("1.1 blob (%u bytes)\n", (unsigned)n11);
    check_blob("v1.1", b11, n11, 0);
    printf("1.0 blob (%u bytes)\n", (unsigned)n10);
    check_blob("v1.0", b10, n10, 1);
    b2 = wrap_two_chunks(b11, n11, &n2);
    printf("two-chunk container (%u bytes)\n", (unsigned)n2);
    check_blob("2chunk", b2, n2, 0);
    free(b2);

    printf("argument and garbage handling\n");
    CHECK(mad_rsd_create(b11, n11, &IID_ID3D12RootSignatureDeserializer, NULL, 0) == E_POINTER, "NULL out");
    out = (void *)1;
    CHECK(mad_rsd_create(NULL, n11, &IID_ID3D12RootSignatureDeserializer, &out, 0) == E_INVALIDARG && !out, "NULL blob");
    CHECK(mad_rsd_create(b11, 0, &IID_ID3D12RootSignatureDeserializer, &out, 0) == E_INVALIDARG, "zero length");
    CHECK(mad_rsd_create(b11, n11, NULL, &out, 0) == E_INVALIDARG, "NULL riid");

    g_quiet = 1;
    /* Every truncation of each container is refused and never read past. The
     * buffer is copied to an exact-size allocation so a sanitizer or page heap
     * would catch an overread. */
    for (i = 0; i < n11; i++) {
        bad = malloc(i ? i : 1); memcpy(bad, b11, i);
        out = NULL;
        hr = mad_rsd_create(bad, i, &IID_ID3D12RootSignatureDeserializer, &out, 0);
        CHECK(FAILED(hr) && !out, "truncated 1.1 at %u accepted", (unsigned)i);
        if (out) IUnknown_Release((IUnknown *)out);
        free(bad);
    }
    /* Truncating the container's view of the chunk (its declared size) too. */
    for (i = 0; i + 44 < n11; i++) {
        bad = malloc(n11); memcpy(bad, b11, n11);
        rs_wr(bad, 40, (UINT32)i);
        out = NULL;
        hr = mad_rsd_create(bad, 44 + i, &IID_ID3D12RootSignatureDeserializer, &out, 0);
        CHECK(FAILED(hr) && !out, "chunk size %u accepted", (unsigned)i);
        if (out) IUnknown_Release((IUnknown *)out);
        free(bad);
    }
    for (i = 0; i < n10; i++) {
        bad = malloc(i ? i : 1); memcpy(bad, b10, i);
        out = NULL;
        hr = mad_rsd_create(bad, i, &IID_ID3D12RootSignatureDeserializer, &out, 0);
        CHECK(FAILED(hr) && !out, "truncated 1.0 at %u accepted", (unsigned)i);
        if (out) IUnknown_Release((IUnknown *)out);
        free(bad);
    }
    g_quiet = 0;

    {   /* Specific corruptions of the payload (which starts at byte 44). */
        struct { SIZE_T at; UINT32 v; HRESULT want; const char *what; } cases[] = {
            { 44 + 0,  3,          E_NOTIMPL,    "version 1.2" },
            { 44 + 0,  7,          E_INVALIDARG, "unknown version" },
            { 44 + 0,  0,          E_INVALIDARG, "version 0" },
            { 44 + 4,  33,         E_NOTIMPL,    "too many parameters" },
            { 44 + 4,  0x7fffffff, E_NOTIMPL,    "absurd parameter count" },
            { 44 + 12, 33,         E_NOTIMPL,    "too many samplers" },
            { 44 + 8,  0xfffffff0, E_INVALIDARG, "parameter offset out of range" },
            { 44 + 16, 0xfffffff0, E_INVALIDARG, "sampler offset out of range" },
            { 44 + 24, 9,          E_INVALIDARG, "unknown parameter type" },
            { 44 + 28, 99,         E_INVALIDARG, "unknown visibility" },
            { 44 + 32, 0xffffff00, E_INVALIDARG, "parameter body out of range" },
            { 0,       0x43425845, E_INVALIDARG, "not DXBC" },   /* "DXBC" is 0x43425844 */
            { 28,      0,          E_INVALIDARG, "no chunks" },
            { 36,      0x30535452 ^ 0x01000000, E_INVALIDARG, "no RTS0 chunk" },
        };
        for (i = 0; i < sizeof cases / sizeof cases[0]; i++) {
            bad = malloc(n11); memcpy(bad, b11, n11);
            rs_wr(bad, cases[i].at, cases[i].v);
            out = (void *)1;
            hr = mad_rsd_create(bad, n11, &IID_ID3D12VersionedRootSignatureDeserializer, &out, 1);
            CHECK(hr == cases[i].want && !out, "%s: hr=%#lx want %#lx", cases[i].what,
                  (unsigned long)hr, (unsigned long)cases[i].want);
            free(bad);
        }
    }
    {   /* The table parameter (index 4): its range count and range type. */
        int b = 0;
        UINT32 poff = rs_rd(b11 + 44, n11 - 44, 8, &b);
        UINT32 body = rs_rd(b11 + 44, n11 - 44, poff + 12 * 4 + 8, &b);
        UINT32 roff = rs_rd(b11 + 44, n11 - 44, body + 4, &b);
        bad = malloc(n11); memcpy(bad, b11, n11);
        rs_wr(bad, 44 + body, 9000);
        CHECK(mad_rsd_create(bad, n11, &IID_ID3D12VersionedRootSignatureDeserializer, &out, 1) == E_NOTIMPL,
              "range count past the sane bound");
        rs_wr(bad, 44 + body, 200);
        CHECK(mad_rsd_create(bad, n11, &IID_ID3D12VersionedRootSignatureDeserializer, &out, 1) == E_INVALIDARG,
              "range count past the end of the chunk");
        memcpy(bad, b11, n11);
        rs_wr(bad, 44 + roff, 4);
        CHECK(mad_rsd_create(bad, n11, &IID_ID3D12VersionedRootSignatureDeserializer, &out, 1) == E_INVALIDARG,
              "unknown range type");
        free(bad);
    }

    {   /* Random corruption: never crash, and anything accepted releases cleanly. */
        unsigned seed = 12345, accepted = 0, k;
        g_quiet = 1;
        for (k = 0; k < 20000; k++) {
            unsigned flips, f;
            bad = malloc(n11); memcpy(bad, b11, n11);
            seed = seed * 1103515245u + 12345u; flips = 1 + (seed >> 16) % 4;
            for (f = 0; f < flips; f++) {
                seed = seed * 1103515245u + 12345u;
                SIZE_T at = 28 + (seed >> 8) % (n11 - 28);
                seed = seed * 1103515245u + 12345u;
                bad[at] = (unsigned char)(seed >> 16);
            }
            out = NULL;
            hr = mad_rsd_create(bad, n11, &IID_ID3D12VersionedRootSignatureDeserializer, &out, 1);
            if (SUCCEEDED(hr) && out) {
                const D3D12_VERSIONED_ROOT_SIGNATURE_DESC *d = NULL;
                ID3D12VersionedRootSignatureDeserializer_GetRootSignatureDescAtVersion(
                    (ID3D12VersionedRootSignatureDeserializer *)out, D3D_ROOT_SIGNATURE_VERSION_1_0, &d);
                accepted++;
                CHECK(ID3D12VersionedRootSignatureDeserializer_Release((ID3D12VersionedRootSignatureDeserializer *)out) == 0,
                      "fuzz release");
            }
            free(bad);
        }
        g_quiet = 0;
        printf("fuzz: 20000 corrupted blobs, %u accepted, no crash\n", accepted);
    }

    {   /* An empty root signature: no parameters, no samplers, NULL arrays. */
        D3D12_ROOT_SIGNATURE_DESC1 e; SIZE_T ne = 0; unsigned char *be;
        ID3D12VersionedRootSignatureDeserializer *vd = NULL;
        memset(&e, 0, sizeof e);
        be = serialize(&e, &ne);
        hr = be ? mad_rsd_create(be, ne, &IID_ID3D12VersionedRootSignatureDeserializer, (void **)&vd, 1) : E_FAIL;
        CHECK(hr == S_OK && vd, "empty root signature");
        if (vd) {
            const D3D12_VERSIONED_ROOT_SIGNATURE_DESC *d = ID3D12VersionedRootSignatureDeserializer_GetUnconvertedRootSignatureDesc(vd);
            CHECK(d->Desc_1_1.NumParameters == 0 && !d->Desc_1_1.pParameters &&
                  d->Desc_1_1.NumStaticSamplers == 0 && !d->Desc_1_1.pStaticSamplers, "empty arrays are NULL");
            ID3D12VersionedRootSignatureDeserializer_Release(vd);
        }
        free(be);
    }

done:
    free(b11); free(b10);
    printf("%d checks, %d failures\n", checks, fails);
    return fails ? 1 : 0;
}
