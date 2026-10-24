/* ml1011: the input-layout resolver for the DXBC/SM5 backend.
 *
 * A translation unit of its own because DXBCParser's signature reader includes a
 * Windows compatibility header that typedefs BOOL as int, which cannot coexist
 * with Objective-C's BOOL in madeira_ir_unix.mm. Plain C++, reached by an
 * extern "C" prototype. */
#include <cstdio>
#include <cstring>
#include <cstdint>

#include "madeira_ir_abi.h"
#include "airconv_public.h"
#include "DXBCParser/DXBCUtils.h"

/* ml1011: the application's input layout, resolved against the shader's own
 * input signature, in the form the DXBC backend wants.
 *
 * Without this the backend emits [[attribute(n)]] stage_in inputs and Metal
 * refuses the pipeline ("Vertex function has input attributes but no vertex
 * descriptor was set"); with it the shader fetches vertices itself from a
 * vertex-buffer table, which is how DXMT has always driven it.
 *
 * `reg` is the SHADER's input register, not the element's index: it comes from
 * matching (SemanticName, SemanticIndex) against the ISGN chunk, exactly as
 * DXMT's ExtractMTLInputLayoutElements does -- including skipping an element the
 * shader does not read, and reporting an input the shader DOES read that the
 * layout fails to supply. The signature parser is DXBCParser's own, linked into
 * this image already, rather than a second hand-rolled ISGN reader. */
extern "C" int madeira_sm5_resolve_ia(const void *bc_in, size_t bclen,
                                      const struct madeira_ir_input_layout *L,
                                      struct SM50_IA_INPUT_ELEMENT *out, uint32_t out_cap,
                                      uint32_t *n_out, uint32_t *slot_mask_out,
                                      char *note, size_t note_cap)
{
    const unsigned char *bc = (const unsigned char *)bc_in;
    (void)bc; (void)bclen;
    using namespace microsoft;
    CSignatureParser parser;
    const D3D11_SIGNATURE_PARAMETER *params = NULL;
    uint32_t nparams, n = 0, slot_mask = 0, reg_mask = 0;

    *n_out = 0; *slot_mask_out = 0;
    if (FAILED(DXBCGetInputSignature(bc, &parser))) {
        snprintf(note, note_cap, "no input signature in the container");
        return 0;
    }
    nparams = parser.GetParameters(&params);

    for (uint32_t i = 0; i < L->n && n < out_cap; i++) {
        const struct madeira_ir_input_element *ie = &L->el[i];
        const D3D11_SIGNATURE_PARAMETER *sig = NULL;
        if (!ie->attr_format) {
            snprintf(note, note_cap, "%s%u has no Metal attribute format (DXGI %u)",
                     ie->semantic, ie->semantic_index, ie->format);
            return 0;
        }
        for (uint32_t j = 0; j < nparams; j++) {
            if (params[j].SemanticIndex != ie->semantic_index) continue;
            if (!params[j].SemanticName || strcasecmp(params[j].SemanticName, ie->semantic)) continue;
            sig = &params[j]; break;
        }
        if (!sig) continue;   /* the shader does not read this element */
        out[n].reg = sig->Register;
        out[n].slot = ie->slot;
        out[n].aligned_byte_offset = ie->offset;
        out[n].format = ie->attr_format;
        out[n].step_function = ie->per_instance ? 1u : 0u;
        out[n].step_rate = ie->per_instance ? (ie->step_rate ? ie->step_rate : 1u) : 1u;
        slot_mask |= 1u << ie->slot;
        reg_mask |= 1u << sig->Register;
        n++;
    }
    /* An input the shader reads but the layout never supplies would fetch
     * garbage. Say which one rather than rendering nonsense. */
    for (uint32_t j = 0; j < nparams; j++) {
        if (params[j].SystemValue != D3D10_SB_NAME_UNDEFINED) continue;   /* SIV/SGV are generated */
        if (reg_mask & (1u << params[j].Register)) continue;
        snprintf(note, note_cap, "shader reads %s%u (v%u) but the input layout does not supply it",
                 params[j].SemanticName ? params[j].SemanticName : "?",
                 params[j].SemanticIndex, params[j].Register);
        return 0;
    }
    *n_out = n; *slot_mask_out = slot_mask;
    return 1;
}

