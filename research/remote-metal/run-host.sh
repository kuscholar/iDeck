#!/bin/sh
# Rebuild AND restart rmetald, then state the protocol version it serves.
#
# Rebuilding the binary is not enough: the daemon keeps running the code it was
# started with, so a protocol bump can leave a stale process serving an old
# version while the source says otherwise. That cost a device run -- the guest
# reported "daemon speaks v6, this build speaks v5" and fell back to local.
set -e
cd "$(dirname "$0")"
BIND="${1:-10.0.1.53}"
: "${RMETAL_TOKEN:?set RMETAL_TOKEN}"

VER=$(sed -n 's/^#define RM_VERSION \([0-9]*\)u.*/\1/p' protocol.h)
echo "  protocol.h declares v$VER"

# Build to a TEMPORARY name and move it into place only on success.
#
# This used to "rm -f host/rmetald" and compile straight to that path, so ANY
# build failure left no binary at all -- and the failure that exposed it was not
# a code error: after a host restart clang refused with "You have not agreed to
# the Xcode license agreements", which destroyed a working daemon and then could
# not rebuild it. A build step must never leave you with less than you started.
#
# Prefer the standalone Command Line Tools toolchain when present: it needs no
# Xcode licence agreement, which is exactly the failure above.
if [ -x /Library/Developer/CommandLineTools/usr/bin/clang ] && \
   [ -d /Library/Developer/CommandLineTools/SDKs/MacOSX.sdk ]; then
  CC=/Library/Developer/CommandLineTools/usr/bin/clang
  SYSROOT="-isysroot /Library/Developer/CommandLineTools/SDKs/MacOSX.sdk"
else
  CC=clang
  SYSROOT=""
fi
if ! $CC -O1 -w -fobjc-arc -fdeclspec $SYSROOT \
      -framework Foundation -framework Metal \
      -framework QuartzCore -framework AppKit -o host/rmetald.new host/rmetald.m; then
  echo "  BUILD FAILED -- keeping the existing binary"
  rm -f host/rmetald.new
  [ -x host/rmetald ] || { echo "  and there is no existing binary to fall back to"; exit 1; }
  echo "  (the running daemon was NOT restarted)"
  exit 1
fi
mv -f host/rmetald.new host/rmetald
echo "  host rebuilt"

pkill -f "host/rmetald" 2>/dev/null || true
# Wait for the listening socket to actually go away. pkill returns as soon as
# the signal is sent, so starting immediately loses the bind to the process
# that is still exiting -- and the new daemon dies with "Address already in
# use" while the script cheerfully reports success.
i=0
while [ $i -lt 100 ]; do
  lsof -nP -iTCP:47821 -sTCP:LISTEN >/dev/null 2>&1 || break
  i=$((i+1))
done
nohup host/rmetald "$BIND" >/tmp/rmetald.log 2>&1 &
i=0; while [ $i -lt 60 ]; do grep -q listening /tmp/rmetald.log 2>/dev/null && break; i=$((i+1)); done
if grep -qa "listening" /tmp/rmetald.log; then
  grep -a "listening\|host GPU" /tmp/rmetald.log | sed 's/^/  /'
  echo "  serving protocol v$VER (process restarted)"
else
  echo "  DAEMON FAILED TO START:"; tail -3 /tmp/rmetald.log | sed 's/^/    /'; exit 1
fi
