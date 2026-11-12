# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""One exact pinned-source transformation shared by diagnostic and archive build.

Only move faulting write translation before the CASP serialization mutex. This
does not qualify CASP/STXP interaction or repair unrelated alignment semantics.
Generated LinuxRunner source retains its component license; no new exception.
"""
def casp_functions(body):
    start=body.index('__no_instrument int c_casp_pair(')
    end=body.index('\n// Interleaved SIMD load',start)
    original=body[start:end]
    old='''    int result = -1;

    lock(&pair_atomic_lock);'''
    new='''    if (size != 2 && size != 3)
        return -1;
    /* Translation can upgrade mm->lock for CoW. Complete it before taking
     * the global pair mutex: other pair waiters still hold mm readers. */
    void *ptr1 = __tlb_write_ptr(tlb, addr);
    void *ptr2 = __tlb_write_ptr(tlb, addr + (size == 2 ? 4 : 8));
    if (ptr1 == NULL || ptr2 == NULL)
        return -1;
    int result = -1;

    lock(&pair_atomic_lock);'''
    assert original.count(old)==1
    candidate=original.replace(old,new)
    for offset in (4,8):
        token=f'        void *ptr1 = __tlb_write_ptr(tlb, addr);\n        void *ptr2 = __tlb_write_ptr(tlb, addr + {offset});\n'
        assert candidate.count(token)==1
        candidate=candidate.replace(token,'')
    return original,candidate

def patched_tlb(body):
    original,candidate=casp_functions(body)
    assert body.count(original)==1
    return body.replace(original,candidate)
