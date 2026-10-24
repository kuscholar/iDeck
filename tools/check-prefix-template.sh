#!/bin/sh
# ml719: reject a prefix template containing absolute host symlinks.
#
# prefix-template.tar.gz shipped six links into the BUILD MACHINE's home
# (drive_c/users/madeira/Documents -> /Users/willfaust/Documents, and the same for
# Desktop/Downloads/Music/Pictures/Videos). They dangle on every device, so every
# Windows shell-folder lookup silently failed -- which is why no game that writes to
# My Documents could produce a log. It shipped unnoticed because nothing we tested
# wrote there until Marvel Cosmic Invasion.
#
# Run from the repo root. Exit 1 makes the offending archive impossible to ship.
set -e
ARCHIVE="${1:-app/Madeira/prefix-template.tar.gz}"
[ -f "$ARCHIVE" ] || { echo "check-prefix-template: no such archive: $ARCHIVE" >&2; exit 1; }

BAD=$(tar tzvf "$ARCHIVE" 2>/dev/null | awk '/^l/ { for (i=1;i<=NF;i++) if ($i=="->") { print $(i+1); break } }' \
      | grep -E '^/' | grep -vE '^/(tmp|var|private)/' || true)

if [ -n "$BAD" ]; then
    echo "check-prefix-template: FAIL -- absolute host symlink target(s) in $ARCHIVE:" >&2
    echo "$BAD" | sed 's/^/  /' >&2
    echo "  Shell folders must be ordinary directories (the container UUID changes across" >&2
    echo "  reinstalls, so container-absolute links rot too). See ml719." >&2
    exit 1
fi
echo "check-prefix-template: OK -- no absolute host symlinks in $ARCHIVE"
