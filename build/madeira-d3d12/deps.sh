#!/bin/bash
# Resolve the Metal Shader Converter dependency for the madeira-d3d12 track.
#
# What the app build needs is in the repository, each file hash-checked here:
#   - the converter's public headers (Apache-2.0), vendored unchanged in
#     madeira-d3d12/third_party/metal-shader-converter;
#   - the iOS library, app/Madeira/d3d12/libmetalirconverter.dylib
#     (distributed under Apple's agreement, see app/Madeira/d3d12/NOTICE.txt).
# Apple's installer package is only needed for the macOS host tools (the
# macOS dylib); it stays local and is never vendored. When it is present its
# hash is checked and its headers must match the vendored copy exactly.
#
# Sourcing this script exports:
#   MSC_INCLUDE   public headers (always)
#   MSC_LIB_IOS   iOS arm64 dylib, what ships in the app (always)
#   MSC_HAVE_PKG  1 when the installer package was found and verified, else 0
#   MSC_ROOT      extraction root                        (package only, else "")
#   MSC_PAYLOAD   .../MetalShaderConverter.pkg/Payload    (package only, else "")
#   MSC_LIB_MACOS macOS universal dylib, host tools only  (package only, else "")
#
# Set MADEIRA_MSC_ROOT to an existing extraction to skip re-extracting.
# On failure it prints why and returns 1 when sourced (exits 1 when run), so a
# caller can report it instead of dying silently.
set -eu
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

_msc_fail() {
    echo "deps: $*" >&2
    return 1
}

_msc_resolve() {
    local vend="$REPO_ROOT/madeira-d3d12/third_party/metal-shader-converter"
    local ios_lib="$REPO_ROOT/app/Madeira/d3d12/libmetalirconverter.dylib"
    # Pinned in MADEIRA_NATIVE_D3D12_EXECUTION_DESIGN.md section 2. A different
    # converter is a different compiler and invalidates every cached shader.
    local pkg="$REPO_ROOT/research/GPTK/Metal Shader Converter 4.0 beta 2.pkg"
    local pkg_sha="1acc33c87ea663933df89721a998d066106685473020bcbe007cee7a16155734"
    local ios_lib_sha="073f903be98e973ff38f4d79f2c48d61ef938754a77b1caedda79c9f05a068c2"
    local have cand d

    [[ -f "$vend/SHA256SUMS" ]] || { _msc_fail "missing $vend/SHA256SUMS"; return 1; }
    (cd "$vend" && shasum -a 256 -c --quiet SHA256SUMS >/dev/null 2>&1) ||
        { _msc_fail "vendored converter headers do not match $vend/SHA256SUMS"; return 1; }
    MSC_INCLUDE="$vend/include"

    [[ -f "$ios_lib" ]] || { _msc_fail "missing $ios_lib"; return 1; }
    have="$(shasum -a 256 "$ios_lib" | cut -d' ' -f1)"
    [[ "$have" == "$ios_lib_sha" ]] ||
        { _msc_fail "$ios_lib hash mismatch (expected $ios_lib_sha, found $have)"; return 1; }
    MSC_LIB_IOS="$ios_lib"

    MSC_HAVE_PKG=0 MSC_ROOT="" MSC_PAYLOAD="" MSC_LIB_MACOS=""
    [[ -f "$pkg" ]] || return 0

    have="$(shasum -a 256 "$pkg" | cut -d' ' -f1)"
    [[ "$have" == "$pkg_sha" ]] ||
        { _msc_fail "converter package hash mismatch (expected $pkg_sha, found $have)"; return 1; }
    MSC_ROOT="${MADEIRA_MSC_ROOT:-}"
    if [[ -z "$MSC_ROOT" || ! -d "$MSC_ROOT/MetalShaderConverter.pkg/Payload" ]]; then
        # Reuse a previous extraction when one is intact, otherwise make a new one.
        for cand in /private/tmp/madeira-msc-*/expanded /private/tmp/madeira-dx12-design.*/expanded; do
            # ml880: a half-deleted /tmp extraction still has the Payload directory
            # but not every header; require one of the headers the compiler failed on.
            [[ -f "$cand/MetalShaderConverter.pkg/Payload/usr/local/include/metal_irconverter/ir_comparison_function.h" && \
               -f "$cand/MetalShaderConverter.pkg/Payload/usr/local/lib/libmetalirconverter.dylib" ]] && { MSC_ROOT="$cand"; break; }
        done
    fi
    if [[ -z "$MSC_ROOT" || ! -d "$MSC_ROOT/MetalShaderConverter.pkg/Payload" ]]; then
        d="$(mktemp -d /private/tmp/madeira-msc-XXXXXX)"
        echo "deps: expanding converter package into $d/expanded" >&2
        pkgutil --expand-full "$pkg" "$d/expanded" >/dev/null
        MSC_ROOT="$d/expanded"
    fi
    MSC_PAYLOAD="$MSC_ROOT/MetalShaderConverter.pkg/Payload"
    MSC_LIB_MACOS="$MSC_PAYLOAD/usr/local/lib/libmetalirconverter.dylib"
    [[ -e "$MSC_LIB_MACOS" ]] || { _msc_fail "extraction incomplete, missing $MSC_LIB_MACOS"; return 1; }
    # One converter version everywhere: the package's headers must be the vendored ones.
    diff -rq "$MSC_PAYLOAD/usr/local/include" "$MSC_INCLUDE" >/dev/null ||
        { _msc_fail "package headers differ from the vendored copy; run build/madeira-d3d12/fetch-converter.sh"; return 1; }
    MSC_HAVE_PKG=1
}

_msc_resolve || return 1 2>/dev/null || exit 1
export MSC_INCLUDE MSC_LIB_IOS MSC_HAVE_PKG MSC_ROOT MSC_PAYLOAD MSC_LIB_MACOS
