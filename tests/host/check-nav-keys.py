#!/usr/bin/env python3
"""Navigation keys: scan code and E0 flag as a PC keyboard sends them.

winios_drv_post_key (build/win32u-unix/driver_ios.c) derives each key's scan
code with NtUserMapVirtualKeyEx(MAPVK_VK_TO_VSC_EX) on Wine's built-in US
layout and marks it extended with winios_key_extended_flag(). This test takes
every virtual key through that chain on a POSIX host:

  * the VK-to-scan lookup is emulated from the Wine tree
    (dlls/win32u/input.c's vsc_to_vk tables, include/kbd.h, winuser.rh);
  * winios_key_extended_flag() is compiled from the production source;

and checks that the ten dedicated navigation keys send their PC set-1 scan code
with the E0 prefix, that their numpad twins do not, that no other key changes,
and that MADEIRA_NAV_KEYS_E0=0 restores the previous flags.

Needs python3, a C compiler (CC, default cc) and the Wine source: the `wine`
submodule, or WINE_SRC=<path to a Wine tree>. No iOS SDK or device is needed.
"""
from pathlib import Path
import os
import re
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
wine = Path(os.environ.get('WINE_SRC', root / 'wine'))
input_c = wine / 'dlls/win32u/input.c'
if not input_c.exists():
    sys.exit(f'FAIL: Wine source not found at {wine}; check out the wine submodule or set WINE_SRC')

failures = []


def check(cond, what):
    if not cond:
        failures.append(what)


# ------------------------------------------------ Wine's VK -> scan lookup ---
vk_values = {}
for header in ('include/winuser.rh', 'include/winuser.h', 'include/kbd.h'):
    for name, val in re.findall(r'#define\s+VK_(\w+)\s+(?:\(\w+\))?(0x[0-9A-Fa-f]+|\d+)\b',
                                (wine / header).read_text(errors='replace')):
        vk_values.setdefault(name, int(val, 0))
kbd = (wine / 'include/kbd.h').read_text(errors='replace')
kbd_type = 4                                            # kbd.h's default KBD_TYPE
macros = dict(re.findall(r'#define\s+([TXY][0-9A-F]{2})\s+(.+)', kbd))


def macro_vk(token):
    body = macros[token].strip()
    if re.fullmatch(r"'.'", body):
        return ord(body[1])
    m = re.fullmatch(r'_EQ\((\w+)\)', body)
    if m:
        return vk_values.get(m.group(1), -1)
    m = re.fullmatch(r'_NE\(([^)]*)\)', body)
    if m:
        return vk_values.get(m.group(1).split(',')[kbd_type - 1].strip(), -1)
    raise ValueError(f'unparsed kbd.h macro {token} = {body}')


text = input_c.read_text(errors='replace')
main_table = re.search(r'static const USHORT vsc_to_vk\[\] =\s*\{(.*?)\};', text, re.S).group(1)
vsc2vk = {}
for vsc, entry in enumerate(t.strip() for t in main_table.split(',') if t.strip()):
    vk = macro_vk(entry.split('|')[0].strip())
    if vk != vk_values['_none_']:
        vsc2vk[vsc] = vk
for table, base in (('vsc_to_vk_e0', 0x100), ('vsc_to_vk_e1', 0x200)):
    body = re.search(r'static const VSC_VK %s\[\] =\s*\{(.*?)\};' % table, text, re.S).group(1)
    for vsc, entry in re.findall(r'\{\s*(0x[0-9a-fA-F]+)\s*,\s*([TXY][0-9A-F]{2})[^}]*\}', body):
        vk = macro_vk(entry)
        if vk != vk_values['_none_']:
            vsc2vk[base + int(vsc, 16)] = vk

# NtUserMapVirtualKeyEx(code, MAPVK_VK_TO_VSC_EX): the generic modifiers and the
# numpad virtual keys are first replaced, then the lowest scan-table index whose
# virtual key matches wins; an E0/E1 position is returned as 0xe0xx/0xe1xx.
assert 'case VK_NUMPAD8: code = VK_UP; break;' in text, "Wine's VK_TO_VSC remapping changed"
remap = {'SHIFT': 'LSHIFT', 'CONTROL': 'LCONTROL', 'MENU': 'LMENU', 'NUMPAD0': 'INSERT', 'NUMPAD1': 'END',
         'NUMPAD2': 'DOWN', 'NUMPAD3': 'NEXT', 'NUMPAD4': 'LEFT', 'NUMPAD5': 'CLEAR', 'NUMPAD6': 'RIGHT',
         'NUMPAD7': 'HOME', 'NUMPAD8': 'UP', 'NUMPAD9': 'PRIOR', 'DECIMAL': 'DELETE'}
remap = {vk_values[a]: vk_values[b] for a, b in remap.items()}


def vk_to_vsc_ex(vk):
    vk = remap.get(vk, vk)
    for idx in range(0x300):
        if idx in vsc2vk and (vsc2vk[idx] & 0xff) == vk:
            return idx + 0xdf00 if idx >= 0x100 else idx
    return 0


# ------------------------------- the driver's extended-flag decision (C) ---
driver = (root / 'build/win32u-unix/driver_ios.c').read_text()
start = driver.index('static UINT winios_key_extended_flag(')
helper = driver[start:driver.index('/* end winios_key_extended_flag */', start)]
nav_names = ('PRIOR', 'NEXT', 'END', 'HOME', 'LEFT', 'UP', 'RIGHT', 'DOWN', 'INSERT', 'DELETE')
c_src = '#include <stdio.h>\ntypedef unsigned int UINT;\n#define KEYEVENTF_EXTENDEDKEY 0x0001\n'
c_src += ''.join(f'#define VK_{nm} 0x{vk_values[nm]:02x}\n' for nm in nav_names)
c_src += helper + r'''
int main(void)
{
    UINT vk, scan;
    while (scanf("%x %x", &vk, &scan) == 2)
        printf("%x %u %u\n", vk, winios_key_extended_flag(vk, scan, 1), winios_key_extended_flag(vk, scan, 0));
    return 0;
}
'''
queries = {vk: vk_to_vsc_ex(vk) for vk in range(1, 0xff)}
with tempfile.TemporaryDirectory(prefix='madeira-navkeys-') as tmp:
    csrc, cexe = Path(tmp) / 'flag.c', Path(tmp) / 'flag'
    csrc.write_text(c_src)
    subprocess.run([os.environ.get('CC', 'cc'), '-Wall', '-Werror', str(csrc), '-o', str(cexe)], check=True)
    res = subprocess.run([str(cexe)], input=''.join(f'{vk:x} {sc:x}\n' for vk, sc in queries.items()),
                         check=True, capture_output=True, text=True).stdout
ext_on, ext_off = {}, {}
for line in res.split('\n'):
    if line.strip():
        vk, on, off = line.split()
        ext_on[int(vk, 16)], ext_off[int(vk, 16)] = int(on), int(off)


def sent(name, nav_e0=True):
    """(scan byte, extended) the driver sends for VK_<name>."""
    vk = vk_values[name]
    return (queries[vk] & 0xff, bool((ext_on if nav_e0 else ext_off)[vk]))


# ------------------------------------------------------------- the checks ---
# PC keyboard, scan code set 1: the dedicated keys carry E0, the numpad does not.
dedicated = {'INSERT': 0x52, 'HOME': 0x47, 'PRIOR': 0x49, 'DELETE': 0x53, 'END': 0x4F, 'NEXT': 0x51,
             'RIGHT': 0x4D, 'LEFT': 0x4B, 'DOWN': 0x50, 'UP': 0x48}
numpad = {'NUMPAD0': 0x52, 'NUMPAD1': 0x4F, 'NUMPAD2': 0x50, 'NUMPAD3': 0x51, 'NUMPAD4': 0x4B,
          'NUMPAD5': 0x4C, 'NUMPAD6': 0x4D, 'NUMPAD7': 0x47, 'NUMPAD8': 0x48, 'NUMPAD9': 0x49,
          'DECIMAL': 0x53}
for name, sc in dedicated.items():
    check(sent(name) == (sc, True), f'VK_{name}: sent {sent(name)} want ({sc:#x}, E0)')
for name, sc in numpad.items():
    check(sent(name) == (sc, False), f'VK_{name}: sent {sent(name)} want ({sc:#x}, no E0)')
# Keys that were already extended stay extended, with or without the switch.
for name, sc in (('RCONTROL', 0x1D), ('RMENU', 0x38), ('DIVIDE', 0x35), ('LWIN', 0x5B), ('APPS', 0x5D)):
    check(sent(name) == (sc, True) and sent(name, nav_e0=False) == (sc, True),
          f'VK_{name}: sent {sent(name)} / {sent(name, nav_e0=False)} want ({sc:#x}, E0) both ways')
# Nothing else changes: only the ten navigation keys differ between the two settings.
nav_vks = {vk_values[n] for n in nav_names}
changed = {vk for vk in queries if ext_on[vk] != ext_off[vk]}
check(changed == nav_vks, f'the fix changes {sorted(map(hex, changed))}, want only the navigation keys')
# MADEIRA_NAV_KEYS_E0=0: the previous flags, under which the up arrow and numpad 8 coincide.
check(sent('UP', nav_e0=False) == sent('NUMPAD8', nav_e0=False) == (0x48, False),
      'rollback: up arrow and numpad 8 should coincide without the fix')
check('getenv( "MADEIRA_NAV_KEYS_E0" )' in driver, 'MADEIRA_NAV_KEYS_E0 switch')
check('flags |= winios_key_extended_flag( vk, scan, nav_e0 );' in driver,
      'winios_drv_post_key uses winios_key_extended_flag')

if failures:
    for f in failures:
        print('FAIL:', f)
    sys.exit(1)
print(f'PASS: {len(dedicated)} navigation keys send E0, {len(numpad)} numpad keys do not, '
      f'{len(queries) - len(nav_vks)} other virtual keys unchanged; MADEIRA_NAV_KEYS_E0=0 rollback checked')
