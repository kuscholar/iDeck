// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Test executable for the production native installer; not a second installer.
// Compile with policy + SteamClientInstaller.swift, place the public catalog next
// to this executable, and pass a NEW private output directory. Never a live prefix.
import Foundation
final class TestDownloadCancellation: @unchecked Sendable {
    private let lock = NSLock()
    private var task: Task<Bool, Error>?
    func set(_ value: Task<Bool, Error>) { lock.lock(); task = value; lock.unlock() }
    func cancel() { lock.lock(); let value = task; lock.unlock(); value?.cancel() }
}
@main struct NativeSteamDownloadTest {
    static func main() async throws {
        let root = URL(fileURLWithPath: CommandLine.arguments[1]).standardizedFileURL.resolvingSymlinksInPath(), fm = FileManager.default
        guard !fm.fileExists(atPath: root.path), !root.path.contains("/Documents/") else { fatalError("Use a new private test directory") }
        let prefix = root.appendingPathComponent("wine")
        try fm.createDirectory(at: prefix, withIntermediateDirectories: true)
        try Data("synthetic runtime sentinel; no Wine launched".utf8).write(to: prefix.appendingPathComponent("system.reg"))
        let result = try await SteamClientInstaller.shared.run(prefix: prefix, cache: root.appendingPathComponent("cache"), sessionInactive: { true }, progress: { value in
            // File-free categorical progress, no account or request payloads.
            print(value.phase.rawValue, value.bytes, value.total)
        })
        guard result else { fatalError("Fresh container did not install") }
        let unchanged = try await SteamClientInstaller.shared.run(prefix: prefix, cache: root.appendingPathComponent("cache"), sessionInactive: { true }, progress: { _ in })
        guard !unchanged else { fatalError("Existing complete client was overwritten") }
        print("PASS production URLSession HTTPS download, full verification, transactional fresh install, existing-install no-op")
        if CommandLine.arguments.contains("--exercise-retry") {
            // Only this test's just-created scratch install; never user data.
            let catalog = try SteamClientCatalog.load(), client=prefix.appendingPathComponent("drive_c/Steam32BundleLab")
            let unchangedHash = try SteamClientIO.hash(client.appendingPathComponent("steam.exe"))
            try fm.removeItem(at:client.appendingPathComponent("steamclient.dll"))
            let package = catalog.packages[0]
            try Data("corrupt synthetic cache".utf8).write(to:root.appendingPathComponent("cache/" + package.sha256 + ".zip"))
            let cancellation = TestDownloadCancellation()
            let task = Task {
                try await SteamClientInstaller.shared.run(prefix:prefix,cache:root.appendingPathComponent("cache"),sessionInactive:{true},progress:{ value in
                    if value.phase == .downloading && value.bytes > 0 { cancellation.cancel() }
                })
            }
            cancellation.set(task)
            do { _ = try await task.value; fatalError("network cancellation did not stop install") }
            catch is CancellationError {}
            catch let error as URLError where error.code == .cancelled {}
            guard try SteamClientIO.hash(client.appendingPathComponent("steam.exe")) == unchangedHash else { fatalError("cancel touched existing client") }
            let repaired=try await SteamClientInstaller.shared.run(prefix:prefix,cache:root.appendingPathComponent("cache"),sessionInactive:{true},progress:{_ in})
            guard repaired, try SteamClientIO.verify(root:client,catalog:catalog) else { fatalError("cached retry/repair failed") }
            print("PASS real network cancellation, corrupt-cache rejection, verified cached retry and missing-file repair")
        }
    }
}
