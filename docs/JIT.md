# JIT setup

Madeira needs an attached debugger to create executable memory on iOS. It can
use either the StikDebug app or its built-in StikJIT helper. Both methods send
the same bundled `madeira-jit.js` debugger script to the current Madeira
process.

## Automatic selection

The default **Automatic** method uses StikDebug when iOS reports that its
`stikdebug://` URL scheme is installed. Otherwise, it uses Built-in StikJIT.
Madeira does not silently switch methods after a failed attempt; the error is
shown so the pairing, VPN, or Developer Disk Image problem can be fixed.

Choose a method under **Settings → JIT**, or open **JIT setup** for its guided
setup and status. First-run setup offers three ways in, each with its own
numbered steps: **In-app** (pair this iPhone with Madeira, iOS 27 and
later) and **In-app with pairing file** both select Built-in StikJIT,
**StikDebug** selects StikDebug, and setting it up later leaves the current
method unchanged.

**Play** enables JIT itself when it is off: it runs the same flow as **Enable
JIT** (the loopback check and the Madeira JIT shortcut included), then starts
the game once the debugger is attached. Meanwhile the button reads **Starting
JIT**, with a spinner, and the game's page stays open. If JIT does not come on, the usual
error is shown and the game is not started; enabling JIT later starts nothing.
This also covers JIT enabled from StikDebug's own list, which sets CS_DEBUGGED
and leaves, so no debugger is attached.

## StikDebug

1. Install [StikDebug](https://github.com/StikDebug/StikDebug/releases/latest).
2. Import this iPhone's pairing file into StikDebug.
3. Install and connect
   [LocalDevVPN](https://apps.apple.com/us/app/localdevvpn/id6755608044).
4. In Madeira, tap **Enable JIT**.

Madeira opens StikDebug's canonical `stikdebug://enable-jit` URL with Madeira's
bundle identifier, current process ID, and custom script. It waits up to 90
seconds for both the `CS_DEBUGGED` flag and a live debugger connection. Enabling
Madeira from StikDebug's own app list is not equivalent because that flow can
detach before Madeira creates its JIT pool.

## Built-in StikJIT

Built-in JIT requires iOS 26 or later and a normal sideloaded installation. It
is unavailable in the simulator and inside LiveContainer. It needs this
iPhone's remote pairing file, which Madeira can make itself on iOS 27, or
import.

### In-app pairing (iOS 27 and later)

iOS 27 can pair with a computer it finds on the local network, started from
the iPhone. Madeira plays that computer for its own iPhone, so no computer is
needed.

1. Turn on Wi-Fi. Tap **In-app**, then **Start pairing**, during first-run setup, or
   **Pair in Madeira** in **Settings → JIT → JIT setup**, and allow Local
   Network access when iOS asks.
2. Open **Settings → Privacy & Security → Developer Mode**, scroll down and
   tap **Pair with Madeira**.
3. Enter the code Madeira shows. It appears in iOS's background-task banner
   and as a notification, and in Madeira when you return.
4. Back in Madeira, continue with LocalDevVPN, **Check setup** and
   **Enable JIT** as below.

Madeira keeps running in the background while you are in Settings through an
iOS continued-processing task (`<bundle id>.pairing.session`). If iOS refuses
it, typically because the sideloader changed the bundle identifier, Madeira
only gets the usual ~30 seconds in the background and says so; go to Settings
straight away. A pairing that has not finished after five minutes is stopped.

Every pairing makes a new host key. The identifier stays the same, so the
iPhone replaces its earlier record for Madeira, and only the newest pairing
file works.

The pairing runs in `libmadeira_rppairing.a` (`build/rppairing-ios`), a small
wrapper around [idevice](https://github.com/jkcoxson/idevice)'s pairable-host
implementation. `app/Madeira/JITPairing.swift` advertises it as a
`_remotepairing-pairable-host._tcp` Bonjour service through mDNSResponder, so
only the Local Network permission is needed.

### Pairing file from a computer

1. Create a pairing file for this iPhone by following the
   [StikDebug pairing-file guide](https://github.com/StikDebug/StikDebug-Guide/blob/main/pairing_file.md).
2. Tap **In-app with pairing file**, then **Choose pairing file**, during first-run setup, or open
   **Settings → JIT → JIT setup** and tap **Import pairing file**.

### Enabling JIT

1. Install and connect LocalDevVPN.
2. Tap **Check setup**. Madeira checks VPN reachability and downloads, mounts,
   and verifies the matching Developer Disk Image when needed.
3. Tap **Enable JIT**.

Either way, the pairing file is kept in the Keychain, for this device only and
readable while it is unlocked, as the Steam sign-in token is. It is a credential
for the iPhone itself, so it is never stored in `Documents`, where the Files app
and every Windows program in Madeira could read it. Madeira sends its bytes only
to its bundled helper process for the current request. A copy an earlier build
left at `Documents/StikJIT/pairingFile.plist` is moved into the Keychain and
deleted the first time Madeira reads it.

The helper is a classic app extension (`PlugIns/MadeiraJITHelper.appex`, on
the `com.apple.ar.viewer` extension point, as LiveContainer's LiveProcess is). A
separate process is required because a process cannot synchronously debug
itself. Madeira starts it through `NSExtension` by the bundle ID the helper has
in this installation, so it is found after a sideloader renames Madeira's bundle
ID (SideStore, AltStore and Plume append the team ID, to the helper's ID as
well). The request (PID, pairing data, script) goes in the extension request;
the helper uses StikJIT with `forceScript` enabled, stays alive while Madeira's
script services debugger requests, and answers when the request completes.
StikJIT.framework is in Madeira's own `Frameworks` folder (the helper loads it
through `@executable_path/../../Frameworks`), where sideloaders re-sign it.

An ExtensionKit extension, which the helper was before, does not survive such a
rename: its extension point is named in files sideloaders do not rewrite, so
iOS registers none for the renamed Madeira and the lookup fails ("Failed to add
observer").

If setup reports stale Developer Disk Image data after an iOS update, use
**Reset Developer Disk Image**, then **Check setup** again.

If the device resets the connection, it no longer accepts the pairing (each
in-app pairing replaces the last), so Madeira offers **Pair Again**. If the
device can't be reached, it offers **Connect LocalDevVPN**, or **Get
LocalDevVPN** when the app isn't installed; LocalDevVPN returns to Madeira
through its `madeira://` URL scheme once connected.

## LocalDevVPN, cellular data and the Madeira JIT shortcut

Both methods reach this iPhone's `lockdownd` through LocalDevVPN's loopback
(`10.7.0.1:62078`). The loopback works on Wi-Fi, or with no network at all,
but not while cellular data is in use.

**Enable JIT** first checks the loopback directly
(`app/Madeira/JITNetwork.swift`), in two steps that do not depend on what
`lockdownd` says (over USB it answers a plain `QueryType`; through the tunnel it
closed the connection instead):

1. The route: which interface traffic to `10.7.0.1` would leave by, asked of the
   kernel without sending anything. It must be LocalDevVPN's tunnel, whose
   address is in `10.7.0.0/16`. Through Wi-Fi or cellular, or through another
   VPN that carries all traffic (it accepts the connection, and the JIT helper
   then reads "early eof"), the check fails at once, so a network or VPN that
   accepts any connection is never asked.
2. Through a VPN interface: a TCP connection, at most 0.4 s. Through a working
   loopback it opens in milliseconds, and JIT is enabled with nothing else
   opening; over cellular data, where the tunnel does not work, it fails.

On a network that accepts any connection, the helper's own error reads "early
eof"; after a check that found no loopback, Madeira explains any JIT failure as
LocalDevVPN not routing.

When the loopback does not answer and **Settings → JIT → Madeira JIT
shortcut** is on (`env.MADEIRA_JIT_SHORTCUT = 1`), Madeira runs your
**Madeira JIT** shortcut:

- **"start"** (with "cellular" when Madeira sees cellular data and no Wi-Fi):
  keep the VPN that is connected now, if any (iOS connects one VPN at a time,
  so LocalDevVPN replaces it); turn Cellular Data off, only when asked; connect
  LocalDevVPN; and output the kept VPN, which tells Madeira whether one was on.
  LocalDevVPN's Connect can return before its tunnel routes, so Madeira checks
  the loopback again for up to 15 s, going on the moment it works, and enables
  JIT.
- **"done"**: with "cellular", turn Cellular Data back on; with "vpn-off" (no
  VPN was on), disconnect LocalDevVPN; with "vpn-restore", connect the kept VPN
  again (it replaces LocalDevVPN). Neither VPN word when LocalDevVPN was already
  connected. Madeira runs it once a game's JIT pool is mapped and the debugger
  has detached, before Wine starts, or at once if enabling JIT fails.

The shortcut keeps the VPN with **Store Content** (iOS 27): only that keeps a
VPN that **Set VPN** accepts. Saved as text (to a file, or as a name Madeira
passes back) it is only its name, and Set VPN cannot convert it ("couldn't
convert from Text to VPN"). Madeira keeps the "done" it owes on disk, so if it
is closed or crashes in between, the next launch runs it. On iOS 26, which has
no Store Content, use the LocalDevVPN prompt instead.

With the shortcut on, Madeira never opens LocalDevVPN's own link: when JIT still
cannot connect, the alert offers **Connect with Madeira JIT**, which enables JIT
again through the shortcut (on the JIT setup page it runs the shortcut, then
checks the loopback). Without it, the alert offers **Connect LocalDevVPN**.

An app can only run a shortcut by opening the Shortcuts app, so each run leaves
Madeira for a moment and returns through `madeira://jit-network/…`
(x-callback-url). Between **Enable JIT** and the game starting, cellular data
stays off.

**Known gap: no network at all.** With Wi-Fi and Cellular Data both off and
LocalDevVPN not connected, the shortcut cannot help: LocalDevVPN does not
connect without any network, so after the 15 s wait the JIT attempt times out
(`[jit-loopback] … no route`) and Madeira reports it cannot reach the device.
LocalDevVPN that was already connected keeps working with no network. Untested
fixes: the shortcut turning Wi-Fi on first (the radio alone, without joining a
network, may be enough; Control Center's Wi-Fi button only disconnects and
leaves the radio on, while Settings turns it off), or turning Cellular Data on
just long enough to connect LocalDevVPN, then off again. Madeira can tell this
case apart (its network path has no interface) and could pass the shortcut a
word for it.

### Getting the shortcut

On iOS 27 and later, setup shows **Connect automatically** on its own page
after any JIT guide, with **Add the shortcut** and the **Use it for JIT**
switch, and **Settings → JIT** has **Add the Madeira JIT shortcut**. Both open its iCloud link, which takes Shortcuts straight to **Add
Shortcut**, but needs a connection: iOS opens a shortcut directly only from an
iCloud link. Without one, **No internet connection? Add local copy** shares
the bundled `app/Madeira/Madeira JIT.shortcut` (a signed export): choose the
**Shortcuts** app in the share sheet, then **Add Shortcut**. Only the share sheet
can hand a file to Shortcuts: iOS gives Shortcuts the file only when the user
picks it there. Either way it is named **Madeira JIT**; then turn it on.

The iCloud link lives only while the shared shortcut stays in its owner's
library: deleting it there breaks the link. The iCloud link and the bundled
file must be the same shortcut. After changing
it, share a new iCloud link and export a new file (**Share** → **Options** →
**Anyone** → **Save to Files**), and replace both (`JITShortcutFile` in
`JITNetwork.swift`, and the file, keeping its name). The file's signing
certificate expires on 26 Oct 2027.

Its steps, to make it by hand (name it exactly **Madeira JIT**):

1. **Text**, with the *Shortcut Input* variable inside it. (*Shortcut Input* on
   its own is untyped, so **If** offers only "has any value"; its text offers
   "contains".)
2. **If** *Text* contains `start`
   1. **Get Current VPN** (before LocalDevVPN replaces it).
   2. **Store Content**: *Current VPN*, named `previous VPN`.
   3. **If** *Text* contains `cellular`: **Set Cellular Data** *Off*. End If.
   4. LocalDevVPN's **Connect** action (or **Set VPN** → *Connect* → LocalDevVPN).
   5. **Stop and Output** *Current VPN*.
3. **Otherwise**
   1. **If** *Text* contains `cellular`: **Set Cellular Data** *On*. End If.
   2. **If** *Text* contains `vpn-off`: LocalDevVPN's **Disconnect** action (or
      **Set VPN** → *Disconnect*). End If.
   3. **If** *Text* contains `vpn-restore`: **Get Stored Content** `previous
      VPN`, then **Set VPN** → *Connect* → that stored content, wired straight in
      (no Text in between). End If.
4. End If.

Then turn on **Settings → JIT → Madeira JIT shortcut**. Without the shortcut,
leave it off: Shortcuts would only report that the shortcut is missing.

## Signing and installation

The app and `MadeiraJITHelper` extension must be signed together. Sideloaders
must keep and provision the app extension (some ask whether to keep app
extensions). If an installer drops it, Madeira says the helper is missing;
select StikDebug instead.

To build Madeira under another bundle identifier, set the
`MADEIRA_BUNDLE_IDENTIFIER` build setting (for example in an `.xcconfig`
passed with `-xcconfig`). The app and the helper (`<id>.JITHelper`) follow it.

JIT also requires Madeira's executable to be signed as debuggable. Madeira
reports a signing error before attempting either method when that entitlement
is missing.

## Licensing

The bundled StikJIT 1.9.0 XCFramework is from
[StikDebug/StikJIT](https://github.com/StikDebug/StikJIT/releases/tag/1.9.0)
(`StikJIT.xcframework.zip` SHA-256
`806664393770c68e75f2b6429955bfdd88cfaad09fec2ba70f8ed615ff90c060`)
and is licensed under MPL-2.0. It includes the
[idevice](https://github.com/jkcoxson/idevice) library, licensed under MIT.
Corresponding source and license links are recorded in
[`THIRD-PARTY-NOTICES.md`](../THIRD-PARTY-NOTICES.md).

In-app pairing links idevice 0.1.68 and its Rust dependencies (MIT,
Apache-2.0, BSD-3-Clause or ISC) into the app from crates.io, pinned by
`build/rppairing-ios/Cargo.lock`; their notices are bundled as
`legal/LICENSES-rppairing-crates.txt`.
