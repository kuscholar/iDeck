# Source-built StikJIT for iDeck alpha

The release replaces StikJIT's opaque prebuilt `libidevice_ffi.a` with a locked
source build. Swift/JS remains StikJIT 1.9.0 at
`32287268fa5824f9edce4cb359f5833ce0cf7b00`; idevice is v0.1.68 at
`d32c8189c51c2789496b0768039419c3705498c3`.

Requirements: macOS/Xcode with iOS SDK, Rust with `aarch64-apple-ios`, Python 3.9+.
Obtain those two pinned Git source checkouts, then run from iDeck:

```sh
bash build/stikjit-source/build.sh /path/to/StikJIT /path/to/idevice /new/output
```

The script checks revisions and relevant source changes, uses `Cargo.lock`,
generates the C interface from that source, builds the framework, and retains
the original JavaScript resources. It does not use StikJIT's bundled prebuilt
archive, sign for a developer account or install anything.
The output's `StikJIT.framework` replaces
`app/Frameworks/StikJIT.xcframework/ios-arm64/StikJIT.framework` for an app build.
It is an iPhone device slice, not a simulator or Mac framework.
To rebuild your own modifications, set `IDECK_ALLOW_MODIFIED_SOURCES=1`.
This deliberately relaxes content checks while retaining the recorded baseline.

The companion source asset includes both pinned sources and vendored Cargo
dependencies. For offline rebuild, configure the idevice checkout's
`.cargo/config.toml` to replace crates.io with the extracted
`vendor/idevice` directory; retain its `.cargo-checksum.json` files. Pairing's
separate vendor directory and Cargo.lock are also provided. The Apple SDK and
Rust toolchain are installed separately and are not redistributed.

Generate notices after fetching/vendoring dependencies:

```sh
python3 tools/cargo-notices.py /path/to/idevice/ffi/Cargo.toml \
  --package idevice-ffi --supplemental LICENSES/stikjit-supplemental \
  --output app/Madeira/legal/LICENSES-StikJIT-source-crates.txt \
  --inventory docs/release/STIKJIT_SOURCE_DEPENDENCIES.json
```

This records normal target dependencies, excluding build-only/proc-macro inputs.
Nested upstream license and notice files are retained. A conservative inventory
can include code removed by the linker's dead stripping. StikJIT retains MPL2.0;
idevice retains MIT and each crate its own license. The original sources and
changes remain available with the release. See `docs/release/LICENSING_REVIEW.md`.
