#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_ARTIFACTS:?Set to a private directory on the verified external volume}"
case "$LINUX_LAB_ARTIFACTS" in /Volumes/easystore/*) ;; *) echo 'Artifacts must use the external volume' >&2; exit 2;; esac
src="$repo/vendor/LinuxRunner"
expected=d1419782da2e299fe22f1ddb85c70ae3d1e276b1
[[ $(git -C "$src" rev-parse HEAD) == "$expected" ]] || exit 2
[[ -z $(git -C "$src" status --porcelain --untracked-files=no) ]] || { echo 'LinuxRunner source is modified' >&2; exit 2; }
: "${MESON:=meson}"
: "${NINJA:=ninja}"
: "${LD_LLD:=ld.lld}"
NINJA=$(command -v "$NINJA")
LD_LLD=$(command -v "$LD_LLD")
export PATH="$(dirname "$LD_LLD"):$PATH"
if [[ ${LINUX_LAB_COMPAT_TOOL:-0} == 1 && ${LINUX_LAB_STEAM_FRONTEND:-0} != 1 ]]; then
    echo 'Compatibility registration requires explicit Steam frontend opt-in' >&2;exit 2
fi
if [[ ${LINUX_LAB_X11_TRACE:-0} == 1 && ( ${LINUX_LAB_COMPAT_TOOL:-0} != 1 || ${LINUX_LAB_NATIVE_LOG:-0} != 1 || ${LINUX_LAB_STEAM_FRONTEND:-0} != 1 ) ]];then
    echo 'X11 trace requires explicit compatibility tool, native logging and Steam frontend' >&2;exit 2
fi
if [[ ${LINUX_LAB_GAME_FILE_POLICY:-0} == 1 && ( ${LINUX_LAB_COMPAT_TOOL:-0} != 1 || ${LINUX_LAB_NATIVE_LOG:-0} != 1 ) ]];then
    echo 'Native game-file diagnostics require explicit compatibility tool and native logging' >&2;exit 2
fi
if [[ ${LINUX_LAB_CEF_DISABLE_GPU:-0} == 1 && ${LINUX_LAB_STEAM_FRONTEND:-0} != 1 ]];then
    echo 'CEF GPU experiment requires explicit Steam frontend opt-in' >&2;exit 2
fi
if [[ ${LINUX_LAB_NATIVE_WORKERS:-0} == 1 && ${LINUX_LAB_GUEST_LIFETIME:-0} != 1 ]];then
    echo 'Native worker accounting requires explicit guest lifetime tracking' >&2;exit 2
fi
if [[ ${LINUX_LAB_MADVISE_STATS:-0} == 1 && ${LINUX_LAB_NATIVE_LOG:-0} != 1 ]];then
    echo 'Madvise request observation requires explicit native logging' >&2;exit 2
fi
if [[ ${LINUX_LAB_PRIVATE_DISCARD:-0} == 1 && ( ${LINUX_LAB_MADVISE_STATS:-0} != 1 || ${LINUX_LAB_LAZY_PAGES:-0} != 1 ) ]];then
    echo 'Private discard experiment requires explicit request observation and grouped lazy pages' >&2;exit 2
fi
if [[ ${LINUX_LAB_RFB_LIFETIME:-0} == 1 && ${LINUX_LAB_STEAM_FRONTEND:-0} != 1 ]];then
    echo 'RFB completion experiment requires explicit frontend opt-in' >&2;exit 2
fi
if [[ ${LINUX_LAB_RETAINED_FRONTEND:-0} == 1 ]];then
    [[ ${LINUX_LAB_RFB_LIFETIME:-0} == 1 && ${LINUX_LAB_COMPAT_TOOL:-0} == 1 && ${LINUX_LAB_NATIVE_LOG:-0} == 1 && ${LINUX_LAB_GUEST_LIFETIME:-0} == 1 && ${LINUX_LAB_NATIVE_WORKERS:-0} == 1 && ${LINUX_LAB_X11_TRACE:-0} == 0 ]] || { echo 'Retained frontend requires viewer completion, tool, native logging/lifetime workers and no X11 trace' >&2;exit 2; }
fi
[[ ${LINUX_LAB_CASP_ORDER:-0} == 0 || ${LINUX_LAB_CASP_ORDER:-0} == 1 ]] || exit 2
if [[ ${LINUX_LAB_CASP_ORDER:-0} == 1 ]];then
    [[ ${LINUX_LAB_STEAM_FRONTEND:-0} == 1 && ${LINUX_LAB_NATIVE_LOG:-0} == 1 ]] || { echo 'CASP ordering experiment requires explicit frontend and native logging' >&2;exit 2; }
fi
mkdir -p "$LINUX_LAB_ARTIFACTS"
sdk=$(xcrun --sdk iphoneos --show-sdk-path)
out="$LINUX_LAB_ARTIFACTS/ios"
mkdir -p "$out"
python3 - "$sdk" "$out/cross.ini" <<'PY'
import json, sys
sdk, dest = sys.argv[1:]
open(dest, 'w').write("[binaries]\nc = ['xcrun', '--sdk', 'iphoneos', 'clang']\nar = ['xcrun', 'ar']\n[host_machine]\nsystem = 'darwin'\ncpu_family = 'aarch64'\ncpu = 'aarch64'\nendian = 'little'\n[properties]\nneeds_exe_wrapper = true\n[built-in options]\nc_args = ['-target', 'arm64-apple-ios26.0', '-isysroot', " + repr(sdk) + "]\nc_link_args = ['-target', 'arm64-apple-ios26.0', '-isysroot', " + repr(sdk) + "]\n")
PY
if [[ ! -f "$out/build.ninja" ]]; then
    "$MESON" setup "$out" "$src" --cross-file "$out/cross.ini" \
        -Dengine=asbestos -Dguest_arch=arm64 -Djit=false -Djit_emit=false -Dcli_aot= -Dvdso_required=true
fi
"$NINJA" -C "$out" libish.a libish_emu.a libfakefs.a
python3 "$repo/experiments/linux-steam/tools/overlay-dirfd.py" "$src" "$out"
xcrun clang --target=aarch64-linux-gnu --ld-path="$LD_LLD" -nostdlib -static \
    -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
    "$repo/experiments/linux-steam/guest/probe.c" "$repo/experiments/linux-steam/guest/clone.S" \
    -Wl,-e,_start -o "$out/probe.elf"
xcrun clang --target=aarch64-linux-gnu --ld-path="$LD_LLD" -nostdlib -static \
    -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
    "$repo/experiments/linux-steam/guest/compatibility.c" "$repo/experiments/linux-steam/guest/compat-start.S" \
    -Wl,-e,_start -o "$out/ideck-madeira"
xcrun clang --target=aarch64-linux-gnu --ld-path="$LD_LLD" -nostdlib -static \
    -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
    "$repo/experiments/linux-steam/guest/packet-pipe-probe.c" -Wl,-e,_start -o "$out/packet-probe.elf"
xcrun clang --target=aarch64-linux-gnu --ld-path="$LD_LLD" -nostdlib -static \
    -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
    "$repo/experiments/linux-steam/guest/tcp-view-probe.c" -Wl,-e,_start -o "$out/tcp-probe.elf"
xcrun clang --target=aarch64-linux-gnu --ld-path="$LD_LLD" -nostdlib -shared \
    -ffreestanding -fno-builtin -fno-stack-protector -fPIC -O2 -Wall -Wextra -Werror \
    "$repo/experiments/linux-steam/guest/xlib-window-trace.c" -Wl,-soname,ideck-x11-window-trace.so -o "$out/xlib-window-trace.so"
runtime="$out"
if [[ ${LINUX_LAB_PACKET_PIPES:-0} == 1 ]]; then
    packet_stage=$(mktemp -d "$LINUX_LAB_ARTIFACTS/ios-packet.XXXXXX")
    runtime="$packet_stage/runtime"
    python3 "$repo/experiments/linux-steam/tools/build-pipe-observer.py" "$src" "$out" "$NINJA" "$runtime" --packet-pipes --archive-only
    cp "$out/libish_emu.a" "$out/libfakefs.a" "$runtime/"
fi
if [[ ${LINUX_LAB_TCP_VIEW:-0} == 1 ]]; then
    [[ ${LINUX_LAB_PACKET_PIPES:-0} == 1 ]] || { echo 'TCP Steam experiment requires explicit packet-pipe opt-in' >&2; exit 2; }
    tcp_stage=$(mktemp -d "$LINUX_LAB_ARTIFACTS/ios-tcp.XXXXXX")
    python3 "$repo/experiments/linux-steam/tools/build-tcp-view.py" "$src" "$out" "$runtime/libish.a" "$NINJA" "$tcp_stage/runtime" --archive-only
    cp "$runtime/libish_emu.a" "$runtime/libfakefs.a" "$tcp_stage/runtime/"
    runtime="$tcp_stage/runtime"
fi
if [[ ${LINUX_LAB_GUEST_LIFETIME:-0} == 1 ]]; then
    lifetime_stage=$(mktemp -d "$LINUX_LAB_ARTIFACTS/ios-lifetime.XXXXXX")
    set --
    [[ ${LINUX_LAB_RETAINED_FRONTEND:-0} != 1 ]] || set -- --join-guests --guest-waves
    python3 "$repo/experiments/linux-steam/tools/build-guest-lifetime.py" "$src" "$out" "$runtime/libish.a" "$lifetime_stage/runtime" ${1+"$@"}
    cp "$runtime/libish_emu.a" "$runtime/libfakefs.a" "$lifetime_stage/runtime/"
    runtime="$lifetime_stage/runtime"
fi
if [[ ${LINUX_LAB_NATIVE_WORKERS:-0} == 1 ]];then
    worker_stage=$(mktemp -d "$LINUX_LAB_ARTIFACTS/ios-workers.XXXXXX")
    set --
    [[ ${LINUX_LAB_RETAINED_FRONTEND:-0} != 1 ]] || set -- --join-workers --stop-profile --worker-waves
    python3 "$repo/experiments/linux-steam/tools/build-native-workers.py" "$src" "$out" "$runtime/libish.a" "$worker_stage/runtime" ${1+"$@"}
    cp "$runtime/libish_emu.a" "$runtime/libfakefs.a" "$worker_stage/runtime/"
    runtime="$worker_stage/runtime"
fi
if [[ ${LINUX_LAB_NATIVE_LOG:-0} == 1 ]];then
    log_stage=$(mktemp -d "$LINUX_LAB_ARTIFACTS/ios-native-log.XXXXXX")
    python3 "$repo/experiments/linux-steam/tools/build-native-logging.py" "$src" "$out" "$runtime/libish.a" "$log_stage/runtime"
    cp "$runtime/libish_emu.a" "$runtime/libfakefs.a" "$log_stage/runtime/"
    runtime="$log_stage/runtime"
fi
if [[ ${LINUX_LAB_RFB_LIFETIME:-0} == 1 ]];then
    rfb_stage=$(mktemp -d "$LINUX_LAB_ARTIFACTS/ios-rfb-parent.XXXXXX")
    python3 "$repo/experiments/linux-steam/tools/build-rfb-lifetime.py" "$rfb_stage/source"
    cp "$rfb_stage/source/LabRFBJoined.generated.inc" "$out/LabRFBJoined.generated.inc"
fi
frontend_libs=""
if [[ ${LINUX_LAB_MADVISE_STATS:-0} == 1 ]];then
    advice_stage=$(mktemp -d "$LINUX_LAB_ARTIFACTS/ios-madvise-stats.XXXXXX")
    set --
    [[ ${LINUX_LAB_PRIVATE_DISCARD:-0} != 1 ]] || set -- --experimental-private-discard
    python3 "$repo/experiments/linux-steam/tools/build-madvise-stats.py" "$src" "$out" "$runtime/libish.a" "$advice_stage/runtime" ${1+"$@"}
    cp "$runtime/libish_emu.a" "$runtime/libfakefs.a" "$advice_stage/runtime/"
    runtime="$advice_stage/runtime"
fi
if [[ ${LINUX_LAB_LAZY_PAGES:-0} == 1 ]];then
    lazy_stage=$(mktemp -d "$LINUX_LAB_ARTIFACTS/ios-lazy-pages.XXXXXX")
    python3 "$repo/experiments/linux-steam/tools/build-lazy-pages.py" "$src" "$out" "$runtime/libish.a" "$lazy_stage/runtime"
    cp "$runtime/libish_emu.a" "$runtime/libfakefs.a" "$lazy_stage/runtime/"
    runtime="$lazy_stage/runtime"
fi
if [[ ${LINUX_LAB_CASP_ORDER:-0} == 1 ]];then
    casp_stage=$(mktemp -d "$LINUX_LAB_ARTIFACTS/ios-casp-order.XXXXXX")
    python3 "$repo/experiments/linux-steam/tools/build-casp-order.py" "$src" "$out" "$runtime/libish_emu.a" "$casp_stage/runtime"
    cp "$runtime/libish.a" "$runtime/libfakefs.a" "$casp_stage/runtime/"
    runtime="$casp_stage/runtime"
fi
if [[ ${LINUX_LAB_STEAM_FRONTEND:-0} == 1 ]]; then
    [[ ${LINUX_LAB_TCP_VIEW:-0} == 1 ]] || { echo 'Steam frontend requires explicit TCP view opt-in' >&2; exit 2; }
    [[ ${LINUX_LAB_ROOTFS_SHA256:-} =~ ^[0-9a-f]{64}$ ]] || { echo 'A verified clean root installation hash is required' >&2; exit 2; }
    bash "$repo/experiments/linux-steam/tools/build-ios-archive.sh"
    archive="$LINUX_LAB_ARTIFACTS/ios-libarchive-v2"
    frontend_libs="$archive/liblabrootfs.a $archive/libarchive/libarchive.a -lz"
fi
set --
if [[ -n ${LINUX_LAB_BUILD_VERSION:-} ]];then
    [[ $LINUX_LAB_BUILD_VERSION =~ ^[0-9]+$ ]] || exit 2
    set -- CURRENT_PROJECT_VERSION="$LINUX_LAB_BUILD_VERSION"
fi
xcodebuild -project "$repo/experiments/linux-steam/LinuxLab.xcodeproj" \
    -scheme LinuxLab -configuration Debug -destination 'generic/platform=iOS' \
    -derivedDataPath "$LINUX_LAB_ARTIFACTS/xcode" CODE_SIGNING_ALLOWED=NO \
    LINUX_LAB_BUILD_DIR="$out" LINUX_LAB_RUNTIME_DIR="$runtime" \
    LINUX_LAB_SHARED_DISPLAY="${LINUX_LAB_SHARED_DISPLAY:-0}" \
    LINUX_LAB_COMPAT_TOOL="${LINUX_LAB_COMPAT_TOOL:-0}" \
    LINUX_LAB_X11_TRACE="${LINUX_LAB_X11_TRACE:-0}" \
    LINUX_LAB_RFB_LIFETIME="${LINUX_LAB_RFB_LIFETIME:-0}" \
    LINUX_LAB_RETAINED_FRONTEND="${LINUX_LAB_RETAINED_FRONTEND:-0}" \
    LINUX_LAB_CASP_ORDER="${LINUX_LAB_CASP_ORDER:-0}" \
    LINUX_LAB_GAME_FILE_POLICY="${LINUX_LAB_GAME_FILE_POLICY:-0}" \
    LINUX_LAB_GUEST_LIFETIME="${LINUX_LAB_GUEST_LIFETIME:-0}" \
    LINUX_LAB_NATIVE_WORKERS="${LINUX_LAB_NATIVE_WORKERS:-0}" \
    LINUX_LAB_NATIVE_LOG="${LINUX_LAB_NATIVE_LOG:-0}" \
    LINUX_LAB_LAZY_PAGES="${LINUX_LAB_LAZY_PAGES:-0}" \
    LINUX_LAB_CEF_DISABLE_GPU="${LINUX_LAB_CEF_DISABLE_GPU:-0}" \
    LINUX_LAB_MADVISE_STATS="${LINUX_LAB_MADVISE_STATS:-0}" \
    LINUX_LAB_PRIVATE_DISCARD="${LINUX_LAB_PRIVATE_DISCARD:-0}" \
    LINUX_LAB_STEAM_FRONTEND="${LINUX_LAB_STEAM_FRONTEND:-0}" \
    LINUX_LAB_ROOTFS_SHA256="${LINUX_LAB_ROOTFS_SHA256:-}" \
    LINUX_LAB_FRONTEND_LIBS="$frontend_libs" ${1+"$@"} build
