<p align="center"><img src="docs/assets/ideck/icon.png" width="156" alt="iDeck cyan and blue iD controller icon"></p>
<h1 align="center">iDeck</h1>
<p align="center"><strong>Your next handheld might already be in your pocket.</strong><br>Real Steam. Local PC games. A little iPhone ambition.</p>
<p align="center">🎮 Steam Big Picture · 🍎 iOS & iPadOS · ⚙️ Powered by Madeira · 🧪 Experimental</p>
<p align="center"><a href="#meet-your-pocket-pc-gaming-experiment">The idea</a> · <a href="#what-actually-works">Current status</a> · <a href="#bring-your-own-curiosity">Build & setup</a> · <a href="CREDITS.md">Credits</a> · <a href="COPYING">License</a></p>

## Meet your pocket PC gaming experiment

You know that Steam backlog you keep promising to play?
**What if your iPhone could take a shift?**

iDeck is building a Steam Deck-style experience for iPhone and iPad: open the
app, connect a controller, and step into **Valve's actual Steam Big Picture**.
Compatible Windows PC games run locally on your Apple device through Madeira's
Wine/FEX/Metal stack. No gaming PC needs to stay awake in the other room.

The ambition: turn the device you already carry into a handheld for the games
you already own. The current reality: an open-source experiment with some very
exciting moments—and some very stubborn loading screens.

> **Real Steam UI. Real local execution. Still a work in progress.**
> iDeck runs Windows Steam through compatibility and instruction translation.
> It brings a SteamOS-style experience; it does **not** install Linux SteamOS
> or make every PC game an ARM-native iOS app.

## The handheld treatment

| | What we're building |
|---|---|
| 🛋️ **Big Picture, small device** | Steam's own controller-friendly interface, library and account system. |
| 🎮 **Pick your controls** | Physical controllers, direct touch and an on-screen virtual controller. |
| 🫧 **One little floating button** | Move it where you want. Open the keyboard, adjust controls, summon the Steam menu or request a graceful game exit. |
| 🔑 **Your account stays with Steam** | Genuine sign-in and Steam Guard. Saved login belongs to the local Steam client. |
| 🛠️ **Open the hood** | Source, compatibility experiments, diagnostic programs and evidence you can inspect. |

These are implemented product paths, **not a promise that every path works in
every game**. Read the status below before packing away your other handheld.

## What actually works?

The test bench so far is an **iPhone 15 Pro Max with an A17 Pro**. iPad is a
development target; it has not been validated in this project yet.

| Status | Evidence so far |
|---|---|
| ✅ **Steam sign-in** | Genuine login, Steam Guard approval and saved-login reuse observed on the test iPhone. |
| ✅ **Big Picture & library** | The real interface and library browsing have worked in earlier builds. |
| ✅ **A PC game on an iPhone** | Game startup observed; gameplay also reported by the tester. This is not a broad compatibility list. |
| ✅ **Input progress** | Tester confirmed text entry and the floating menu's Steam-menu action. |
| 🧪 **Startup & transitions** | Still unreliable. Recent logs reached successful login and `BrowserReady`; those events alone do not prove an interactive home screen. |
| 🧪 **Controller coverage** | Windows recognizes the virtual controller. Full Steam/game input behavior and Bluetooth validation remain open. |
| 🧪 **The full couch session** | Reliable game return, long-session stability and iPad testing still need work. |

**JIT is required**, using Madeira's authorized pairing/debug workflow. No
jailbreak or private entitlement is assumed. Compatibility varies by game;
anti-cheat support and “your entire library works” are not promised. Steam
ownership, authentication and license checks remain in place.

For the receipts, see [technical status](docs/IDECK.md),
[POC results](docs/BIG_PICTURE_POC_RESULTS.md) and
[login/transition evidence](docs/IDECK_LOGIN_TRANSITION_EVIDENCE.json).

## How does that fit in a phone?

The native iOS shell handles setup and controls. Madeira provides the runtime:
Wine supplies Windows compatibility, FEX translates x86 instructions to ARM64,
and the graphics stack connects supported rendering paths to Metal. Steam and
the game run on the device.

**Will Faust's Madeira is the foundation of this project.** Most of the runtime
and build system is its work. iDeck adds the handheld launcher experience,
Steam UI integration, input work and compatibility experiments; it does not claim
to have invented the stack underneath.

[Meet the projects and contributors →](CREDITS.md) ·
[Exact source snapshot and component pins →](docs/PROVENANCE.json)

[DroidDeck](https://github.com/Droid-Deck/DroidDeck) inspired the mobile Steam
handheld experience. iDeck takes the Madeira route on iOS, rather than DroidDeck's
Android/ARM64 Proton implementation. No DroidDeck code or artwork was imported
for this snapshot.

## Bring your own curiosity

**This is a source release for tinkerers, not a download-and-play app yet.**
There is no public IPA, and a fresh clone is not a one-command build. Runtime
resources and proprietary dependencies need separate preparation.

```sh
git clone --recurse-submodules https://github.com/kuscholar/iDeck.git
cd iDeck
```

Start with [build & setup prerequisites](docs/GETTING_STARTED.md), then
[Madeira's build instructions](docs/BUILDING.md) and [JIT setup](docs/JIT.md).
The Xcode project is still `app/Madeira.xcodeproj`, with scheme `Madeira`, to
preserve the inherited build system. On your Home Screen, it's **iDeck** with
the cyan-and-blue **iD** icon.

Use your own development team and a unique app identifier; the source defaults
to `com.kuscholar.ideck.steamui`. Keep existing Madeira installs and their data
separate. Obtain Steam through Valve's legitimate channels and sign in yourself.
Steam/CEF, games, account caches, signing profiles and the proprietary Apple
runtime library are not included in this public repository. The tested legacy
Steam client is not bundled, either.

Found a reproducible failure? [Open an issue](https://github.com/kuscholar/iDeck/issues)
with the build, device, steps and **redacted** diagnostics. Keep passwords, tokens,
Steam Guard details and account identifiers out of reports. A useful bug report
gets us closer to fewer loading screens.

## Open source, with proper credit

The iDeck-authored additions use **GPL-3.0-or-later**, with the existing
[Madeira Converter Exception](LICENSE-EXCEPTION.md) for work whose rights holders
grant it. Upstream files keep their own terms, including LGPL, MIT, BSD and MPL.
Original copyright and license notices are retained.

Read [CREDITS](CREDITS.md), [NOTICE](NOTICE),
[third-party notices](THIRD-PARTY-NOTICES.md) and [COPYING](COPYING).
Public IPA distribution remains subject to corresponding-source, relinking and
proprietary-library review; see [distribution requirements](docs/DISTRIBUTION.md).
Publishing source is not a blanket clearance to redistribute an assembled app.

Steam, SteamOS and Steam Deck are Valve trademarks. iPhone, iPad, iOS and Metal
are Apple trademarks. iDeck is independent and is not affiliated with or endorsed
by Valve, Apple, Madeira or DroidDeck.

---

<p align="center"><strong>A big library. A small screen. Let's see how far this goes.</strong></p>
