#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
# Fixed :97 control in a fresh private unauthenticated root. No Steam launched.
set -eu
if test -e /tmp/.X97-lock || test -S /tmp/.X11-unix/X97;then
    echo X11_WINDOW_EXISTING_DISPLAY_REFUSED;exit 5
fi
umask 077
Xvfb :97 -screen 0 640x480x24 -nolisten tcp -extension MIT-SHM > /tmp/ideck-x11-window-server.log 2>&1 &
xpid=$!
cleanup(){ kill "$xpid" 2>/dev/null || :;wait "$xpid" 2>/dev/null || :; }
trap cleanup EXIT
n=0
while ! test -S /tmp/.X11-unix/X97;do
    kill -0 "$xpid" || exit 3
    n=$((n+1));test "$n" -lt 200 || exit 4
    sleep .1
done
timeout 60 /x11-window-probe
