#!/usr/bin/env python3
"""Retain published CEF126 crash glue in the disposable chrome_elf source tree.

SPDX-License-Identifier: GPL-3.0-or-later
Madeira Converter Exception: see LICENSE-EXCEPTION.md
The applied upstream CEF/Chromium code retains its original BSD notices.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from prepare import REVISION, focused_elf_build, gn_target, run

CEF_REVISION = "a5d51ba9db7ee74a523dc247bd09ec91ba4d7446"
PATCH_SHA256 = "28c7eb14cb25305c392586888f271edde9ce56406d7282fd0e2ddd0a89d0ffdd"
PATCHED_ELF_BUILD_SHA256 = "9ea7d1278b35248ee77df7030dcccc9094b469fee4d659c1b058149c6c089051"
CEF_BUILD_SHA256 = "61184106c1693c073a08e775ca30f8b864d8c815bcdd3a724363f85531eeb7fe"
BUILD_FLAGS = {
    "chrome/common/BUILD.gn": ("d1bb1fd2be93e16022892174d34e66d694a0ef35d31bbc3fc50327fdf7cea782", "buildflags", [
        "//build/buildflag_header.gni", "//chrome/browser/downgrade/buildflags.gni", "//chrome/common/features.gni"]),
    "media/BUILD.gn": ("d7a6dd248b5eccbdec11b4c23021a10edda688f9017c51100fc752ae898422db", "media_buildflags", None),
    "ui/base/BUILD.gn": ("6bf961b872eac7e81d3600cf1abba08d2ddf0861c58a6c49a42985a969522a73", "buildflags", [
        "//build/buildflag_header.gni", "//build/config/features.gni", "//build/config/ui.gni",
        "//build/config/linux/gtk/gtk.gni", "//build/config/ozone.gni", "//ui/base/ui_features.gni", "//ui/qt/qt.gni"]),
    "tools/v8_context_snapshot/BUILD.gn": ("6958a78560e72a8a083cf6b34f7dc3be0e6536ec4632d4ae8e2426deda77498f", "buildflags", [
        "//build/buildflag_header.gni", "//tools/v8_context_snapshot/v8_context_snapshot.gni"]),
}
V8_GENERATOR_DEP = '  deps += [ "//tools/v8_context_snapshot:buildflags" ]\n'


def focused_cef_target(data):
    if hashlib.sha256(data).hexdigest() != CEF_BUILD_SHA256:
        raise ValueError("unrecognized CEF build metadata")
    original = data.decode()
    target = gn_target(original, "static_library", "chrome_elf_set")
    # Full CEF normally also builds this generated header through other
    # targets. Make content_switches.h's actual dependency explicit here.
    target = target[:-1] + V8_GENERATOR_DEP + "}"
    return ("\n".join(original.splitlines()[:3]) + "\n\n" + target + "\n").encode()


def focused_buildflag_file(name, data):
    expected, target, imports = BUILD_FLAGS[name]
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("unrecognized CEF buildflag dependency " + name)
    original = data.decode()
    if imports is None:
        # Media's preamble contains only imports and conditional CDM imports.
        # Retain it verbatim except unused test templates; flag values remain
        # derived from the original production options.
        prefix = original.split('buildflag_header("media_buildflags")', 1)[0]
        prefix = "\n".join(line for line in prefix.splitlines() if not line.startswith('import("//testing/')) + "\n"
    else:
        prefix = "\n".join(original.splitlines()[:3]) + "\n\n"
        prefix += "\n".join('import("' + path + '")' for path in imports) + "\n\n"
        if name == "chrome/common/BUILD.gn":
            prefix += 'assert(enable_supervised_users)\nassert(!is_fuchsia, "Fuchsia shouldn\'t use anything in //chrome")\n\n'
    return (prefix + gn_target(original, "buildflag_header", target) + "\n").encode()


def prepare_cef_glue(root):
    manifest_file = root / "ideck-elf-source.json"
    manifest = json.loads(manifest_file.read_text())
    if run(root, "git", "rev-parse", "HEAD") != REVISION or manifest["chromium_revision"] != REVISION:
        raise ValueError("CEF glue requires exact already-prepared Chromium checkout")
    elf_build = root / "chrome/chrome_elf/BUILD.gn"
    original_elf = subprocess.check_output(["git", "show", "HEAD:chrome/chrome_elf/BUILD.gn"], cwd=root)
    if elf_build.read_bytes() != focused_elf_build(original_elf):
        raise ValueError("preserve unexpected existing ELF metadata changes")
    allowed = {"BUILD.gn", "chrome/chrome_elf/BUILD.gn", "content/public/common/BUILD.gn",
               "sandbox/BUILD.gn", "sandbox/win/BUILD.gn", "components/nacl/common/BUILD.gn",
               "base/allocator/partition_allocator/src/partition_alloc/partition_address_space.h"}
    if set(run(root, "git", "diff", "--name-only").splitlines()) != allowed:
        raise ValueError("preserve unrelated tracked changes before CEF integration")
    cef = root / "cef"
    if cef.exists():
        raise ValueError("CEF checkout already exists; do not overwrite it")
    # Retain history: upstream version generation uses real branch ancestry and
    # commit counts. Do not invent a CEF version from a shallow commit count.
    subprocess.run(["git", "clone", "--config", "core.autocrlf=false", "--config", "core.longpaths=true", "--filter=blob:none", "--no-checkout",
                    "https://github.com/chromiumembedded/cef.git", str(cef)], check=True)
    subprocess.run(["git", "checkout", "--detach", CEF_REVISION], cwd=cef, check=True)
    if run(cef, "git", "rev-parse", "HEAD") != CEF_REVISION:
        raise ValueError("wrong CEF revision")
    compatibility = (cef / "CHROMIUM_BUILD_COMPATIBILITY.txt").read_text()
    if "refs/tags/126.0.6478.183" not in compatibility:
        raise ValueError("CEF requires another Chromium version")
    patch = cef / "patch/patches/crashpad_1995.patch"
    if hashlib.sha256(patch.read_bytes()).hexdigest() != PATCH_SHA256:
        raise ValueError("unrecognized published CEF crash patch")
    # Apply the complete published patch, not selected C++ hunks or stubs.
    # The checked focused metadata is the only prepared file it also touches.
    elf_build.write_bytes(original_elf)
    subprocess.run(["git", "apply", "-p0", "--check", str(patch)], cwd=root, check=True)
    subprocess.run(["git", "apply", "-p0", str(patch)], cwd=root, check=True)
    elf_build.write_bytes(focused_elf_build(elf_build.read_bytes(), PATCHED_ELF_BUILD_SHA256))
    cef_build = cef / "BUILD.gn"
    cef_build.write_bytes(focused_cef_target(cef_build.read_bytes()))
    # The original header targets share BUILD files with whole Chrome/UI/PDF
    # libraries. Keep only their checked target bodies, not unused runtimes.
    # Selecting media/base brings parent media metadata without its test data.
    subprocess.run(["git", "sparse-checkout", "add", "media/base", "ui/base", "tools/v8_context_snapshot"], cwd=root, check=True)
    for name in BUILD_FLAGS:
        path = root / name
        path.write_bytes(focused_buildflag_file(name, path.read_bytes()))
    # The official tool defaults to depot_tools git.bat on Windows. Use the
    # already working Git on PATH instead; keep real ancestry/version logic.
    subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'tools'); "
                    "import git_util; git_util.git_exe='git'; import make_version_header; "
                    "make_version_header.main(['make_version_header.py', 'include/cef_version.h'])"], cwd=cef, check=True)
    if CEF_REVISION not in (cef / "include/cef_version.h").read_text():
        raise ValueError("generated CEF version does not identify pinned source")
    manifest.update({"cef_revision": CEF_REVISION, "cef_crash_patch_sha256": PATCH_SHA256,
                     "cef_glue": "complete upstream crashpad_1995.patch plus exact chrome_elf_set target",
                     "focused_buildflag_headers": list(BUILD_FLAGS),
                     "scope": "only chrome_elf with upstream CEF crash integration; no libcef or Valve binary changes"})
    manifest_file.write_text(json.dumps(manifest, indent=2) + "\n")
