# Credits

## Primary foundation — Madeira

**Will Faust and the Madeira contributors** created the iOS runtime, integration
and build system on which iDeck depends. Their work is the substantial foundation
of this repository, not merely an incidental dependency.

- [Madeira upstream](https://github.com/willfaust/Madeira)
- [Source snapshot history](https://github.com/kuscholar/Madeira/tree/b6ea0dc11543973148c3f54ef81f44724333d4da)
- [Pinned source and components](docs/PROVENANCE.json)
- [Original README retained](docs/MADEIRA_UPSTREAM_README.md)

## Compatibility, graphics and device tooling

| Project / contributors | Role | Terms / notices |
|---|---|---|
| [Wine](https://www.winehq.org/), Wine authors, and [Will Faust's iOS branch](https://github.com/willfaust/wine/tree/madeira-lgpl) | Windows API and process compatibility | Pinned branch LGPL-2.1-or-later; `wine/LICENSE-MADEIRA.md`, file notices, `docs/wine-lgpl-provenance.md` |
| [FEX-Emu](https://github.com/FEX-Emu/FEX), Ryan Houdek and contributors; Will Faust's port | x86/x64 instruction translation on ARM64 | MIT upstream; Madeira modifications GPL-3.0-or-later as specified in `FEX/LICENSE-MADEIRA.md` |
| [DXMT](https://github.com/3Shain/dxmt), Feifan He and contributors; Will Faust's port | Direct3D to Metal | MIT upstream plus fork notices; `dxmt/LICENSE-MADEIRA.md` |
| David Acevedo and other DXMT/DXSO contributors | Direct3D9 frontend | LGPL-2.1-or-later parts; detailed file-level notices retained |
| Madeira D3D12 / Will Faust | Experimental D3D12 runtime | `madeira-d3d12/LICENSE` and original file notices |
| [Madeira Dock](https://github.com/willfaust/madeira-dock), Jfishin / SwiftSteam contributors | Inherited Steam library/sign-in infrastructure | Component/file licenses and documented permission provenance in `docs/STEAM_SIGNIN.md` |
| [StikJIT / StikDebug](https://github.com/StikDebug/StikJIT) | Authorized JIT/debug tooling | MPL-2.0; source/version links in `docs/JIT.md` |
| [idevice](https://github.com/jkcoxson/idevice), Jackson Coxson and contributors | Device pairing | MIT; pinned Rust dependency notices in `app/Madeira/legal/` |
| GnuTLS, GMP, Nettle, FFmpeg, Wine Mono, libxml2, libxslt and their contributors | Crypto, media, .NET and XML support | Per-component LGPL/MIT/BSD/zlib/other terms in `THIRD-PARTY-NOTICES.md`, `LICENSES/` and component source |
| fmt, SoftFloat, Cephes, xxHash, zstd, rpmalloc and other bundled libraries | Runtime utilities | Original notices retained; see component inventory |

This table is an overview, not a replacement for exhaustive inherited notices.
No whole-directory authorship is claimed. Copyright holders named in individual
files retain their rights. FEX's no-AI-contribution policy is respected: the iDeck
experiment does not modify FEX.

## Research and experience inspiration

- [deezhizyu/madeira](https://github.com/deezhizyu/madeira): historical Steam/CEF
  architecture research; historical observations are distinguished from new tests.
- [DroidDeck](https://github.com/Droid-Deck/DroidDeck): handheld Steam experience
  inspiration. No code/artwork imported for the iDeck snapshot; no affiliation.
- **Valve**: Steam, Big Picture and PC gaming ecosystem. Valve's proprietary
  client, games and authentication materials are not licensed by this repository
  and are not included in the public source payload.

## iDeck changes

The kuscholar iDeck derivative adds the product launcher, Steam UI experiments,
controller/input integration, movable menu, diagnostic tests and original branding.
Changes and evidence are recorded in `docs/BIG_PICTURE_POC_RESULTS.md` and the
`IDECK_*` documents. Current iD app icon supplied by the project owner; the previous Imagegen design
is retained as design history. Asset provenance is in `docs/assets/ideck/README.md`.
