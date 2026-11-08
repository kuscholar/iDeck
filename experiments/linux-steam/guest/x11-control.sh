#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
# Bounded control in an unauthenticated experimental root only. Never logs keys.
set -eu
case "${1:---display-only}" in
    --display-only) steam=0 ;;
    --steam) steam=1 ;;
    *) exit 2 ;;
esac
umask 077
head -c 12 /dev/urandom | base64 | head -c 8 > /tmp/ideck-vnc-password
Xvfb :99 -screen 0 1280x800x24 -nolisten tcp -extension MIT-SHM > /tmp/ideck-xvfb.log 2>&1 &
xpid=$!
vpid=
spid=
cleanup() {
    test -z "$spid" || kill "$spid" 2>/dev/null || :
    test -z "$vpid" || kill "$vpid" 2>/dev/null || :
    kill "$xpid" 2>/dev/null || :
    wait || :
}
trap cleanup EXIT
n=0
while ! test -S /tmp/.X11-unix/X99; do
    kill -0 "$xpid" || exit 3
    n=$((n+1)); test "$n" -lt 100 || exit 4
    sleep .1
done
x11vnc -norc -display :99 -localhost -no6 -rfbport 5993 -passwdfile /tmp/ideck-vnc-password -forever -noshm -noxdamage -noxrecord -noscr -nosel -noclipboard > /tmp/ideck-x11vnc.log 2>&1 &
vpid=$!
echo X11_SESSION_STARTED
if test "$steam" = 1; then
    cd /Steam
    export DISPLAY=:99 STEAM_RUNTIME=1
    export LD_LIBRARY_PATH=/Steam/steamrtarm64:/Steam/steamrtarm64/libs:/Steam/steamrtarm64/panorama
    ./steamrtarm64/steam -clientbeta steamdeck_stable -nobigpicture > /tmp/ideck-steam-x11.log 2>&1 &
    spid=$!
fi
sleep 90
kill -0 "$vpid"
# This status describes the display session only. Inspect Steam's own log/status.
