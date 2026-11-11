#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
# Build only separate copied archives. Never launch/change a device or Steam.
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_ARTIFACTS:?Prepared host build required}"
: "${LINUX_LAB_RESTART_OUT:?New external output required}"
: "${NINJA:?Explicit ninja required}"
: "${LINUX_LAB_SHUTDOWN_PROFILE:=0}"
[[ $LINUX_LAB_SHUTDOWN_PROFILE == 0 ]] || exit 2 # Profiler has one lifetime; no revival.
[[ $LINUX_LAB_SHUTDOWN_PROFILE == 0 || $LINUX_LAB_SHUTDOWN_PROFILE == 1 ]] || exit 2
case "$LINUX_LAB_RESTART_OUT" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_RESTART_OUT" ]] || exit 2
out="$LINUX_LAB_RESTART_OUT";mkdir -m 700 "$out";src="$repo/vendor/LinuxRunner";host="$LINUX_LAB_ARTIFACTS/host";lab="$repo/experiments/linux-steam"
python3 "$lab/tools/build-pipe-observer.py" "$src" "$host" "$NINJA" "$out/packet" --packet-pipes --archive-only
python3 "$lab/tools/build-tcp-view.py" "$src" "$host" "$out/packet/libish.a" "$NINJA" "$out/tcp" --archive-only
python3 "$lab/tools/build-guest-lifetime.py" "$src" "$host" "$out/tcp/libish.a" "$out/lifetime" --join-guests --guest-waves
python3 "$lab/tools/build-native-workers.py" "$src" "$host" "$out/lifetime/libish.a" "$out/workers" --join-workers --stop-profile --worker-waves
python3 "$lab/tools/build-native-logging.py" "$src" "$host" "$out/workers/libish.a" "$out/logging"
python3 "$lab/tools/build-madvise-stats.py" "$src" "$host" "$out/logging/libish.a" "$out/advice"
python3 "$lab/tools/build-lazy-pages.py" "$src" "$host" "$out/advice/libish.a" "$out/lazy"
xcrun clang -DGUEST_ARM64=1 -DENGINE_ASBESTOS=1 -DLOG_HANDLER_DPRINTF=1 -DISH_INTERNAL=1 \
  -DIDECK_HOST_SHUTDOWN_PROFILE="$LINUX_LAB_SHUTDOWN_PROFILE" \
  -DIDECK_LAB_STEAM_FRONTEND=1 -DIDECK_LAB_COMPAT_TOOL=1 -DIDECK_LAB_GUEST_LIFETIME=1 -DIDECK_LAB_NATIVE_WORKERS=1 -DIDECK_LAB_NATIVE_LOG=1 \
  -DIDECK_LAB_LAZY_PAGES=1 -DIDECK_LAB_MADVISE_STATS=1 -DIDECK_LAB_CEF_DISABLE_GPU=1 -DIDECK_LAB_SHARED_DISPLAY=1 \
  -I "$src" -I "$host" -I "$lab/app" -Wall -Wextra -Werror -Wno-unused-parameter \
  "$lab/app/LinuxLabRuntime.c" "$lab/app/LabDeviceFS.c" "$lab/app/LabBridge.c" "$lab/app/LaunchProtocol.c" "$lab/app/ToolInstall.c" \
  "$lab/app/NativeKernelLog.c" "$lab/app/NativeSignalLease.c" "$lab/tools/steam-restart-control.c" \
  "$out/lazy/libish.a" -L "$host" -lish_emu -lfakefs -lsqlite3 -o "$out/control"
echo 'Built own host actual-Steam restart control; not launched or device-validated'
