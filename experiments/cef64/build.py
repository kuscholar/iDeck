#!/usr/bin/env python3
"""Build only chrome_elf in the prepared disposable Windows source tree.

SPDX-License-Identifier: GPL-3.0-or-later
Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import urllib.request
import zipfile


def ensure_source(root, relative):
    """Materialize only a missing tracked source directory or pinned gitlink."""
    target = (root / relative).resolve()
    relative = target.relative_to(root).as_posix()  # Reject paths outside checkout.
    if target.exists():
        raise RuntimeError(f"reported missing input already exists: {relative}")
    parts = Path(relative).parts
    for i in range(1, len(parts) + 1):
        prefix = Path(*parts[:i]).as_posix()
        entry = subprocess.check_output(["git", "ls-tree", "HEAD", "--", prefix], cwd=root, text=True)
        if entry.startswith("160000"):
            subprocess.run(["git", "submodule", "update", "--init", "--depth", "1", "--", prefix], cwd=root, check=True)
            return
    entry = subprocess.check_output(["git", "ls-tree", "HEAD", "--", relative], cwd=root, text=True)
    if not entry:
        raise RuntimeError(f"input is not a tracked source or recognized gitlink: {relative}")
    subprocess.run(["git", "sparse-checkout", "add", Path(relative).parent.as_posix()], cwd=root, check=True)


def command_with_sources(root, command, *, cwd, log, attempts=100):
    for _ in range(attempts):
        result = subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        with log.open("a", encoding="utf-8") as output:
            output.write(result.stdout)
        print(result.stdout[-9000:], flush=True)
        if result.returncode == 0:
            return
        match = re.search(r'Unable to load "([^"]+)"', result.stdout)
        if match:
            filename = match.group(1)
            target = root / filename[2:] if filename.startswith("//") else Path(filename)
        else:
            match = re.search(r"ninja: error: '([^']+)'.*missing and no known rule", result.stdout)
            if match:
                # Ninja's missing inputs are relative to its -C build dir,
                # not Python's working directory (which remains source root).
                ninja_dir = Path(command[command.index("-C") + 1]) if "-C" in command else cwd
                target = ninja_dir / match.group(1)
            else:
                match = re.search(r"can't open file ['\"]([^'\"]+)['\"].*\[Errno 2\]", result.stdout)
                if match:
                    target = Path(match.group(1))
                else:
                    match = re.search(r"fatal error: '([^']+)' file not found", result.stdout)
                    if not match:
                        raise subprocess.CalledProcessError(result.returncode, command)
                    target = root / match.group(1)
        ensure_source(root, target.resolve().relative_to(root))
    raise RuntimeError("bounded source-discovery limit reached")


def build(root):
    if sys.platform != "win32":
        raise RuntimeError("use a Windows worker with an already installed official Visual Studio/SDK")
    # GN revision is the version in the pinned Chromium126 DEPS. The package
    # service and build inputs are public; no Google/Valve credentials needed.
    gn_dir = root / "buildtools/win"
    gn_dir.mkdir(parents=True, exist_ok=True)
    package = root / "ideck-gn.zip"
    urllib.request.urlretrieve("https://chrome-infra-packages.appspot.com/dl/gn/gn/windows-amd64/+/git_revision:df98b86690c83b81aedc909ded18857296406159", package)
    with zipfile.ZipFile(package) as z:
        data = z.read("gn.exe")
    (gn_dir / "gn.exe").write_bytes(data)
    subprocess.run([sys.executable, "tools/clang/scripts/update.py", "--package", "clang"], cwd=root, check=True)
    # Chromium's rc.py invokes its own checked-in resource compiler before
    # comparing the result with Microsoft's SDK rc.exe. Reproduce the pinned
    # public rc_win DEPS hook; the official SDK alone does not supply this file.
    rc_dir = root / "build/toolchain/win/rc/win"
    rc_hash = (rc_dir / "rc.exe.sha1").read_text().strip()
    if rc_hash != "6f85dcbb9eb8e31022cf3064dc7f1d129a8f0ad7":
        raise RuntimeError("unexpected resource compiler pin")
    with urllib.request.urlopen("https://storage.googleapis.com/chromium-browser-clang/rc/" + rc_hash) as response:
        rc_bytes = response.read()
    if hashlib.sha1(rc_bytes).hexdigest() != rc_hash:
        raise RuntimeError("resource compiler download hash mismatch")
    (rc_dir / "rc.exe").write_bytes(rc_bytes)
    subprocess.run([sys.executable, "build/util/lastchange.py", "--source-dir", str(root),
                    "--filter", ".", "-o", "build/util/LASTCHANGE"], cwd=root, check=True)
    if "2e81dea53f5ecdc1c057e4c70ecd66151987296a" not in (root / "build/util/LASTCHANGE").read_text():
        raise RuntimeError("generated revision metadata does not identify pinned source")
    output = root / "out/ideck-elf"
    log = root / "ideck-elf-build.log"
    command_with_sources(root, [str(gn_dir / "gn.exe"), "gen", "out/ideck-elf"], cwd=root, log=log)
    command_with_sources(root, ["ninja", "-C", str(output), "chrome_elf", "-j", "3"], cwd=root, log=log)
    if not (output / "chrome_elf.dll").is_file():
        raise RuntimeError("build returned success without requested DLL")
    probe_source = Path(__file__).resolve().parent
    probe_output = root / "out/ideck-load-probe"
    subprocess.run(["cmake", "-S", str(probe_source), "-B", str(probe_output), "-A", "x64"], check=True)
    subprocess.run(["cmake", "--build", str(probe_output), "--config", "Release"], check=True)
    command_with_sources(root, [str(probe_output / "Release/cef64-load-probe.exe"), str(output / "chrome_elf.dll")],
                         cwd=output, log=log, attempts=1)
    source_manifest = json.loads((root / "ideck-elf-source.json").read_text())
    cef_glue = bool(source_manifest.get("cef_revision"))
    if cef_glue:
        # Exercise non-browser DllMain too, which invokes the published CEF
        # CrashReporterClient path. No Steam config, credentials or network.
        command_with_sources(root, [str(probe_output / "Release/cef64-load-probe.exe"),
                                    str(output / "chrome_elf.dll"), "--type=renderer"],
                             cwd=output, log=log, attempts=1)
    # This output is produced ONLY after the real Windows load/VA test passes.
    # Include public source provenance and notices; never stage a Valve tree,
    # Windows SDK, credentials, signing profile or device log as an artifact.
    artifact = root / "ideck-elf-artifact"
    artifact.mkdir(exist_ok=True)
    dll = output / "chrome_elf.dll"
    data = dll.read_bytes()
    pe = struct.unpack_from("<I", data, 0x3c)[0]
    if data[pe:pe+4] != b"PE\0\0" or struct.unpack_from("<H", data, pe+4)[0] != 0x8664:
        raise RuntimeError("unexpected non-AMD64 output")
    shutil.copyfile(dll, artifact / dll.name)
    for parent, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in (".git", "out", "ideck-elf-artifact", "llvm-build")]
        for name in files:
            if name.startswith(("LICENSE", "COPYING", "NOTICE")) and not Path(parent, name).is_symlink():
                source = Path(parent, name)
                destination = artifact / "notices" / source.relative_to(root)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
    shutil.copyfile(root / "ideck-elf-source.json", artifact / "source.json")
    shutil.copyfile(output / "args.gn", artifact / "args.gn")
    for name in ("prepare.py", "cef_glue.py", "build.py", "load-probe.c", "owned-contract.h", "CMakeLists.txt", "README.md"):
        shutil.copyfile(probe_source / name, artifact / name)
    for name in ("LICENSE", "LICENSE-EXCEPTION.md"):
        shutil.copyfile(probe_source.parents[1] / name, artifact / ("IDeck-" + name))
    (artifact / "validation.json").write_text(json.dumps({
        "pe_machine": "0x8664", "sha256": hashlib.sha256(data).hexdigest(),
        "windows_load_va_and_15_exports": "passed", "ios": "not tested",
        "cef_crash_glue": cef_glue, "windows_render_child_load": "passed" if cef_glue else "not tested",
        "steam_ui": "not tested", "product_release": False}, indent=2) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("checkout", type=Path)
    build(p.parse_args().checkout.resolve())
