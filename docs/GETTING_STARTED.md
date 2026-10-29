# Building iDeck from source

For the packaged alpha, see [IPA installation](INSTALL_IPA.md). The release's
source and relink companion assets contain inputs omitted from Git and avoid
depending on the maintainer's private directory. A complete clean-machine build
of every Madeira runtime component remains unverified.

The public snapshot is source-only and is **not yet a self-contained clean-room
one-command build**. The private development checkout is not a reproducible
public dependency source. Follow docs/BUILDING.md and preserve its component
pins; read docs/DISTRIBUTION.md before sharing binaries.

1. Clone recursively and verify docs/PROVENANCE.json pins. Initialize nested
   FEX/DXMT dependencies at their pinned commits; do not modify FEX with AI code.
2. Install Xcode and the Wine/FEX/LLVM-Mingw prerequisites from BUILDING.md.
   The iDeck helper needs x86_64-w64-mingw32-clang (LLVM_MINGW or PATH).
3. Rebuild Wine PE/runtime resources and static libraries from the checked source
   using the inherited build scripts. Public source excludes the prebuilt PE,
   archive and prefix-template artifacts listed in PUBLIC_SOURCE_EXCLUSIONS.json.
   Reconstruct the Wine prefix using the documented prefix/bootstrap scripts;
   no authenticated development prefix is provided.
4. Build StikJIT1.9.0 with pinned idevice source using
   [the release recipe](../build/stikjit-source/README.md); honor its MPL/idevice
   notices. Obtain Apple's converter under its own agreement, or use the
   separately licensed library in the IPA for its permitted shader-conversion
   purpose. It is excluded from the Git source tree.
5. Build with SteamClientInstaller.swift and the pinned SteamClientPackages.json
   resource (the Xcode target includes both). After Prepare runtime, use
   Download & Install Steam. No Valve binaries need to be bundled or imported.
   This branch downloads the full official pinned legacy client on device;
   [verification and unfinished device/support gates](AUTOMATIC_STEAM_INSTALL.md)
   remain explicit. Manual repair/import is available if Valve removes packages.
   Do not use repacks or copy another installation's login cache.
6. Open app/Madeira.xcodeproj, select Madeira and your own development team. The
   new app ID is com.kuscholar.ideck.steamui; use a suffix-compatible unique ID
   for your team. Internal filenames remain Madeira for build compatibility.
7. Build/sign for your own device. Use the existing authorized pairing/JIT flow.
   Launch iDeck and let the user complete genuine Steam authentication/Guard.

Example after all prerequisites have been prepared:

```sh
xcodebuild -project app/Madeira.xcodeproj -scheme Madeira \
  -configuration Debug -destination 'generic/platform=iOS' \
  CODE_SIGNING_ALLOWED=NO build
```

This command is a build invocation, not proof the missing assets are prepared.
No iPad success or general game compatibility is implied. See IDECK.md and the
POC evidence for actual device results and remaining failures.
