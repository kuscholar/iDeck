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
        pending = nil
        return 0
    }

    /// Used at the existing native Dock launch-option selection point. All
    /// authentication/JIT/session/installer/Valve LaunchApp steps remain in
    /// ContentView.startDock. This snapshot neither claims nor discards a slot.
    func launchOption(for game: DockGame, options: [SteamLaunchOption]?,
                      fallback: UInt32, installedGames: () -> [DockGame]) throws -> UInt32 {
        guard let captured = snapshot() else { return fallback }
        guard let options else { throw LabDockSelection.Failure.missing }
        let selected = try captured.request.select(installedGames: installedGames())
        guard selected.game == game else { throw LabDockSelection.Failure.mismatched }
        return try selected.launchOption(appID: game.id, options: options)
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
