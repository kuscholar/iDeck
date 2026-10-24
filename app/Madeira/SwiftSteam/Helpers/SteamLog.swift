// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright 2026 125hz
// Madeira Converter Exception: see LICENSE-EXCEPTION.md

import Foundation

/// Logging for Steam sign-in.
///
/// `event` lines are the always-on, low-volume record ([steam-signin]). They
/// never contain tokens, passwords, Steam Guard codes, account names, Steam
/// IDs or message payloads.
///
/// `trace` lines are protocol-level detail, off by default. Enable with
/// `env.MADEIRA_STEAM_TRACE = 1` in madeira.cfg. They are still written
/// without credentials or payload bytes.
enum SteamLog {
    static let tracing = SteamSignIn.flag("MADEIRA_STEAM_TRACE", default: false)

    static func trace(_ message: @autoclosure () -> String) {
        guard tracing else { return }
        // LogStore, not stderr: stderr is only captured into the log once a
        // Wine session starts, and sign-in happens before one.
        LogStore.shared.log("[steam-trace] " + message())
    }

    static func event(_ message: String) {
        LogStore.shared.log(message)
    }
}
