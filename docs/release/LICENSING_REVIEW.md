# iDeck alpha binary distribution review — 2026-10-25

This is the maintainer's engineering review of the release inputs and fulfillment
of their distribution requirements. It is not represented as a lawyer's opinion.
The inherited Madeira working document is retained in `docs/LICENSING.md`.
For iDeck, its recommendation to obtain lawyer review is not treated as an
additional copyright license condition or a claim that such review occurred.
The release decisions below are specific to this alpha and its companion assets.

| Component | Release basis | Material supplied |
|---|---|---|
| Madeira/iDeck original code | GPL-3.0-or-later, with the adopted Converter Exception for the licensors' own work | Source snapshot, notices, original license and exception; own additions follow CONTRIBUTING.md |
| Wine, native side and PE builtins | LGPL-2.1-or-later branch; current and historical i386 pins identified separately | Exact source archives, native source/patch files, build recipes, application objects/static libraries and a tested relink recipe |
| FEX, DXMT and rpmalloc | Upstream MIT/0BSD; fork changes under GPL plus the original authors' additional permission | Pinned source trees and nested dependency archives; original license/exception texts; no new FEX edits |
| DXMT D3D9/DXSO | LGPL-2.1-or-later retained | Source, notices, object/library relink materials |
| GMP/Nettle/GnuTLS/FFmpeg | LGPL selections retained; FFmpeg GPL/nonfree features disabled per its recipe | Hash-verified upstream source archives, configure/build scripts, notices and tested application relink inputs |
| LLVM and compiler runtimes | Apache-2.0 with LLVM exception; MinGW runtime components retain their individual notices | Pinned LLVM source, toolchain pin/recipe, LLVM and MinGW runtime notices |
| StikJIT | MPL-2.0 retained | Exact tagged Swift/JS source; new source-build recipe and covered-source availability notice |
| idevice FFI for StikJIT | MIT; built from v0.1.68 rather than the opaque upstream archive | Fixed source commit, Cargo.lock, generated header, vendored locked dependencies and generated notices for 162 input packages |
| In-app pairing library | Existing MIT/Apache/BSD/ISC dependency selections; wrapper under GPL | Source, Cargo.lock, vendored dependencies and existing crate notices |
| Apple Metal Shader Converter | Its own agreement, section 2.B for shader conversion, subject to the agreement's remaining conditions | Unmodified library code aside from signatures, full agreement, notices and header Apache license; Apple-only runtime |
| Apple OS/SDK libraries | System/compiler components, supplied by the recipient's Apple toolchain/OS | Build requirements; no SDK, signing key, developer profile or device pairing material in public assets |
| Steam/client/games | Independent user-obtained software | No Valve client, CEF, game, authentication cache or Microsoft redistributable bundled |

The GPL application terms do not restrict modification for private use or
reverse engineering needed to debug modifications of LGPL libraries. The
companion relink package contains the application objects and static archives;
recipients can replace libraries and relink. The release also supplies the source
and scripts. Re-signing instructions require recipients' own development identity
and profiles; no maintainer signing key is required. Installation/JIT validation
was explicitly skipped at the owner's request and is not reported as passed.

The original Wine GPL-converted branch is not used. The retired branch's
exception problem must not be projected onto these LGPL branch binaries.
Apple's agreement grants rights only for Apple software, and the Madeira
exception grants rights only for code covered by its licensors' permission.
Neither text is described as granting rights for unrelated components.

The six omitted crate license files are handled explicitly: three compression
crate license texts were retrieved from their exact published VCS commits;
the three Jackson Coxson crates retain their manifest's MIT declaration and
author attribution, accompanied by the MIT permission/disclaimer text. No
copyright dates or extra grants were invented. See `LICENSES/stikjit-supplemental`.
All vendored source notices remain intact. The input dependency inventory is a
conservative set before dead stripping, rather than a claim every crate survives
into the framework.
The pairing library was also re-inventoried: 108 normal input packages, zero
missing license texts. Its published idevice crate omits the workspace-root MIT
file; that exact file was recovered from the pinned upstream workspace and
provided with an origin record rather than inventing a new notice.

This review does not promise freedom from all third-party claims, ownership
certainty beyond the published upstream grants, platform approval, or trademark
permission. Steam/Steam Deck/SteamOS references identify compatibility goals;
iDeck is independent and must not claim Valve endorsement or distribution of
Linux SteamOS. No authentication, Steam Guard, entitlement or DRM bypass is part
of the release.

License texts controlling these decisions are supplied with the assets. Primary
references: [GPLv3](https://www.gnu.org/licenses/gpl-3.0.html),
[LGPL2.1](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html),
[MPL2.0](https://www.mozilla.org/en-US/MPL/2.0/),
[MIT](https://opensource.org/license/mit),
[Apache2.0](https://www.apache.org/licenses/LICENSE-2.0), and the included Apple
Metal Shader Converter agreement. Preserve each component's own terms when
redistributing or modifying this combination.
