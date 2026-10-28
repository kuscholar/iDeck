#!/usr/bin/env python3
"""Build only chrome_elf in the prepared disposable Windows source tree.

SPDX-License-Identifier: GPL-3.0-or-later
Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""
import argparse
from pathlib import Path
import re
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
            if not match:
                raise subprocess.CalledProcessError(result.returncode, command)
            target = cwd / match.group(1)
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


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("checkout", type=Path)
    build(p.parse_args().checkout.resolve())
