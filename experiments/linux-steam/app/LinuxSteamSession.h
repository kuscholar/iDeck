/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Fixed genuine desktop launch, not an account/credential command contract.
 * Native adapter removes only its own stale display readiness paths BEFORE
 * this first/only runtime lifetime starts. No remote CEF debugging on device.
 */
#if IDECK_LAB_SHARED_DISPLAY
#define IDECK_LAB_VNC_SHARING "-shared "
#else
#define IDECK_LAB_VNC_SHARING ""
#endif
#if IDECK_LAB_X11_TRACE
#if !IDECK_LAB_STEAM_FRONTEND || !IDECK_LAB_NATIVE_LOG || !IDECK_LAB_COMPAT_TOOL
#error X11 trace requires explicit frontend/native-log/compatibility-tool build opt-ins
#endif
#include "X11TraceInstall.h"
#endif
#if IDECK_LAB_CEF_DISABLE_GPU
/* Official Steam client switch, not a Valve/renderer binary patch. This changes
 * only this Lab browser experiment, never Madeira's game GPU implementation. */
#define IDECK_LAB_CEF_GPU_ARGS " -cef-disable-gpu"
#else
#define IDECK_LAB_CEF_GPU_ARGS ""
#endif
#define IDECK_LINUX_STEAM_ARGS_IMPL(TRACE_ENV) \
    "/bin/sh\0-c\0" \
    "set -eu; umask 077; " \
    "head -c 12 /dev/urandom | base64 | head -c 8 > /tmp/ideck-vnc-password; " \
    "Xvfb :99 -screen 0 1280x800x24 -nolisten tcp -extension MIT-SHM > /tmp/ideck-xvfb.log 2>&1 & xpid=$!; " \
    "vpid=; spid=; cleanup() { test -z \"$spid\" || kill \"$spid\" 2>/dev/null || :; " \
    "test -z \"$vpid\" || kill \"$vpid\" 2>/dev/null || :; kill \"$xpid\" 2>/dev/null || :; wait || :; }; trap cleanup EXIT; " \
    "n=0; while ! test -S /tmp/.X11-unix/X99; do kill -0 \"$xpid\"; n=$((n+1)); test \"$n\" -lt 100; sleep .1; done; " \
    "x11vnc " IDECK_LAB_VNC_SHARING "-norc -display :99 -localhost -no6 -rfbport 5993 -passwdfile /tmp/ideck-vnc-password -forever -noshm -noxdamage -noxrecord -noscr -nosel -noclipboard > /tmp/ideck-x11vnc.log 2>&1 & vpid=$!; " \
    "n=0; until lsof -n -P -a -p \"$vpid\" -iTCP:5993 -sTCP:LISTEN -Fn > /tmp/ideck-display-listener; do " \
    "kill -0 \"$vpid\"; n=$((n+1)); test \"$n\" -lt 100; sleep .1; done; " \
    "echo ready > /tmp/ideck-display-ready; " \
    "cd /Steam; export DISPLAY=:99 STEAM_RUNTIME=1; " \
    "export LD_LIBRARY_PATH=/Steam/steamrtarm64:/Steam/steamrtarm64/libs:/Steam/steamrtarm64/panorama; " \
    TRACE_ENV \
    "./steamrtarm64/steam -clientbeta steamdeck_stable -nobigpicture" IDECK_LAB_CEF_GPU_ARGS " > /tmp/ideck-steam.log 2>&1 & spid=$!; " \
    "wait \"$spid\"\0"
#define IDECK_LINUX_STEAM_ARGS IDECK_LINUX_STEAM_ARGS_IMPL("")
#if IDECK_LAB_X11_TRACE
#define IDECK_LINUX_STEAM_TRACE_ARGS IDECK_LINUX_STEAM_ARGS_IMPL("export LD_PRELOAD=" IDECK_X11_TRACE_FILE "; ")
#endif
