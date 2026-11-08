#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Opt-in private archive overlay: real guest socket identities and TCP view.

Requires a pristine pinned vendor, an existing (possibly packet-enabled) copied
archive, and a NEW output. Does not change the vendor or any input archive.
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
p.add_argument("archive", type=Path)
p.add_argument("ninja", type=Path)
p.add_argument("output", type=Path)
p.add_argument("--sanitize", action="store_true")
p.add_argument("--archive-only", action="store_true")
a = p.parse_args()
source, build, archive, output = [x.resolve() for x in (a.source, a.build, a.archive, a.output)]
pin = "d1419782da2e299fe22f1ddb85c70ae3d1e276b1"
assert subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip() == pin
assert not subprocess.check_output(["git", "-C", str(source), "status", "--porcelain", "--untracked-files=no"], text=True).strip()
assert not output.exists()
output.mkdir(parents=True)
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
input_hash = digest(archive)
snapshot = output / "LinuxProcTCP.c"
shutil.copy2(Path(__file__).parents[1] / "app/LinuxProcTCP.c", snapshot)
entries = json.loads((build / "compile_commands.json").read_text())
generated_hashes = {}
for name in ("fs/sock.c", "fs/proc/net.c", "fs/proc/pid.c"):
    original = subprocess.check_output(["git", "-C", str(source), "show", pin + ":" + name])
    assert (source / name).read_bytes() == original
    body = original.decode()
    if name == "fs/sock.c":
        before = "    fd->stat.mode = S_IFSOCK | 0666;\n    fd->real_fd = sock_fd;"
        after = """    fd->stat.mode = S_IFSOCK | 0666;
    /* Stable open-description identity, shared by dup/fork and never a host PID. */
    static atomic_ullong ideck_socket_inode = (1ULL << 40);
    fd->stat.inode = atomic_fetch_add(&ideck_socket_inode, 1);
    fd->stat.uid = current->euid;
    fd->stat.gid = current->egid;
    fd->stat.nlink = 1;
    fd->real_fd = sock_fd;"""
    elif name == "fs/proc/net.c":
        before = "struct proc_children proc_net_children = PROC_CHILDREN({"
        after = '#include ' + json.dumps(str(snapshot)) + '\n' + before + '\n    {"tcp", .show = ideck_proc_tcp4},\n    {"tcp6", .show = ideck_proc_tcp6},'
    else:
        before = "struct proc_children proc_pid_children = PROC_CHILDREN({"
        after = "extern struct proc_children proc_net_children;\n" + before + '\n    {"net", S_IFDIR, .children = &proc_net_children},'
    assert body.count(before) == 1
    body = body.replace(before, after)
    generated = output / name.replace("/", "_")
    generated.write_text(body)
    generated_hashes[name] = digest(generated)
    entry = next(e for e in entries if e["file"].endswith("/" + name))
    command = shlex.split(entry["command"])
    command[command.index(entry["file"])] = str(generated)
    obj = output / (name.replace("/", "_") + ".o")
    command[command.index("-o") + 1] = str(obj)
    for flag, value in (("-MF", output / (obj.name + ".d")), ("-MQ", obj)):
        if flag in command: command[command.index(flag) + 1] = str(value)
    # The inherited sock/pid units already emit warnings with this SDK. Keep
    # those visible; enforce Werror for the new TCP implementation/net unit.
    if name == "fs/proc/net.c": command += ["-Werror"]
    if a.sanitize: command += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
    subprocess.run(command, cwd=entry["directory"], check=True)
copied = output / "libish.a"
shutil.copy2(archive, copied)
for obj in output.glob("*.c.o"):
    subprocess.run(["xcrun", "ar", "r", str(copied), str(obj)], check=True)
assert digest(archive) == input_hash
receipt = dict(linuxrunner=pin, scope="opt-in guest-owned TCP snapshot only", sanitized_changed_units=a.sanitize,
               input_archive_sha256=input_hash, input_unchanged=True, generated=generated_hashes,
               tcp_source_sha256=digest(snapshot), archive_sha256=digest(copied))
if not a.archive_only:
    link = subprocess.check_output([str(a.ninja.resolve()), "-C", str(build), "-t", "commands", "ish"], text=True).splitlines()[-1]
    command = shlex.split(link)
    command[command.index("-o") + 1] = str(output / "ish-tcp-view")
    command[command.index("libish.a")] = str(copied)
    if a.sanitize: command += ["-fsanitize=address,undefined"]
    subprocess.run(command, cwd=build, check=True)
    receipt["binary_sha256"] = digest(output / "ish-tcp-view")
(output / "build-evidence.json").write_text(json.dumps(receipt, indent=2) + "\n")
print("Built isolated TCP view; input archive/vendor unchanged. No device or UI claim.")
