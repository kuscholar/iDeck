#!/usr/bin/env python3
"""Build the real standalone handler and require an own-process Windows dump.

SPDX-License-Identifier: GPL-3.0-or-later
Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys
import urllib.request
import zipfile

from prepare import CRASHPAD, CEF

GN_REVISION = "5e19d2fb166fbd4f6f32147fbb2f497091a54ad8"


def run(command, root, log, timeout=900):
    result = subprocess.run(command, cwd=root, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=timeout)
    with log.open("ab") as output:
        output.write(result.stdout)
    print(result.stdout.decode(errors="replace")[-5000:], flush=True)
    if result.returncode:
        raise subprocess.CalledProcessError(result.returncode, command)
    return result.stdout.decode(errors="replace")


def amd64_pe(path):
    data = path.read_bytes()
    if len(data) < 64 or data[:2] != b"MZ":
        raise ValueError("missing PE image")
    pe = struct.unpack_from("<I", data, 0x3c)[0]
    if pe + 6 > len(data) or data[pe:pe + 4] != b"PE\0\0" or struct.unpack_from("<H", data, pe + 4)[0] != 0x8664:
        raise ValueError("handler is not AMD64 PE")
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "machine": "0x8664"}


def build(root, host_compile=False):
    windows = sys.platform == "win32"
    if not windows and not (host_compile and sys.platform == "darwin"):
        raise RuntimeError("use official Windows MSVC/SDK, or explicit Mac compile-only discriminator")
    source = json.loads((root / "ideck-crashpad-source.json").read_text())
    if source["crashpad_revision"] != CRASHPAD or source["cef_revision"] != CEF:
        raise ValueError("wrong source manifest")
    cpu = "x64" if windows or platform.machine() == "x86_64" else "arm64"
    package_platform = "windows-amd64" if windows else ("mac-amd64" if cpu == "x64" else "mac-arm64")
    url = "https://chrome-infra-packages.appspot.com/dl/gn/gn/" + package_platform + "/+/git_revision:" + GN_REVISION
    with urllib.request.urlopen(url, timeout=60) as response:
        package = response.read(40 * 1024 * 1024 + 1)
    if len(package) > 40 * 1024 * 1024:
        raise ValueError("oversized GN package")
    gn = root / ("ideck-gn.exe" if windows else "ideck-gn")
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        gn.write_bytes(archive.read("gn.exe" if windows else "gn"))
    gn.chmod(0o755)
    log = root / "ideck-crashpad-build.log"
    version = run([str(gn), "--version"], root, log, timeout=15).strip()
    if GN_REVISION[:7] not in version:
        raise ValueError("GN binary does not report requested upstream revision")
    output = root / "out/ideck-crashpad"
    output.mkdir(parents=True, exist_ok=True)
    args = 'is_debug = false\ncrashpad_dependencies = "standalone"\ntarget_cpu = "' + cpu + '"\n'
    if not windows:
        args += 'mac_deployment_target = "14.0"\n'
        # This old public revision uses APIs newly deprecated by the local SDK.
        # Keep the warnings visible; change no runtime checks or Windows flags.
        args += 'extra_cflags = "-Wno-error=deprecated-declarations"\n'
    (output / "args.gn").write_text(args)
    run([str(gn), "gen", str(output)], root, log)
    deps = run([str(gn), "desc", str(output), "//handler:crashpad_handler", "deps", "--all"], root, log)
    if any("partition_alloc" in line or line.strip().startswith("//base:")
           or line.strip().startswith("//base/") for line in deps.splitlines()):
        raise ValueError("standalone handler unexpectedly pulls full Chromium allocator/base")
    run(["ninja", "-C", str(output), "crashpad_handler", "crashpad_smoke", "-j", "3"], root, log)
    if not windows:
        (root / "ideck-crashpad-host-compile.json").write_text(json.dumps({
            "host": "macOS", "result": "compiled real handler and own smoke", "windows_ipc": "not tested",
            "ios": "not tested", "gn_revision": GN_REVISION, "gn_sha256": hashlib.sha256(gn.read_bytes()).hexdigest()}, indent=2) + "\n")
        return

    handler, smoke = output / "crashpad_handler.exe", output / "crashpad_smoke.exe"
    images = {p.name: amd64_pe(p) for p in (handler, smoke)}
    # Fresh own database, no Valve process, credentials or external uploads.
    database = root / "ideck-own-crash-database"
    if database.exists():
        raise ValueError("refuse stale minidumps: use a fresh build/test directory")
    database.mkdir()
    receipt = run([str(smoke), str(handler), str(database)], root, log, timeout=60)
    if "handler_registration=PASS" not in receipt or "real_local_minidump=PASS" not in receipt:
        raise ValueError("real handler registration and local dump not both proved")
    artifact = root / "ideck-crashpad-artifact"
    artifact.mkdir()
    for p in (handler, smoke):
        shutil.copyfile(p, artifact / p.name)
    # Never upload raw dumps: only categorical own-test evidence and sources.
    (artifact / "validation.json").write_text(json.dumps({
        "images": images, "windows_registration": "passed", "windows_real_minidump": "passed",
        "own_test_upload_url": "empty", "full_chromium_base_in_graph": False,
        "ios": "not tested", "steam_ui": "not tested", "gn_revision": GN_REVISION,
        "gn_sha256": hashlib.sha256(gn.read_bytes()).hexdigest()}, indent=2) + "\n")
    (artifact / "dependencies.txt").write_text(deps)
    shutil.copyfile(root / "ideck-crashpad-source.json", artifact / "source.json")
    shutil.copyfile(root / "ideck-cef-crashpad.patch", artifact / "cef-upstream.patch")
    shutil.copyfile(output / "args.gn", artifact / "args.gn")
    here = Path(__file__).resolve().parent
    for p in here.iterdir():
        if p.is_file():
            shutil.copyfile(p, artifact / p.name)
    for parent, dirs, files in __import__("os").walk(root):
        dirs[:] = [d for d in dirs if d not in (".git", "out", artifact.name, database.name)]
        for name in files:
            if name.startswith(("LICENSE", "COPYING", "NOTICE")):
                p = Path(parent, name)
                if not p.is_symlink():
                    target = artifact / "notices" / p.relative_to(root)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(p, target)
    for name in ("LICENSE", "LICENSE-EXCEPTION.md"):
        shutil.copyfile(here.parents[2] / name, artifact / ("iDeck-" + name))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--host-compile", action="store_true")
    args = parser.parse_args()
    build(args.checkout.resolve(), args.host_compile)
