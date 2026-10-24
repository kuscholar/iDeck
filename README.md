<p align="center"><img src="docs/assets/ideck/icon.png" width="156" alt="iDeck cyan and blue iD controller icon"></p>
<h1 align="center">iDeck</h1>
<p align="center"><strong>Your iPhone. Your iPad. Your PC games.</strong><br>Genuine Steam Big Picture, running locally on iOS and iPadOS.</p>
<p align="center"><a href="COPYING">GPL-3.0-or-later</a> · <a href="CREDITS.md">Built on Madeira</a> · <a href="docs/GETTING_STARTED.md">Build & setup</a> · <a href="docs/IDECK.md">Technical status</a></p>

Bring a Steam Deck-style handheld experience to the Apple device you already own.
iDeck is an experimental, open-source launcher that runs Valve's real Windows
Steam client and compatible PC games **on the device**, using Madeira's
Wine/FEX/Metal runtime. No gaming PC stream is required.

**This is a SteamOS-style experience, not the Linux SteamOS operating system.**
Windows instructions are translated; “local” does not mean an ARM-native Steam
binary or a native port of every game. iDeck is independent and is not affiliated
with or endorsed by Valve, Apple, Madeira or DroidDeck.

## What iDeck adds

- Genuine Steam Big Picture rather than a recreated library interface.
- A setup launcher and a Steam-owned sign-in/account entry; saved login stays in Steam.
- Physical controller integration, direct touch and an on-screen virtual controller.
- A movable floating menu for keyboard, controls, Steam menu and graceful game exit.
- Isolated Steam/CEF compatibility work, diagnostic programs and reproducible evidence.

## Current status — experimental

Development targets iPhone and iPad. Actual device evidence currently comes from
an **iPhone 15 Pro Max (A17 Pro)**; iPad operation is a target, not validated here.
Real Steam login, saved-login reuse and Big Picture/library browsing have been
observed in earlier builds. A PC game has run, including user-reported gameplay.
These results do not establish broad compatibility. Startup and post-login
transitions remain unreliable. Latest Build51/52 logs report successful saved
login and BrowserReady, but final interactive navigation is pending confirmation.
Virtual-controller recognition in Windows does not establish every Steam/game
input path; Bluetooth, reliable game return and long-session stability remain open.

JIT through Madeira's authorized pairing/debug workflow is required. No jailbreak
or private entitlement is assumed. Game ownership, Steam Guard and license checks
remain Valve's responsibility. This is not a DRM bypass or a way to run every PC
game, and anti-cheat compatibility is not promised.

## Build and run

This first public version is **source-only**: no IPA, Steam client, games, signed
profiles or proprietary Apple runtime library is published. It is not a
one-click build from this snapshot. Read [setup and missing prerequisites](docs/GETTING_STARTED.md),
[Madeira build instructions](docs/BUILDING.md), [JIT](docs/JIT.md), and
[distribution requirements](docs/DISTRIBUTION.md) first.

```sh
git clone --recurse-submodules https://github.com/kuscholar/iDeck.git
cd iDeck
```

The Xcode project remains `app/Madeira.xcodeproj` and the scheme `Madeira` to
preserve the inherited build system. The app displays **iDeck**, uses the cyan/blue **iD** controller icon supplied
for this project, and defaults to its own `com.kuscholar.ideck.steamui` development identifier.
Select your own development team. Do not overwrite an existing Madeira app or copy
its authentication caches. Obtain Steam through Valve's legitimate channels and
sign in yourself; the previously tested legacy client is not bundled here.

## Foundation and inspiration

**Most of this project's runtime and build system is Will Faust's Madeira.**
iDeck is a derivative source snapshot of the existing iDeck experiment, not a
newly invented compatibility stack. [Exact provenance and submodule pins](docs/PROVENANCE.json)
link to the original history. [CREDITS.md](CREDITS.md) names the projects and people
whose work makes it possible.

[DroidDeck](https://github.com/Droid-Deck/DroidDeck) is the product-experience
inspiration: a genuine Steam handheld interface on a mobile device. iDeck uses
Madeira's iOS architecture, not DroidDeck's Android/ARM64 Proton implementation;
no DroidDeck code or artwork was imported for this snapshot.

## License and credit

The iDeck-authored additions are **GPL-3.0-or-later**, with the existing
[Madeira Converter Exception](LICENSE-EXCEPTION.md) for code whose rights holders
grant it. Upstream files and components keep their own terms, including LGPL,
MIT, BSD and MPL. All existing copyright notices, license texts and component
notices are retained. See [NOTICE](NOTICE), [CREDITS.md](CREDITS.md),
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) and [COPYING](COPYING).

Publishing this source is not a declaration that an assembled IPA satisfies all
Apple, Valve or open-source distribution terms. Binary redistribution remains
gated by corresponding-source, relinking and proprietary-library review described
in [docs/DISTRIBUTION.md](docs/DISTRIBUTION.md). Steam, SteamOS and Steam Deck are
Valve trademarks; iPhone, iPad, iOS and Metal are Apple trademarks.
