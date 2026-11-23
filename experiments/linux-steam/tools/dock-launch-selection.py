#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Exact private ContentView option hook; does not change normal runtime gates."""
OLD = '            let launchOption = chosen ?? 0'
NEW = '''            let labLaunch: (index: UInt32, sequence: UInt64?)
            do {
                labLaunch = try LabDockPending.shared.launchOption(
                    for: game, options: options, fallback: chosen ?? 0,
                    installedGames: { MadeiraDock.games(drive: MadeiraDock.drive) })
            } catch { fail(error); return }
            let launchOption = labLaunch.index'''
TRANSFER = '                guard let signIn = SteamSignIn.credentialsForDock() else {'
RECHECK = '''                try LabDockPending.shared.validateForHandoff(
                    sequence: labLaunch.sequence, recheck: ideck_game_file_policy_revalidate_pending_shared)
'''

RESERVATION = """        let labPreparation: UInt64?
        do {
            labPreparation = try LabDockPending.shared.beginPreparation()
        } catch {
            logStore.log("[madeira-dock] a captured Play is already being prepared", level: .error)
            return
        }
"""
WINE_ENTRY = '    private func runWineFullSequence(profile: LibraryEntry? = nil, steamUI: Bool = false) {'
JIT_REFUSAL = '            if profile != nil { LibraryModel.shared.launchFailed() }'
POOL_REFUSAL = '                DispatchQueue.main.async { LibraryModel.shared.launchFailed(reason, offerJIT: offerJIT) }'
EARLY_RELEASE = """if labDockPreparation != nil {
                    MadeiraDock.cleanup()
                    SteamOwnedLibrary.shared.dockEnded()
                    LabDockPending.shared.releasePreparationBeforeWine(labDockPreparation)
                }"""

def replace_once(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new)

def retain_preparation(dock):
    failure = '        func fail(_ error: Error) {'
    dock = replace_once(dock, failure, RESERVATION + failure)
    task = '        } catch { fail(error); return }'
    # Only the initial, synchronous validation uses this standalone catch line.
    dock = replace_once(dock, task + '\n        // Only one sign-in', """        } catch {
            fail(error)
            LabDockPending.shared.releasePreparationBeforeWine(labPreparation)
            return
        }
        // Only one sign-in""")
    anchor = '        Task { @MainActor in'
    dock = replace_once(dock, anchor, anchor + """
            var submittedToWine = false
            defer {
                if !submittedToWine { LabDockPending.shared.releasePreparationBeforeWine(labPreparation) }
            }""")
    anchor = '            let launchOption = labLaunch.index'
    dock = replace_once(dock, anchor, """            guard labLaunch.sequence == labPreparation else {
                fail(LabDockSelection.Failure.mismatched)
                return
            }
""" + anchor)
    configure = '            MadeiraDock.configure(game, launchOption: launchOption)'
    dock = replace_once(dock, configure, configure + r"""
            if let labPreparation {
                guard let reportName = LabDockPending.shared.beginReport(sequence: labPreparation) else {
                    fail(LabDockSelection.Failure.mismatched)
                    return
                }
                guard setenv("MADEIRA_STEAM_HOST_LOG", "C:\\\(reportName)", 1) == 0 else {
                    fail(DockError.message("Madeira could not configure the Lab’s launch report."))
                    return
                }
            }""")
    call = '            runWineFullSequence(profile: profile)'
    return replace_once(dock, call, """            submittedToWine = true
            runWineFullSequence(profile: profile, labDockPreparation: labPreparation)""")

def allow_retry_before_wine(source):
    start = source.index(WINE_ENTRY)
    stop = source.index('\n    private func ', start + len(WINE_ENTRY))
    body = source[start:stop]
    body = replace_once(body, WINE_ENTRY,
        '    private func runWineFullSequence(profile: LibraryEntry? = nil, steamUI: Bool = false, labDockPreparation: UInt64? = nil) {')
    body = replace_once(body, JIT_REFUSAL, JIT_REFUSAL + '\n            ' + EARLY_RELEASE.replace('\n    ','\n'))
    body = replace_once(body, POOL_REFUSAL, """                DispatchQueue.main.async {
                    LibraryModel.shared.launchFailed(reason, offerJIT: offerJIT)
                    """ + EARLY_RELEASE.replace('\n','\n    ') + """
                }""")
    return source[:start] + body + source[stop:]

def patched(source, recheck_pending=False):
    assert source.count(OLD) == 1, 'Pinned native Dock option selection changed'
    result = source.replace(OLD, NEW)
    # Preserve ordering and all native checks/actions. A matcher refusal must
    # return BEFORE closing the native CM or creating a sign-in transfer.
    start = result.index('    private func startDock(')
    body = result[start:]
    assert body.index('guard SteamSignIn.isSignedIn') < body.index(NEW)
    assert body.index(NEW) < body.index('await SteamOwnedLibrary.shared.prepareDock()')
    assert body.index('await SteamOwnedLibrary.shared.prepareDock()') < body.index('try MadeiraDock.writeHandoff(')
    if recheck_pending:
        stop = body.index('\n    private func ', 1)
        dock, rest = body[:stop], body[stop:]
        assert dock.count(TRANSFER)==1, 'Pinned Dock credential handoff changed'
        assert dock.index('await SteamOwnedLibrary.shared.prepareDock()') < dock.index(TRANSFER)
        dock = retain_preparation(dock.replace(TRANSFER,RECHECK+TRANSFER))
        result = allow_retry_before_wine(result[:start] + dock + rest)
    return result


def patched_report_reader(source):
    source = replace_once(source, '"game-scm", "game-scm-timeout", "launch-keep-alive",',
        '"game-scm", "game-scm-timeout", "launch-keep-alive", "launch-game-running", "launch-game-ended",')
    start = source.index('    @MainActor static func pollReport() -> Report {')
    end = source.index('\n    }', start)
    body = source[start:end]
    body = replace_once(body, '        let url = drive.appendingPathComponent("madeira-dock.txt")',
        '        let name = LabDockPending.shared.reportFilename() ?? "madeira-dock.txt"\n'
        '        let url = drive.appendingPathComponent(name)')
    body = replace_once(body, '        lastReport = report', """        if let evidence = LabDockPending.shared.observeReport(filename: name, fields: report.fields),
           let support = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first {
            let file = support.appendingPathComponent("iDeckLinuxLab/last-native-dock-game.json")
            do {
                try JSONEncoder().encode(evidence).write(to: file, options: .atomic)
            } catch {
                SteamLog.event("[dock-report] lab-lifecycle-receipt-write-failed=1")
            }
        }
        lastReport = report""")
    return source[:start] + body + source[end:]
