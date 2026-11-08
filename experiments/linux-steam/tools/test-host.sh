#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_ARTIFACTS:?Set a private external artifact directory}"
: "${LD_LLD:=ld.lld}"
: "${MESON:=meson}"
: "${NINJA:=ninja}"
LD_LLD=$(command -v "$LD_LLD")
export PATH="$(dirname "$LD_LLD"):$PATH"
src="$repo/vendor/LinuxRunner"
build="$LINUX_LAB_ARTIFACTS/host"
mkdir -p "$LINUX_LAB_ARTIFACTS"
if [[ ! -f "$build/build.ninja" ]]; then
    "$MESON" setup "$build" "$src" -Dengine=asbestos -Dguest_arch=arm64 \
        -Djit=false -Djit_emit=false -Dvdso_required=true -Dcli_aot=
fi
"$NINJA" -C "$build" ish
python3 "$repo/experiments/linux-steam/tools/overlay-dirfd.py" "$src" "$build"
"$NINJA" -C "$build" ish
lab="$repo/experiments/linux-steam"
flags=(-nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror)
mkdir -p "$LINUX_LAB_ARTIFACTS/host-root" "$LINUX_LAB_ARTIFACTS/compat-root"
xcrun clang --target=aarch64-linux-gnu --ld-path="$LD_LLD" "${flags[@]}" \
    "$lab/guest/probe.c" "$lab/guest/clone.S" -Wl,-e,_start -o "$LINUX_LAB_ARTIFACTS/host-root/probe"
xcrun clang --target=aarch64-linux-gnu --ld-path="$LD_LLD" "${flags[@]}" \
    "$lab/guest/compatibility.c" "$lab/guest/compat-start.S" -Wl,-e,_start -o "$LINUX_LAB_ARTIFACTS/compat-root/ideck-madeira"
xcrun clang -DGUEST_ARM64=1 -DENGINE_ASBESTOS=1 -DLOG_HANDLER_DPRINTF=1 -DISH_INTERNAL=1 \
    -I "$src" -I "$build" -Wall -Wextra -Werror -Wno-unused-parameter \
    "$lab/app/LinuxLabRuntime.c" "$lab/app/LabDeviceFS.c" "$lab/app/LabBridge.c" \
    "$lab/app/LaunchProtocol.c" "$lab/tools/host-embed.c" \
    -L "$build" -lish -lish_emu -lfakefs -lsqlite3 -o "$LINUX_LAB_ARTIFACTS/host-embed"
python3 - "$LINUX_LAB_ARTIFACTS" <<'PY'
from pathlib import Path
import subprocess, sys
base = Path(sys.argv[1]).resolve()
for name, argv in [('embedded-probe', [str(base/'host-embed'), str(base/'host-root')]),
                   ('compat-wrapper', [str(base/'host-embed'), str(base/'compat-root'), '--compatibility-probe'])]:
    with (base/(name+'.log')).open('wb') as log:
        subprocess.run(argv, stdout=log, stderr=log, check=True, timeout=20)
lines=(base/'host-root/probe-results.txt').read_text().splitlines()
assert len(lines) == 16 and all(line.endswith('=PASS') for line in lines), lines
print('\n'.join(lines))
PY
xcrun clang -fsanitize=address,undefined -Wall -Wextra -Werror \
    "$lab/app/LaunchProtocol.c" "$lab/tests/protocol-test.c" -o "$LINUX_LAB_ARTIFACTS/protocol-test"
"$LINUX_LAB_ARTIFACTS/protocol-test"
TMPDIR="$LINUX_LAB_ARTIFACTS" PYTHONDONTWRITEBYTECODE=1 python3 "$lab/tests/test_packages.py"
