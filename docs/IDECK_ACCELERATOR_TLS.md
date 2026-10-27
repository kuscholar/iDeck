# Accelerator / Steam Cloud TLS investigation

2026-10-26. Investigation only; no TLS/network runtime patch or fix claim.
User reports an accelerator is needed for Steam access, but Madeira shows an
unspecified TLS error and then cannot obtain an initial online/offline-ready
session. Accelerator name, iOS/build and exact error/log are pending. The
report may concern upstream Madeira rather than iDeck's genuine Steam client.
Do not conflate those implementations or use this Mac's network as reproduction.

## Verified current-code distinctions

- Madeira native Cloud: SteamCloudTransfer uses ephemeral URLSession for file
  download/upload; native Steam CM is a separate WSS connection. A generic
  network failure already logs categorical `reason=url-<numeric code>` under
  [steam-cloud] in SteamOwnedLibrary. No signed Cloud URL/header/token needs
  to be published to obtain the error code.
- A Cloud pre-launch check failure offers Try again / Launch anyway. The latter
  bypasses only that Cloud check, not Steam authorization, and does not set
  MADEIRA_DOCK_OFFLINE. A failed sync alone is not a forced offline logon.
- DockOffline.configure requests offline when its NWPathMonitor reports a
  non-satisfied path. Dock can also fall back after connection failures, only
  if Valve's client grants offline logon using its own previously issued
  ticket. No fake online/offline ticket is appropriate.
- JIT's optional shortcut stores the previous VPN, temporarily enables
  LocalDevVPN, and restores the previous VPN after debugger/pool setup, before
  Wine starts. The callback/type repair in local Build 65 addresses that
  control path; it has not been proven to solve this TLS report.
- Wine/Windows TLS and native URLSession are different stacks. Wine crypt32
  reads the bundled Mozilla CA set. Native URLSession follows platform TLS
  behavior. An accelerator's DNS/tunnel behavior or interception could affect
  them differently; none is established as the reporter's cause.
- Ratatan's earlier unrelated logs and successful local builds are not evidence
  of this accelerator/game/network combination working.

## Next discriminating tests, in the reporter's environment

1. Identify iOS/build, actual app (Madeira or iDeck), selected JIT method,
   accelerator and exact numeric TLS/SSL error. Redact credentials, pairing
   files, account identifiers, cookies, signed Cloud URLs and headers.
2. With the accelerator enabled, before JIT/LocalDevVPN switching, use the
   native Cloud Sync now action. If this already fails, investigate its native
   URLSession/CM/TLS path rather than assuming Wine root certificates caused it.
3. If that succeeds, compare after JIT setup and confirmed accelerator
   restoration. A failure introduced only by the switch distinguishes route/
   resolver/VPN-restoration state from a persistent certificate incompatibility.
4. Distinguish DNS, TCP/transport, TLS negotiation, certificate trust/name/date,
   Steam authentication, Cloud transfer and offline-ticket refusal. Steam's own
   logs apply when the app is iDeck's genuine Windows Steam, rather than native
   Cloud. Do not disable verification, import unverified roots, switch to HTTP,
   skip ownership checks or claim Cloud success from a CM logon alone.
5. Preserve saves. A Cloud failure can leave local saves usable, but Launch
   anyway may use older files and does not guarantee first-time Steam/game
   authorization. It is not represented as a general solution.

Steam's official offline preparation instructions:
https://help.steampowered.com/en/faqs/view/0E18-319B-E34B-B2C8

No accelerator was installed/reconfigured, no account logged in, no save synced
or overwritten, and no affected-device success claimed during this audit.
Existing user-requested JIT repairs remain separate uncommitted changes. The
commit/push time restriction remains in force; no automatic task is created.

## Follow-up report and local Build 66

Reporter supplied iDeck marketing version 0.1.3, iOS 27.2, both LeiShen and
Karing, and these two messages (no raw error code/build number):
- `Connection failed: A TLS error caused the secure connection to fail.`
- `Steam signed in offline, but what it has saved does not list this game...`

The first string matches the old native SteamConnection.sendPing catch:
`SteamError.connectionFailed(error.localizedDescription)`. It discarded the
NSURL domain/code. Initial handshake failure left the task/session attached
and did not mark the selected CM failed; the next start could choose the same
endpoint. The existing logon retry loop runs *after* connect(), so it never
handled this initial TLS failure. These are verified source defects matching
the report's native-CM stage; the accelerator's underlying TLS fault is not
yet reproduced or attributed to a specific certificate/proxy/DNS setting.

The second string exactly matches MadeiraDock result 52: Valve's offline
session did not list the game in its cached licenses. This is not Cloud's
TLS error and cannot be repaired by pretending a license/offline ticket exists.
It also indicates the legacy Dock route, rather than the actual Windows Steam
Big Picture UI. The separate Build 65 re-signing product-gate repair may be
relevant if a custom Bundle ID accidentally disabled the product shell; the
reporter's final Bundle ID and actual build are still unknown. Marketing
version 0.1.3 alone does not identify Build 56/64/65/etc.

### Minimal network recovery patch

- Preserve safe transport domain and numeric code as SteamError.transportFailed;
  never retain/log NSError URL/header/userInfo payloads in that new error.
- Release failed WebSocket tasks and invalidate their URLSessions.
- Mark initial-handshake failures in CMServerList, exclude endpoints already
  tried, and allow at most three distinct endpoints from Valve's existing list
  for transient URL errors including generic TLS negotiation failure (-1200).
  No same-endpoint blind retry, manual port rewrite, plaintext fallback or
  substitute server list is introduced. Exhausting a short list preserves the
  original transport failure rather than masking it with no-servers.
- Do not automatically retry explicit certificate trust/date/root/client-cert
  failures, cancellation or offline errors. Normal platform certificate and
  hostname verification remain unchanged; no challenge override is installed.
- Identity-check receive callbacks so a cancelled old task cannot close the
  replacement connection. Preserve the disconnected CM identity for the
  existing later reconnect policy.
- UI/logs retain the code so the next report can distinguish TLS negotiation
  from trust failure and other transport errors.

### Actual validation / limits

Production connection-loop methods and the actual CMServerList run in a host
harness with scripted transport results. Tests pass transient TLS/DNS failures
then success on three different endpoints, cancellation, one-server exhaustion,
three-attempt budget, certificate fail-closed, task/session cleanup, last-code
preservation, sensitive userInfo redaction and stale-task callback isolation.
This does not exercise real TLS handshakes or either accelerator.

Existing Steam Cloud save comparison/conflict/backup tests all pass. Full
unsigned iOS Build 66 succeeds with custom Bundle ID org.example.ideck.resigned;
final linked dylib contains the new categorical transport and TLS error markers.
No affected-device install/accelerator/Cloud-sync/gameplay success is claimed.
Existing phone Build 64 session is preserved. This patch and earlier JIT fixes
remain uncommitted/unpushed under the user's daytime restriction.

Private build log SHA-256:
`e53fd94e8e84f87f6104ab17563450dd07f881c80c4767d2cb414f2873be2e13`.
SteamConnection.swift working-source SHA-256:
`4b723e03a079d7d65e1276e9a0b2461f877a8db75ee7bf2a40baf8ce2cd255d2`.
SteamError.swift working-source SHA-256:
`770e3be1c9be4e733e53ea97acf800225621bbf2ffc53ad9e47c1b0c4338a878`.

Next acceptance: on the affected iOS 27.2 install, test native CM/Cloud before
JIT with each accelerator; record categorical transport code/attempts. Then
compare after JIT and verified previous-VPN restoration. Finally verify genuine
online entitlement and first game launch separately from Cloud file transfer.
If all three CMs fail, use that preserved code to investigate the actual route/
TLS failure rather than expanding retry counts or weakening verification.
