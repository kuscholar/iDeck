#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
# HOST only. Use immutable namespaced archive from build-symbol-isolated.py.
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
: "${LINUX_LAB_NAMESPACE_BUILD:?Prepared namespace-host output}"
: "${LINUX_LAB_NAMESPACE_TEST_OUT:?Fresh private external output}"
: "${LD_LLD:?Explicit Linux linker}"
case "$LINUX_LAB_NAMESPACE_TEST_OUT" in /Volumes/easystore/*) ;; *) exit 2;; esac
[[ ! -e "$LINUX_LAB_NAMESPACE_TEST_OUT" ]] || exit 2
out="$LINUX_LAB_NAMESPACE_TEST_OUT"; mkdir -m 700 "$out"
lab="$repo/experiments/linux-steam";src="$repo/vendor/LinuxRunner"
build="$LINUX_LAB_NAMESPACE_BUILD/build"
flags=(-DIDECK_LAB_LINUX_SYMBOL_NAMESPACE=1 -include "$LINUX_LAB_NAMESPACE_BUILD/LinuxSymbolNamespace.h")
xcrun clang -fsanitize=address,undefined -Wall -Wextra -Werror -c "$lab/tools/symbol-regular-current-control.c" -o "$out/regular.o"
xcrun clang -fsanitize=address,undefined -Wall -Wextra -Werror "${flags[@]}" -c "$lab/tools/symbol-current-selector-control.m" -o "$out/selector.o"
# A forgotten adapter include can bind incorrectly to Wine's ordinary global.
# Reject it from Linux-only inputs before a combined link, rather than execute
# an intentionally ABI-invalid TLS lookup. This negative object stays private.
cat > "$out/consumer.c" <<'EOF'
#include "kernel/task.h"
struct task *ideck_consumer(void) { return current; }
EOF
xcrun clang -DGUEST_ARM64=1 -DENGINE_ASBESTOS=1 -I "$src" -I "$build" -c "$out/consumer.c" -o "$out/forgotten.o"
if python3 "$lab/tools/audit-linux-symbols.py" "$out/forgotten.o" > "$out/negative-audit.log" 2>&1; then exit 2; fi
xcrun clang -DGUEST_ARM64=1 -DENGINE_ASBESTOS=1 "${flags[@]}" -I "$src" -I "$build" -c "$out/consumer.c" -o "$out/consumer.o"
python3 "$lab/tools/audit-linux-symbols.py" "$out/consumer.o" "$build/libish.a" "$build/libish_emu.a" "$build/libfakefs.a"
xcrun clang -fsanitize=address,undefined -DGUEST_ARM64=1 -DENGINE_ASBESTOS=1 -DLOG_HANDLER_DPRINTF=1 -DISH_INTERNAL=1 \
    "${flags[@]}" -I "$src" -I "$build" -I "$lab/app" -Wall -Wextra -Werror -Wno-unused-parameter \
    "$lab/app/LinuxLabRuntime.c" "$lab/app/LabDeviceFS.c" "$lab/app/LabBridge.c" "$lab/app/LaunchProtocol.c" \
    "$lab/tools/symbol-namespace-control.c" "$out/regular.o" "$out/selector.o" \
    -L "$build" -lish -lish_emu -lfakefs -lsqlite3 -framework Foundation -o "$out/control"
mkdir "$out/root"
xcrun clang --target=aarch64-linux-gnu --ld-path="$LD_LLD" -nostdlib -static -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra -Werror \
    "$lab/guest/probe.c" "$lab/guest/clone.S" -Wl,-e,_start -o "$out/root/probe"
python3 - "$out" <<'PY'
from pathlib import Path
import hashlib,json,subprocess,sys
out=Path(sys.argv[1])
with (out/'control.log').open('xb') as log:
    result=subprocess.run([str(out/'control'),str(out/'root')],stdout=log,stderr=log,timeout=20)
assert result.returncode==0,result.returncode
lines=(out/'root/probe-results.txt').read_text().splitlines()
assert len(lines)==16 and all(x.endswith('=PASS') for x in lines),lines
text=(out/'control.log').read_text()
assert 'tls_isolated=1 regular_fixture_unchanged=1 objc_selector_current=1 elf_status=0' in text
(out/'evidence.json').write_text(json.dumps(dict(scope='HOST two real native TLS threads + synthetic regular global + actual ObjC selector + ARM64 ELF; NOT actual Wine runtime or iPad',
    status=result.returncode,elf_checks=len(lines),forgotten_adapter_refused=True,namespace_consumer_audit_passed=True,log_sha256=hashlib.sha256(text.encode()).hexdigest(),
    control_sha256=hashlib.sha256((out/'control').read_bytes()).hexdigest()),indent=2)+'\n')
print('Namespace TLS/global/ObjC controls and16 actual ELF checks PASS (host only)')
PY
