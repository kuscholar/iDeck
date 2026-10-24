#ifndef MADEIRA_GRAPHICS_ENTRY_H
#define MADEIRA_GRAPHICS_ENTRY_H

#include <stdint.h>

EXTERN_C IMAGE_DOS_HEADER __ImageBase;

/* A native COM address cannot be patched with x64 instructions. Let clang/lld
 * emit the ARM64EC fast-forward entry and its ABI thunks, rather than building
 * an untyped jump or copying guest instructions into native .text. External
 * linkage is required: clang ignores hybrid_patchable on static functions. */
#if defined(__arm64ec__)
# if !__has_attribute(hybrid_patchable)
#  error "The ARM64EC toolchain must support hybrid_patchable"
# endif
# define MAD_X64_GRAPHICS_ENTRY __attribute__((hybrid_patchable, noinline))
#else
# define MAD_X64_GRAPHICS_ENTRY
#endif

/* Per-process opt-in. Preserve LastError even during factory/DLL startup. */
static inline int mad_x64_graphics_entry_enabled(void) {
    char value[2];
    DWORD saved_error = GetLastError();
    DWORD n = GetEnvironmentVariableA("MADEIRA_X64_GRAPHICS_ENTRY", value, sizeof value);
    int enabled = n == 1 && value[0] == '1';
    SetLastError(saved_error);
    return enabled;
}

/* Native code takes addresses in its executable pool copy. x64 entries must
 * instead name the loader's PE view: the emulator executes that view, and an
 * inline patcher's relative branches and nearby allocations must use the same
 * address space. Only callers selecting the opt-in x64 entries use this helper.
 * FROM_ADDRESS knows the pool alias; the module-relative offset is unchanged.
 * Do not change native methods, the loader's shared tables or module refcounts. */
static inline void *mad_x64_graphics_entry_pe(const void *entry, const IMAGE_DOS_HEADER *image) {
    uintptr_t base = (uintptr_t)image, address = (uintptr_t)entry;
    const IMAGE_NT_HEADERS *nt;
    HMODULE module = NULL;
    DWORD saved_error;
    void *result = (void *)entry;
    if (image->e_magic != IMAGE_DOS_SIGNATURE || image->e_lfanew <= 0 || image->e_lfanew > 0x100000)
        return result;
    nt = (const IMAGE_NT_HEADERS *)(base + image->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE || nt->OptionalHeader.Magic != IMAGE_NT_OPTIONAL_HDR64_MAGIC ||
        address < base || address - base >= nt->OptionalHeader.SizeOfImage)
        return result;
    saved_error = GetLastError();
    if (GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                           (LPCSTR)image, &module) && module)
        result = (void *)((uintptr_t)module + address - base);
    SetLastError(saved_error);
    return result;
}

/* DXMT's single-interface factory has 32 COM slots, two virtual destructor
 * slots, and the two Itanium ABI header words preceding the address point.
 * Retain all of them in instance storage. Only the five generated x64 entries
 * change address; native methods and RTTI/destruction keep their pool values. */
static inline void mad_x64_graphics_factory_table(void *const *original, void **storage,
                                                const IMAGE_DOS_HEADER *image) {
    static const unsigned slots[] = {8, 10, 15, 16, 24};
    unsigned i;
    for (i = 0; i < 36; i++) storage[i] = original[(int)i - 2];
    for (i = 0; i < sizeof(slots) / sizeof(slots[0]); i++)
        storage[2 + slots[i]] = mad_x64_graphics_entry_pe(original[slots[i]], image);
}

#endif
