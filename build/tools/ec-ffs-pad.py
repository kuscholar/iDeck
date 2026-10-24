#!/usr/bin/env python3
"""
ml941: give every ARM64EC fast-forward sequence a patchable x64 landing pad.

WHY
An ARM64EC export's entry is a 16-byte x64 "fast-forward sequence" (FFS):

    48 8b c4           mov  rax, rsp
    48 89 58 20        mov  [rax+20h], rbx
    55 5d              push rbp / pop rbp
    e9 <rel32>         jmp  <ARM64EC body>
    cc cc              int3 / int3

x64 code that inline-hooks an API resolves the export, sees a jmp/thunk at the
entry, and FOLLOWS it to find the "real" implementation -- correct on x64
Windows, where entries are forwarders and API-set thunks. On ARM64EC that jmp
lands on ARM64 instructions, so the hook writes an x64 branch over ARM64 code.
Native callers then execute those bytes as ARM64 and take SIGILL.

Measured: a game's anti-tamper DLL hooked kernelbase LoadLibraryA (rva 0x26400)
and GetFileAttributesW (rva 0x1e2c4) -- exactly the FFS jmp targets of those
two exports -- with 6- and 5-byte patches, and the app died with c000001d in the
ARM64 body.

WHAT THIS DOES
Repoints each FFS jmp at a per-thunk landing pad and puts the transfer to the
real body behind a NOP sled:

    pad:  90 x19          <- every byte is an instruction boundary
          e9 <rel32>      jmp <ARM64EC body>

A hook engine may overwrite 5, 6, 8 or 14 bytes and resume at pad+N for any of
those N; because the sled is single-byte NOPs, every N <= 19 lands on a valid
boundary and falls through to the jmp. That removes the one thing we cannot
measure: how a given engine computes its resume offset.

Native callers are unaffected: they reach the body through the image's
RedirectionMetadata (consulted before any byte decode), so an x64 hook on the
x64-visible entry does not intercept them -- which is exactly ARM64EC's own
semantics.

WHERE THE PADS LIVE
In the slack of the module's own .hexpthk section: it is already CODE|EXEC|READ,
its SizeOfRawData is section-aligned well past its VirtualSize, and the slack is
all zero. Being INSIDE the image matters -- both the PE mapping and its JIT-pool
copy execute the same bytes, and only an image-relative jmp is correct in both.
An absolute target would be right for one copy and wrong for the other.
"""

import struct, sys, os

FFS_PROLOGUE = bytes.fromhex('488bc448895820555d')   # 9 bytes, then 0xe9 rel32
THUNK_STRIDE = 16
SLED         = 19          # single-byte NOPs
PAD_SIZE     = 24          # SLED + 5-byte jmp, rounded to 8


class Pe:
    def __init__(self, path):
        self.path = path
        self.d = bytearray(open(path, 'rb').read())
        d = self.d
        if d[:2] != b'MZ':
            raise ValueError("not MZ")
        self.e_lfanew = struct.unpack_from('<I', d, 0x3c)[0]
        if d[self.e_lfanew:self.e_lfanew+4] != b'PE\0\0':
            raise ValueError("not PE")
        coff = self.e_lfanew + 4
        self.machine, self.nsec = struct.unpack_from('<HH', d, coff)
        self.optsz = struct.unpack_from('<H', d, coff + 16)[0]
        self.opt = coff + 20
        self.sec_tbl = coff + 20 + self.optsz
        self.sections = []
        for i in range(self.nsec):
            o = self.sec_tbl + 40 * i
            name = bytes(d[o:o+8]).rstrip(b'\0').decode('latin1')
            vsz, rva, rawsz, rawoff = struct.unpack_from('<IIII', d, o + 8)
            chars = struct.unpack_from('<I', d, o + 36)[0]
            self.sections.append(dict(i=i, hdr=o, name=name, vsz=vsz, rva=rva,
                                      rawsz=rawsz, rawoff=rawoff, chars=chars))

    def section(self, name):
        for s in self.sections:
            if s['name'] == name:
                return s
        return None

    def set_vsize(self, sec, v):
        struct.pack_into('<I', self.d, sec['hdr'] + 8, v)
        sec['vsz'] = v

    def save(self):
        open(self.path, 'wb').write(bytes(self.d))



def _find_ec_metadata(pe, n_thunks):
    """Locate the ARM64EC metadata and return the set of RedirectionMetadata
    Source rvas, or None.

    The metadata is reached through IMAGE_LOAD_CONFIG_DIRECTORY's
    CHPEMetadataPointer. Rather than hardcode that field offset (it moved
    between SDK revisions and a wrong guess reads 0), scan the load config's
    8-byte slots for an image VA whose target looks like the real thing:
    Version 1 or 2 and a RedirectionMetadataCount equal to the thunk count we
    independently counted in .hexpthk. Self-validating, so a layout change
    makes this return None instead of silently reading garbage.
    """
    d = pe.d
    imgbase = struct.unpack_from('<Q', d, pe.opt + 24)[0]
    szimg = struct.unpack_from('<I', d, pe.opt + 56)[0]
    lc_rva, lc_sz = struct.unpack_from('<II', d, pe.opt + 112 + 8 * 10)
    if not lc_rva or not lc_sz:
        return None
    lo = _r2o(pe, lc_rva)
    if lo is None:
        return None
    for off in range(0, min(lc_sz, 0x200), 8):
        if lo + off + 8 > len(d):
            break
        v = struct.unpack_from('<Q', d, lo + off)[0]
        if not (imgbase <= v < imgbase + szimg):
            continue
        mo = _r2o(pe, v - imgbase)
        if mo is None or mo + 0x38 > len(d):
            continue
        ver = struct.unpack_from('<I', d, mo)[0]
        if ver not in (1, 2):
            continue
        redir = struct.unpack_from('<I', d, mo + 0x10)[0]
        rmc = struct.unpack_from('<I', d, mo + 0x34)[0]
        if rmc != n_thunks or not redir:
            continue
        ro = _r2o(pe, redir)
        if ro is None or ro + 8 * rmc > len(d):
            continue
        return set(struct.unpack_from('<I', d, ro + 8 * i)[0] for i in range(rmc))
    return None


def _r2o(pe, rva):
    for s in pe.sections:
        if s['rva'] <= rva < s['rva'] + max(s['vsz'], s['rawsz']):
            return s['rawoff'] + (rva - s['rva'])
    return None


def transform(path, verbose=True):
    """Returns (status, message). status in {'ok','skip','fail'}."""
    try:
        pe = Pe(path)
    except Exception as ex:
        return 'skip', "unreadable PE (%s)" % ex

    hx = pe.section('.hexpthk')
    if not hx:
        return 'skip', "no .hexpthk (not an ARM64EC image)"

    # Enumerate the FFS thunks. They are a dense 16-byte-stride array; anything
    # else means a layout we do not understand, and we refuse rather than guess.
    n = 0
    while True:
        o = hx['rawoff'] + n * THUNK_STRIDE
        if o + THUNK_STRIDE > hx['rawoff'] + hx['vsz']:
            break
        if bytes(pe.d[o:o+9]) != FFS_PROLOGUE or pe.d[o+9] != 0xe9:
            break
        n += 1
    if n == 0:
        return 'skip', ".hexpthk has no canonical FFS thunks"
    if n * THUNK_STRIDE != hx['vsz']:
        return 'skip', (".hexpthk VirtualSize %#x != %d thunks * %d (already padded, "
                        "or an unexpected layout)" % (hx['vsz'], n, THUNK_STRIDE))

    pad_off  = (hx['vsz'] + 15) & ~15          # section-relative
    need     = n * PAD_SIZE
    room     = hx['rawsz'] - pad_off
    if need > room:
        return 'skip', ("needs %#x bytes of .hexpthk slack, only %#x available "
                        "(%d thunks)" % (need, room, n))

    # The slack must be untouched, or we would be overwriting real content.
    blank = bytes(pe.d[hx['rawoff'] + pad_off: hx['rawoff'] + pad_off + need])
    if blank.count(0) != len(blank):
        return 'skip', "target slack is not zero-filled -- refusing to overwrite"

    # HARD PRECONDITION. Native ARM64 callers must never receive a pad: 19 NOP
    # bytes decode as ARM64 `adrp x16, ...` and the sled would run as garbage.
    # They are safe only because arm64ec_redirect_ptr consults the image's
    # RedirectionMetadata (FFS rva -> body rva) BEFORE it ever byte-decodes an
    # FFS, so a covered thunk never routes a native caller through the pad. If
    # any thunk lacks an entry, its native path depends on that byte decode and
    # padding it would break native callers -- so refuse the whole image rather
    # than pad it partially.
    covered = _find_ec_metadata(pe, n)
    if covered is None:
        return 'skip', "could not locate ARM64EC RedirectionMetadata -- refusing"
    missing = [i for i in range(n)
               if (hx['rva'] + i * THUNK_STRIDE) not in covered]
    if missing:
        return 'skip', ("%d of %d FFS thunks have no RedirectionMetadata entry "
                        "(first: rva %#x) -- refusing"
                        % (len(missing), n, hx['rva'] + missing[0] * THUNK_STRIDE))

    bodies = []
    for i in range(n):
        t_off = hx['rawoff'] + i * THUNK_STRIDE
        t_rva = hx['rva'] + i * THUNK_STRIDE
        rel   = struct.unpack_from('<i', pe.d, t_off + 10)[0]
        body_rva = t_rva + 14 + rel            # jmp is at +9, ends at +14
        pad_rva  = hx['rva'] + pad_off + i * PAD_SIZE
        pad_foff = hx['rawoff'] + pad_off + i * PAD_SIZE

        # pad: NOP sled, then jmp to the original body
        pe.d[pad_foff:pad_foff + SLED] = b'\x90' * SLED
        pe.d[pad_foff + SLED] = 0xe9
        struct.pack_into('<i', pe.d, pad_foff + SLED + 1,
                         body_rva - (pad_rva + SLED + 5))
        # repoint the thunk at its pad
        struct.pack_into('<i', pe.d, t_off + 10, pad_rva - (t_rva + 14))
        bodies.append(body_rva)

    pe.set_vsize(hx, pad_off + need)
    pe.save()

    # Verify from the file we just wrote: every thunk must resolve
    # FFS -> pad -> sled -> jmp -> the SAME body it had before.
    v = Pe(path)
    vhx = v.section('.hexpthk')
    for i in range(n):
        t_off = vhx['rawoff'] + i * THUNK_STRIDE
        t_rva = vhx['rva'] + i * THUNK_STRIDE
        rel = struct.unpack_from('<i', v.d, t_off + 10)[0]
        pad_rva = t_rva + 14 + rel
        pad_foff = vhx['rawoff'] + (pad_rva - vhx['rva'])
        if bytes(v.d[pad_foff:pad_foff + SLED]) != b'\x90' * SLED:
            return 'fail', "thunk %d: pad is not a NOP sled" % i
        if v.d[pad_foff + SLED] != 0xe9:
            return 'fail', "thunk %d: pad does not end in jmp rel32" % i
        rel2 = struct.unpack_from('<i', v.d, pad_foff + SLED + 1)[0]
        got = pad_rva + SLED + 5 + rel2
        if got != bodies[i]:
            return 'fail', ("thunk %d: chain resolves to %#x, original body %#x"
                            % (i, got, bodies[i]))
    return 'ok', ("%d thunks padded, pads at rva %#x..%#x, .hexpthk VirtualSize %#x -> %#x"
                  % (n, vhx['rva'] + pad_off, vhx['rva'] + pad_off + need,
                     n * THUNK_STRIDE, vhx['vsz']))


if __name__ == '__main__':
    files = sys.argv[1:]
    if not files:
        print("usage: ec-ffs-pad.py <arm64ec dll> ...", file=sys.stderr)
        sys.exit(2)
    counts = dict(ok=0, skip=0, fail=0)
    for f in files:
        st, msg = transform(f)
        counts[st] += 1
        if st != 'ok':
            print("  %-6s %-24s %s" % (st.upper(), os.path.basename(f), msg))
        else:
            print("  OK     %-24s %s" % (os.path.basename(f), msg))
    print("\n%d padded, %d skipped, %d FAILED" % (counts['ok'], counts['skip'], counts['fail']))
    sys.exit(1 if counts['fail'] else 0)
