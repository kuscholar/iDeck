#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Check the production text-input ownership policy without capturing user input."""
from pathlib import Path
import os,subprocess,tempfile
root=Path(__file__).resolve().parents[2]
s=(root/'app/Madeira/HardwareInput.swift').read_text()
policy=s[s.index('enum TextKeyboardRouting {'):s.index('// MARK: - Device glue')]
checks='''
assert(TextKeyboardRouting.responderOwnsText(experimental: true, firstResponder: true))
assert(!TextKeyboardRouting.responderOwnsText(experimental: false, firstResponder: true))
assert(!TextKeyboardRouting.responderOwnsText(experimental: true, firstResponder: false))
for key: Int32 in [0x41, 0x5A, 0x30, 0x39, 0x08, 0x0D, 0x09, 0x20, 0xDE] {
 assert(TextKeyboardRouting.isTextKey(key))
}
for key: Int32 in [0x10, 0x11, 0x12, 0x25, 0x70, 0xA0] {
 assert(!TextKeyboardRouting.isTextKey(key))
}
assert(!TextKeyboardRouting.shortcutHeld([]))
assert(!TextKeyboardRouting.shortcutHeld([0xA0]))
for modifier: Int32 in [0x11, 0x12, 0x5B, 0x5C, 0xA2, 0xA3, 0xA4, 0xA5] {
 assert(TextKeyboardRouting.shortcutHeld([modifier]))
}
'''
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'policy.swift').write_text('import Foundation\n'+policy+checks)
 subprocess.run([os.environ.get('SWIFTC','swiftc'),str(p/'policy.swift'),'-o',str(p/'policy')],check=True)
 subprocess.run([str(p/'policy')],check=True)
print('PASS: production lab text ownership, ordinary-path preservation, text/control keys and shortcut routing')
