/* Builds the real serialized root signature both tests use.
 *
 * Shared so the offscreen suite and the visible demo cannot disagree about the
 * layout the shaders were converted against. A mismatch there would not fail to
 * build; it would bind the constant buffer somewhere the shader does not read,
 * and show up as a blank or garbled image much later.
 *
 * One root CBV at b0, visible to every stage. That is exactly what the cube and
 * triangle shaders declare. */
#ifndef MADEIRA_TEST_ROOT_SIG_H
#define MADEIRA_TEST_ROOT_SIG_H

typedef HRESULT (WINAPI *pfn_serialize)(const D3D12_ROOT_SIGNATURE_DESC1 *, unsigned char *, SIZE_T *);

/* Returns a root signature built through the runtime's own serializer and
 * parser, so the blob the runtime reads is a real container rather than
 * something the test handed straight to an internal structure. */
static ID3D12RootSignature *make_root_sig(ID3D12Device *dev, pfn_serialize serialize,
                                          unsigned char *scratch, SIZE_T scratch_len) {
    D3D12_ROOT_PARAMETER1 rp;
    D3D12_ROOT_SIGNATURE_DESC1 rd;
    ID3D12RootSignature *rs = NULL;
    SIZE_T n = scratch_len;

    ZeroMemory(&rp, sizeof rp);
    rp.ParameterType = D3D12_ROOT_PARAMETER_TYPE_CBV;
    rp.ShaderVisibility = D3D12_SHADER_VISIBILITY_ALL;
    rp.Descriptor.ShaderRegister = 0;
    rp.Descriptor.RegisterSpace = 0;

    ZeroMemory(&rd, sizeof rd);
    rd.NumParameters = 1;
    rd.pParameters = &rp;
    rd.Flags = D3D12_ROOT_SIGNATURE_FLAG_ALLOW_INPUT_ASSEMBLER_INPUT_LAYOUT;

    if (!serialize || FAILED(serialize(&rd, scratch, &n))) return NULL;
    if (FAILED(ID3D12Device_CreateRootSignature(dev, 0, scratch, n,
                                                &IID_ID3D12RootSignature, (void **)&rs)))
        return NULL;
    return rs;
}

/* The textured layout: a root CBV plus an SRV table and a sampler table. This
 * is the first signature here whose parameters are not all root descriptors,
 * and the tables are what the descriptor-heap path exists to serve. */
static ID3D12RootSignature *make_textured_root_sig(ID3D12Device *dev, pfn_serialize serialize,
                                                   unsigned char *scratch, SIZE_T scratch_len) {
    D3D12_DESCRIPTOR_RANGE1 ranges[2];
    D3D12_ROOT_PARAMETER1 rp[3];
    D3D12_ROOT_SIGNATURE_DESC1 rd;
    ID3D12RootSignature *rs = NULL;
    SIZE_T n = scratch_len;

    ZeroMemory(ranges, sizeof ranges);
    ranges[0].RangeType = D3D12_DESCRIPTOR_RANGE_TYPE_SRV;
    ranges[0].NumDescriptors = 1;
    ranges[0].BaseShaderRegister = 0;
    ranges[1].RangeType = D3D12_DESCRIPTOR_RANGE_TYPE_SAMPLER;
    ranges[1].NumDescriptors = 1;
    ranges[1].BaseShaderRegister = 0;

    ZeroMemory(rp, sizeof rp);
    rp[0].ParameterType = D3D12_ROOT_PARAMETER_TYPE_CBV;
    rp[0].ShaderVisibility = D3D12_SHADER_VISIBILITY_ALL;
    rp[1].ParameterType = D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE;
    rp[1].DescriptorTable.NumDescriptorRanges = 1;
    rp[1].DescriptorTable.pDescriptorRanges = &ranges[0];
    rp[1].ShaderVisibility = D3D12_SHADER_VISIBILITY_ALL;
    rp[2].ParameterType = D3D12_ROOT_PARAMETER_TYPE_DESCRIPTOR_TABLE;
    rp[2].DescriptorTable.NumDescriptorRanges = 1;
    rp[2].DescriptorTable.pDescriptorRanges = &ranges[1];
    rp[2].ShaderVisibility = D3D12_SHADER_VISIBILITY_ALL;

    ZeroMemory(&rd, sizeof rd);
    rd.NumParameters = 3;
    rd.pParameters = rp;

    if (!serialize || FAILED(serialize(&rd, scratch, &n))) return NULL;
    if (FAILED(ID3D12Device_CreateRootSignature(dev, 0, scratch, n,
                                                &IID_ID3D12RootSignature, (void **)&rs)))
        return NULL;
    return rs;
}

#endif
