# Build137: one selected Steam runtime for ordinary app-open

The previous explicit Steam64 tests used `wine-steam64`, but ordinary app-open
selected legacy `wine`/Steam32BundleLab. Each prefix retained its own Steam-owned
login. Neither batch contained changeuser. This explained the user seeing a
different saved account without an agent account-change action.

Persisted `steam-runtime = steam64` now selects that prefix for ordinary app-open,
launcher/account actions and JIT return. Its local `steam64.env.*` settings are
read with the existing C config parser before native holds/JIT; ordinary env
exports do not activate them in explicit legacy diagnostics. A missing selected
profile/reservation rejects launch rather than silently opening the old account.
The launcher labels the selected32/64bit runtime.32bit file repair is not applied
to a64bit prefix. No account cache or saves are transferred between prefixes.

The observed legacy browser fault was0xc0000005 reading0x180c, exact native
LDRSW instruction0xb9980e48 and Wow64 caller. Its narrow own-TEB adaptation was
restricted to wine-steam64. The adapter now accepts the two preserved Steam
prefixes under the existing session/registered-thread/opcode/offset/x18 checks,
reading the actual signed field. It does not fabricate a value or ignore general
access violations. Existing and added negative/signed-value tests pass.

Full Build137 and37native units pass. Final linked fix markers and deep strict
signing pass. Kusch actually installs/readbacks137; the selected local config
and minimal ExternalHandler update match after readback. Normal app-open is
launched WITHOUT diagnostic arguments or injected environment. The bounded wait
observes no fresh Steam login and native log shows app initialization only, not
Wine startup. Keep the existing auto-start preference. This is installation and
normal app-open validation, not fresh Steam login/game/legacy-browser success.

The user is to complete launcher prerequisites, start Steam, verify the selected
saved account and test game/exit/navigation. No agent game launch is performed
in137. Stable repeated gameplay and the earlier capacity/lifetime failures are
still unresolved. Exact private FEX131 remains local-only, not in this source
checkpoint; no release is made. Source changes stay on fix/steam-runtime-entry.

Evidence: [IDECK_RUNTIME_ENTRY_EVIDENCE.json](IDECK_RUNTIME_ENTRY_EVIDENCE.json).

## November2 user test: ordinary entry verified, repeated game still fails

User confirms first game enters/returns and later failures leave Steam usable.
Native launcher marker11:14:11 verifies wine-steam64. Hot Roads11:15:18..42
exits0. Further starts11:15:54 and11:16:15 each exitc0000135 after3seconds.
Their original UnityPlayer pool-copy allocation failsc0000017, not file open or
architecture query:22.047MiB requested,21.859MiB largest free block,85.891MiB
total free bookkeeping. A192KiB shortfall in the largest block is sufficient
to refuse the copy. Requested704MiB becomes actual592MiB main span/C336MiB.

First-game exit records60freed ranges, but the exact large-image block's fate
is not established. Existing best-fit and adjacent clean-block merging already
exist. Next collect interval/owner/reuse/protection history, then change the
demonstrated allocation/lifetime contract. No leak, browser OOM or missing-DLL
claim is made. Current user session stays alive; collection was read-only.
