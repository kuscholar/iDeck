# iDeck licensing and distribution scope

Review date: 2026-10-24. This is an engineering license inventory and release gate,
not a guarantee of legal clearance for every combination or jurisdiction.

## This public repository

This is a **source snapshot**, with exact origin/revisions in PROVENANCE.json.
Existing source, component license texts, notices and attribution are retained.
Compiled runtime/app payloads are ignored and not committed; the private local
copy may contain such resources for development. See PUBLIC_SOURCE_EXCLUSIONS.json.
No previous Git history containing compiled/proprietary payloads is imported;
upstream history is explicitly linked rather than claimed as new authorship.
Source archives for GNU/FFmpeg dependencies remain with their checksums/scripts.

Our modifications date from2026-10-22 through2026-10-24, including the iDeck
launcher, Steam experiments, controller handling, diagnostics and branding.
Original/new iDeck work is GPL-3.0-or-later plus the Madeira Converter Exception
version1 for our own contributions. Other authors' grants are not expanded.
Retain COPYRIGHT headers, COPYING, LICENSE, LICENSE-EXCEPTION, LICENSES,
THIRD-PARTY-NOTICES and all submodule notices when redistributing.

## Exact component rules

- Wine pin is the **madeira-lgpl** branch, LGPL-2.1-or-later, not the historical
  GPL-converted branch. `wine/LICENSE-MADEIRA.md` and file-level notices control.
  Top-level native Wine-derived source keeps its original file notices.
- FEX/DXMT upstream MIT terms remain; Madeira-authored changes have their fork's
  GPL/additional-permission terms. DXMT's D3D9/DXSO LGPL portions stay LGPL.
- StikJIT is MPL-2.0; preserve notices and provide corresponding covered source
  for any distributed version/modifications. idevice is MIT; retain its notice
  and the complete Rust dependency notices pinned in Cargo.lock.
- GnuTLS, GMP, Nettle, FFmpeg and other static dependencies require exact
  source/build options and applicable relinking rights for binary distribution.
- The inherited SwiftSteam permission provenance is retained verbatim in
  docs/STEAM_SIGNIN.md. This audit does not invent a new grant or eliminate
  upstream permission uncertainty.

## Before publishing an IPA or runtime package

No public binary release is approved by this source publication. First:

1. Resolve the upstream notice's open assembled-work/Apple exception questions.
   An exception applies only to code whose holder granted it, not all dependencies.
2. Provide the exact corresponding source, nested dependency pins, patches and
   build scripts for every shipped covered binary, including generated outputs.
   Build and document a usable relink/re-sign path or required object material
   for LGPL components; source links alone are not an automatic substitute.
3. Obtain Apple Metal Shader Converter under Apple's own agreement. Do not assume
   GPL, our exception, or the upstream repository grants Apple's redistribution
   permission. The converter binary is excluded here. Preserve headers' own terms.
4. Audit StikJIT, Wine Mono, FFmpeg and transitive dependencies against the actual
   resulting package and attach their required source/notices as appropriate.
5. Never bundle Steam/CEF/Valve files, Microsoft redistributables or games merely
   because they are on the development phone. Obtain/distribute only under their
   applicable owner terms; this repo grants no rights to them. Do not publish
   authentication data or patched proprietary binaries.
6. Use your own authorized Apple developer identity and device pairing. Do not
   ship development credentials, profiles, private entitlements or pairing files.

The inherited THIRD-PARTY-NOTICES and LICENSE-EXCEPTION explicitly identify open
binary-distribution issues. Those issues are not silently marked solved here.

## References

- GNU GPLv3 sections4–6 and7: https://www.gnu.org/licenses/gpl-3.0.html
- LGPL2.1 section6: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html
- MPL2.0: https://www.mozilla.org/en-US/MPL/2.0/
- Component-specific copies are included in LICENSES and pinned submodules.
