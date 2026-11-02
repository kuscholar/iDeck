#!/bin/bash
# SPDX-License-Identifier: LGPL-2.1-or-later
# Build the isolated i386 PE overlay; never edit a Wine/FEX submodule or baseline.
set -euo pipefail
task_root="$(cd "$(dirname "$0")/../.." && pwd)"
task_wine_build="${1:?Usage: build.sh absolute-wine-build absolute-new-output-dll}"
task_output="${2:?Missing output DLL path}"
task_cc="${LLVM_MINGW:?Set LLVM_MINGW}/bin/i686-w64-mingw32-clang"
test -x "$task_cc"
test -x "$task_wine_build/tools/winegcc/winegcc"
test ! -e "$task_output"
mkdir -p "$(dirname "$task_output")"
task_temp="$(mktemp -d "${TMPDIR:-/tmp}/ideck-atlthunk.XXXXXX")"
trap 'rm -rf "$task_temp"' EXIT
"$task_cc" -c -o "$task_temp/atlthunk.o" "$task_root/build/atlthunk/atlthunk_ios.c" \
  -I"$task_wine_build/include" -I"$task_root/wine/include" -I"$task_root/wine/include/msvcrt" \
  -D_UCRT -D__WINESRC__ -D__WINE_PE_BUILD -DMADEIRA_ATL_HOST_PAGE_SIZE=16384 \
  -Wall -target i686-windows -fuse-ld=lld --no-default-config -fno-strict-aliasing \
  -ffunction-sections -fasync-exceptions -ffp-exception-behavior=maytrap \
  -fms-hotpatch -fno-omit-frame-pointer -mlong-double-64 -O2 -g -gdwarf-4
cd "$task_wine_build"
for task_module in ucrtbase kernel32; do
  tools/winebuild/winebuild -w --implib -o "$task_temp/lib${task_module}.a" \
    --cc-cmd="$task_cc -D__STDC__" -b i686-windows \
    --export "$task_root/wine/dlls/$task_module/$task_module.spec"
done
tools/winegcc/winegcc -o "$task_output" --wine-objdir "$task_wine_build" \
  --cc-cmd="$task_cc -D__STDC__" -b i686-windows -Wl,--wine-builtin -shared \
  "$task_root/wine/dlls/atlthunk/atlthunk.spec" "$task_temp/atlthunk.o" \
  libs/winecrt0/i386-windows/libwinecrt0.a libs/compiler-rt/i386-windows/libcompiler-rt.a \
  "$task_temp/libucrtbase.a" "$task_temp/libkernel32.a" \
  dlls/ntdll/i386-windows/libntdll.a --no-default-config -fms-hotpatch -Wl,-debug:dwarf
echo "Built i386 ATL thunk PE with separate 16 KiB code/data pages: $task_output"
