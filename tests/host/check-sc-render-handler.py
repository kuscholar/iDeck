#!/usr/bin/env python3
"""[sc-rph]: the browser CefApp hands out the renderer app's handler; no Wine runs.

Under --single-process Chromium asks the browser CefApp for the renderer's
CefRenderProcessHandler, and Social Club's browser app returns NULL, so the page
bridge never ran (GTA log 2026-10-04 12:56: the launcher's pages loaded, nobody
opened the per-page IPC channels, SC_INIT_ERR_WEBSITE_FAILED_LOAD after 75 s).
build/ntdll-unix/virtual_ios.c installs a small thunk in the helper's own image
at map time and points the browser app's GetRenderProcessHandler slot at it.

This checks the patch structurally, without a Wine run and without reproducing
the helper's own code (the owner's SocialClubHelper.exe is never committed):
  - the call site sits after relocation and before the section protections and
    the eager JIT-pool copy, so the copy of .text carries the thunk;
  - the thunk is a self-consistent position-independent x64 blob: its five
    rip-relative rel32 displacements land exactly on the two cache slots and the
    three helper routines it names (operator new, the renderer-app constructor
    and the handler getter), computed from the documented RVAs; its two short
    branches stay inside the blob; it ends in ret;
  - ios_sch_mismatch guards every byte it relies on: it requires the analysed
    TimeDateStamp and SizeOfImage, the .text/.data layout, the five code-byte
    windows, the four CefApp vtable slots in the view/preferred base, and zero
    code/cache tails. The additional renderer-loop adapter and WebKit callback
    are executed by check-sc-render-loop.py;
  - the guard and the writes are gated by MADEIRA_SC_RENDER_HANDLER and
    MADEIRA_SC_CEF and by the image being SocialClubHelper.exe.
Needs only python3.
"""
from pathlib import Path
import re
import struct

root = Path(__file__).resolve().parents[2]
native = (root / 'build/ntdll-unix/virtual_ios.c').read_text()


def function(source, signature):
    start = source.index(signature)
    return source[start:source.index('\n}', start) + 2] + '\n'


def define(name):
    m = re.search(r'#define %s\s+(0x[0-9a-fA-F]+u?|[0-9]+)' % name, native)
    t = m.group(1).rstrip('uU')
    return int(t, 16) if t.startswith('0x') else int(t)


# --- call site ----------------------------------------------------------------
mapper = function(native, 'static NTSTATUS map_image_into_view(')
call = mapper.index('ios_sc_render_handler_patch( ptr, total_size, nt, sec, nt_name );')
assert mapper.index('rel = process_relocation_block( ptr + rel->VirtualAddress, rel, delta );') < call, \
    'the patch runs after relocation'
assert call < mapper.index('mprotect_exec(sec_addr, sec_size, prot);'), 'before the eager JIT-pool copy'
# the per-section protection pass that first marks exec pages comes after the call too
assert call < mapper.index('set_vprot( view, ptr + sec[i].VirtualAddress, size, vprot )'), \
    'before the section protections'

# --- constants ----------------------------------------------------------------
THUNK = define('IOS_SCH_THUNK')
CACHE = define('IOS_SCH_CACHE')
NEW = 0x13e708
CTOR = 0x69a0
GET = define('IOS_SCH_GET_HANDLER')
VT_BROWSER = define('IOS_SCH_VT_BROWSER')
VT_RENDERER = define('IOS_SCH_VT_RENDERER')
GET_NULL = define('IOS_SCH_GET_NULL')
SLOT_B = define('IOS_SCH_SLOT_BROWSER')
SLOT_R = define('IOS_SCH_SLOT_RENDERER')

# --- the thunk blob -----------------------------------------------------------
blob = native[native.index('static const unsigned char ios_sch_thunk[112] ='):]
blob = blob[:blob.index('};') + 2]
thunk = bytes(int(b, 16) for b in re.findall(r'0x([0-9a-fA-F]{2})', blob))
assert len(thunk) == 112, len(thunk)
assert 0xc3 in thunk, 'the thunk returns'

# Every `e8 <rel32>` (call) and `48 8b 05 / 48 89 05 <rel32>` (cache load/store):
# resolve the target from the instruction address relative to the blob at THUNK.
targets = {}
i = 0
while i < len(thunk) - 4:
    if thunk[i] == 0xe8:                              # call rel32
        disp = struct.unpack_from('<i', thunk, i + 1)[0]
        targets.setdefault('call', []).append((THUNK + i + 5 + disp))
        i += 5
        continue
    if thunk[i:i + 3] in (b'\x48\x8b\x05', b'\x48\x89\x05'):   # mov rax,[rip+x] / mov [rip+x],rax
        disp = struct.unpack_from('<i', thunk, i + 3)[0]
        targets.setdefault('cache', []).append((THUNK + i + 7 + disp))
        i += 7
        continue
    i += 1

assert sorted(set(targets['call'])) == sorted({NEW, CTOR, GET}), [hex(x) for x in targets['call']]
assert set(targets['cache']) == {CACHE}, [hex(x) for x in targets['cache']]

# short branches (0x74/0x75/0xeb rel8) stay inside the blob
i = 0
while i < len(thunk) - 1:
    if thunk[i] in (0x74, 0x75, 0xeb):
        dest = i + 2 + struct.unpack_from('<b', thunk, i + 1)[0]
        assert 0 <= dest < len(thunk), (hex(THUNK + i), dest)
    i += 1
print('PASS: the thunk is position-independent and its five rel32s hit the cache, new, ctor and getter')

# --- the guard and the writes -------------------------------------------------
guard = function(native, 'static const char *ios_sch_mismatch(')
for need in ('TimeDateStamp != IOS_SCH_STAMP', 'SizeOfImage != IOS_SCH_SIZE',
             'IMAGE_FILE_MACHINE_AMD64', 'VirtualAddress == IOS_SCH_TEXT',
             'VirtualAddress == IOS_SCH_DATA', 'ios_sch_code', 'IOS_SCH_SLOT_BROWSER',
             'IOS_SCH_SLOT_RENDERER', 'IOS_SCH_GET_HANDLER', 'IOS_SCH_GET_NULL',
             'base[IOS_SCH_THUNK + k]', 'base + IOS_SCH_CACHE'):
    assert need in guard, need

code_tbl = native[native.index('static const struct { unsigned int rva'):]
code_tbl = code_tbl[:code_tbl.index('};') + 2]
rvas = [int(x, 16) for x in re.findall(r'\{ (?:IOS_SCH_GET_HANDLER|IOS_SCH_GET_NULL|0x[0-9a-f]+),', code_tbl)] \
    if False else None
# the five guarded windows name new, the ctor, the getter, the null-getter and the C++ slot-4 call
assert 'IOS_SCH_GET_HANDLER' in code_tbl and 'IOS_SCH_GET_NULL' in code_tbl
assert code_tbl.count('{ ') >= 5, 'five code-byte windows'

patch = function(native, 'static void ios_sc_render_handler_patch(')
assert 'MADEIRA_SC_RENDER_HANDLER' in patch and 'ios_sc_cef_enabled()' in patch
assert 'ios_sc_path_is_helper(' in patch, 'only SocialClubHelper.exe'
assert patch.index('if ((why = ios_sch_mismatch(') < patch.index('memcpy( base + IOS_SCH_THUNK'), \
    'the guard runs before any write'
assert 'memcpy( base + IOS_SCH_THUNK, ios_sch_thunk, sizeof(ios_sch_thunk) );' in patch, 'writes the thunk'
assert '((ULONG64 *)(base + IOS_SCH_VT_BROWSER))[IOS_SCH_SLOT_RENDERER] = vtbase + IOS_SCH_THUNK;' \
    in patch, 'points the browser app slot 4 at the thunk, in the vtables\' own base'
# the vtable base is read from a slot (the helper is mapped high but runs at its
# preferred base through the sub-floor when its directory is not applied), and
# accepted only as the view or the preferred base.
assert '*vtbase = vb[IOS_SCH_SLOT_BROWSER] - IOS_SCH_GET_HANDLER;' in guard, 'derives the vtable base from a slot'
assert "!= IOS_SCH_IMAGE_BASE" in guard and '*vtbase != b' in guard, 'base is the view or the preferred base'
# the two writes land in zero tails past SizeOfRawData (.text raw 0x17f400, .data raw end 0x1cc000+0x1a00)
assert THUNK >= 0x1000 + 0x17f400 - 0x1000, 'thunk past .text raw data'
assert 0x180800 <= THUNK < 0x181000 and 0x1d0000 <= CACHE < 0x1d1000, (hex(THUNK), hex(CACHE))
# The CefApp change is still only browser slot 4. The separate render-process
# handler vtable's WebKit callback now initializes and pumps the renderer loop.
assert 'VT_BROWSER))[IOS_SCH_SLOT_RENDERER]' in patch
assert 'VT_RENDERER' not in patch.split('memcpy')[1] and 'SLOT_BROWSER]' not in patch.split('memcpy')[1], \
    'CefApp browser slot 3 and the renderer app vtable are unchanged'
assert '((ULONG64 *)(base + IOS_SCH_VT_RPH))[0] = vtbase + IOS_SCH_LOOP_INIT;' in patch
print('PASS: guarded CefApp slot 4 change and render-process-handler WebKit callback are wired')

print('PASS: [sc-rph] renderer-process-handler patch is wired, guarded and self-consistent')
