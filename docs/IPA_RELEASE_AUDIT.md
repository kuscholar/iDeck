# IPA release preparation — 2026-10-25

## Build 56 follow-up release

[v0.1.3-alpha.2](https://github.com/kuscholar/iDeck/releases/tag/v0.1.3-alpha.2)
adds the sequential launcher and bilingual setup guide. Full compilation, host
checks, exact Build 56 relink and certificate-free packaging passed. The 20
native static-library inputs match the reviewed Build 54 inputs. Main, StikJIT
and converter Mach-O sections match their build/input copies after packaging.
See [Build 56 evidence](release/BUILD56_EVIDENCE.json).

Build 55 was installed on Kusch and its checklist was visually observed at 6/6.
Build 56 has no fresh device/JIT/gameplay or third-party signer validation. The
Build 54 records below are historical and are not new Build 56 test results.


Status: **Build 54 engineering release checks completed; alpha assets prepared**.
See the completion record below. The earlier Build 53 findings are retained.
The owner requested skipping phone installation validation. That test is not
claimed, and its absence is not the remaining source-distribution gate.

Candidate: version 0.1.3, Build 53, source snapshot
`6fad3df2929dda0a0c9cbd49e84663be788390f0`.
SHA-256: `547189dcb8c94cb5c20b1fcdc50de124b16bbf89194812f8fd2f3a2e0d64a304`.
This audit does not relabel an old binary as newly rebuilt.

## Build 54 completion

- Rebuilt StikJIT 1.9.0 with idevice v0.1.68 from fixed source commits and the
  upstream Cargo.lock, replacing the opaque precompiled FFI archive.
- Rebuilt the same component from exported source trees and vendored dependencies
  with `CARGO_NET_OFFLINE=true`. This verifies the source package's StikJIT path;
  it is not a claim of a fresh-machine rebuild of the entire Madeira runtime.
- Recorded 162 normal target input packages with zero missing license texts.
  Nested notices and the six explicit supplemental notices are retained.
- All 17 Swift imports used by the prior helper are provided by the new framework.
  Full Build 54 Xcode compilation passed with the rebuilt component and new notices.
- Included corrected Wine license notices and LLVM-MinGW runtime notices in
  the actual app. Source archives, pinned manifests and a Build 54 relink kit
  accompany the IPA. The portable relink recipe was executed successfully.
- Packaged the alpha with certificate-free ad-hoc signatures, retaining the
  helper and debugging entitlement requests. Profiles, pairing data, Steam/CEF,
  games and local Wine Mono are excluded. Recipients must re-sign it themselves.
- Completed the component-by-component
  [engineering licensing review](release/LICENSING_REVIEW.md). No external
  lawyer opinion is represented as obtained. The inherited recommendation
  is no longer presented as a component-license condition.

The remaining limits are testing boundaries, not undisclosed completed checks:
the owner requested skipping phone installation; different-account sideloading,
JIT and gameplay were not revalidated for this alpha. The release is experimental.

## Completed checks

- Inventoried and SHA-256 hashed all 1,204 IPA files; ZIP CRC checks passed.
  Checked prefix-template member names as well. No excluded Valve executable,
  selected authentication filename, provisioning profile or signature-resource
  directory found. This is a scoped check, not proof of the absence of all secrets.
- The original converter input matches the pinned upstream SHA-256
  `073f903be98e973ff38f4d79f2c48d61ef938754a77b1caedda79c9f05a068c2`.
  After removing signatures on temporary copies, the input and packaged library
  are byte-identical (SHA-256
  `41cce9b38d5e39f513da21ad6ee9ecc940a38a44899041106b14bac140da5daf`).
  The full Apple agreement and notices are present in the IPA. Section 2.B of
  that agreement expressly addresses distribution for shader conversion;
  sections 2.C–E and the other conditions still apply. This corrects the earlier
  blanket statement that no redistribution basis had been found. It does not
  establish clearance for every component of the assembled application.
- The local StikJIT framework input is byte-identical to the official 1.9.0
  release's iOS arm64 slice: SHA-256
  `f15ad5c6766fa07d545be283c1c99eccde6a8baa97d73978a09ec080ca6381df`.
  Its tagged source was retrieved at
  `32287268fa5824f9edce4cb359f5833ce0cf7b00`.
- Archived 21 pinned source trees, including nested build dependencies.
  Excluded upstream precompiled test corpora and documentation-site submodules;
  the exclusion list records their revisions. These archives are not yet labeled
  complete corresponding source for every binary.
- Retrieved LLVM source revision
  `8dfdcc7b7bf66834a761bd8de445840ef68e4d1a`, resolving the abbreviated build-doc
  pin, and vendored the pairing library's locked Rust dependencies.
- Collected 103 main-library link inputs. Relinking on the current Mac passed.
  Added a new test symbol to a temporary GnuTLS archive, relinked, and verified
  the symbol is defined in the resulting Mach-O. Restored the original inputs.
  This demonstrates that a static library can be replaced; it does not prove
  clean-machine rebuilding of all dependencies or on-device execution.
- Extracted and re-signed a disposable candidate copy with matching development
  profiles using `tools/resign-app.py`; `codesign --verify --deep --strict` passed.
  No credentials or profiles belong in public assets. This was the maintainer's
  existing identity, not Sideloadly/AltStore or a different tester's account.

## Build 53 investigation and gates (superseded by completion above)

394 candidate `.dll`/`.exe`/`.dylib` files exactly match blobs in the working
Madeira baseline `ee9fd2f4c21229dfce31a25c211d44df267336d8`. That establishes
artifact origin, not source reproducibility. A further comparison resolved the
i386 farm's origin: **all 729 files exactly match** the official Madeira 0.1.3
IPA (SHA-256 `71e900cbc140778bd6fa67c1062821981ed98e6bfb674d853cfeefd6d242e1c0`).
That release points to Madeira `4e9d45a74294cd820120791c4b3f2b79adf4fc70`,
Wine `4f5b19718f4de88ecc5cb0dc08b119497a67ba8f` and
DXMT `35a4db11bd1bda380c5176a3bc6c1878f7192101`. The historical Wine notice
confirms LGPL-2.1-or-later; both historical source archives were retrieved.
They must accompany the current source snapshot, whose pins differ.
The inherited i386 build recipe still describes an unverified macOS translation
of the WSL recipe; no clean i386 rebuild was performed here.

Before publishing the candidate:

1. Complete mapping of remaining generated/runtime binaries to exact source,
   patches and build inputs; keep the verified historical i386 mapping above.
2. Verify correspondence for the LLVM-containing combined archive and finish
   transitive notices/source mapping, including the precompiled idevice library
   carried in the StikJIT source release.
3. Package the verified source, relink inputs, notices and portable recipes
   together, hash them and inspect the final public assets. Current preparation
   materials remain private; copying an entire private build directory is unsafe.
4. Resolve the assembled-work review items recorded in
   [LICENSING.md](LICENSING.md). This engineering audit is not a legal opinion.

Public release notes must state installation/JIT testing was skipped at the
owner's request. Do not claim AltStore/Sideloadly compatibility, a successful
clean-source rebuild, or newly validated gameplay.

Concrete StikJIT follow-up: the tagged source embeds `idevice/libidevice_ffi.a`.
Its embedded registry paths identify 111 crate/version pairs, including
`aws-lc-rs-1.16.2`, `async-compression-0.4.41` and `mdns-sd-0.19.2`, which are
not covered by the app's existing pairing-crate notice list. These paths come
from the input static archive, **not** a proof that all 111 crates survive
dead stripping into StikJIT. Resolve the library's source/lock/build provenance
and the linked subset, or rebuild from a documented source lock and regenerate
the appropriate notices. A guessed dependency list is not completion evidence.

## Reproduce scoped checks

```sh
python3 tools/audit-ipa.py candidate.ipa --output ipa-inventory.json
python3 -m unittest discover -s tests/release
python3 tools/prepare-relink.py /path/to/build.log /new/private/relink-directory
python3 /new/private/relink-directory/relink.py
```

To re-sign on macOS, extract the candidate using `ditto -x -k` into a disposable
directory. Obtain **your own** matching development profiles for the main app
and JIT helper through Xcode. Both must allow debugging. The helper must remain
present. This tool intentionally does not silently change bundle IDs or log in
to Apple:

```sh
python3 tools/resign-app.py unpacked/Payload/Madeira.app \
  --identity YOUR_SIGNING_IDENTITY \
  --keychain "$HOME/Library/Keychains/login.keychain-db" \
  --app-profile /path/to/main.mobileprovision \
  --helper-profile /path/to/helper.mobileprovision
```

Successful signing does not activate JIT, install the application or supply Steam.
Recipient signing-tool compatibility still requires separate validation.
