# Building iDeck from source

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
4. Build/fetch the exact StikJIT1.9.0 component from its official source/release,
   as documented in JIT.md, and honor its MPL/idevice notices. Obtain Apple's
   proprietary converter only under Apple's agreement; it is not published here.
5. Supply a legitimate full Steam client/CEF tree in the app's isolated prefix.
   Current experiments use an older32-bit Windows Steam version; no supported
   clean acquisition/download installer is delivered in this snapshot. Do not
   download third-party repacks or copy another installation's login cache.
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
