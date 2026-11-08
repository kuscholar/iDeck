#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Host acquisition control; not the future in-app Steam installer.

Official manifests supply package hashes over HTTPS, not signed trust metadata.
No login data is read. Extract only into a new, private staging directory.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import urllib.request
import zipfile

CDN = "https://client-update.steamstatic.com/"
MAX_PACKAGE = 512 * 1024 * 1024


class OfficialRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not newurl.startswith(CDN):
            raise ValueError("non-official redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = urllib.request.build_opener(OfficialRedirects)


def packages(text):
    if len(text.encode()) > 1024 * 1024:
        raise ValueError("manifest too large")
    found = []
    for block, body in re.findall(r'"([^"\n]+)"\s*\{([^{}]+)\}', text):
        if not (block.endswith("_all") or block.endswith("_linuxarm64_linuxarm64")):
            continue
        pairs = re.findall(r'"([^"\n]+)"\s+"([^"\n]*)"', body)
        values = dict(pairs)
        if len(values) != len(pairs):
            raise ValueError("duplicate package field")
        filename, digest = values["file"], values["sha2"]
        size = int(values["size"])
        if not re.fullmatch(r"[a-zA-Z0-9_.-]+", filename) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("invalid package identity")
        if not 0 < size <= MAX_PACKAGE:
            raise ValueError("package size outside limit")
        found.append(dict(block=block, file=filename, sha256=digest, size=size))
    if not any(p["block"].endswith("_linuxarm64_linuxarm64") for p in found):
        raise ValueError("no ARM64 Linux packages")
    if len(found) > 128 or len({p["file"] for p in found}) != len(found):
        raise ValueError("duplicate or excessive packages")
    return sorted(found, key=lambda p: p["block"])


def acquire(package, cache):
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / package["file"]
    partial = target.with_name(target.name + ".partial")
    def verified(path):
        if not path.exists() or path.stat().st_size != package["size"]:
            return False
        with path.open("rb") as f:
            digest = hashlib.sha256()
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)
            return digest.hexdigest() == package["sha256"]
    if verified(target):
        return target
    offset = partial.stat().st_size if partial.exists() else 0
    if offset > package["size"]:
        raise ValueError("partial exceeds manifest size")
    if offset == package["size"]:
        if not verified(partial):
            partial.unlink()
            raise ValueError("cached checksum mismatch; retry will refetch")
    else:
        request = urllib.request.Request(CDN + package["file"], headers={"Range": f"bytes={offset}-"} if offset else {})
        with OPENER.open(request, timeout=60) as response:
            if response.status == 206:
                content_range = response.headers.get("Content-Range", "")
                if not re.fullmatch(rf"bytes {offset}-[0-9]+/{package['size']}", content_range):
                    raise ValueError("range response does not match request")
            elif response.status == 200:
                offset = 0
            else:
                raise ValueError("unexpected download status")
            with partial.open("ab" if offset else "wb") as output:
                received = offset
                while chunk := response.read(1024 * 1024):
                    received += len(chunk)
                    if received > package["size"]:
                        raise ValueError("download exceeds manifest size")
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
        if not verified(partial):
            if partial.stat().st_size == package["size"]:
                partial.unlink()
            raise ValueError("download incomplete or checksum mismatch")
    partial.replace(target)
    return target


def extract_verified(archive, destination):
    if destination.exists():
        raise ValueError("staging destination already exists")
    root = destination.resolve()
    total, seen, links, regular = 0, set(), [], set()
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        if len(infos) > 100000:
            raise ValueError("too many ZIP members")
        for item in infos:
            path = PurePosixPath(item.filename.replace("\\", "/"))
            if path.is_absolute() or ".." in path.parts or not path.parts or ":" in item.filename:
                raise ValueError("unsafe ZIP path")
            mode = item.external_attr >> 16
            if item.flag_bits & 1:
                raise ValueError("encrypted ZIP member")
            normalized = str(path).casefold()
            if normalized in seen:
                raise ValueError("duplicate ZIP member")
            seen.add(normalized)
            if stat.S_ISLNK(mode):
                if item.file_size > 4096:
                    raise ValueError("symlink too long")
                value = z.read(item).decode("utf-8")
                target = PurePosixPath(value)
                if not value or target.is_absolute() or "\\" in value or ":" in value or any(ord(c) < 32 for c in value):
                    raise ValueError("unsafe symlink target")
                resolved = list(path.parent.parts)
                for component in target.parts:
                    if component == "..":
                        if not resolved: raise ValueError("symlink escapes package")
                        resolved.pop()
                    elif component != ".":
                        resolved.append(component)
                links.append((path, value, "/".join(resolved)))
            elif not item.is_dir():
                regular.add(str(path))
            total += item.file_size
            if total > 2 * 1024**3 or item.file_size > MAX_PACKAGE:
                raise ValueError("expanded ZIP too large")
        if any(target not in regular for _, _, target in links):
            raise ValueError("symlink must refer to a regular member of the same package")
        link_names = {str(path) for path, _, _ in links}
        if any(str(parent) in link_names for item in infos for parent in PurePosixPath(item.filename.replace("\\", "/")).parents):
            raise ValueError("member nested through symlink")
        destination.mkdir(parents=True, exist_ok=False)
        for item in infos:
            path = root.joinpath(*PurePosixPath(item.filename.replace("\\", "/")).parts)
            if stat.S_ISLNK(item.external_attr >> 16):
                continue
            if item.is_dir():
                path.mkdir(parents=True, exist_ok=True)
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            with z.open(item) as source, path.open("xb") as output:
                while chunk := source.read(1024 * 1024):
                    output.write(chunk)
            path.chmod(0o700 if (item.external_attr >> 16) & 0o111 else 0o600)
        for path, value, _ in links:
            target = root.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--block", help="Acquire one exact platform block only")
    parser.add_argument("--extract", type=Path, help="New private staging directory")
    args = parser.parse_args()
    selected = packages(args.manifest.read_text())
    if args.block:
        selected = [p for p in selected if p["block"] == args.block]
        if len(selected) != 1:
            parser.error("block not found")
    print(json.dumps(selected, indent=2))
    if args.cache:
        for p in selected:
            archive = acquire(p, args.cache)
            if args.extract:
                extract_verified(archive, args.extract / p["block"])


if __name__ == "__main__":
    main()
