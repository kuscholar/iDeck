#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Read-only HTML IPC schema comparison from explicitly supplied Valve PEs.

Reads embedded public protobuf descriptors, never runtime/account data. Does
not prove transport compatibility, enumerate command IDs or execute a PE.
Keep the proprietary inputs outside Git. No third-party Python dependencies.
"""
import argparse
import hashlib
import json
from pathlib import Path


def varint(data, pos, end):
    value = 0
    for shift in range(0, 70, 7):
        if pos >= end:
            raise ValueError('Truncated descriptor varint')
        byte = data[pos]
        pos += 1
        value |= (byte & 127) << shift
        if byte < 128:
            return value, pos
    raise ValueError('Invalid descriptor varint')


def fields(data):
    pos, end = 0, len(data)
    while pos < end:
        key, pos = varint(data, pos, end)
        number, wire = key >> 3, key & 7
        if not number:
            return  # C string terminator after the serialized file descriptor.
        if wire == 0:
            value, pos = varint(data, pos, end)
        elif wire in (1, 2, 5):
            size = 8 if wire == 1 else 4
            if wire == 2:
                size, pos = varint(data, pos, end)
            if size > end - pos:
                raise ValueError('Truncated descriptor field')
            value = data[pos:pos + size]
            pos += size
        else:
            raise ValueError('Unsupported descriptor wire type')
        yield number, wire, value


def schema(path):
    data = path.read_bytes()
    marker = b'\x0a\x12htmlmessages.proto'
    if data.count(marker) != 1:
        raise ValueError('Expected a unique htmlmessages file descriptor')
    start = data.index(marker)
    result = {}
    for number, wire, value in fields(data[start:start + 512 * 1024]):
        if number > 12 or number == 12:
            break
        if number != 4:
            continue
        message = list(fields(value))
        name = next(v.decode('ascii') for n, w, v in message if n == 1)
        if name in result:
            raise ValueError('Duplicate message name')
        entries = []
        for n, w, v in message:
            if n != 2:
                continue
            entry = {str(fn): fv.decode('utf8') if isinstance(fv, bytes) else fv
                     for fn, fw, fv in fields(v) if fn in (1, 3, 4, 5, 6, 7)}
            entries.append(entry)
        result[name] = entries
    if not 50 <= len(result) <= 2048 or 'CMsgBrowserCreate' not in result:
        raise ValueError('Unexpected HTML IPC schema')
    return result, hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--require-identical', action='store_true',
                        help='Refuse schema drift before a controlled hybrid test; equality is not runtime proof')
    args = parser.parse_args()
    old, old_hash = schema(args.reference)
    new, new_hash = schema(args.candidate)
    changes = {name: {'reference': old[name], 'candidate': new[name]}
               for name in sorted(old.keys() & new.keys()) if old[name] != new[name]}
    result = {'reference_sha256': old_hash, 'candidate_sha256': new_hash,
              'reference_message_count': len(old), 'candidate_message_count': len(new),
              'added': sorted(new.keys() - old.keys()),
              'removed': sorted(old.keys() - new.keys()), 'changed': changes,
              'limits': 'Descriptor metadata only; not command-ID, transport or runtime validation'}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print('Message counts:', len(old), len(new))
    print('Added:', ', '.join(result['added']) or 'none')
    print('Removed:', ', '.join(result['removed']) or 'none')
    print('Changed:', ', '.join(changes) or 'none')
    if args.require_identical and (result['added'] or result['removed'] or changes):
        parser.exit(2, 'REFUSED: embedded HTML IPC schemas differ; do not claim a compatible pair.\n')


if __name__ == '__main__':
    main()
