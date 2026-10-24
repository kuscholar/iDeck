// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright 2026 Jfishin, 125hz
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
//
// Derived from Jfishin's Madeira Steam client, used in Madeira with the
// author's permission (see docs/STEAM_SIGNIN.md, "Provenance"). Adapted for
// the owned library and downloads (docs/STEAM_LIBRARY.md).

import Foundation

/// One-shot async delivery of the owned-package-ID list.
///
/// Steam pushes `CMsgClientLicenseList` automatically right after every CM
/// logon. `set(_:)` records it; `value(timeout:)` returns it immediately if
/// already received, otherwise waits — with a per-waiter timeout that throws
/// rather than hanging forever. `reset()` is called at the start of each
/// connection so a stale list never satisfies a post-reconnect waiter.
@MainActor
final class LicenseListBox {
    private var packageIDs: [UInt32]?
    private var waiters: [UUID: CheckedContinuation<[UInt32], Error>] = [:]

    /// Record a license list and wake every pending waiter. Overwrites any
    /// previous list so a fresh logon's list supersedes a stale one.
    func set(_ ids: [UInt32]) {
        packageIDs = ids
        let pending = waiters
        waiters = [:]
        for (_, continuation) in pending {
            continuation.resume(returning: ids)
        }
    }

    /// Forget the current list so the next `value(timeout:)` waits for a
    /// fresh push instead of returning a pre-reconnect list.
    func reset() {
        packageIDs = nil
    }

    /// Return the package IDs, waiting up to `timeout` seconds if none have
    /// arrived yet. Throws `SteamError.connectionTimeout` on expiry.
    func value(timeout: TimeInterval) async throws -> [UInt32] {
        if let packageIDs { return packageIDs }
        let waiterID = UUID()
        return try await withCheckedThrowingContinuation { continuation in
            waiters[waiterID] = continuation
            Task { @MainActor [weak self] in
                try? await Task.sleep(nanoseconds: UInt64(timeout * 1_000_000_000))
                guard let self, let waiter = self.waiters.removeValue(forKey: waiterID) else { return }
                waiter.resume(throwing: SteamError.connectionTimeout)
            }
        }
    }
}
