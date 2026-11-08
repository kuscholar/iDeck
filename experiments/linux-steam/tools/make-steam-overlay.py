#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Create a guest-only tar from already verified, newly extracted Valve parts.

Never unpack this with a host tar into an existing root. Import it through the
LinuxRunner guest/fakefs. No account/config/login data is taken from another app.
"""
import argparse
import hashlib
import io
from pathlib import Path
import stat
import tarfile
from steam_packages import packages

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("manifest", type=Path)
p.add_argument("parts", type=Path)
p.add_argument("output", type=Path)
args = p.parse_args()
if args.output.exists(): p.error("output must be new")
seen = {"Steam": ("dir",)}
partial = args.output.with_suffix(args.output.suffix + ".partial")
with tarfile.open(partial, "w:gz", compresslevel=1) as tar:
    root_info = tarfile.TarInfo("Steam")
    root_info.type = tarfile.DIRTYPE; root_info.mode = 0o755
    root_info.uid = root_info.gid = root_info.mtime = 0
    tar.addfile(root_info)
    for package in packages(args.manifest.read_text()):
        component = args.parts / package["block"]
        if not component.is_dir(): raise ValueError("missing verified component")
        root = component.resolve()
        for source in sorted(component.rglob("*")):
            relative = source.relative_to(component)
            name = "Steam/" + relative.as_posix()
            info = tarfile.TarInfo(name)
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = "root"
            if source.is_symlink():
                target = source.readlink()
                try: source.resolve(strict=True).relative_to(root)
                except ValueError: raise ValueError("source link escapes its verified component")
                if not source.resolve().is_file(): raise ValueError("link must point to a regular member")
                info.type = tarfile.SYMTYPE; info.linkname = str(target); info.mode = 0o777
                identity = ("link", str(target))
            elif source.is_dir():
                info.type = tarfile.DIRTYPE; info.mode = 0o755
                identity = ("dir",)
            elif source.is_file():
                with source.open("rb") as stream:
                    header = stream.read(4); digest = hashlib.sha256(header)
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""): digest.update(chunk)
                info.size = source.stat().st_size
                info.mode = 0o755 if header == b"\x7fELF" or source.suffix == ".sh" else 0o644
                identity = ("file", digest.hexdigest())
            else:
                raise ValueError("unsupported verified file type")
            if name in seen:
                if seen[name] != identity: raise ValueError("conflicting component content: " + name)
                continue
            seen[name] = identity
            if info.isreg():
                with source.open("rb") as stream: tar.addfile(info, stream)
            else: tar.addfile(info)
    def directory(name):
        if name in seen: return
        info = tarfile.TarInfo(name);info.type=tarfile.DIRTYPE;info.mode=0o700;tar.addfile(info)
        seen[name] = ("dir",)
    directory("Steam/package");directory("root");directory("root/.steam")
    data = b"steamdeck_stable\n"
    info = tarfile.TarInfo("Steam/package/beta");info.size=len(data);info.mode=0o600
    tar.addfile(info, io.BytesIO(data))
    for name,target in [("root/.steam/steam","/Steam"),("root/.steam/root","/Steam"),
                        ("root/.steam/bin64","/Steam/steamrtarm64"),("root/.steam/binarm64","/Steam/steamrtarm64"),
                        ("root/.steam/sdkarm64","/Steam/linuxarm64"),("Steam/steamrtarm32","steamrtarm64")]:
        if name in seen: raise ValueError("unexpected client link collision")
        info=tarfile.TarInfo(name);info.type=tarfile.SYMTYPE;info.mode=0o777;info.linkname=target;tar.addfile(info)
partial.replace(args.output)
print("Guest-only Steam overlay written; component members:", len(seen))
