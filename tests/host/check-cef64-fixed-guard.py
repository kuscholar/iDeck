#!/usr/bin/env python3
"""Check the observed generic fixed-map hole in the owned FEX experiment."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
code = r'''
#include <assert.h>
#include "cef64_fixed_guard.h"
int main(void) {
    const uint64_t a=0x7400000000ULL, e=0x77c0000000ULL, g=0x40000000ULL;
    /* Exact successful-but-wrong Build88 cppgc placement. */
    assert(cef64_fixed_fex_conflict(0x7600000000ULL,4*g,a,e,0,0));
    assert(cef64_fixed_fex_conflict(a,g,a,e,0,0));
    assert(cef64_fixed_fex_conflict(a-g/2,g,a,e,0,0));
    assert(cef64_fixed_fex_conflict(e-g/2,g,a,e,0,0));
    assert(!cef64_fixed_fex_conflict(a-g,g,a,e,0,0));
    assert(!cef64_fixed_fex_conflict(e,g,a,e,0,0));
    assert(!cef64_fixed_fex_conflict(a,g,a,e,a,e-1));
    assert(cef64_fixed_fex_conflict(a,g,a,e,a+1,e-1));
    assert(cef64_fixed_fex_conflict(a,g,a,e,a,a+g-2));
    assert(cef64_fixed_fex_conflict(a,g,a,e,0,e-1));
    assert(cef64_fixed_fex_conflict(a,g,a,e,a,UINT64_MAX));
    assert(cef64_fixed_fex_conflict(UINT64_MAX-g/2,g,a,e,0,0));
    assert(!cef64_fixed_fex_conflict(0,g,a,e,0,0));
    assert(!cef64_fixed_fex_conflict(a,g-1,a,e,0,0));
    assert(!cef64_fixed_fex_conflict(a,g,0,0,0,0));
    /* New dynamic64GiB arena is protected by the same owner-bounded contract. */
    const uint64_t wide=0x6000000000ULL, wide_end=0x7000000000ULL;
    assert(cef64_fixed_fex_conflict(wide,9*g,wide,wide_end,0,0));
    assert(!cef64_fixed_fex_conflict(wide,9*g,wide,wide_end,wide,wide_end-1));
    assert(cef64_fixed_fex_conflict(wide_end-g/2,g,wide,wide_end,wide,wide_end-1));
    assert(!cef64_fixed_fex_conflict(wide_end,g,wide,wide_end,0,0));
    return 0;
}
'''
with tempfile.TemporaryDirectory() as directory:
    tmp = Path(directory)
    (tmp / 'guard.c').write_text(code)
    subprocess.run(['clang', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                    '-I'+str(root/'build/ntdll-unix'), str(tmp/'guard.c'), '-o', str(tmp/'guard')], check=True)
    subprocess.run([str(tmp/'guard')], check=True)
src = (root/'build/ntdll-unix/virtual_ios.c').read_text()
view = src.split('static NTSTATUS map_view(', 1)[1].split('static int', 1)[0]
assert 'ios_cef64_owned_layout() &&' in view
assert view.index('cef64_fixed_fex_conflict(') < view.index('map_fixed_area( base, size, unix_prot )')
assert 'return STATUS_CONFLICTING_ADDRESSES;' in view
print('PASS: observed4GiB conflict, edge/overflow/bounded-owner cases and pre-map owned-only integration (ASan/UBSan); not a device result')
