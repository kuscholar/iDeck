# Linux Steam + Madeira iPad continuation

User requested every305 minutes until repeatedly stable on **iPad Air4/iPad13,1**.
As of run2, a user LaunchAgent `com.kusch.ideck-linux-steam-ipad-305m` is loaded,
interval18300seconds, official CLI dispatch actually tested, last exit0. It calls
`codex app-server daemon start`, then `codex queue --resume` for this existing
thread. The active writer correctly deferred resume. A full unattended research
turn after writer release is not yet observed. This is a macOS task, not a task
created in the app's native Scheduled UI. Sleep/offline storage can delay work.

## Required context and constraints

Work in `/Volumes/easystore/GitHub/FunProjects/iDeck-linux-steam-ipad`, branch
`experiment/linux-steam-madeira-ipad`, origin kuscholar/iDeck. Read migration status
and verify volume UUID580CADCD-33F5-4D78-9530-2287615873CA before writes. Read
AGENTS/CONTRIBUTING, LINUX_STEAM_MADEIRA.md and its EVIDENCE.json FIRST. Inspect
current branch/remote/uncommitted work and active processes. Preserve all other
worktrees, apps, accounts/games/saves. No main merge, reset/force push or FEX edit.
Check the user's commit/push window immediately before each operation and sign off.
Do not restart completed audits or overwrite an active experiment's executable.

**User requires command-line operation and explicitly prohibits any further Mac
unlock requests.** Do not operate around locks, alter security settings or extract
credentials. Normal authorized CLI tools are allowed. Never automate Steam login,
Guard or user trust approval. Continue independent verifiable work at real human
authorization gates; do not repeat unchanged prompts or assume unsupported paths.

## Current actual status and next gates

The selected Air is paired, developer-enabled, iPadOS27.2(24B119). Its exact ID and
fresh metadata are in private run2/air-details.json. Do not substitute Pro/iPhone
or simulator. Default Lab ID linuxlab has no profile. CLI-only deployment uses
existing **com.kuschqin.ideck.freshtest**, absent on Air before this run, because
its current authorized profile covers Air/certificate. It is distinct from the
unchanged installed Mac Allocator and production iDeck. No phone install changed.

Lab1 actually signed/deep-verified/installed/read back as iDeck Linux Lab, but
SpringBoard refused launch with generic signature/entitlement/trust message.
**No device ELF result yet.** The user was asked to inspect the exact Air prompt
and trust the developer only if iPad reports it untrusted. That reply is pending.
Don't infer Linux crash, repeatedly launch, install over a live test or ask to
unlock Mac. Verify local profile/signature/device coverage before later upgrades.

Lab2 source/unsigned iOS arm64 build has the corrected v3 patch and16 host probe
lines; final Mach-O marker verified. It has not been deployed on Air yet. For the
existing Air lab, build with PRODUCT_BUNDLE_IDENTIFIER=com.kuschqin.ideck.freshtest
and matching authorized profile; preserve its container. Do not accidentally
replace the phone Fresh Test installation. Source default remains linuxlab.

LinuxRunner vendor pin d1419782 and optional libarchive fc6563f5 source remain
pristine. Interpreter-only Lab excludes JIT, GUI and Madeira linkage currently.
Host genuine ELF tests cover fs/entropy/shared mmap/clone/wait/socketpair/futex,
invalid openat/faccessat2 and absolute-dirfd plus NULL-path file utimensat; all16 pass. Native
bridge and actual ARM64 compatibility wrapper return diagnostic125, never a game.
Protocol sanitizers/package/archive/scheduler tests pass. No Steam discovery or
native host path/license/symlink/TOCTOU authorization is implemented by syntax-only
IPC. Complete Linux shutdown and Wine's session-once lifecycle remain gates.

Important correction: v1 common-path guard broke touch. v2 moved the guard to
relative openat, allowing full Debian initialization. Full-root real Steam then
still aborted: actual backtrace shows generic_accessat -> sys_faccessat2.
Current v3 checks relative openat AND accessat with explicit non-directory fds;
it preserves absolute-dirfd behavior, file-null utimensat and the original common
normalization/assertion. Generated fs_path.c.o is restored pristine, fs_generic.c.o
replaced, linked marker IDECK_LINUXRUNNER_DIRFD_GUARD_V3 required. Host16 controls
and final unsigned iOS2 marker pass; installed Air1 still has v1, no device fix claim.

All103 pinned Debian base packages verified, assembled and configured IN the
Linux guest, with normal CA setup. ARM64 glibc2.41/curl8.14.1/OpenSSL3.5.7 and genuine
Valve HTTPS download pass on host outside the tool network sandbox. Prior sparse
root http0/DNS errors are not evidence of an intrinsic LinuxRunner network failure.
All17 official stable ARM64/resource packages verified/extracted. Root assembly
is under run2; read latest import/client logs before claiming startup. Codec ../
links resolve to regular same-package targets, escapes/chains rejected. A native
host-only fakefs importer patch accepts only existing SAME regular inode aliases
on case-insensitive storage (PAM/pam doc hardlink), rejects different-inode conflicts.
It is not a guest filesystem/runtime or permission workaround.

Full-root assembly now includes explicit /Steam directory metadata. Root
run2/steam-fakefs-v3 really executes Steam with current v3 guard, downloads the
client update to100% and begins extracting packages. The75.057-second bounded
observer deliberately sends SIGTERM (returncode-15); this is NOT a crash, update
completion, UI or natural client exit. Receipt run2/steam-dirfd-v3.json and log
are private. No X11 server exists. Next inspect/resume the same unauthenticated
root under a longer bounded observer, identify the next actual error, then bring
up minimal X11/display. Do not overwrite host/ish while it executes or infer a
network/CEF failure from an observer timeout. No account was ever logged into
these host roots. Keep raw data/private packages out of Git.

After actual Air ELF controls, bring up complete rootfs and minimal X11/display,
then genuine Valve ARM64 Steam login/Library/BPM. Reuse LinuxRunner RFB client/
Metal framebuffer only after checking dependencies; no fake Steam UI. Only then
validate Steam-discovered compatibility tool and Madeira's real licensed game
launch/return. Keep Wine/FEX/DXMT and ordinary iDeck unchanged; no Proton substitute,
DRM/auth bypass, assumed private entitlements, converter-exception expansion or
unreviewed combined binary publication. Wired controls are not Bluetooth proof.

At every run record exact revisions, experiment hypothesis/discriminator, real
artifact evidence/hashes, regression results/limits and next action in the log.
Private artifacts: `.madeira-install/linux-steam-ipad`, raw device/profile/auth
files excluded from Git. Observe only bounded identity-checked processes. Never
call build/install/process/BrowserReady a working interactive UI.

Stop this scheduled task only after repeated actual Air ELF/interactive genuine
Library+BPM/input, Play->licensed Madeira game->return and stability evidence.
Record evidence-backed STABLE_SUCCESS.json privately, then boot out **only**
`gui/<uid>/com.kusch.ideck-linux-steam-ipad-305m`; do not stop other services.
The task itself does not evaluate milestones; the agent must verify evidence.
