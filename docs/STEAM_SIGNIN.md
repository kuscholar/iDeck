# Steam sign-in

Madeira can sign in to a Steam account and keep the resulting sign-in token in
the iOS Keychain. Madeira Dock uses the token to sign Valve's client in, and
the owned library and downloads (`docs/STEAM_LIBRARY.md`) use it for their Steam
connection. This document covers sign-in only; the library and downloads have
their own.

## Using it

The developer interface has a **Steam sign-in** button next to **Enable JIT**.
In the library, **Settings › Steam** and first-run setup open the same sheet
(`docs/LIBRARY.md`, "Steam setup"). The sheet has two methods:

- **Password** (default on iPhone): the Steam *account name* (not the email
  address) and password. When Steam asks for Steam Guard, the sheet offers a
  code field (Steam app or email code) and, when Steam allows it, approval in
  the Steam app. Both are offered at once; whichever happens first wins.
- **QR code** (default on iPad): scan it with the Steam app on another device.
  **Open in the Steam app on this device** passes the same sign-in link to the
  Steam app installed on this device.

When signed in, the sheet shows the account and **Sign out**.

`env.MADEIRA_STEAM_SIGNIN = 0` in `Documents/madeira.cfg` hides the button.
`env.MADEIRA_STEAM_TRACE = 1` adds protocol-level trace lines (method names and
Steam result codes, never payloads or credentials).

## What it does

Sign-in talks to Steam's public authentication service
(`https://api.steampowered.com/IAuthenticationService/<method>/v1/`) over
HTTPS, with protobuf-encoded requests, the same service Valve's own clients use:

1. `GetPasswordRSAPublicKey`, then the password is encrypted with that RSA key
   on the device (PKCS#1, Security framework) and sent with
   `BeginAuthSessionViaCredentials`. The password is not stored; the field is
   cleared when the request is submitted.
2. Or `BeginAuthSessionViaQR`, whose challenge URL is shown as a QR code.
3. `UpdateAuthSessionWithSteamGuardCode` when a code is typed.
4. `PollAuthSessionStatus` until Steam returns the tokens (5 minutes for the
   password flow, about 10 for QR; Steam's own interval is honoured).

Steam reports most failures as HTTP 200 with an `x-eresult` header. The
transport (`SteamAuthAPI`) turns those into specific errors (wrong password or
account, wrong Steam Guard code, rate limit, disabled account, expired
request) instead of polling an empty session.

The token requested is a Steam *client* token
(`k_EAuthTokenPlatformType_SteamClient`, persistent session), which is what
Valve's client accepts for its own sign-in.

## Storage and privacy

- Keychain only: one generic-password item, service `madeira.steam.tokens`,
  accessibility `kSecAttrAccessibleWhenUnlockedThisDeviceOnly` (this device,
  while unlocked; not synchronised, not in backups that leave the device).
- It holds the account name, the refresh token and the access token.
- **Sign out** deletes the item.
- Log lines are `[steam-signin] signed in method=qr|password`,
  `[steam-signin] sign-in failed method=… reason=<short code>` and
  `[steam-signin] signed out`. No password, code, token, account name or
  Steam ID is ever logged.

## Public API

```swift
enum SteamSignIn {
    static var isSignedIn: Bool
    static var accountName: String?
    static func credentialsForDock() -> (accountName: String, refreshToken: String)?
    static func signOut()
}
```

`credentialsForDock()` returns the stored account name and refresh token, or
nil when there is none. A token whose own `exp` claim has passed counts as
none; otherwise the token is not interpreted, and Valve decides whether it is
accepted. `SteamSignIn.didChange` is posted after a sign-in is stored or
removed.

## 64-bit and runtime impact

None. This is app-side Swift that runs only when the sheet is used. It does not
touch Wine, FEX, DXMT, the JIT pool, madeira.cfg defaults or any launch path.

## Provenance

The code in `app/Madeira/SwiftSteam/` is derived from **Jfishin's** Madeira
Steam client (his private Madeira fork; its Steam module is also called
SwiftSteam). Jfishin gave permission to use it in the Madeira Discord server on
2026-09-22 ("Yeah do whatever you want with it"). Will Faust is a member of
that server and saw the message. Jfishin is fine with both 125hz and Will
Faust using it for Madeira. An earlier pull request pointed to a GitHub URL for
this permission that does not resolve; that reference is withdrawn. The
permission is a chat message, not a written licence; a public confirmation by
Jfishin on the pull request would make it verifiable by anyone.

The sign-in files listed below are the sign-in part of that client. The
owned library and downloads (`docs/STEAM_LIBRARY.md`) are a second part, with
their own audit; Steam Cloud, launch and DRM-related parts of his client, and
the channel encryption that cites a third-party key dictionary, are **not**
included anywhere. 125hz's changes are GPL-3.0-or-later with the Madeira
Converter Exception; the derived files say `Copyright 2026 Jfishin, 125hz`.

Audit method: the files below were compared line by line with Jfishin's
original tree (a local copy of his fork, last commit 2026-09-19 "Prepare
provenance-clean public source tree"), and both his originals and these files
were searched for references to third-party Steam projects (SteamKit2,
JavaSteam, DepotDownloader, SteamRE, ValvePython/steam, node-steam-user,
GameNative/Pluvia, SteamDatabase) and for licence or copyright text.
"Lines" counts non-blank lines; "common" counts those identical to a line
of Jfishin's version.

| File | Lines | Common with Jfishin | Origin | Third-party code |
|---|---|---|---|---|
| `Auth/SteamCredentialAuth.swift` | 183 | 125 | Jfishin, rewritten by 125hz (begin / code / poll split, every allowed confirmation offered, cancellable polling) | none found; the manual RSA DER builder is iOS-specific (Security framework) |
| `Auth/SteamQRAuth.swift` | 131 | 116 | Jfishin, adapted (challenge-rotation callback, cancellable polling, shared transport) | none found |
| `Auth/SteamTokenStore.swift` | 86 | 75 | Jfishin, adapted (service name, logging) | none found |
| `Auth/SteamAuthAPI.swift` | 62 | request construction from Jfishin's per-flow helper | 125hz (shared transport, `x-eresult` mapping) | none |
| `Core/SteamError.swift` | 44 | 31 | Jfishin, reduced to sign-in errors | none |
| `Proto/SteamProtoMessages.swift` | 371 | 336 | Jfishin (hand-written protobuf encoder/decoder and the nine `CAuthentication_*` request and response messages); 125hz fixed the credentials field numbers and made hostile lengths throw | none found. Field numbers and message names are Valve's public protocol definitions (`steammessages_auth.steamclient.proto`), i.e. interface facts, not copied code |
| `Helpers/SteamDevice.swift` | 20 | 14 | Jfishin | none |
| `Helpers/SteamLog.swift` | 25 | new | 125hz | none |
| `SteamSignIn.swift` | 191 | model adapted from 125hz's account model around Jfishin's flows | 125hz (public API, expiry rule) | none |
| `SteamSignInView.swift` | 152 | from 125hz's fork sign-in sheet | 125hz | none |

Result: no file here contains code ported from SteamKit2 (LGPL-2.1),
JavaSteam (MIT), DepotDownloader (GPL-2.0) or another third-party Steam
library, as far as this audit can tell; nothing here needs a licence other
than GPL-3.0-or-later with the Madeira Converter Exception. What the audit
cannot establish is how Jfishin himself wrote his originals: it rests on his
statement, his tree carrying no third-party notice for these files, and the
absence of any reference or recognisable foreign code. The channel encryption
of his client cites the SteamKit2/JavaSteam key dictionary; it is left out
(the connection is a WebSocket over TLS). His depot downloader is in
`docs/STEAM_LIBRARY.md`, which records its own audit.

## Tests

`tests/host/check-steam-signin-native.py` (needs `swiftc` and
`python3`; never contacts Steam):

- static: licence headers, the module holds only sign-in code, every file is
  in the Xcode project, the Keychain item is device-only and not
  synchronised, no log line interpolates a credential;
- compiled production Swift under AddressSanitizer: Valve's field numbers for
  every request, decoding of every response (float intervals, all allowed
  confirmations, unknown fields), hostile lengths and truncated input throw
  instead of trapping, the `x-eresult` mapping, request shapes (POST form,
  GET query, percent-encoded base64) through a stub `URLProtocol`, and the
  `credentialsForDock()` rules (trimmed name, expired or empty token = signed
  out, sign-out removes it).

Not covered: a live sign-in against Steam (password, Steam Guard code, in-app
approval, QR, same-device hand-off) from this branch; this extraction has not
been run on a device. In the owner's fork, which runs the same flows, QR
sign-in is confirmed in device logs. The typed-password flow there carries the
field-number fix above, but no device log in the fork's records confirms a
password sign-in since that fix, and the same-device hand-off has never been
tested.
