// SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
import Foundation
import Darwin

/// One owned request, converted through the SAME C protocol/path mapper used
/// by the Linux capture. No JSON, raw-frame log, credential or launch action.
struct LabDockRequest {
    let appID: UInt32
    let verb: UInt32
    let install: String
    let executable: String
    let workingDirectory: String
    let arguments: [String]
    enum Failure: Error { case invalidFrame, mapping(Int32), invalidText }

    init(frame: Data) throws {
        guard frame.count == MemoryLayout<ideck_launch_request>.size else { throw Failure.invalidFrame }
        // Aligned owned copy, not a borrowed guest pointer across queues.
        var input = ideck_launch_request()
        _ = withUnsafeMutableBytes(of: &input) { frame.copyBytes(to: $0) }
        var mapped = ideck_windows_launch_map()
        let status = ideck_windows_launch_map(&input, &mapped)
        guard status == 0 else { throw Failure.mapping(status) }
        func text<T>(_ field: T) throws -> String {
            try withUnsafeBytes(of: field) { bytes in
                guard let end = bytes.firstIndex(of: 0), let string = String(bytes: bytes[..<end], encoding: .utf8) else { throw Failure.invalidText }
                return string
            }
        }
        let args: [String] = try withUnsafeBytes(of: mapped.arguments) { bytes in
            let used = Int(mapped.argument_bytes)
            guard used > 0, used <= bytes.count else { throw Failure.invalidFrame }
            var result: [String] = []; var start = 0
            for _ in 0..<mapped.argc {
                guard start < used, let end = bytes[start..<used].firstIndex(of: 0),
                      let value = String(bytes: bytes[start..<end], encoding: .utf8) else { throw Failure.invalidText }
                result.append(value); start = end + 1
            }
            guard start == used else { throw Failure.invalidFrame }
            return result
        }
        appID = mapped.appid; verb = mapped.verb
        install = try text(mapped.install); executable = try text(mapped.executable)
        workingDirectory = try text(mapped.working); arguments = args
    }

    func select(installedGames: [DockGame]) throws -> LabDockSelection {
        try LabDockSelection.resolve(appID: appID, install: install, executable: executable,
                                     workingDirectory: workingDirectory, arguments: arguments,
                                     installedGames: installedGames)
    }
}

/// One native-owned handoff slot. Staging never starts Wine and does not
/// consume the Linux policy's original pending request or declare an exit.
final class LabDockPending {
    static let shared = LabDockPending()
    private let lock = NSLock()
    private let owner = getpid()
    private var lastSequence: UInt64 = 0
    private var pending: (sequence: UInt64, request: LabDockRequest)?
    private var preparingSequence: UInt64?
    private var activeReport: (token: UUID, last: ReportEvidence?)?

    struct ReportEvidence: Encodable, Equatable {
        let schema = 1
        let pid = getpid()
        let build = Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? ""
        let capture_sequence: UInt64
        let report_token: UUID
        let appid: UInt32
        let valve_reported_result: Int?
        let valve_reported_running: Bool
        let valve_reported_ended: Bool
        let valve_client_shutdown: Bool
        let dock_exit_status: Int?
    }

    private static func reportFilename(_ token: UUID) -> String {
        "madeira-lab-dock-\(token.uuidString.lowercased()).txt"
    }

    func stage(_ request: LabDockRequest, sequence: UInt64) -> Int32 {
        lock.lock(); defer { lock.unlock() }
        guard owner == getpid() else { return -18 }
        guard sequence > lastSequence else { return -116 }
        guard pending == nil else { return -16 }
        pending = (sequence, request); lastSequence = sequence
        return 0
    }
    func snapshot() -> (sequence: UInt64, request: LabDockRequest)? {
        lock.lock(); defer { lock.unlock() }
        guard owner == getpid() else { return nil }
        return pending
    }
    func discard(sequence: UInt64) -> Int32 {
        lock.lock(); defer { lock.unlock() }
        guard owner == getpid() else { return -18 }
        guard sequence != 0, pending?.sequence == sequence else { return -116 }
        guard preparingSequence == nil else { return -16 }
        pending = nil
        return 0
    }

    /// Serializes the captured Play while Dock awaits Steam configuration and
    /// submits native startup. Ordinary Dock choices do not claim this slot.
    func beginPreparation() throws -> UInt64? {
        lock.lock(); defer { lock.unlock() }
        guard owner == getpid() else { throw LabDockSelection.Failure.mismatched }
        guard let sequence = pending?.sequence else { return nil }
        guard preparingSequence == nil else { throw Failure.preparing }
        preparingSequence = sequence
        return sequence
    }

    /// Only for an attempt that returned before starting Wine or wineserver.
    /// The captured request remains available for a legitimate retry.
    func releasePreparationBeforeWine(_ sequence: UInt64?) {
        guard let sequence else { return }
        lock.lock(); defer { lock.unlock() }
        guard owner == getpid(), preparingSequence == sequence else { return }
        preparingSequence = nil
        activeReport = nil
    }

    /// Allocate the filename once, after the existing report reset. The
    /// Windows host already supports an explicit destination for its report.
    func beginReport(sequence: UInt64) -> String? {
        lock.lock(); defer { lock.unlock() }
        guard owner == getpid(), preparingSequence == sequence, pending?.sequence == sequence,
              activeReport == nil else { return nil }
        let token = UUID()
        activeReport = (token, nil)
        return Self.reportFilename(token)
    }

    func reportFilename() -> String? {
        lock.lock(); defer { lock.unlock() }
        guard owner == getpid(), let report = activeReport else { return nil }
        return Self.reportFilename(report.token)
    }

    /// Positive observations only come from the active request's report.
    /// Valve's running/ended observations and Dock's exit remain separate
    /// from proof of game input, Wine teardown or readiness to resume Linux.
    func observeReport(filename: String, fields: [String: String]) -> ReportEvidence? {
        lock.lock(); defer { lock.unlock() }
        guard owner == getpid(), let pending, preparingSequence == pending.sequence,
              let report = activeReport, Self.reportFilename(report.token) == filename,
              fields["probe-start-bits"] == "64" else { return nil }
        let sample = ReportEvidence(capture_sequence: pending.sequence, report_token: report.token,
            appid: pending.request.appID,
            valve_reported_result: fields["launch-client-error"].flatMap(Int.init),
            valve_reported_running: fields["launch-game-running"] == "1",
            valve_reported_ended: fields["launch-game-ended"] == "1",
            valve_client_shutdown: fields["shutdown-complete"] == "1",
            dock_exit_status: fields["probe-result"].flatMap(Int.init))
        guard sample != report.last else { return nil }
        activeReport = (report.token, sample)
        return sample
    }

    /// Used at the existing native Dock launch-option selection point. All
    /// authentication/JIT/session/installer/Valve LaunchApp steps remain in
    /// ContentView.startDock. Keep the exact capture sequence across the
    /// asynchronous Dock preparation without claiming or discarding it.
    func launchOption(for game: DockGame, options: [SteamLaunchOption]?,
                      fallback: UInt32, installedGames: () -> [DockGame]) throws -> (index: UInt32, sequence: UInt64?) {
        guard let captured = snapshot() else { return (fallback, nil) }
        guard let options else { throw LabDockSelection.Failure.missing }
        let selected = try captured.request.select(installedGames: installedGames())
        guard selected.game == game else { throw LabDockSelection.Failure.mismatched }
        return (try selected.launchOption(appID: game.id, options: options), captured.sequence)
    }

    /// Fail closed before the regular native Steam handoff. Ordinary Dock
    /// choices keep their fallback and never touch the Lab shared library.
    enum Failure: Error { case sharedExecutable(Int32), preparing }

    func validateForHandoff(sequence: UInt64?, recheck: (UInt64) -> Int32) throws {
        guard snapshot()?.sequence == sequence else { throw LabDockSelection.Failure.mismatched }
        guard let sequence else { return }
        let status = recheck(sequence)
        guard status == 0 else { throw LabDockPending.Failure.sharedExecutable(status) }
        guard snapshot()?.sequence == sequence else { throw LabDockSelection.Failure.mismatched }
    }
}

@_cdecl("ideck_lab_receive_dock_request")
public func ideckLabReceiveDockRequest(_ frame: UnsafeRawPointer?, _ length: Int,
                               _ sequence: UInt64) -> Int32 {
    guard let frame, length == MemoryLayout<ideck_launch_request>.size, sequence > 0 else { return -22 }
    do {
        let owned = Data(bytes: frame, count: length)
        return LabDockPending.shared.stage(try LabDockRequest(frame: owned), sequence: sequence)
    } catch { return -22 }
}

@_cdecl("ideck_lab_pending_dock_sequence")
public func ideckLabPendingDockSequence() -> UInt64 {
    LabDockPending.shared.snapshot()?.sequence ?? 0
}

@_cdecl("ideck_lab_discard_staged_dock_sequence")
public func ideckLabDiscardStagedDockSequence(_ sequence: UInt64) -> Int32 {
    LabDockPending.shared.discard(sequence: sequence)
}
