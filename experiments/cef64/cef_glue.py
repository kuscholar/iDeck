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


def focused_cef_target(data):
    if hashlib.sha256(data).hexdigest() != CEF_BUILD_SHA256:
        raise ValueError("unrecognized CEF build metadata")
    original = data.decode()
    target = gn_target(original, "static_library", "chrome_elf_set")
    return ("\n".join(original.splitlines()[:3]) + "\n\n" + target + "\n").encode()


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
    subprocess.run(["git", "clone", "--config", "core.autocrlf=false", "--filter=blob:none", "--no-checkout",
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
    # The official tool defaults to depot_tools git.bat on Windows. Use the
    # already working Git on PATH instead; keep real ancestry/version logic.
    subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'tools'); "
                    "import git_util; git_util.git_exe='git'; import make_version_header; "
                    "make_version_header.main(['make_version_header.py', 'include/cef_version.h'])"], cwd=cef, check=True)
    if CEF_REVISION not in (cef / "include/cef_version.h").read_text():
        raise ValueError("generated CEF version does not identify pinned source")
    manifest.update({"cef_revision": CEF_REVISION, "cef_crash_patch_sha256": PATCH_SHA256,
                     "cef_glue": "complete upstream crashpad_1995.patch plus exact chrome_elf_set target",
                     "scope": "only chrome_elf with upstream CEF crash integration; no libcef or Valve binary changes"})
    manifest_file.write_text(json.dumps(manifest, indent=2) + "\n")
