#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Build a separate host diagnostic binary; never change vendor or base archive.

Default mode changes no syscall behavior. Explicit --packet-pipes enables the
experimental adapter only in the copied output archive. Logs are bounded numeric
flags/status/PID. Use an unauthenticated Lab root; no buffers, paths or tokens.
"""
import argparse
import hashlib
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
p.add_argument("--packet-pipes", action="store_true", help="enable lab-only packet-at-creation adapter in this separate binary")
p.add_argument("--sanitize", action="store_true", help="instrument the changed host translation unit with ASan/UBSan")
p.add_argument("--archive-only", action="store_true", help="produce only the copied archive, including cross-compiled iOS builds")
a = p.parse_args()
src, build, output = a.source.resolve(), a.build.resolve(), a.output.resolve()
pin = "d1419782da2e299fe22f1ddb85c70ae3d1e276b1"
assert subprocess.check_output(["git", "-C", str(src), "rev-parse", "HEAD"], text=True).strip() == pin
assert not subprocess.check_output(["git","-C",str(src),"status","--porcelain","--untracked-files=no"],text=True).strip()
original = subprocess.check_output(["git", "-C", str(src), "show", pin + ":fs/pipe.c"])
assert (src / "fs/pipe.c").read_bytes() == original
output.mkdir(parents=True, exist_ok=False)
body = original.decode().replace("int_t sys_pipe2(addr_t pipe_addr, int_t flags) {", "static int_t ideck_original_pipe2(addr_t pipe_addr, int_t flags) {")
assert body != original.decode()
if a.packet_pipes:
    snapshot=output/'PacketPipe.c'
    shutil.copy2(Path(__file__).parents[1]/'app/PacketPipe.c',snapshot)
    body += '\n#include ' + json.dumps(str(snapshot)) + '\n'
body += '''
int_t sys_pipe2(addr_t pipe_addr, int_t flags) {
    int_t result = IDECK_DISPATCH_PIPE2;
    static atomic_uint observations;
    if (atomic_fetch_add(&observations, 1) < 64)
        printk("IDECK_PIPE2_OBSERVER flags=%#x status=%d guest_pid=%d\\n", flags, result, current->tgid);
    return result;
}
'''
body = body.replace("IDECK_DISPATCH_PIPE2", "(flags & O_DIRECT_) ? ideck_packet_pipe2(pipe_addr, flags) : ideck_original_pipe2(pipe_addr, flags)" if a.packet_pipes else "ideck_original_pipe2(pipe_addr, flags)")
if a.packet_pipes:
    body = body.replace("IDECK_PIPE2_OBSERVER", "IDECK_PACKET_PIPE_V3")
generated = output / "pipe.c"
generated.write_text(body)
entries = json.loads((build / "compile_commands.json").read_text())
entry = next(e for e in entries if e["file"].endswith("/fs/pipe.c"))
entry_source=Path(entry["file"])
if not entry_source.is_absolute(): entry_source=Path(entry["directory"])/entry_source
assert entry_source.read_bytes()==original
command = shlex.split(entry["command"])
if a.packet_pipes: command += ["-Werror"]
if a.sanitize: command += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
command[command.index(entry["file"])] = str(generated)
obj = output / "fs_pipe.c.o"
command[command.index("-o") + 1] = str(obj)
for flag, value in [("-MF", output / "pipe.d"), ("-MQ", obj)]:
    if flag in command:
        command[command.index(flag) + 1] = str(value)
subprocess.run(command, cwd=entry["directory"], check=True)
archive = output / "libish.a"
base_digest=hashlib.sha256((build/'libish.a').read_bytes()).hexdigest()
shutil.copy2(build / "libish.a", archive)
subprocess.run(["xcrun", "ar", "r", str(archive), str(obj)], check=True)
assert hashlib.sha256((build/'libish.a').read_bytes()).hexdigest()==base_digest
(output/'build-evidence.json').write_text(json.dumps(dict(linuxrunner=pin,packet_enabled=a.packet_pipes,
    sanitized=a.sanitize,base_archive_sha256=base_digest,base_archive_unchanged=True,
    generated_pipe_sha256=hashlib.sha256(generated.read_bytes()).hexdigest(),
    packet_source_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest() if a.packet_pipes else None,
    archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest()),indent=2)+'\n')
if a.archive_only:
    print("Private packet archive built; original archive/vendor unchanged")
    raise SystemExit(0)
link = subprocess.check_output([str(a.ninja.resolve()), "-C", str(build), "-t", "commands", "ish"], text=True).splitlines()[-1]
command = shlex.split(link)
if a.sanitize: command += ["-fsanitize=address,undefined"]
command[command.index("-o") + 1] = str(output / "ish-pipe-observer")
command[command.index("libish.a")] = str(archive)
subprocess.run(command, cwd=build, check=True)
print("Separate host packet adapter built; stream path/base archives/vendor unchanged" if a.packet_pipes else "Separate host pipe observer built; original syscall/archives/vendor unchanged")
