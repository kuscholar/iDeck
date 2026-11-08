#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
# Bounded control in an unauthenticated experimental root only. Never logs keys.
set -eu
case "${1:---display-only}" in
    --display-only) steam=0 ;;
    --steam) steam=1 ;;
    *) exit 2 ;;
esac
duration=${2:-90}
case "$duration" in ''|*[!0-9]*) exit 2 ;; esac
test "$duration" -ge 1 && test "$duration" -le 600 || exit 2
case "${3:---no-cef-debug}" in
    --cef-debug) cef_debug=1 ;;
    --no-cef-debug) cef_debug=0 ;;
    *) exit 2 ;;
esac
# Refuse stale/occupied display state; do not delete a possibly live server's
# lock. A caller must inspect the stopped private root before any recovery.
if test -e /tmp/.X99-lock || test -S /tmp/.X11-unix/X99; then
    echo X11_EXISTING_DISPLAY_REFUSED
    exit 5
fi
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
    set -- -clientbeta steamdeck_stable -nobigpicture
    test "$cef_debug" = 0 || set -- "$@" -cef-enable-debugging
    ./steamrtarm64/steam "$@" > /tmp/ideck-steam-x11.log 2>&1 &
    spid=$!
fi
sleep "$duration"
kill -0 "$vpid"
# This status describes the display session only. Inspect Steam's own log/status.
