<p align="center">
  <img src="docs/assets/ideck/icon.png" width="156" alt="iDeck">
</p>
<h1 align="center">iDeck</h1>
<p align="center"><strong>iDeck brings the SteamOS experience to iOS</strong></p>
<p align="center">
  <a href="docs/GETTING_STARTED.md"><img src="https://img.shields.io/badge/Platform-iOS%20%26%20iPadOS-007AFF" alt="iOS and iPadOS"></a>
  <a href="docs/IDECK.md"><img src="https://img.shields.io/badge/Status-Experimental-orange" alt="Experimental"></a>
  <a href="https://github.com/willfaust/Madeira"><img src="https://img.shields.io/badge/Powered%20by-Madeira-28C7D9" alt="Powered by Madeira"></a>
  <a href="COPYING"><img src="https://img.shields.io/badge/License-GPL--3.0--or--later-blue" alt="GPL-3.0-or-later"></a>
</p>

iDeck brings Valve's real Steam client in Big Picture to your iPhone and iPad,
with compatible Windows PC games running locally through **Madeira, Wine, FEX
and Metal**. Connect a controller, open your library, and give that backlog a
new home in your pocket.

Inspired by [DroidDeck](https://github.com/Droid-Deck/DroidDeck)'s mobile Steam
experience, built on [Will Faust's Madeira](https://github.com/willfaust/Madeira).
No gaming PC stream is required.

> **SteamOS experience, iOS underneath.** iDeck runs Windows Steam through
> compatibility and instruction translation. It does not install Linux SteamOS,
> and it does not make every game an ARM-native iOS app.

<p align="center">
  <img src="docs/assets/ideck/demo-landscape-ccw90-1.5x.gif" width="831" alt="Landscape iDeck demo: launching Steam and a PC game on iPhone, played at 1.5× speed">
  <br><sub>On-device demo · 1.5× playback speed · Experimental build</sub>
</p>

## Requirements and setup

This is currently an **experimental source release**, not a download-and-play
IPA. Development targets iPhone and iPad; actual device evidence so far comes
from an **iPhone 15 Pro Max (A17 Pro)**. iPad support has not been validated.
JIT is required through Madeira's authorized pairing/debug workflow. No jailbreak
or private entitlement is assumed.

Prepare the runtime, configure pairing and JIT, then launch Steam from iDeck.
Steam handles sign-in, Steam Guard and saved login. The launcher also provides
an account entry for choosing another Steam account. Game ownership and license
checks stay with Valve.

Read [setup and missing prerequisites](docs/GETTING_STARTED.md) before building.
The tested legacy Windows Steam client/CEF is not bundled, and a supported clean
acquisition/setup flow remains unfinished. Obtain software through legitimate
owner channels; do not copy another installation's authentication cache.

## Your phone, with a handheld habit

- **The real Big Picture.** Steam's own interface, account system and library.
- **Play locally.** Compatible PC games execute on the device through Madeira's
  runtime; there is no required gaming PC in the other room.
- **Bring your controller.** Physical controller integration, direct touch and an
  on-screen virtual controller are implemented, with validation still in progress.
- **Keep the little button handy.** Move the floating iDeck button wherever it
  suits you. Open the keyboard, show controls, adjust their layout, open the Steam
  menu or request a graceful game exit.
- **Keep your Steam session.** Saved authentication stays in Steam's local prefix.
  iDeck does not enter your credentials or replace Steam's authentication.

## Compatibility and current status

> **Game support is limited.** Expect only a limited selection of games to work
> with this experimental runtime—not your entire Steam library. A game may fail
> to start, render incorrectly, crash, or need device-specific settings.

For upstream game reports, check **[Madeira's official Discord](https://discord.gg/4t5mNjwCn7)**
and **[Madeira game compatibility reports on GitHub](https://github.com/willfaust/Madeira/issues?q=is%3Aissue%20compatibility)**.
Madeira's current [official README](https://github.com/willfaust/Madeira#readme)
does not publish a standalone supported-games table. These are upstream report
sources, **not an iDeck-supported-games list**: results depend on the device,
OS, runtime version and settings, and a game working in Madeira does not guarantee
it works in iDeck's Steam Big Picture path.


Real Steam login, saved-login reuse, Big Picture and library browsing have been
observed on the test iPhone. A PC game has started locally, with gameplay also
reported by the tester. Text entry and the floating menu's Steam action have
received positive device feedback.

There are still rough edges: startup and post-login transitions can hang.
Windows enumerating a controller is not proof that every Steam/game input path
works. Bluetooth, reliable game return, longer sessions and iPad testing remain
open. Recent logs reached successful login and `BrowserReady`; those events alone
do not prove an interactive home screen.

Compatibility is per game. Broad library support and anti-cheat compatibility
are not promised. This is an experiment for people who enjoy opening the hood—
including when the loading screen decides to become the main character.

See [technical status](docs/IDECK.md), [POC results](docs/BIG_PICTURE_POC_RESULTS.md)
and [login/transition evidence](docs/IDECK_LOGIN_TRANSITION_EVIDENCE.json).

## Build

```sh
git clone --recurse-submodules https://github.com/kuscholar/iDeck.git
cd iDeck
```

Follow [Getting started](docs/GETTING_STARTED.md), [Building](docs/BUILDING.md)
and [JIT setup](docs/JIT.md). The public snapshot excludes compiled runtime
payloads and requires separately prepared dependencies; this is not a one-command
clean build yet.

The inherited Xcode project is `app/Madeira.xcodeproj`, scheme `Madeira`. The
app displays **iDeck** with the cyan-and-blue **iD** icon. Select your own Apple
development team and a unique identifier; the source defaults to
`com.kuscholar.ideck.steamui`. Keep existing Madeira installs and their data
separate.

No public IPA, Steam/CEF client, games, account caches, signing profiles or
proprietary Apple runtime library is included. Read the
[distribution requirements](docs/DISTRIBUTION.md) before sharing a built package.

## Feedback

[Open an issue](https://github.com/kuscholar/iDeck/issues) with your device,
build, steps to reproduce and redacted diagnostics. Tell us what actually
appeared on screen, not just whether compilation passed. Never attach passwords,
tokens, Steam Guard details, pairing files or account identifiers.

## Credits

**Madeira is the foundation of iDeck.** Will Faust and the Madeira contributors
created the substantial runtime, graphics/device integration and build system
used here. iDeck adds its launcher experience, Steam UI integration, input work,
diagnostics and compatibility experiments; it does not claim authorship of that
underlying stack.

Thanks to the Wine, FEX-Emu, DXMT, StikJIT/StikDebug, idevice and other upstream
contributors, and to the historical CEF research in
[deezhizyu/madeira](https://github.com/deezhizyu/madeira).

[DroidDeck](https://github.com/Droid-Deck/DroidDeck) inspired the product direction
and this README's straightforward structure. iDeck uses Madeira's iOS runtime,
not DroidDeck's Android/ARM64 Proton implementation. No DroidDeck code or artwork
was imported for this snapshot; the README text here is written for iDeck.

Full attribution: [CREDITS.md](CREDITS.md), [NOTICE](NOTICE),
[third-party notices](THIRD-PARTY-NOTICES.md) and
[exact source/component provenance](docs/PROVENANCE.json).

## License

The iDeck-authored additions use **GPL-3.0-or-later**, with the existing
[Madeira Converter Exception](LICENSE-EXCEPTION.md) for work whose rights holders
grant it. Upstream files keep their own licenses, including LGPL, MIT, BSD and
MPL. Original copyright and license notices are retained; see [COPYING](COPYING).

Source publication does not resolve every obligation for distributing a built
IPA. Corresponding-source, relinking and proprietary-library requirements remain
in [docs/DISTRIBUTION.md](docs/DISTRIBUTION.md).

Steam, SteamOS and Steam Deck are Valve trademarks. iPhone, iPad, iOS and Metal
are Apple trademarks. iDeck is independent and is not affiliated with or endorsed
by Valve, Apple, Madeira or DroidDeck.
