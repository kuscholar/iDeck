#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Exact private ContentView option hook; does not change normal runtime gates."""
OLD = '            let launchOption = chosen ?? 0'
NEW = '''            let launchOption: UInt32
            do {
                launchOption = try LabDockPending.shared.launchOption(
                    for: game, options: options, fallback: chosen ?? 0,
                    installedGames: { MadeiraDock.games(drive: MadeiraDock.drive) })
            } catch { fail(error); return }'''

def patched(source):
    assert source.count(OLD) == 1, 'Pinned native Dock option selection changed'
    result = source.replace(OLD, NEW)
    # Preserve ordering and all native checks/actions. A matcher refusal must
    # return BEFORE closing the native CM or creating a sign-in transfer.
    start = result.index('    private func startDock(')
    body = result[start:]
    assert body.index('guard SteamSignIn.isSignedIn') < body.index(NEW)
    assert body.index(NEW) < body.index('await SteamOwnedLibrary.shared.prepareDock()')
    assert body.index('await SteamOwnedLibrary.shared.prepareDock()') < body.index('try MadeiraDock.writeHandoff(')
    return result
