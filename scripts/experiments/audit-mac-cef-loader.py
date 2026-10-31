#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Read-only ARM64 CEF loader contract audit; never executes or changes Steam.

Recognizes one narrow lookup/store/null-check/return-zero instruction shape.
Unknown or ambiguous code is an error, never evidence of an optional API.
Reports addresses and symbol names only; no proprietary instruction dump.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import subprocess

spec = importlib.util.spec_from_file_location('cef_abi', Path(__file__).with_name('audit-mac-cef-abi.py'))
abi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(abi)
CUSTOM = ('cef_generate_gpu_report', 'cef_is_gpu_compositing_disabled',
          'cef_is_hardware_acceleration_enabled', 'cef_set_force_device_scale_factor',
          'cef_set_minimum_font_size', 'cef_set_preferred_contrast',
          'cef_set_reduced_motion_enabled')


def arm64_slice(data):
    if data[:4] != b'\xca\xfe\xba\xbe':
        abi.MachO(data)
        return data
    if len(data) < 8:
        raise ValueError('Truncated fat header')
    count = struct.unpack_from('>I', data, 4)[0]
    if count > (len(data)-8)//20:
        raise ValueError('Truncated fat architecture table')
    found = []
    ranges = []
    for i in range(count):
        cpu, _, offset, size, _ = struct.unpack_from('>5I', data, 8+20*i)
        if offset < 8+count*20 or size == 0 or offset+size > len(data):
            raise ValueError('Invalid fat slice bounds')
        if any(offset < end and start < offset+size for start, end in ranges):
            raise ValueError('Overlapping fat slices')
        ranges.append((offset, offset+size))
        if cpu == 0x100000c:
            found.append(data[offset:offset+size])
    if len(found) != 1:
        raise ValueError('Expected exactly one ARM64 slice')
    abi.MachO(found[0])
    return found[0]


def text_section(image):
    if image.read(0x100000000, 32) != image.data[:32]:
        raise ValueError('Unknown executable preferred base')
    offset = 32
    sections = []
    count = struct.unpack_from('<I', image.data, 16)[0]
    for _ in range(count):
        command, size = struct.unpack_from('<II', image.data, offset)
        if command == 0x19:
            number = struct.unpack_from('<I', image.data, offset+64)[0]
            if size != 72+number*80:
                raise ValueError('Invalid section table')
            for i in range(number):
                at = offset+72+i*80
                name, segment, address, length, file_offset = struct.unpack_from('<16s16sQQI', image.data, at)
                if name.rstrip(b'\0') == b'__text' and segment.rstrip(b'\0') == b'__TEXT':
                    if address % 4 or length % 4:
                        raise ValueError('Unaligned ARM64 text')
                    code = image.read(address, length)
                    if code != image.data[file_offset:file_offset+length]:
                        raise ValueError('Section/segment file mapping mismatch')
                    sections.append((address, code))
        offset += size
    if len(sections) != 1:
        raise ValueError('Expected one ARM64 text section')
    return sections[0]


def relative(word, pc, bits, shift=0):
    value = (word >> shift) & ((1 << bits)-1)
    if value & (1 << (bits-1)):
        value -= 1 << bits
    return pc+4*value


def page_address(word, pc, register):
    if word & 0x9f00001f != 0x90000000 | register:
        raise ValueError('Unknown ADRP addressing')
    delta = ((word >> 29) & 3) | (((word >> 5) & 0x7ffff) << 2)
    if delta & (1 << 20):
        delta -= 1 << 21
    return (pc & ~4095)+(delta << 12)


def add_address(word, base, register):
    if word & 0xffc003ff != 0x91000000 | register | (register << 5):
        raise ValueError('Unknown ADD addressing')
    return base+((word >> 10) & 4095)


def words(image, address, count):
    return struct.unpack('<'+'I'*count, image.read(address, count*4))


def inspect_lookup(image, address, dlsym_stub):
    w = words(image, address, 12)
    if w[0] != 0xf9400be0 or w[3] & 0xfc000000 != 0x94000000:
        raise ValueError('Unknown lookup argument/call')
    resolver = relative(w[3], address+12, 26)
    r = words(image, resolver, 12)
    page_address(r[5], resolver+20, 8)
    if (r[:5] != (0xd10143ff, 0xa9047bfd, 0x910103fd, 0xf81f83a0, 0xf81f03a1) or
        r[6] & 0xffc003ff != 0xf9400100 or r[7] != 0xf85f03a1 or
        r[8] & 0xfc000000 != 0x94000000 or
        relative(r[8], resolver+32, 26) != dlsym_stub or
        r[9:11] != (0xf81e83a0, 0xf85e83a8) or r[11] & 0xff00001f != 0xb5000008):
        raise ValueError('Unknown dlsym result flow')
    tail = relative(r[11], resolver+44, 19, 5)
    if words(image, tail, 4) != (0xf85e83a0, 0xa9447bfd, 0x910143ff, 0xd65f03c0):
        raise ValueError('Unknown resolver return')
    slot_base = add_address(w[5], page_address(w[4], address+16, 8), 8)
    if (w[6] & 0xffc003ff != 0xf9000100 or
        w[7] & 0xffc003ff != 0xf9400108 or (w[6] >> 10) & 4095 != (w[7] >> 10) & 4095 or
        w[8] & 0xff00001f != 0xb5000008 or relative(w[8], address+32, 19, 5) != address+48 or
        w[9] != 0x14000001 or w[10] != 0xb81fc3bf or w[11] & 0xfc000000 != 0x14000000):
        raise ValueError('Unknown lookup/null-failure contract')
    failure = relative(w[11], address+44, 26)
    if words(image, failure, 4) != (0xb85fc3a0, 0xa9427bfd, 0x9100c3ff, 0xd65f03c0):
        raise ValueError('Unknown loader return-zero epilogue')
    return {'lookupRVA': address-0x100000000, 'resolverRVA': resolver-0x100000000,
            'slotVA': slot_base+8*((w[6] >> 10) & 4095),
            'failureReturnRVA': failure-0x100000000,
            'nullLookupReturnsZero': True}


def audit(image, dlsym_stub, names=CUSTOM):
    base, code = text_section(image)
    result = {}
    for name in names:
        needle = name.encode()+b'\0'
        matches = []
        for i in range(4, len(code)-44, 4):
            word = struct.unpack_from('<I', code, i)[0]
            if word & 0x9f00001f != 0x90000001:
                continue
            add = struct.unpack_from('<I', code, i+4)[0]
            if add & 0xffc003ff != 0x91000021:
                continue
            target = add_address(add, page_address(word, base+i, 1), 1)
            try:
                if image.read(target, len(needle)) != needle:
                    continue
            except ValueError:
                continue
            matches.append(inspect_lookup(image, base+i-4, dlsym_stub))
        if len(matches) != 1:
            raise ValueError('Expected one verified mandatory lookup for '+name)
        result[name] = matches[0]
    if (len({x['resolverRVA'] for x in result.values()}) != 1 or
        len({x['failureReturnRVA'] for x in result.values()}) != 1 or
        len({x['slotVA'] for x in result.values()}) != len(result)):
        raise ValueError('Inconsistent loader table/failure path')
    return result


def find_dlsym_stub(text):
    active = False
    found = []
    for line in text.splitlines():
        if line.startswith('Indirect symbols for '):
            active = line.startswith('Indirect symbols for (__TEXT,__stubs)')
        elif active:
            match = re.fullmatch(r'\s*(0x[0-9a-fA-F]+)\s+\d+\s+_dlsym\s*', line)
            if match:
                found.append(int(match[1], 16))
    if len(found) != 1:
        raise ValueError('Expected exactly one ARM64 dlsym import stub')
    return found[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--helper', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() == args.helper.resolve() or (args.output.exists() and args.output.samefile(args.helper)):
        raise ValueError('Report must preserve binary input')
    data = args.helper.read_bytes()
    thin = arm64_slice(data)
    imports = subprocess.check_output(['xcrun', 'otool', '-arch', 'arm64', '-Iv', str(args.helper)], text=True)
    result = audit(abi.MachO(thin), find_dlsym_stub(imports))
    report = {'mode': 'static read-only; CEF not initialized',
              'helperSHA256': hashlib.sha256(data).hexdigest(),
              'arm64SliceSHA256': hashlib.sha256(thin).hexdigest(),
              'customLookups': result,
              'limits': ['Narrow static loader-block evidence, not runtime CEF initialization.',
                         'Mandatory symbol presence does not prove full ABI or behavior compatibility.',
                         'Never skip lookups, stub custom semantics or spoof cef_api_hash.']}
    abi.write_report(args.output, report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
