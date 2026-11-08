#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Build a separate host diagnostic binary; never change vendor or base archive.

Only bounded pipe2 flags/status/PID are logged; syscall behavior is unchanged.
Run only in the unauthenticated Lab root. No user buffers, paths or tokens.
"""
import argparse
import json
from pathlib import Path
import shlex
import shutil
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("source", type=Path)
p.add_argument("build", type=Path)
p.add_argument("ninja", type=Path)
p.add_argument("output", type=Path)
a = p.parse_args()
src, build, output = a.source.resolve(), a.build.resolve(), a.output.resolve()
pin = "d1419782da2e299fe22f1ddb85c70ae3d1e276b1"
assert subprocess.check_output(["git", "-C", str(src), "rev-parse", "HEAD"], text=True).strip() == pin
original = subprocess.check_output(["git", "-C", str(src), "show", pin + ":fs/pipe.c"])
assert (src / "fs/pipe.c").read_bytes() == original
output.mkdir(parents=True, exist_ok=False)
body = original.decode().replace("int_t sys_pipe2(addr_t pipe_addr, int_t flags) {", "static int_t ideck_original_pipe2(addr_t pipe_addr, int_t flags) {")
assert body != original.decode()
body += '''
int_t sys_pipe2(addr_t pipe_addr, int_t flags) {
    int_t result = ideck_original_pipe2(pipe_addr, flags);
    static atomic_uint observations;
    if (atomic_fetch_add(&observations, 1) < 64)
        printk("IDECK_PIPE2_OBSERVER flags=%#x status=%d guest_pid=%d\\n", flags, result, current->tgid);
    return result;
}
'''
generated = output / "pipe.c"
generated.write_text(body)
entries = json.loads((build / "compile_commands.json").read_text())
entry = next(e for e in entries if e["file"].endswith("/fs/pipe.c"))
command = shlex.split(entry["command"])
command[command.index(entry["file"])] = str(generated)
obj = output / "fs_pipe.c.o"
command[command.index("-o") + 1] = str(obj)
for flag, value in [("-MF", output / "pipe.d"), ("-MQ", obj)]:
    if flag in command:
        command[command.index(flag) + 1] = str(value)
subprocess.run(command, cwd=entry["directory"], check=True)
archive = output / "libish.a"
shutil.copy2(build / "libish.a", archive)
subprocess.run(["xcrun", "ar", "r", str(archive), str(obj)], check=True)
link = subprocess.check_output([str(a.ninja.resolve()), "-C", str(build), "-t", "commands", "ish"], text=True).splitlines()[-1]
command = shlex.split(link)
command[command.index("-o") + 1] = str(output / "ish-pipe-observer")
command[command.index("libish.a")] = str(archive)
subprocess.run(command, cwd=build, check=True)
print("Separate host pipe observer built; original syscall/archives/vendor unchanged")
