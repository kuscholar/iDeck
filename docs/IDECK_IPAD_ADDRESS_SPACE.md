# Issue 1: iPad green desktop and WoW64 capacity

Issue: https://github.com/kuscholar/iDeck/issues/1

## Failure, evidence and attribution

The reporter identifies iPad15,3 / iPadOS27.0.1, ad-hoc Build67 IPA with the
published matching hash and a development re-sign. Their quoted runtime trace
explicitly reports 639MiB free VA, refuses a 4GiB guest window plus the default
8GiB remaining margin, and returns STATUS_NO_MEMORY 0xc0000017 at the child
boot stage guest-window-reserve. This is reporter-supplied evidence, not our
own on-device reproduction. The full process mapping census is not supplied;
we cannot attribute every VA mapping or claim a specific entitlement/device
combination will solve it.

The refusal is intentional in virtual_ios.c: ios_wow_map_allows_window checks
actual task map size and sum of holes before a fresh window reservation. Each
32-bit pseudo-process needs a separate 4GiB translated host window. Physical
RAM, disk space, successful JIT/debugger attachment, a host surface present or
running=1 do not prove this reservation fits. Even a zero remaining margin
cannot make a 4GiB window fit in 639MiB. We do not remove that guard or invent
an overlapping allocation.

Confirmed UI defects: readiness checked files/signing/JIT but no VA capacity;
SteamUIEvidence recorded presents/milestones but not child-boot refusal, while
the Wine desktop could remain alive. Thus neither the successful JIT check nor
the running flag produced a useful visible failure. We repair these defects,
not the underlying limited-address-space runtime.

## Minimal local changes (Build68)

- A seventh prerequisite, 32-bit address space, samples the actual task map and
  free holes via the existing map query and vm_region_64. Object ports are
  released. Query errors yield unknown, not fabricated free space. Defaults
  and configured map/free margins match the runtime's necessary-capacity rule.
  This is a snapshot of total free VA, not an aligned contiguous reservation or
  a guarantee of multiple CEF children succeeding.
- File readiness and launch now use the same complete-directory selector;
  the checklist displays that selected directory. A bundled-client import no
  longer silently changes a valid fallback directory during launch. Replacing
  only steam.exe while retaining mixed-architecture CEF is still refused.
- The direct/automatic launch path also checks capacity. Runtime failures that
  occur later are observed independently of the paused UI log tail, using
  newly appended bytes only, bounded sequential reads and partial-line state.
  The exact guest-window stage plus c0000017 raises a native error alert.
  Old-session messages, unrelated stages and host presents do not trigger it.
- No FEX/native allocator/Steam binary/entitlement/credential modifications.
  No automatic close/restart, account logout or data deletion.

## Client acquisition and entitlements

Valve's official notice says support for 32-bit Windows ended January1,2026:
https://help.steampowered.com/en/faqs/view/49A1-B944-48B8-FF00

The tested legacy32 path is not a supported current-client acquisition solution
for new users. iDeck does not supply Valve archives, a maintained legacy client
installer or credentials. A full matching older client is necessary; swapping
an old bootstrapper into current 64-bit CEF is not sufficient. A fully current
64-bit Steam mode needs separate compatibility work and is not enabled merely
to bypass this check. This remains a product limitation.

increased-memory-limit concerns memory budgeting; it does not establish a
sufficient contiguous VA window. extended-virtual-addressing may affect the
actual map where legitimately granted, but adding a key does not grant it.
We do not assume that a free-team profile allows it or that re-signing solves
this report. The task map is measured rather than inferred from plist claims.
DDI downloading/reusing an already-mounted image is separate from this
post-JIT failure and is not fixed by this patch.

## Reproducible local validation

Run with writable Swift/Clang module caches as needed:

```
python3 tests/host/check-ideck-startup-failure.py
python3 tests/host/check-steam-ui.py
python3 tests/host/check-ideck.py
```

Actual Swift production-policy tests cover 639MiB, zero-margin insufficiency,
minimum map, exact boundary, integer overflow, old logs, split/new failure lines,
>64KiB busy logging, rotation, unrelated stages and negative statuses. Existing
launcher tests verify a failed capacity row blocks launch. Shared client tests
verify readiness agrees with selected Steam32Lab and rejects mixed CEF.

Local full Build68 and final linked markers are recorded in POC results. No
claim that this affected iPad can run Steam after the patch; next runtime
experiment needs the reporter's full redacted map census at JIT-ready and child
boot, then a separately validated reservation-layout change or current-client
architecture effort. No unsafe capacity workaround is shipped.
