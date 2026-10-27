# JIT callback failure after re-signing

2026-10-26. Source baseline: `0ec1eb7`; fixes are an uncommitted working tree.
No commit/push is permitted during the current weekday daytime window. Existing
public release remains Build 56. The connected phone's existing test session
was not replaced for this investigation.

## Report and attribution limit

A tester reports Shortcuts saying the destination app for its output could not
be determined, and one roughly one-minute loading wait after Xcode signing.
No diagnostic log, final Bundle ID, iOS version or signing profile from that
tester is available. The defects below are confirmed in source and reproduced
in policy/metadata tests; they match a renamed-install path. They do not prove
that every Steam/browser/game loading stall has this cause.

## Confirmed callback mismatch

Old `SteamUIExperiment.callbackScheme` inferred `madeira-steamui` only when the
Bundle ID ended with `.steamui`; otherwise it chose `madeira`. The actual
Info.plist registered only `madeira-steamui`. A custom Xcode ID or a signer
appending `.TEAMID` therefore produced an unregistered x-success/x-error/
x-cancel URL. The same error affected LocalDevVPN return URLs. Shortcuts has
no matching destination in that installation; the app's pending callback timer
waits 60 seconds. This is separate from a debugger-attachment timeout.

Old `allowed` also required the `.steamui` suffix. The iDeck product marker
could remain true in the app while the launcher was disabled after ID changes.

Fixes:
- Read and validate actual CFBundleURLTypes, preferring a declared scheme that
  matches the installed Bundle ID. Declare the expanded product Bundle ID as a
  unique scheme alongside the existing stable `madeira-steamui` scheme.
- A post-build re-signer retaining old schemes still uses one actually declared
  in its installed metadata. No inferred `madeira` fallback is manufactured.
- Reject missing/invalid callback metadata before opening Shortcuts; build
  LocalDevVPN's URL with the same selected scheme.
- Accept an explicitly marked iDeck product independently of bundle suffix,
  still requiring the feature flag and a nonempty Bundle ID. Unmarked
  ordinary Madeira builds retain the original experimental-app restriction.

Multiple differently re-signed copies retaining identical URL schemes remain
subject to iOS's shared-scheme routing ambiguity. Prefer the unique scheme in a
source build; this fix does not claim to control Apple's choice among duplicates.

## Shortcut output contract

The original signed archive was verified/decrypted with Apple's `aea` using
its included public signing certificate, then read with `aa`. Its workflow
output type was WFVPNContentItem and its start Stop and Output referenced
Current VPN directly. The app expects textual callback output. Apple's
[x-callback documentation](https://support.apple.com/en-euro/guide/shortcuts/apdcd7f20a6f/ios)
describes the result as textual output. This mismatch is a compatibility risk;
its exact OS-specific contribution to the tester's message is not device-proven.

The corrected workflow adds explicit Text conversion before start output,
explicit empty Text output for done, and declares WFStringContentItem. The
original native VPN object remains in Store Content so Set VPN can restore it.
Only output is converted. No VPN credentials or names are added to logging.

Editable source: `tools/shortcuts/Madeira JIT.plist`; Apple's official
`shortcuts sign --mode anyone` generated the bundled signed file. Tests verify
its archive signature and exact payload/source equality. Setup/settings import
the corrected bundled file instead of the old iCloud workflow. Users must
replace an already imported old workflow; an app upgrade cannot replace it.

## Validation

- Production Swift policy: old mismatch reproduced for a Team-suffixed ID;
  corrected registered callback and product gates pass for original,
  Team-suffixed and arbitrary custom IDs. Missing/invalid schemes fail closed.
- Existing ordinary-app/feature-flag tests pass.
- JIT network regression: actual local listeners, closed port, route rejection
  and LocalDevVPN tunnel-address classification all pass.
- Signed shortcut signature/payload/source/text-output/Store Content checks pass.
- Full unsigned iOS Build 65 succeeds with `MADEIRA_BUNDLE_IDENTIFIER=
  org.example.ideck.resigned` (intentionally no experimental suffix).
- Actual final app metadata: custom ID, IDeckEnabled=true, own custom URL scheme
  plus stable scheme, helper `org.example.ideck.resigned.JITHelper`.
- Final linked debug dylib includes the missing-callback error marker; final
  bundled shortcut hash matches the corrected source artifact.

This is not an on-device Shortcuts/JIT or tester-hardware success claim.
Build 65 was not installed over the user's active Build 64 session. Future
acceptance: re-sign with custom ID and matching app/helper development profiles,
replace shortcut, complete a start/done round trip, verify actual debugger/JIT
pool initialization, then test Steam separately.

## Workaround / next tester evidence

On an old installation disable the optional Madeira JIT shortcut, connect
LocalDevVPN manually with Wi-Fi enabled, return and Enable JIT. A valid
get-task-allow development signature, preserved helper and correct device
pairing are still necessary. On iOS 26 use this manual route; the workflow's
Store Content requires iOS 27. No jailbreak or private entitlement is assumed.

If Steam/game startup still waits after JIT succeeds, request iOS/build,
final Bundle ID, JIT method and a redacted log identifying the first failed
stage. Do not request passwords, pairing secrets or public signed profiles.

Private build/test artifacts: `FunProjects/.madeira-install/ideck-resign65-build`,
`ideck-resign65-build.log`, `ideck-jit-network65-tests.log`.

Signed shortcut SHA-256:
`9270488e220104e22b45445b4ce0e75896d2c271a2b219a863dfb87d417f9e41`.
Workflow source SHA-256:
`3d3e72c0e12ce7a59d5d28028fbdcfb582989de2444d05a43272cd1bb27158d1`.
