#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
# Build only our Linux ARM64 diagnostics against an inspected distro's runtime
# ELF files. Does not edit the distro, run Steam, modify or install any app.
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_XLIB_ROOT:?Inspected private fakefs with distribution libX11/glibc required}"
: "${LINUX_LAB_XLIB_OUT:?New private external artifact directory required}"
: "${LD_LLD:=ld.lld}"
case "$LINUX_LAB_XLIB_ROOT:$LINUX_LAB_XLIB_OUT" in /Volumes/easystore/*:/Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_XLIB_OUT" ]] || exit 2
mkdir -m 700 "$LINUX_LAB_XLIB_OUT"
lab="$repo/experiments/linux-steam";root="$LINUX_LAB_XLIB_ROOT/data/usr/lib/aarch64-linux-gnu";out="$LINUX_LAB_XLIB_OUT"
flags=(--target=aarch64-linux-gnu --ld-path="$(command -v "$LD_LLD")" -nostdlib -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror)
xcrun clang "${flags[@]}" -fPIC -shared "$lab/guest/xlib-window-trace.c" -Wl,-soname,ideck-x11-window-trace.so -o "$out/xlib-window-trace.so"
for mode in normal stress;do
    queries=0;[[ $mode != stress ]] || queries=4000
    xcrun clang "${flags[@]}" -fPIE -DX11_EXTRA_ATTRIBUTE_QUERIES="$queries" \
        "$lab/guest/xlib-window-probe.c" "$lab/guest/xlib-glibc-start.S" \
        "$root/libX11.so.6.4.0" "$root/libc.so.6" \
        -Wl,-pie,-e,_start,-dynamic-linker,/lib/ld-linux-aarch64.so.1 -o "$out/$mode.elf"
done
xcrun clang "${flags[@]}" -fPIC -shared "$lab/guest/xlib-scope-plugin.c" \
    "$root/libX11.so.6.4.0" "$root/libc.so.6" -Wl,-soname,ideck-scope-plugin.so -o "$out/scope-plugin.so"
xcrun clang "${flags[@]}" -fPIE "$lab/guest/xlib-scope-control.c" "$lab/guest/xlib-glibc-start.S" \
    "$root/libc.so.6" -Wl,-pie,-e,_start,-dynamic-linker,/lib/ld-linux-aarch64.so.1 -o "$out/scope.elf"
python3 - "$lab" "$root" "$out" <<'PY'
from pathlib import Path
import hashlib,json,sys
lab,root,out=map(Path,sys.argv[1:]);hashof=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p in (root/'libX11.so.6.4.0',root/'libc.so.6'):
    assert p.read_bytes()[:4]==b'\x7fELF','Native linker inputs must be regular ARM64 ELF, not fakefs guest symlink text'
evidence=dict(scope='Linux ARM64 diagnostic build only; not iOS app linkage/execution or Steam compatibility',
    dependencies={p.name:hashof(p) for p in (root/'libX11.so.6.4.0',root/'libc.so.6')},
    sources={str(p.relative_to(lab)):hashof(p) for p in (lab/'guest/xlib-window-trace.c',lab/'guest/xlib-window-probe.c',lab/'guest/xlib-glibc-start.S',lab/'guest/xlib-scope-plugin.c',lab/'guest/xlib-scope-control.c')},
    artifacts={name:hashof(out/name) for name in ('xlib-window-trace.so','normal.elf','stress.elf','scope-plugin.so','scope.elf')})
(out/'build-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n');print(json.dumps(evidence))
PY
