/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception-1.0
 * Minimal loader compatibility for Unity's optional WinRT buffer marshaling.
 * This does not implement IMarshal: callers receive an explicit failure and
 * a null output, never a false success or an invalid COM object.
 * Wine's pinned wintypes.spec also lists RoGetBufferMarshaler as a stub.
 */
typedef int HRESULT;
__declspec(dllexport) HRESULT __stdcall RoGetBufferMarshaler(void **out)
{
    if (!out) return (HRESULT)0x80004003; /* E_POINTER */
    *out = 0;
    return (HRESULT)0x80004001; /* E_NOTIMPL */
}
