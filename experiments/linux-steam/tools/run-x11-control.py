#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Host control on a stopped, unauthenticated private fakefs, never production.

The wrapper refuses recognizable Steam login state without reading its contents.
This is a guard, not proof that a caller-selected root contains no secrets. The
caller must use a fresh experiment root and check for other active Linux tasks.
The output directory must be new; raw logs/images/passwords remain outside Git.
"""
import argparse
import fcntl
import json
from pathlib import Path
import subprocess
import time

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("ish", type=Path)
p.add_argument("root", type=Path)
p.add_argument("output", type=Path)
p.add_argument("--steam", action="store_true")
p.add_argument("--seconds",type=int,default=90,help="bounded guest observation, 1..600 seconds")
a = p.parse_args()
if not 1<=a.seconds<=600: p.error("observation must be between1 and600 seconds")
ish, root, output = a.ish.resolve(), a.root.resolve(), a.output.resolve()
if not (root / "data").is_dir() or not (root / "meta.db").is_file():
    p.error("prepared stopped fakefs required")
if output.exists():
    p.error("output directory must be new")
for location in ["Steam/config/loginusers.vdf", "root/.steam/config/loginusers.vdf"]:
    if (root / "data" / location).exists():
        p.error("refusing recognizable Steam account configuration; use an unauthenticated control root")
with (root / ".ideck-x11-observer.lock").open("a") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    output.mkdir(parents=True)
    script = (Path(__file__).parents[1] / "guest/x11-control.sh").read_text()
    command = [str(ish), "-f", str(root), "/bin/sh", "-c", script, "ideck-x11-control", "--steam" if a.steam else "--display-only",str(a.seconds)]
    start = time.monotonic()
    with (output / "host.log").open("wb") as log:
        child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            rc = child.wait(timeout=a.seconds+50)
            outcome = "exited"
        except subprocess.TimeoutExpired:
            outcome = "bounded-observer-terminated"
            child.terminate()
            try:
                rc = child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                rc = child.wait()
    for name in ["ideck-steam-x11.log", "ideck-xvfb.log", "ideck-x11vnc.log"]:
        source = root / "data/tmp" / name
        if source.is_file():
            with source.open("rb") as log:
                log.seek(0, 2)
                size = log.tell()
                log.seek(max(0, size - 1024 * 1024))
                (output / name).write_bytes(log.read(1024 * 1024))
    report = dict(scope="host ARM64 Linux interpreter; actual X11/VNC, not iPad", display_session_returncode=rc,
                  outcome=outcome, elapsed_seconds=round(time.monotonic()-start, 3),
                  steam_requested=a.steam,requested_seconds=a.seconds, steam_ui="UNVERIFIED; inspect real frame and guest log")
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
