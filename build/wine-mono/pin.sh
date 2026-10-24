# Pinned Wine Mono for the app bundle. Sourced by fetch.sh and bundle.sh; not run directly.
#
# The bundle carries exactly the build it was verified with (Terraria, 2026-10-05). The version
# does not follow WINE_MONO_VERSION in wine/dlls/mscoree/mscoree_private.h: mscoree finds the
# bundled runtime through C:\windows\mono\mono-2.0, a path it does not check the version of, so
# a newer Wine still loads it; the scripts only warn about the mismatch.
#
# bundle.sh also patches the bundled mscorlib.dll (ml1281, a stopgap, see the TODO there), and that
# patch is verified for exactly this build of mscorlib.dll and nothing else.
#
# Changing the version means new hashes below, a new COPYING from that release's source, redoing
# and re-verifying the mscorlib patch (new offset and both mscorlib hashes), and a device run of a
# .NET Framework game.

WINE_MONO_VER=11.0.0

# wine-mono-11.0.0-x86.tar.xz from https://dl.winehq.org/wine/wine-mono/11.0.0/, downloaded
# 2026-10-05. WineHQ publishes no checksum for the tarball; its contents equal, file for file,
# those of wine-mono-11.0.0-x86.msi, whose SHA-256 Wine pins in dlls/appwiz.cpl/addons.c.
WINE_MONO_TAR_SHA256=0cd723aa28897f7d7d2702eed6c72e4262255980e212bc2b3c94bfa234abe5fd

# wine-mono-11.0.0-src.tar.xz from the same folder (372 MB): the source of that build, for the
# LGPL parts (THIRD-PARTY-NOTICES.md). `fetch.sh --source` downloads and checks it.
WINE_MONO_SRC_SHA256=c504cb0b91ce09b72869e063844ce114564d4ac340479a82aa6789f51510e520

# lib/mono/4.5/mscorlib.dll of that build, before and after bundle.sh's patch (ml1281).
WINE_MONO_MSCORLIB_SHA256=ea40cb9dcad1bd96221ab9a826dd0cce298e57d75f06087b8c7b69319c0e6137
WINE_MONO_MSCORLIB_PATCHED_SHA256=cfc4fb50c0e4f93d6e2c5fd827e2d7b3f215d3b183df024db68d6784c5388bc6
