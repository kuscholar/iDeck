[English](README.md) · [简体中文](README.zh-CN.md)

<p align="center">
  <img src="docs/assets/ideck/icon.png" width="156" alt="iDeck">
</p>
<h1 align="center">iDeck</h1>
<p align="center"><strong>iDeck brings the Steam Big Picture experience to iOS</strong></p>
<p align="center">
  <a href="https://discord.gg/aQdsaJyTM"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fdiscord.com%2Fapi%2Finvites%2FaQdsaJyTM%3Fwith_counts%3Dtrue&query=%24.approximate_member_count&suffix=%20members&label=Discord&logo=discord&logoColor=white&color=5865F2&style=for-the-badge" alt="Join the iDeck Discord"></a>
</p>
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

## Install the alpha and help test

The newest experimental checkpoint is **[v0.1.3-alpha.6 · Build 145](https://github.com/kuscholar/iDeck/releases/tag/v0.1.3-alpha.6)**.
Download its IPA and `SHA256SUMS`; matching source, Steam64 support-source,
license and relink materials are attached to the same release. You must sign
the IPA for your own device.

**Less setup treasure hunt, more Steam.** The launcher now walks through four
actions, with a direct Steam64 installer, visible pairing button and automatic
checkmarks. The installer downloads and verifies the matched client from Valve;
it keeps the old environment and offers repair/rollback.

> **Still experimental:** Steam can freeze after the third game exit. This
> release improves setup; it does not fix that game-return failure or guarantee
> broad game support. The Build144 installer was reported complete by the user;
> Build145's new UI was built, signed, installed and opened on the test iPhone,
> but its complete revised first-run/gameplay flow has not been independently
> validated. See the [Build145 test record](docs/release/BUILD145_RESULTS.md).

The IPA includes the local runtime and pinned **source-built open compatibility
components** with notices. It includes no Valve Steam client/libcef, games or
account data. Steam is downloaded in the launcher, and you authenticate through
Valve yourself. The matched older client/CEF snapshot has compatibility and
security limitations; it is not the latest Steam/Chromium.

1. **Download and verify.** Compare the IPA's SHA-256 with `SHA256SUMS`.
2. **Sign and sideload.** Use your own Apple ID with a tool such as
   [Sideloadly](https://sideloadly.io/) or
   [AltStore Classic](https://faq.altstore.io/altstore-classic/your-altstore).
   Free development signing is an option; follow the tool's account limits and
   refresh instructions. Keep `MadeiraJITHelper.appex`, sign all nested code,
   and retain development debugging permission (`get-task-allow`). A signature
   alone does not enable JIT. These signers are options, not a verified support list.
3. **Trust and open.** Connect/trust the device and complete Apple's developer
   and trust prompts when requested. Back up saves before upgrading an existing
   install; deleting the app can delete its local Steam data and games.
4. **Prepare Steam and JIT.** Follow the checklist below. The IPA includes the
   local runtime and open compatibility helpers, but **no Valve Steam client/libcef,
   games or a Steam account**. Download Steam through the launcher.
5. **Test in stages.** Check launcher readiness → enter genuine Steam and complete
   Steam Guard yourself → browse Library → try a compatible game → return to
   Steam → reopen iDeck to check saved login. Try touch, keyboard and your
   controller separately. Report the first failing stage, not just “it hangs”.

Target: **iOS 26+**, with JIT through Madeira's authorized pairing/debug workflow.
Device evidence comes from **iPhone 15 Pro Max (A17 Pro)**; iPad remains unvalidated.
No jailbreak is required. See [full IPA installation instructions](docs/INSTALL_IPA.md)
for signing details and limitations, or [source setup](docs/GETTING_STARTED.md).

### JIT shortcut destination error?

On an older build, re-signing with a different Bundle ID can break the
Shortcuts return URL. As a temporary workaround, turn off the optional
**Madeira JIT shortcut**, connect **LocalDevVPN** manually, then return and tap
**Enable JIT**. Current releases use registered callback metadata. After updating,
re-import the signed shortcut from iDeck and replace the old copy; an app update
does not automatically replace an already imported shortcut.
See [JIT troubleshooting](docs/JIT.md#shortcut-destination-errors-after-re-signing).

## Before Steam: four steps, then play

Follow the highlighted step. The launcher checks the device automatically,
marks completed steps and moves to the next action—no hunting below the list.

| Step | Your action |
| --- | --- |
| 1 · Install Steam | Tap **Install Steam64**. iDeck downloads/verifies Steam and its browser and prepares the runtime automatically. Keep it open; fully close/reopen when prompted. |
| 2 · Connect LocalDevVPN | Open LocalDevVPN, tap Connect and return. An already reachable connection is checked off automatically. |
| 3 · Pair this device | Tap **Pair in iDeck**. Follow the live instructions/PIN in this card; iOS Settings calls the pairing host **Madeira**. Normally needed once. |
| 4 · Enable JIT | Tap **Enable JIT** and return to iDeck. A fresh app process needs JIT again. |

When every required check passes, tap **Launch Steam Big Picture**. Signing,
address-space/native reservations and installed runtime files still gate launch;
shortening the UI does not bypass them. **Check again** refreshes the automatic
checks. On iOS26, use the pairing-file import fallback; direct on-device pairing
requires iOS27.

**Advanced options** holds Verify/Repair Steam64, Return to previous environment,
other JIT methods/import, account switching and auto-start. The old `wine` prefix
is retained; Steam64 uses `wine-steam64`. Login caches, games and saves are not
automatically migrated. Use Steam's own sign-in/Steam Guard and account flow.
Never copy someone else's login cache or delete the app to switch environments.

Steam64 does **not** create virtual address space. Unsupported device/signing
layouts can still fail, and 32-bit games/helpers may retain separate limits.
See [Steam64 setup and recovery](docs/STEAM64_SETUP.md) for capacity, download,
version-pinning and rollback details. Passing setup is not gameplay validation.

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

Build 143 improves menu handling and browsing in the tester’s report, but Steam
can still freeze after the third game return. Startup and post-login transitions
can also hang.
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

To rebuild a release, check out its tag and use its matching source/relink
companions. Alpha.6 retains the exact FEX131 overlay/rebuild materials and adds a
separate Steam64 support-source companion for Chromium/CEF and standalone Crashpad.
Stage its hash-pinned open components with `tools/stage-steam64-compatibility.py`;
see [Build145 rebuild notes](docs/release/BUILD145_RESULTS.md#source-and-relink-materials).

Follow [Getting started](docs/GETTING_STARTED.md), [Building](docs/BUILDING.md)
and [JIT setup](docs/JIT.md). The public snapshot excludes compiled runtime
payloads and requires separately prepared dependencies; this is not a one-command
clean build yet.

The inherited Xcode project is `app/Madeira.xcodeproj`, scheme `Madeira`. The
app displays **iDeck** with the cyan-and-blue **iD** icon. Select your own Apple
development team and a unique identifier; the source defaults to
`com.kuscholar.ideck.steamui`. Keep existing Madeira installs and their data
separate.

The Git checkout excludes compiled runtime payloads, Valve client/libcef, games, account
caches, signing profiles and the proprietary Apple converter. The alpha IPA
and its source/license/relink companion assets are distributed separately. Read the
[distribution requirements](docs/DISTRIBUTION.md) before sharing a built package.

## Feedback

<p align="center">
  <a href="https://discord.gg/aQdsaJyTM"><b>Join the iDeck community on Discord</b></a>
</p>

### Discord Community

The iDeck Discord server is an informal space for testers and enthusiasts to share experiences, discuss compatibility, report findings, and occasionally receive project updates.

iDeck is a personal, non-commercial hobby project developed in my spare time. There is no dedicated support team, guaranteed response time, or commitment to ongoing maintenance, bug fixes, or feature development.

Participation is entirely voluntary, and updates or responses are provided only when time and interest permit.

### Bug reports

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


## Earlier updates

[Build 67 · v0.1.3-alpha.3](https://github.com/kuscholar/iDeck/releases/tag/v0.1.3-alpha.3)
introduced Steam file recovery, 64-bit game installation detection and the JIT
re-signing callback fix. Re-import old JIT shortcuts after updating. TLS recovery
was checked with local fault simulation; it is not a guarantee for every VPN or
accelerator. See [Steam recovery](docs/IDECK_STEAM_RECOVERY.md).
