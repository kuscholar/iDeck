# Steam client recovery

## Observed failure and limits

User reported a Steam crash during logout/account switching, followed by a failed
“Steam & browser files” prerequisite. A fresh device-list query succeeded, but
copying the client's executable failed CoreDevice 4000 / transport reset (54).
No device file header or crash log was obtained. The logout crash's root cause
is therefore not established. Do not label this as confirmed file corruption.

The prerequisite checks x86 PE headers for steam.exe, steamclient.dll,
steamwebhelper.exe and libcef.dll. A missing/truncated file, incompatible x64
client update or unsafe symlink can fail it; credentials are not part of this
check. The old Prepare Steam action called importBundledX86, which intentionally
returned without changing an existing directory, even when it was incomplete.
That confirmed recovery-path defect left users unable to repair from the app.

## In-app recovery

The launcher now reports which required file is missing, invalid/unsafe or an
unsupported x64 client update. Steam recovery → Repair Steam files is available
without a successful prerequisite check or JIT. Reopen iDeck first if any Wine
session has already started. The action refuses active Wine/server/JIT-pool
sessions. Successful repair disables auto-start and requires another app reopen
before launch, avoiding a fragmented JIT address space after large file reads.

Repair prefers a compatible bundled Steam32OfficialClient; otherwise it accepts
an explicitly user-provided Documents/Steam32OfficialRepair. Source-only public
builds may not contain Valve files. Copy a complete compatible client there with
Files; do not copy credentials from another device. iDeck does not download an
unverified alternate client or bypass Valve login. If no source exists, the UI
explains this instead of silently succeeding.

Only public client resources are restored. Config, userdata, steamapps, logs,
cache directories, ssfn files and save data are excluded. Existing replaced
public files are copied to wine/client-rollbacks/<UUID>. All destination paths
are checked for symlinks before writing. Files are atomically replaced, checked
again afterwards, and a failed repair attempts rollback while retaining the
backup. A full disk can also prevent rollback; retry after freeing storage.
No prefix reset, account-cache deletion or uninstall is performed.

Existing pinned x86 bootstrap switches remain enabled. They reduce accidental
client architecture upgrades but do not establish the cause of this incident or
prevent every Steam crash. Authentication and account switching remain Valve's.

## Validation

Host production-policy tests cover incompatible upgrade restoration, missing
browser repair, account-data preservation, rollback copies, architecture gates
and symlink rejection. iDeck prerequisite/lifecycle regressions pass.
Build 67 compilation and device validation are recorded separately in the POC
results. Compilation is not proof of device repair or fixed account switching.

## Device follow-up

The affected phone steam.exe was read successfully as AMD64 (0x8664), while
the existing repair source is i386 (0x014c). This explains the architecture
check failure. Build67 was signed, installed in place and launched; the user
confirmed the in-app repair restored use. The logout crash causal chain is
still unverified. No general account-switch crash fix is claimed.

## Automatic download and transactional repair (feature branch)

`feature/automatic-steam-client-install` adds **Download & Install Steam** to
prerequisite2 and **Repair Steam Files** for existing clients. It uses all19
pinned Valve packages, not Dock's three component archives. Manual repair/import
uses the same complete catalog validator. The earlier four-PE maintenance helpers
remain for historical explicit diagnostics; the launcher verifies the full client
on its background actor before turning step2 green or scheduling auto-start.

The source/whole-file SHA pins, actual availability results, storage budget,
verified-package cache, safe streaming extraction, cancellation, durable journal,
rollback, preserved directories and support/licensing limits are documented in
[AUTOMATIC_STEAM_INSTALL.md](AUTOMATIC_STEAM_INSTALL.md). The previous sections
record Build67 behavior; they do not describe the automatic installer's full-file
checks. No prefix/account reset is required. After repair, reopen the app before JIT.
