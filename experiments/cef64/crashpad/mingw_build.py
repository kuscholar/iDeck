#!/usr/bin/env python3
"""Local Mac -> AMD64 Windows Crashpad build, never a publish or runtime pass.

SPDX-License-Identifier: GPL-3.0-or-later
Madeira Converter Exception: see LICENSE-EXCEPTION.md
Source-level platform adaptations retain upstream Apache/BSD notices.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

from prepare import replace_once, write_lf
from build import GN_REVISION, amd64_pe


def extended_dbghelp(text):
    # Reuse the matching upstream Crashpad definitions missing in MinGW's SDK.
    # Do not invent a smaller dump format or omit context/thread information.
    result = "\n".join(text.splitlines()[:14]) + '''
#ifndef IDECK_MINGW_DBGHELP_EXTENSIONS_H_
#define IDECK_MINGW_DBGHELP_EXTENSIONS_H_
#include_next <dbghelp.h>
#include <stdint.h>
static_assert(sizeof(wchar_t)==2, "Windows UTF16 field ABI");
'''
    sizes = {"XSTATE_CONFIG_FEATURE_MSC_INFO": 528, "MINIDUMP_MISC_INFO_3": 232,
             "MINIDUMP_MISC_INFO_4": 832, "MINIDUMP_MISC_INFO_5": 1364,
             "MINIDUMP_THREAD_NAME": 12, "MINIDUMP_THREAD_NAME_LIST": 4}
    for name in sizes:
        matches = re.findall(r'struct __attribute__\(\(packed, aligned\(4\)\)\) ' + name + r'(?=[\s:{]).*?\n};', text, re.S)
        if len(matches) != 1:
            raise ValueError("ambiguous upstream minidump structure " + name)
        result += matches[0] + "\n"
    for match in re.finditer(r'^#define (MINIDUMP_MISC[345]_\w+) (.*)$', text, re.M):
        result += match.group(0) + "\n"
    result = result.replace("char16_t BuildString[260]", "wchar_t BuildString[260]")
    result = result.replace("char16_t DbgBldStr[40]", "wchar_t DbgBldStr[40]")
    result += "typedef MINIDUMP_MISC_INFO_5 MINIDUMP_MISC_INFO_N;\n"
    for name, size in sizes.items():
        result += f'static_assert(sizeof({name})=={size}, "public minidump ABI");\n'
    return result + "#endif\n"


def adapt_tls(text):
    start = text.index('#ifdef _WIN64\n\n#pragma comment')
    end = text.index('#endif  // _WIN64', start) + len('#endif  // _WIN64')
    text = text[:start] + '// GNU link arguments explicitly retain both original TLS symbols.\n' + text[end:]
    text = replace_once(text, '#pragma const_seg(".CRT$XLB")',
                        '// GNU equivalent of the original .CRT$XLB section selection.')
    text = replace_once(text, 'const PIMAGE_TLS_CALLBACK p_thread_callback_base = OnThreadExit;',
                        'const PIMAGE_TLS_CALLBACK p_thread_callback_base __attribute__((section(".CRT$XLB"), used)) = OnThreadExit;')
    return replace_once(text, '#pragma const_seg()', '// GNU section attribute above applies to this variable only.')


def verify_image(path, tools):
    receipt = amd64_pe(path)
    data = path.read_bytes()
    pe = struct.unpack_from("<I", data, 60)[0]
    count = struct.unpack_from("<H", data, pe + 6)[0]
    optional = pe + 24
    size = struct.unpack_from("<H", data, pe + 20)[0]
    base = struct.unpack_from("<Q", data, optional + 24)[0]
    sections = []
    for i in range(count):
        offset = optional + size + 40 * i
        name = data[offset:offset + 8].rstrip(b"\0").decode()
        virtual_size, address, raw_size, raw_offset = struct.unpack_from("<IIII", data, offset + 8)
        sections.append((name, virtual_size, address, raw_size, raw_offset))

    def raw(rva):
        for _, _, address, raw_size, raw_offset in sections:
            if address <= rva < address + raw_size:
                return raw_offset + rva - address
        raise ValueError("unbacked PE RVA")

    tls, tls_size = struct.unpack_from("<II", data, optional + 112 + 9 * 8)
    if not tls or tls_size < 40:
        raise ValueError("missing real PE TLS directory")
    callbacks = struct.unpack_from("<Q", data, raw(tls) + 24)[0]
    cursor = raw(callbacks - base)
    callback_addresses = []
    for i in range(32):
        address = struct.unpack_from("<Q", data, cursor + i * 8)[0]
        if not address:
            break
        callback_addresses.append(address)
    symbols = subprocess.check_output([str(tools / "llvm-nm"), str(path)], text=True)
    symbol = next(line for line in symbols.splitlines() if line.endswith(" p_thread_callback_base"))
    callback = struct.unpack_from("<Q", data, raw(int(symbol.split()[0], 16) - base))[0]
    if callback not in callback_addresses:
        raise ValueError("original mini_chromium thread-exit callback lost")
    cpad = any(s[0] == "CPADinfo" for s in sections)
    if path.name == "crashpad_handler.exe" and not cpad:
        raise ValueError("missing actual Crashpad info section")
    if not any(s[0] == ".pdata" and s[1] > 0 for s in sections):
        raise ValueError("missing Windows unwind metadata")
    imports = subprocess.check_output([str(tools / "llvm-readobj"), "--coff-imports", str(path)], text=True)
    dlls = [line.strip().split(": ", 1)[1] for line in imports.splitlines() if line.strip().startswith("Name: ")]
    if any(any(word in name.lower() for word in ("libcef", "chrome_elf", "libc++", "libwinpthread")) for name in dlls):
        raise ValueError("unexpected browser or non-system runtime import")
    receipt.update({"TLS_callback_retained": True, "CPADinfo_present": cpad,
                    "unwind_present": True, "imports": dlls, "runtime": "not run"})
    return receipt


def runtime_sections(data):
    """Resolve COFF long names; compare every mapped non-DWARF section."""
    pe = struct.unpack_from("<I", data, 60)[0]
    optional = pe + 24
    count = struct.unpack_from("<H", data, pe + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    symbols, symbol_count = struct.unpack_from("<II", data, pe + 12)
    strings = symbols + symbol_count * 18
    result = {}
    for index in range(count):
        offset = optional + optional_size + index * 40
        name = data[offset:offset + 8].rstrip(b"\0").decode()
        if name.startswith("/"):
            start = strings + int(name[1:])
            name = data[start:data.index(b"\0", start)].decode()
        if name.startswith(".debug_"):
            continue
        virtual_size, address, raw_size, raw_offset = struct.unpack_from("<IIII", data, offset + 8)
        characteristics = struct.unpack_from("<I", data, offset + 36)[0]
        if name in result:
            raise ValueError("duplicate mapped section")
        result[name] = (virtual_size, address, characteristics,
                        data[raw_offset:raw_offset + min(virtual_size, raw_size)])
    # Entry point, image base and executable/security flags must not change.
    identity = (data[pe + 4:pe + 6], data[pe + 22:pe + 24],
                data[optional:optional + 2], data[optional + 16:optional + 20],
                data[optional + 24:optional + 40], data[optional + 68:optional + 72])
    return result, identity, struct.unpack_from("<I", data, optional + 56)[0]


def prepare_runtime(build_dir, tools):
    """Keep originals for symbols; deploy separate, verified DWARF-free PEs.

    Madeira currently copies SizeOfImage into its executable image pool. GNU
    DWARF sections can otherwise turn a 1.3MiB handler into a 24MiB allocation.
    This removes debug data only, never machine code or runtime failure checks.
    """
    output = build_dir / "runtime"
    output.mkdir(exist_ok=False)
    receipts = {}
    for name in ("crashpad_handler.exe", "crashpad_smoke.exe"):
        source, target = build_dir / name, output / name
        subprocess.run([str(tools / "llvm-strip"), "--strip-debug", "-o", str(target), str(source)], check=True)
        before, identity, original_size = runtime_sections(source.read_bytes())
        after, new_identity, runtime_size = runtime_sections(target.read_bytes())
        if before != after or identity != new_identity or runtime_size > original_size:
            raise ValueError("debug stripping changed a runtime section/header")
        receipt = verify_image(target, tools)
        receipt.update({"original_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                        "original_image_size": original_size, "runtime_image_size": runtime_size,
                        "all_non_debug_section_bytes_RVAs_sizes_flags_preserved": True,
                        "scope": "only debug data removed; original PE retained privately for symbols"})
        receipts[name] = receipt
    (output / "runtime-integrity.json").write_text(json.dumps(receipts, indent=2) + "\n")
    return receipts


def prepare_cross(root, tools):
    here = Path(__file__).resolve().parent
    for name in ("mingw_tool.py", "mingw_config.gn", "smoke.cc"):
        shutil.copyfile(here / name, root / "ideck" / name)
    changed = {}

    def change(name, transform):
        path = root / name
        before = path.read_bytes()
        after = transform(before.decode())
        write_lf(path, after)
        changed[name] = {"original_sha256": hashlib.sha256(before).hexdigest(),
                         "adapted_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    change("build/BUILDCONFIG.gn", lambda s: replace_once(s,
           '"$_mini_chromium_dir/build/config:msvc_toolchain_$current_cpu"',
           '"$_mini_chromium_dir/build/config:ideck_mingw"'))
    config = "third_party/mini_chromium/mini_chromium/build/config/BUILD.gn"
    change(config, lambda _: (here / "mingw_config.gn").read_text())
    for path in sorted((root / "compat/win").rglob("*.h")):
        if re.search(r'#include <\.\./(?:ucrt|um)/', path.read_text()):
            change(path.relative_to(root).as_posix(), lambda s: re.sub(
                r'#include <\.\./(?:ucrt|um)/([^>]+)>', r'#include_next <\1>', s))
    change("third_party/mini_chromium/mini_chromium/base/threading/thread_local_storage_win.cc", adapt_tls)
    change("client/crashpad_info.cc", lambda s: replace_once(s,
           '#pragma section("CPADinfo", read, write)\n__declspec(allocate("CPADinfo"))',
           '__attribute__((section("CPADinfo"), used))'))
    for name in ("snapshot/x86/cpuid_reader.cc", "snapshot/win/system_snapshot_win.cc"):
        change(name, lambda s: replace_once(s, "__declspec(align(16))", "alignas(16)"))
    change("compat/win/winbase.h", lambda s: replace_once(s, '#endif  // CRASHPAD_COMPAT_WIN_WINBASE_H_',
           '#ifdef __cplusplus\nextern "C" {\n#endif\n'
           'WINBASEAPI BOOL WINAPI InitializeContext2(void*, DWORD, CONTEXT**, DWORD*, ULONG64);\n'
           '#ifdef __cplusplus\n}\n#endif\n\n#endif  // CRASHPAD_COMPAT_WIN_WINBASE_H_'))
    write_lf(root / "compat/win/dbghelp.h", extended_dbghelp((root / "compat/non_win/dbghelp.h").read_text()))
    (root / "ideck-mingw-source.json").write_text(json.dumps({
        "scope": "explicit Mac to AMD64 Windows LLVM-MinGW build; no publication",
        "source_adaptations": changed, "missing_SDK_types": "exact matching Crashpad definitions with public-size asserts",
        "TLS": "original callback and original assembly retained; GNU section/link/C++-name equivalents",
        "InitializeContext2": "declaration only; original dynamic lookup/fallback unchanged",
        "diagnostics": "format/sign warnings remain visible; no assertions/reporting removed"}, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tools", type=Path, required=True)
    parser.add_argument("--gn", type=Path, required=True)
    args = parser.parse_args()
    source, output, tools, gn = (p.resolve() for p in (args.source, args.output, args.tools, args.gn))
    if sys.platform != "darwin" or output.exists() or source in output.parents:
        raise ValueError("use a new separate output directory on macOS")
    if any(any(c.isspace() for c in str(p)) for p in (source, output, tools, gn)):
        raise ValueError("this experimental GN adapter requires paths without whitespace")
    version = subprocess.check_output([str(gn), "--version"], text=True)
    if GN_REVISION[:7] not in version:
        raise ValueError("wrong pinned GN")
    subprocess.run([sys.executable, str(Path(__file__).resolve().parents[3] / "tests/host/check-cef64-crashpad.py"),
                    "--source", str(source), "--source-only"], check=True)
    subprocess.run(["cp", "-cR", str(source), str(output)], check=True)
    prepare_cross(output, tools)
    build_dir = output / "out/ideck-mingw"
    build_dir.mkdir(parents=True)
    (build_dir / "args.gn").write_text('target_os="win"\ntarget_cpu="x64"\nis_debug=false\ncrashpad_dependencies="standalone"\nideck_mingw_bin="' + str(tools) + '"\n')
    subprocess.run([str(gn), "gen", str(build_dir), "--root=" + str(output)], check=True)
    subprocess.run(["ninja", "-C", str(build_dir), "crashpad_handler", "crashpad_smoke", "-j", "4"], check=True)
    receipts = {name: verify_image(build_dir / name, tools) for name in ("crashpad_handler.exe", "crashpad_smoke.exe")}
    (output / "ideck-mingw-pe-verification.json").write_text(json.dumps(receipts, indent=2) + "\n")
    prepare_runtime(build_dir, tools)
    print("AMD64 cross build and final PE integrity PASS; Windows/iOS runtime NOT established")
