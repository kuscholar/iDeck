#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
# Build only, never launch Steam or touch account/device state. All overlays
# use NEW copied archives; vendor and prepared baseline libraries stay intact.
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_ARTIFACTS:?Prepared external host build required}"
: "${LINUX_LAB_TRACE_HOST_OUT:?New external output required}"
: "${NINJA:?Explicit ninja required}"
case "$LINUX_LAB_TRACE_HOST_OUT" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_TRACE_HOST_OUT" ]] || exit 2
mkdir -m 700 "$LINUX_LAB_TRACE_HOST_OUT"
src="$repo/vendor/LinuxRunner";build="$LINUX_LAB_ARTIFACTS/host"
lab="$repo/experiments/linux-steam";out="$LINUX_LAB_TRACE_HOST_OUT"
python3 "$lab/tools/build-pipe-observer.py" "$src" "$build" "$NINJA" "$out/packet" --packet-pipes --archive-only
python3 "$lab/tools/build-tcp-view.py" "$src" "$build" "$out/packet/libish.a" "$NINJA" "$out/tcp" --archive-only
python3 "$lab/tools/build-guest-lifetime.py" "$src" "$build" "$out/tcp/libish.a" "$out/lifetime"
python3 "$lab/tools/build-native-workers.py" "$src" "$build" "$out/lifetime/libish.a" "$out/workers"
python3 "$lab/tools/build-native-logging.py" "$src" "$build" "$out/workers/libish.a" "$out/logging"
python3 "$lab/tools/build-madvise-stats.py" "$src" "$build" "$out/logging/libish.a" "$out/advice"
python3 "$lab/tools/build-lazy-pages.py" "$src" "$build" "$out/advice/libish.a" "$out/lazy"
xcrun clang -DGUEST_ARM64=1 -DENGINE_ASBESTOS=1 -DLOG_HANDLER_DPRINTF=1 -DISH_INTERNAL=1 \
  -DIDECK_LAB_STEAM_FRONTEND=1 -DIDECK_LAB_COMPAT_TOOL=1 -DIDECK_LAB_X11_TRACE=1 \
  -DIDECK_LAB_GUEST_LIFETIME=1 -DIDECK_LAB_NATIVE_WORKERS=1 -DIDECK_LAB_NATIVE_LOG=1 \
  -DIDECK_LAB_LAZY_PAGES=1 -DIDECK_LAB_MADVISE_STATS=1 -DIDECK_LAB_CEF_DISABLE_GPU=1 \
  -DIDECK_LAB_SHARED_DISPLAY=1 -I "$src" -I "$build" -I "$lab/app" \
  -Wall -Wextra -Werror -Wno-unused-parameter \
  "$lab/app/LinuxLabRuntime.c" "$lab/app/LabDeviceFS.c" "$lab/app/LabBridge.c" \
  "$lab/app/LaunchProtocol.c" "$lab/app/ToolInstall.c" "$lab/app/X11TraceInstall.c" \
  "$lab/app/NativeKernelLog.c" "$lab/tools/steam-window-trace-control.c" \
  "$out/lazy/libish.a" -L "$build" -lish_emu -lfakefs -lsqlite3 -o "$out/control"
echo 'Built fixed HOST Steam trace control; not launched, no iPad validation'
