#!/bin/sh
# Keep rmetald running. A daemon that dies mid-session silently costs a device
# run: the guest reports "cannot reach" and falls back to local, which looks
# exactly like a successful local render. Restart it and record why it exited.
cd "$(dirname "$0")"
BIND="${1:-10.0.1.53}"
: "${RMETAL_TOKEN:?set RMETAL_TOKEN}"

# BUILD FIRST. This script only ran the existing binary, so editing rmetald.m
# and restarting the supervisor kept serving the OLD code -- twice in a row,
# while the source said otherwise. Building here means "restart" can never
# again mean "restart the stale one".
echo "  building rmetald (protocol v$(sed -n 's/^#define RM_VERSION \([0-9]*\)u.*/\1/p' protocol.h))"
# Build to a temp name, swap on success -- never delete the working binary
# first (see run-host.sh: a clang licence refusal once destroyed it outright).
if [ -x /Library/Developer/CommandLineTools/usr/bin/clang ] && \
   [ -d /Library/Developer/CommandLineTools/SDKs/MacOSX.sdk ]; then
  CC=/Library/Developer/CommandLineTools/usr/bin/clang
  SYSROOT="-isysroot /Library/Developer/CommandLineTools/SDKs/MacOSX.sdk"
else
  CC=clang
  SYSROOT=""
fi
if $CC -O1 -w -fobjc-arc -fdeclspec $SYSROOT -framework Foundation -framework Metal \
      -framework QuartzCore -framework AppKit -o host/rmetald.new host/rmetald.m; then
  mv -f host/rmetald.new host/rmetald
else
  echo "  BUILD FAILED -- keeping the existing binary" >&2
  rm -f host/rmetald.new
  [ -x host/rmetald ] || exit 1
fi

while :; do
    host/rmetald "$BIND" >>/tmp/rmetald.log 2>&1
    rc=$?
    echo "[supervisor] rmetald exited rc=$rc -- restarting" >>/tmp/rmetald.log
    i=0
    while [ $i -lt 100 ]; do
        lsof -nP -iTCP:47821 -sTCP:LISTEN >/dev/null 2>&1 || break
        i=$((i+1))
    done
done
