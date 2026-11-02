#!/usr/bin/env python3
"""Explicit LLVM-MinGW cross-tool adapter; no reporting/runtime stubs.

SPDX-License-Identifier: GPL-3.0-or-later
Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""
from pathlib import Path
import subprocess
import sys


def main():
    directory, mode, *arguments = sys.argv[1:]
    tools = Path(directory)
    # MSVC diagnostic numbers in the public per-target GN files. These only
    # select diagnostics; corresponding GNU warnings remain enabled below.
    diagnostic_flags = {"/wd4201", "/wd4131", "/wd4244", "/wd4245", "/wd4267", "/wd4324", "/wd4702"}
    args = []
    for argument in arguments:
        if argument in diagnostic_flags:
            continue
        if argument.lower() == "/subsystem:windows":
            args.append("-mwindows")
        elif argument.lower() == "/subsystem:console":
            args.append("-mconsole")
        elif argument.endswith(".lib") and "/" not in argument and "\\" not in argument:
            args.append("-l" + argument[:-4])
        elif argument.startswith("/wd"):
            raise ValueError("unreviewed diagnostic flag")
        else:
            args.append(argument)
    if mode in ("cc", "cxx"):
        compiler = "x86_64-w64-mingw32-clang" + ("++" if mode == "cxx" else "")
        command = [str(tools / compiler), *args]
    elif mode == "link":
        command = [str(tools / "x86_64-w64-mingw32-clang++"), "-static", "-municode", *args]
    elif mode == "ar":
        output, *inputs = args
        Path(output).unlink(missing_ok=True)
        command = [str(tools / "llvm-ar"), "rcs", output, *inputs]
    elif mode == "asm":
        output, source = args
        subprocess.run([str(tools / "llvm-ml"), "-m64", "/c", "/Fo" + output, source], check=True)
        # Keep the exact upstream x64 instruction/unwind implementation.
        # Only its public C++ name changes between MSVC and the GNU C++ ABI.
        if Path(source).name == "capture_context_win.asm":
            subprocess.run([str(tools / "llvm-objcopy"), "--redefine-sym",
                            "?CaptureContext@crashpad@@YAXPEAU_CONTEXT@@@Z=_ZN8crashpad14CaptureContextEP8_CONTEXT",
                            output], check=True)
        return
    elif mode == "stamp":
        Path(args[0]).touch()
        return
    else:
        raise ValueError("unsupported cross-tool mode")
    subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
