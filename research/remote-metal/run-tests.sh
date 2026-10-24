#!/bin/sh
# Rebuild AND run every suite. Stale test binaries speak an old protocol and
# get refused by a newer daemon, which reads as a product failure ("newLibrary
# -> err", "auth failed") when it is only a rebuild that did not happen.
set -e
cd "$(dirname "$0")"
HOST="${1:-10.0.1.53}"
: "${RMETAL_TOKEN:?set RMETAL_TOKEN}"
echo "  protocol: v$(sed -n 's/^#define RM_VERSION \([0-9]*\)u.*/\1/p' protocol.h)"
rm -f /tmp/wire_test /tmp/pack_test guest/rmclient_test guest/rmtest guest/rmreplay
clang -O1 -w -I. -o /tmp/wire_test schema/wire_test.c && /tmp/wire_test | tail -1 | sed 's/^/  wire:   /'
clang -O1 -w -fdeclspec -I ../dxmt/src/winemetal -o /tmp/pack_test schema/pack_test.c && /tmp/pack_test | tail -1 | sed 's/^/  pack:   /'
clang -O1 -w -o guest/rmclient_test guest/rmclient_test.c
DXMT_REMOTE_METAL="$HOST" guest/rmclient_test | tail -1 | sed 's/^/  client: /'
clang -O1 -w -I. -o guest/rmtest guest/rmtest.c
guest/rmtest "$HOST" | tail -1 | sed 's/^/  rmtest: /'
clang -O1 -w -I. -o guest/rmreplay guest/rmreplay.c
guest/rmreplay "$HOST" | tail -1 | sed 's/^/  replay: /'
