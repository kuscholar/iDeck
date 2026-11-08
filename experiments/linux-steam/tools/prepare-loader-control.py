#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Prepare a NEW sparse, unauthenticated HOST loader fixture, not a distro install."""
import argparse
import hashlib
from pathlib import Path
import re
import shutil
import tarfile
import tempfile
import urllib.request
from steam_packages import acquire, extract_verified, packages

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("manifest", type=Path)
parser.add_argument("artifacts", type=Path)
parser.add_argument("root", type=Path)
parser.add_argument("--use-host-dns", action="store_true", help="Copy host nameservers into this host-only fixture")
args = parser.parse_args()
manifest = args.manifest.read_text()
version = re.search(r'"version"\s+"([0-9]+)"', manifest)
if not version or version[1] != "1792618285":
    parser.error("unreviewed client snapshot; inspect it and record new evidence first")
if args.root.exists():
    parser.error("root must be NEW; never point this at an app/account root")
args.artifacts.mkdir(parents=True, exist_ok=True)
package = next(p for p in packages(manifest) if p["block"] == "bins_linuxarm64_linuxarm64")
archive = acquire(package, args.artifacts / "packages")
libc = args.artifacts / "libc6.deb"
expected = "8784eda966b189c777a384dac5ce009e8fc9b52d006926c5a013e7fa8aa688cc"
if not libc.exists():
    partial = libc.with_suffix(".deb.partial")
    url = "https://deb.debian.org/debian/pool/main/g/glibc/libc6_2.41-12+deb13u4_arm64.deb"
    # Download is small; trust only the pinned hash, regardless of CDN redirects.
    with urllib.request.urlopen(url, timeout=60) as response, partial.open("wb") as out:
        if response.geturl().split("/", 3)[:3] != ["https:", "", "deb.debian.org"]:
            raise ValueError("non-Debian redirect")
        size = 0
        while chunk := response.read(1024 * 1024):
            size += len(chunk)
            if size > 2483572: raise ValueError("Debian package exceeds pin")
            out.write(chunk)
    if partial.stat().st_size != 2483572 or hashlib.sha256(partial.read_bytes()).hexdigest() != expected:
        raise ValueError("Debian package checksum mismatch")
    partial.replace(libc)
if libc.stat().st_size != 2483572 or hashlib.sha256(libc.read_bytes()).hexdigest() != expected:
    raise ValueError("cached Debian package checksum mismatch")

import subprocess
with tempfile.TemporaryDirectory(prefix="loader-fixture-", dir=args.artifacts.resolve()) as tmp:
    stage = Path(tmp)
    extract_verified(archive, stage / "Steam")
    # ar extracts only this verified package's data member into owned temp storage.
    subprocess.run(["/usr/bin/ar", "x", str(libc.resolve()), "data.tar.xz"], cwd=stage, check=True)
    args.root.mkdir(parents=True, exist_ok=False)
    library = args.root / "lib/aarch64-linux-gnu"
    library.mkdir(parents=True)
    with tarfile.open(stage / "data.tar.xz") as tar:
        for member in tar:
            if not member.isfile() or not member.name.startswith("./usr/lib/aarch64-linux-gnu/") or "/gconv/" in member.name:
                continue
            target = library / Path(member.name).name
            if target.exists() or member.size > 32 * 1024 * 1024:
                raise ValueError("unexpected glibc library member")
            with tar.extractfile(member) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output)
            target.chmod(0o700)
    shutil.copy2(library / "ld-linux-aarch64.so.1", args.root / "lib/ld-linux-aarch64.so.1")
    shutil.copytree(stage / "Steam", args.root / "Steam", symlinks=True)
    (args.root / "Steam/steamrtarm64/steam").chmod(0o700)
    package_dir = args.root / "Steam/package"
    package_dir.mkdir(exist_ok=True)
    (package_dir / "beta").write_text("steamdeck_stable\n")
    if args.use_host_dns:
        lines = [line for line in Path("/etc/resolv.conf").read_text().splitlines() if line.strip().startswith("nameserver ")]
        if not lines: raise ValueError("no host resolver; no guessed substitute")
        (args.root / "etc").mkdir(exist_ok=True)
        (args.root / "etc/resolv.conf").write_text("\n".join(lines) + "\n")
print("Sparse loader root prepared; not a complete Steam installation or Linux distro")
