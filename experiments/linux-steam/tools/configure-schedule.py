#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Generate a user LaunchAgent using only official CLI commands at dispatch.

No background external Python script, credential extraction, database editing,
permission change or remote-control enablement. The CLI's writer lock serializes
research in the existing thread. The researcher stops the job after real evidence.
"""
import argparse
from pathlib import Path
import plistlib
import uuid

LABEL = "com.kusch.ideck-linux-steam-ipad-305m"
START = 'cli="$1"; shift; "$cli" app-server daemon start || exit $?; exec "$cli" queue "$@"'


def launch_agent(cli, thread, project, prompt, logs):
    uuid.UUID(thread)
    if not all(Path(p).is_absolute() for p in [cli, project, logs]):
        raise ValueError("CLI, project and logs must be absolute")
    return dict(Label=LABEL, ProgramArguments=["/bin/sh", "-c", START, LABEL, str(cli),
                "--thread", thread, "--message", prompt, "--resume", "--cd", str(project)],
                StartInterval=18300,RunAtLoad=False,ProcessType="Background",
                StandardOutPath=str(Path(logs)/"out.log"),StandardErrorPath=str(Path(logs)/"err.log"))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cli", required=True)
    p.add_argument("--thread", required=True)
    p.add_argument("--project", required=True)
    p.add_argument("--prompt", required=True, type=Path)
    p.add_argument("--logs", required=True)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    value = launch_agent(args.cli,args.thread,args.project,args.prompt.read_text(),args.logs)
    args.output.write_bytes(plistlib.dumps(value))
    print("LaunchAgent generated. Load/read back with launchctl; registration alone is not execution proof.")


if __name__ == "__main__": main()
