#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Apply the recorded GPL LinuxRunner patch ONLY to generated private build inputs."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source", type=Path)
parser.add_argument("build", type=Path)
args = parser.parse_args()
source, build = args.source.resolve(), args.build.resolve()
pin = "d1419782da2e299fe22f1ddb85c70ae3d1e276b1"
assert subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip() == pin
original = subprocess.check_output(["git", "-C", str(source), "show", pin + ":fs/generic.c"])
assert (source / "fs/generic.c").read_bytes() == original
stage = build / "ideck-dirfd-overlay"
(stage / "fs").mkdir(parents=True, exist_ok=True)
(stage / "fs/generic.c").write_bytes(original)
patch = Path(__file__).parents[1] / "patches/linuxrunner-dirfd.patch"
subprocess.run(["/usr/bin/patch", "--batch", "-p1", "-i", str(patch.resolve())], cwd=stage, check=True)
entries = json.loads((build / "compile_commands.json").read_text())
entry = next(e for e in entries if e["file"].endswith("/fs/generic.c"))
command = shlex.split(entry["command"])
command[command.index(entry["file"])] = str(stage / "fs/generic.c")
command[command.index("-o") + 1] = str(stage / "fs_generic.c.o")
for flag, value in (("-MF", str(stage / "generic.d")), ("-MQ", str(stage / "fs_generic.c.o"))):
    if flag in command:
        command[command.index(flag) + 1] = value
subprocess.run(command, cwd=entry["directory"], check=True)
# Undo the earlier broad v1 path overlay when reusing its private build directory.
subprocess.run(["xcrun", "ar", "r", str(build / "libish.a"), str(build / "libish.a.p/fs_path.c.o"), str(stage / "fs_generic.c.o")], check=True)
print("dirfd guard overlaid in generated libish.a; vendor source and assertion retained")
