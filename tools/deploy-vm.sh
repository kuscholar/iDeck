#!/bin/bash
# Push changed app files straight into the INSTALLED bundle on the vphone VM and
# verify they landed, so a build can never be "installed after the run" again.
#
# The bundle is writable and the VM does not enforce the app signature for the
# debug dylib, so a full reinstall is unnecessary: replacing the payload files
# in place takes effect on the next launch. Each file is verified after transfer
# by comparing sha256 against the local copy -- a deploy that cannot be proven
# is treated as a failure.
#
#   ./tools/deploy-vm.sh                 # deploy the current build
#   ./tools/deploy-vm.sh <marker>        # also assert the marker is present
set -uo pipefail
R="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$HOME/Library/Developer/Xcode/DerivedData/Madeira-fytoydazgayvqxgeytwxbzkogigx/Build/Products/Debug-iphoneos/Madeira.app"
# The VM takes a fresh DHCP lease across host restarts, so this default is a
# convenience, not a fact. Override with VM_HOST=<addr> when it moves.
VM_HOST="${VM_HOST:-192.168.64.10}"
BUNDLE="/var/containers/Bundle/Application/873AC6F5-34E3-4308-8303-C6B7EE0166E3/Madeira.app"
MARKER="${1:-}"
SSH=(sshpass -p alpine ssh -p 22222 -o StrictHostKeyChecking=no -o ConnectTimeout=20 "root@$VM_HOST")
RPATH='export PATH=/var/jb/usr/bin:/var/jb/usr/sbin:/var/jb/bin:/var/jb/sbin:$PATH'

# Only the payload that actually changes between builds. Add paths as needed.
FILES=(
  "Madeira.debug.dylib"
  "arm64ec-windows/ntdll.dll"
  "arm64ec-windows/xtajit64.dll"
  "arm64ec-windows/dxgi.dll"
  # ml1008: the native D3D12 runtime. Without these two a madeira_d3d12 change
  # has no route to the device at all -- the same omission dxgi.dll had, which
  # silently ran old code for a whole round of DXMT work.
  "arm64ec-windows/madeira_d3d12.dll"
  "arm64ec-windows/d3d12.dll"
)

fail=0

# Refuse an UNSIGNED dylib before touching the device.
#
# A build made with CODE_SIGNING_ALLOWED=NO produces a Madeira.debug.dylib with
# no signature at all. The VM does not enforce the APP signature, which is why
# in-place replacement works -- but dyld still refuses to load a dylib that
# carries no signature, so the app dies at launch with
#   DYLD / Library missing: "missing code signature in .../Madeira.debug.dylib"
# and NO log is written at all, because the crash is before LogStore.init. That
# looks exactly like a catastrophic code regression and is not one; it cost a
# launch. sha256 cannot catch it -- an unsigned file verifies against itself
# perfectly -- so check the signature itself, here, before the push.
for dylib in "$APP/Madeira.debug.dylib" "$APP/d3d12/libmetalirconverter.dylib"; do
  [ -f "$dylib" ] || continue
  if ! codesign -dv "$dylib" >/dev/null 2>&1; then
    echo "  REFUSING TO DEPLOY: $(basename "$dylib") has no code signature"
    echo "  (rebuild WITHOUT CODE_SIGNING_ALLOWED=NO, or dyld will refuse it at launch)"
    fail=1
  fi
done
if [ "$fail" != "0" ]; then
  echo "DEPLOY ABORTED — nothing was pushed"
  exit 1
fi

# Kill any running/suspended instance FIRST.
#
# rdr55/rdr57/rdr58 all executed STALE code despite a sha256-verified deploy:
# LogStore.init runs on resume as well as on cold start, so a suspended process
# re-created the log file (making the run look new) while still running the
# dylib it had already mapped. Replacing a file never affects a process that has
# it mapped. Three "impossible" missing-probe anomalies came from this, so the
# deploy now guarantees the next launch is cold and says so.
echo -n "  terminating any running instance... "
before=$("${SSH[@]}" "$RPATH; ps ax | grep -c '[M]adeira'")
"${SSH[@]}" "$RPATH; killall -9 Madeira 2>/dev/null; pkill -9 -f 'Madeira.app' 2>/dev/null; true" >/dev/null 2>&1
after=$("${SSH[@]}" "$RPATH; ps ax | grep -c '[M]adeira'")
echo "was_running=${before:-?} now=${after:-?}"
if [ "${after:-0}" != "0" ]; then
  echo "  STILL RUNNING — a launch now would keep using the old mapped dylib"
  fail=1
fi

for f in "${FILES[@]}"; do
  src="$APP/$f"
  [ -f "$src" ] || { echo "  SKIP $f (not in build)"; continue; }
  lsum=$(shasum -a 256 "$src" | awk '{print $1}')
  rsum=$("${SSH[@]}" "$RPATH; sha256sum '$BUNDLE/$f' 2>/dev/null | cut -d' ' -f1")
  if [ "$lsum" = "$rsum" ]; then echo "  same $f (already deployed)"; continue; fi
  echo -n "  push $f ($(stat -f%z "$src") bytes)... "
  base64 -i "$src" | "${SSH[@]}" "$RPATH; base64 -d > '$BUNDLE/$f.new' && mv '$BUNDLE/$f.new' '$BUNDLE/$f'" || { echo "TRANSFER FAILED"; fail=1; continue; }
  rsum=$("${SSH[@]}" "$RPATH; sha256sum '$BUNDLE/$f' 2>/dev/null | cut -d' ' -f1")
  if [ "$lsum" = "$rsum" ]; then echo "OK (sha256 verified)"; else echo "MISMATCH local=$lsum remote=$rsum"; fail=1; fi
done

if [ -n "$MARKER" ]; then
  n=$("${SSH[@]}" "$RPATH; grep -c '$MARKER' '$BUNDLE/Madeira.debug.dylib' 2>/dev/null || echo 0")
  echo "  marker '$MARKER' in installed dylib: $n"
  [ "$n" = "0" ] && { echo "  MARKER ABSENT — do not run this build"; fail=1; }
fi

# Clear the log so the next launch cannot be confused with the previous one --
# but ONLY on success. Clearing it after a failed transfer is worse than useless:
# it hands the next launch a fresh log written by the OLD binary, which reads
# exactly like a deployed build that changed nothing.
if [ "$fail" = "0" ]; then
  "${SSH[@]}" "$RPATH; D=/var/mobile/Containers/Data/Application/5BC39EAE-C20C-41FA-BCE2-7BF3D2B5822F/Documents; rm -f \$D/madeira-log.txt \$D/madeira-log.prev.txt" >/dev/null 2>&1

# ml1024: clear RDR2's session marker.
#
# RDR2 writes AppData/Local/Rockstar Games/Red Dead Redemption 2/exit_file.dat
# while running and expects to tidy it up on a clean shutdown. Every run here
# ends in a force-kill, so the stale marker survives and the NEXT launch opens
# with the game's own modal "Red Dead Redemption 2 exited unexpectedly!" dialog.
# That looks exactly like a fresh regression -- it cost a round trip once -- and
# it blocks the run until someone clicks it. It is stale state, not a crash, so
# clear it with the log.
"${SSH[@]}" "$RPATH; rm -f '/var/mobile/Containers/Data/Application/5BC39EAE-C20C-41FA-BCE2-7BF3D2B5822F/Documents/wine/drive_c/users/mobile/AppData/Local/Rockstar Games/Red Dead Redemption 2/exit_file.dat'" >/dev/null 2>&1
echo "  RDR2 session marker cleared — no stale 'exited unexpectedly' dialog"
  echo "  log cleared — next launch starts a fresh madeira-log.txt"
  echo "DEPLOY VERIFIED — no instance running, next launch is COLD and uses this build"
else
  echo "  log NOT cleared (deploy failed) — the installed build is still the previous one"
  echo "DEPLOY FAILED"
fi
exit $fail
