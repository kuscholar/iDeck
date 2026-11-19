#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Reuse LinuxRunner lazy reservations for the observed glibc stack request."""

import argparse
import hashlib
import json
import shlex
import shutil
import subprocess
from pathlib import Path

PIN = "d1419782da2e299fe22f1ddb85c70ae3d1e276b1"


def replace_once(source, before, after):
    if source.count(before) != 1:
        raise ValueError("Pinned mmap control flow changed")
    return source.replace(before, after, 1)


def patch(source):
    source = replace_once(
        source, "static addr_t do_mmap(",
        """/* Aggregate counters only. No guest addresses or arguments leave this unit. */
_Atomic uint64_t ideck_stack_map_requests, ideck_stack_map_reserved;
_Atomic uint64_t ideck_stack_map_no_hole, ideck_stack_map_metadata_failures;

static addr_t do_mmap(""")
    source = replace_once(
        source, "    page_t page;\n    bool caller_hint_used",
        """    /* Linux MAP_STACK is 0x20000. Limit this experiment to the exact
     * observed 4 MiB stack plus 64 KiB guard request from glibc. Use the
     * same address selection, protection and page accounting as lazy VMAs. */
    const dword_t linux_map_stack = 0x20000;
    const bool lazy_stack = addr == 0 && len == 0x410000 && prot == 0 &&
            flags == (MMAP_PRIVATE | MMAP_ANONYMOUS | linux_map_stack) &&
            fd_no == -1 && offset == 0;
    if (lazy_stack)
        atomic_fetch_add_explicit(&ideck_stack_map_requests, 1, memory_order_relaxed);
    page_t page;
    bool caller_hint_used""")
    source = replace_once(
        source, "        if (page == BAD_PAGE) {",
        """        if (page == BAD_PAGE) {
            if (lazy_stack)
                atomic_fetch_add_explicit(&ideck_stack_map_no_hole, 1, memory_order_relaxed);""")
    source = replace_once(
        source, "(pages >= 0x10000 || (!(prot & P_RWX) && pages >= 0x1000)))",
        "(lazy_stack || pages >= 0x10000 || (!(prot & P_RWX) && pages >= 0x1000)))")
    source = replace_once(
        source, """            if ((err = pt_map_lazy(current->mem, page, pages, prot)) < 0)
                return err;""",
        """            err = pt_map_lazy(current->mem, page, pages, prot);
            if (lazy_stack) {
                if (err < 0)
                    atomic_fetch_add_explicit(&ideck_stack_map_metadata_failures, 1, memory_order_relaxed);
                else
                    atomic_fetch_add_explicit(&ideck_stack_map_reserved, 1, memory_order_relaxed);
            }
            if (err < 0)
                return err;""")
    return source


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("vendor", "build", "archive", "mmap_source", "output"):
        p.add_argument(name, type=Path)
    p.add_argument("--sanitize", action="store_true", help="Host ASan/UBSan build")
    a = p.parse_args()
    vendor, build, archive, source, out = (
        getattr(a, name).resolve() for name in ("vendor", "build", "archive", "mmap_source", "output"))
    assert all(str(path).startswith("/Volumes/easystore/") for path in (build, archive, source, out))
    assert not out.exists() and not source.is_relative_to(vendor)
    assert subprocess.check_output(["git", "-C", vendor, "rev-parse", "HEAD"], text=True).strip() == PIN
    assert not subprocess.check_output(["git", "-C", vendor, "status", "--porcelain", "--untracked-files=no"], text=True).strip()
    entries = json.loads((build / "compile_commands.json").read_text())
    entry, = (e for e in entries if e["file"].endswith("/kernel/mmap.c"))
    cmd = shlex.split(entry["command"])
    member = Path(cmd[cmd.index("-o") + 1]).name
    assert subprocess.check_output(["xcrun", "ar", "t", archive], text=True).splitlines().count(member) == 1
    body = patch(source.read_text())
    out.mkdir(mode=0o700)
    generated, obj = out / "mmap.c", out / member
    generated.write_text(body)
    cmd[cmd.index(entry["file"])] = str(generated)
    cmd[cmd.index("-o") + 1] = str(obj)
    for key, value in (("-MF", out / "mmap.d"), ("-MQ", obj)):
        if key in cmd:
            cmd[cmd.index(key) + 1] = str(value)
    cmd += ["-I", str(source.parent), "-I", str(Path(__file__).resolve().parents[1] / "app")]
    if a.sanitize:
        assert not any("iphoneos" in arg.lower() or "-apple-ios" in arg.lower() for arg in cmd)
        cmd += ["-fsanitize=address,undefined", "-fno-sanitize-recover=all"]
    subprocess.run(cmd, cwd=entry["directory"], check=True)
    before = sha(archive)
    target = out / "libish.a"
    shutil.copy2(archive, target)
    subprocess.run(["xcrun", "ar", "r", target, obj], check=True)
    assert sha(archive) == before
    (out / "evidence.json").write_text(json.dumps({
        "linuxrunner": PIN, "base_archive_sha256": before,
        "input_mmap_sha256": sha(source), "generated_mmap_sha256": sha(generated),
        "object_sha256": sha(obj), "archive_sha256": sha(target),
        "builder_sha256": sha(Path(__file__)), "command": cmd,
        "scope": "One private anonymous PROT_NONE MAP_STACK shape via existing lazy VMA"
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
