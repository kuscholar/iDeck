# Bounded CEF64 lease evidence

This is an experiment diagnostic, not a reservation, reclamation or compatibility
fix. It records the existing Wine adopter/free observer without changing their
results. The integration is currently local to the experimental checkout.

Build132 reached the Hot Roads menu twice in one native lifetime. The first
exit is recorded as exit0. After the second visible return, clicking Steam Search
showed Steam's own content-error page. The second exit code and cause of the
content error have not been collected. Do not promote this to a stable-release
result. See [the game-return record](CEF64_GAME_RETURN_FAILURE.md).

## Why a separate file

CoreDevice copies subsequently failed for both small Steam records and the large
native log, including after the user restored the remote connection. A partial
native copy is exactly10,000,000 bytes and ends mid-line before the second game;
it is not a complete no-fault record. Official lockState reports
passcodeRequired=false. The exact experimental task was ended after capturing
the Steam content-error screen; its absence is verified. Temporary configuration
restoration stopped at a timed-out first upload and remains unverified. Do not
start another Steam trial or upgrade before verifying/restoring that state.

Build133 prepares a smaller, numeric-only evidence channel. Enable all of:

```text
MADEIRA_STEAM_UI_SESSION=1
MADEIRA_CEF64_LEASE_TRACE=1
MADEIRA_CEF64_LEASE_FILE=1
```

The existing standalone CEF64 owned layout and isolated `wine-steam64` prefix
are also required. Each native lifetime creates an exclusive file under
`drive_c/ideck-cef64-leases-<native-pid>-<seconds>-<nanos>.txt`. Retrieve only the
file matching the current launch receipt. Records include sequence, monotonic
time, numeric process/thread identity, slot, operation, sizes, status and whether
any Wine view still overlaps the lease. No paths, command lines, auth data or
arbitrary object contents are recorded. An `adopt` attempt with nonzero status
is not a successful adoption; `remaining=-1` means it was not queried.

The writer preserves errno, is serialized, stops before512KiB/4096records, and
emits a budget-exhausted marker when that limit is reached. It never overwrites
an existing file or follows a final symlink. Replaced/truncated/externally
appended files stop collection. Any write/open failure stops diagnostics without
retrying a VM operation. A missing/truncated record is not proof of release,
failure absence, or complete coverage. This file never authorizes lease reuse.

## Verified boundaries

- `python3 tests/host/check-cef64-lease-file.py`: actual POSIX files and production
  writer, ASan/UBSan; exact gates/schema/errno, exclusive-file and symlink safety,
  replacement/truncation detection, eight concurrent writers and budget framing.
- Existing production adopter/observer host tests pass with unchanged ownership,
  bounds, exhaustion and rollback results; these do not exercise device VM.
- All37 native units and full Xcode133 build pass. Final debug-dylib markers,
  unchanged private FEX131/helper126 hashes and deep-strict signing are verified.
- Build133 has **not** been installed or device-run on Kusch. Separate Air133/134
  native capacity tests do not exercise this Steam lease channel. Signing uses the existing
  valid main/helper profiles; no account re-login or new entitlement is assumed.

## Source-grounded next discriminator

The exact Chromium revision
[`2e81dea53f5ecdc1c057e4c70ecd66151987296a`](https://github.com/chromium/chromium/blob/2e81dea53f5ecdc1c057e4c70ecd66151987296a/content/browser/renderer_host/render_process_host_impl.cc#L4643)
returns true for renderer reuse in single-process mode before checking the
process-count limit. Therefore adding a renderer-process-limit flag alone is not
an established fix for this existing single-process path. This source finding
does not prove how many V8 isolates the actual Valve client keeps alive.

The pinned [V8 table implementation](https://github.com/v8/v8/blob/12.6.228/src/sandbox/external-entity-table-inl.h#L119)
frees its first segment and destroys its subspace during TearDown. After remote
file access is restored, collect the new lease channel through two real
game/return/navigation cycles. Distinguish preserved placeholders, successful
full releases with no remaining view, and still-live peak demand. Only then
design a minimal ownership/lifetime patch; do not recycle a live reservation.

## Read-only analysis for the next iPhone cycle

```sh
python3 tools/analyze-cef64-leases.py /private/path/to/current-lifetime.txt
python3 tests/host/check-cef64-lease-analysis.py
```

The analyzer separates successful adoptions, failed attempts, refusals, failed
frees, preserved placeholders and successful frees with/without an observed
remaining Wine view. Even the last category does not release the native claim
or authorize reuse. A partial trailing record is ignored and flagged; a budget
marker is terminal. Sequence gaps, mixed non-monotonic records, foreign schemas
and invalid numeric fields fail without printing arbitrary input payloads.
Every report explicitly limits coverage to observations. Missing records never
prove the absence of a failure or that teardown completed.

Host fixtures pass for the analyzer, including false-success traps and truncated
evidence. The production writer/observer ASan/UBSan regressions also pass. No
new iPhone game/return result is implied by these local checks.
