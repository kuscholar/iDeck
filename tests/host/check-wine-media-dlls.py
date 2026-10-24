#!/usr/bin/env python3
"""Exercise the media packaging gate (tools/check-wine-media-dlls.py) with real
bundled PEs and malformed fixtures.

The generated PE fixtures are only parsed; no Windows executable is run.
Building WMVCORE and winegstreamer is not this test's job: while the farm has no
wmvcore.dll the gate must name it as missing, and once it has one the gate must
pass the farm.
"""
from contextlib import redirect_stdout
import io
from pathlib import Path
import runpy
import struct
import tempfile

root = Path(__file__).resolve().parents[2]
gate = runpy.run_path(str(root / 'tools/check-wine-media-dlls.py'))
PE, check = gate['PE'], gate['check']


def image(functions, imports=(), delayed=(), machine=0xa641, forward=False):
    data = bytearray(0x1200)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 0x3c, 0x80)
    data[0x80:0x84] = b'PE\0\0'
    struct.pack_into('<HH', data, 0x84, machine, 1)
    struct.pack_into('<HH', data, 0x94, 240, 0x2000)
    optional = 0x98
    struct.pack_into('<H', data, optional, 0x20b)
    struct.pack_into('<I', data, optional + 108, 16)
    struct.pack_into('<IIII', data, optional + 240 + 8, 0x1000, 0x1000, 0x1000, 0x200)
    def offset(rva): return rva - 0x1000 + 0x200
    struct.pack_into('<II', data, optional + 112, 0x1100, 0x300)
    struct.pack_into('<IIHHIIIIIII', data, offset(0x1100),
                     0, 0, 0, 0, 0, 1, len(functions), len(functions), 0x1140, 0x1160, 0x1180)
    name_rva = 0x1200
    for i, name in enumerate(functions):
        raw = name.encode('ascii') + b'\0'
        data[offset(name_rva):offset(name_rva) + len(raw)] = raw
        struct.pack_into('<I', data, offset(0x1140) + i * 4, 0x1200 if forward else 0x1f00 + i * 4)
        struct.pack_into('<I', data, offset(0x1160) + i * 4, name_rva)
        struct.pack_into('<H', data, offset(0x1180) + i * 2, i)
        data[offset(0x1f00) + i * 4] = 0xc3
        name_rva += len(raw)
    for directory, names, rva, strings, width in ((1, imports, 0x1600, 0x1700, 20),
                                                (13, delayed, 0x1800, 0x1900, 32)):
        if not names: continue
        struct.pack_into('<II', data, optional + 112 + directory * 8, rva, (len(names) + 1) * width)
        for i, name in enumerate(names):
            raw = name.encode('ascii') + b'\0'
            data[offset(strings):offset(strings) + len(raw)] = raw
            if directory == 13: struct.pack_into('<I', data, offset(rva) + i * width, 1)
            struct.pack_into('<I', data, offset(rva) + i * width + (4 if directory == 13 else 12), strings)
            strings += len(raw)
    return bytes(data)


def rejected(function, message):
    try:
        with redirect_stdout(io.StringIO()): function()
    except ValueError as error:
        assert message in str(error), str(error)
    else: raise AssertionError('bad media package unexpectedly accepted')


farm = root / 'app/Madeira/arm64ec-windows'
for name in ('mf.dll', 'mfplat.dll', 'kernel32.dll'):
    module = PE(farm / name)
    assert module.exports() and module.imports()
if any(p.name.lower() == 'wmvcore.dll' for p in farm.iterdir()):
    with redirect_stdout(io.StringIO()): check(farm)   # built and bundled: the whole reader closure
else:
    rejected(lambda: check(farm), 'missing required wmvcore.dll')

reader = ('WMCreateReader', 'WMCreateSyncReader', 'WMCreateProfileManager')
backend = ('winegstreamer_create_wm_sync_reader',)
with tempfile.TemporaryDirectory(prefix='madeira-media-pe-') as tmp:
    folder = Path(tmp)
    wmv, wg = folder / 'WMVCORE.DLL', folder / 'winegstreamer.dll'
    wmv.write_bytes(image(reader, ('winegstreamer.dll',)))
    wg.write_bytes(image(backend))
    with redirect_stdout(io.StringIO()): check(folder)
    wg.unlink()
    rejected(lambda: check(folder), 'missing imports winegstreamer.dll')
    wg.write_bytes(image(backend, ('not-packaged.dll',)))
    rejected(lambda: check(folder), 'missing imports not-packaged.dll')
    wg.write_bytes(image(backend))
    wmv.write_bytes(image(reader[:-1], ('winegstreamer.dll',)))
    rejected(lambda: check(folder), 'missing implemented reader exports')
    wmv.write_bytes(image(reader, ('winegstreamer.dll',), forward=True))
    rejected(lambda: check(folder), 'missing implemented reader exports')
    wmv.write_bytes(image(reader, delayed=('winegstreamer.dll',)))
    rejected(lambda: check(folder), 'must import its real winegstreamer frontend')
    wmv.write_bytes(image(reader, ('winegstreamer.dll',)))
    wg.write_bytes(image(backend, delayed=('wmvcore.dll',)))
    rejected(lambda: check(folder), 'dependencies must use regular imports')
    wg.write_bytes(image(backend, machine=0x14c))
    rejected(lambda: check(folder), 'expected a 64-bit')
    wg.write_bytes(image(backend)[:0x190])
    rejected(lambda: check(folder), 'truncated PE field')
print('PASS: real bundled PE tables, missing modules/imports/exports, forwarders, delay imports, wrong architecture and truncation')
