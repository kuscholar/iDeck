# Alpha source and relink companion assets

The alpha release carries three substantive packages plus an audit/notice asset
and SHA-256 checksums. The IPA has no developer certificate or profile.

## Source package

`iDeck-0.1.3-alpha.3-source.tar.gz` contains the release's Git source snapshot,
pinned current component source archives, additional historical Wine/DXMT sources
for the original i386 farm, pinned LLVM source, and exported StikJIT/idevice
source with locked vendored Rust dependencies. `SOURCE_MANIFEST.json` records
archive roles, revisions and hashes. StikJIT's old opaque static archive is
intentionally omitted from the exported source tree because the new build
generates its replacement from source.

Extract the iDeck source archive first. Extract current component archives into
that checkout in parent-before-child order, preserving the prefixes recorded in
the manifest. Historical component archives are separate source references for
the i386 binaries and must not overwrite the current checkout's submodules.
Alternatively, use a recursive Git clone of the exact release tag.

See `build/stikjit-source/README.md` to rebuild the framework from the exported
source trees. The source archive's idevice `.cargo/config.toml` uses the included
vendor directory; the checksummed source manifest intentionally excludes that
local build configuration. The archive's `README-REBUILD.md` gives its layout.
The same StikJIT component was rebuilt with networking disabled during preparation.

The Apple SDK, Swift/Rust toolchains and signing identity are installed by the
recipient. The entire Wine/FEX/DXMT runtime has not been freshly rebuilt from
scratch on another machine in this release; do not mistake the verified component
rebuild or supplied sources for that broader test.

## Relink package

`iDeck-0.1.3-alpha.3-relink.tar.gz` contains 103 exact inputs from Build 67's
main-library link, a hash manifest, portable link arguments and `relink.py`.
To replace an LGPL library, build its source for the matching iOS arm64 target
using its supplied recipe, replace the appropriate archive in `libraries/`, then:

```sh
python3 relink.py
```

The output is `Madeira.debug.dylib`. Extract the IPA with `ditto -x -k`, replace
that file in `Payload/Madeira.app`, and use your own main/helper profiles with
`tools/resign-app.py`. Retain the helper and re-sign nested code. No maintainer
key, provisioning profile or login cache is needed or supplied.

The portable link command was run successfully. A modified static-library symbol
was also linked and verified during preparation. This is local evidence; Build 67 was installed and the user confirmed Steam file recovery restored use.
This does not validate all gameplay or another-account sideloading. Build 55 checklist observation is recorded separately. See [IPA installation](../INSTALL_IPA.md).

## Rebuild the application shell

After staging the documented runtime resources (available in the IPA) and native
archives (in the relink companion), the actual Build 67 invocation was:

```sh
LLVM_MINGW=/path/to/llvm-mingw-20260421-ucrt-macos-universal \
xcodebuild -project app/Madeira.xcodeproj -scheme Madeira \
  -configuration Debug -destination 'generic/platform=iOS' \
  -derivedDataPath /new/private/build \
  CODE_SIGNING_ALLOWED=NO CURRENT_PROJECT_VERSION=67 \
  IPHONEOS_DEPLOYMENT_TARGET=26.0 \
  MADEIRA_BUNDLE_IDENTIFIER=com.kuschqin.madeira.steamui \
  LD_GENERATE_MAP_FILE=YES build
```

This preserves the existing test app ID; use coherent main/helper identifiers
when signing for your own account. See `docs/BUILDING.md` for the remaining
source-build dependencies and generated Wine/FEX headers. No full clean-machine
application rebuild claim is made.

To package a prepared unsigned Xcode product without profiles/certificates:

```sh
python3 tools/package-ipa.py /path/to/Madeira.app output.ipa \
  --entitlements app/Madeira/Madeira.entitlements
```

The packaging tool validates nested ad-hoc signatures and excludes provisioning
profiles/local Mono. It inventories the resulting archive and prefix members.
Signing requests do not grant privileges: recipient profiles must actually allow
the permissions required by the debugging/JIT workflow.
