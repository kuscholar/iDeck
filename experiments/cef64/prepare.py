#!/usr/bin/env python3
"""Prepare a source-only, version-pinned chrome_elf build, never a Valve tree.

SPDX-License-Identifier: GPL-3.0-or-later
Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

REVISION = "2e81dea53f5ecdc1c057e4c70ecd66151987296a"
HEADER = "base/allocator/partition_allocator/src/partition_alloc/partition_address_space.h"
HEADER_SHA256 = "96faadaf33cafc64caba2d404838e765453dd45f3cc6d8747d7278c6faebdf34"
INITIAL = ["base", "build", "build_overrides", "buildtools", "chrome/chrome_elf",
           "chrome/install_static", "chrome/common", "chrome/app/theme",
           "components/crash", "components/version_info", "content/public/common",
           "sandbox", "testing", "tools/clang", "tools/grit", "tools/win",
           "third_party/abseil-cpp", "third_party/crashpad", "third_party/zlib",
           "third_party/libc++", "third_party/libc++abi", "third_party/llvm-libc",
           "third_party/ninja", "third_party/mini_chromium"]


def run(root, *args):
    return subprocess.check_output(args, cwd=root, text=True).strip()


def patch_header(data):
    """Keep masks derived from sizes, BRP and all allocator failure checks."""
    if hashlib.sha256(data).hexdigest() != HEADER_SHA256:
        raise ValueError("unrecognized allocator header; refusing patch")
    text = data.decode()
    for name in ("kRegularPoolSize", "kBRPPoolSize"):
        old = f"static constexpr size_t {name} = kPoolMaxSize;"
        if text.count(old) != 1:
            raise ValueError("non-unique allocator declaration")
        text = text.replace(old, f"static constexpr size_t {name} = 1 * kGiB;")
    return text.encode()


def prepare(root):
    if run(root, "git", "rev-parse", "HEAD") != REVISION:
        raise ValueError("checkout does not match pinned Chromium revision")
    # Refuse to overwrite existing work. This checkout is disposable and separate
    # from iDeck, Wine, FEX and every Steam installation.
    dirty = run(root, "git", "status", "--porcelain", "--untracked-files=no")
    if dirty:
        raise ValueError("source checkout contains changes; preserve and inspect it")
    subprocess.run(["git", "sparse-checkout", "set", *INITIAL], cwd=root, check=True)
    header = root / HEADER
    header.write_bytes(patch_header(header.read_bytes()))
    (root / "BUILD.gn").write_text('group("default") { deps = [ "//chrome/chrome_elf:chrome_elf" ] }\n')
    # gclient normally generates this. The focused target does not require
    # Android, private/internal sources or optional browser test datasets.
    (root / "build/config/gclient_args.gni").write_text(
        "build_with_chromium = true\n" + "\n".join(f"{n} = false" for n in (
            "checkout_android", "checkout_android_prebuilts_build_tools",
            "checkout_android_native_support", "checkout_clang_coverage_tools",
            "checkout_ios_webkit", "checkout_nacl", "checkout_openxr",
            "checkout_src_internal", "generate_location_tags")) +
        '\ncros_boards = ""\ncros_boards_with_qemu_images = ""\n')
    out = root / "out/ideck-elf"
    out.mkdir(parents=True, exist_ok=True)
    (out / "args.gn").write_text('''target_os = "win"
target_cpu = "x64"
is_debug = false
is_official_build = false
is_component_build = false
symbol_level = 0
chrome_pgo_phase = 0
enable_nacl = false
enable_base_tracing = false
use_remoteexec = false
use_thin_lto = false
treat_warnings_as_errors = false
''')
    manifest = {"chromium_revision": REVISION, "target": "chrome_elf",
                "scope": "only this DLL and its statically linked allocator; not libcef",
                "header_original_sha256": HEADER_SHA256,
                "header_patched_sha256": hashlib.sha256(header.read_bytes()).hexdigest(),
                "regular_pool_bytes": 1 << 30, "brp_pool_bytes": 1 << 30,
                "runtime_validation": False}
    (root / "ideck-elf-source.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    prepare(parser.parse_args().checkout.resolve())
