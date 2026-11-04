// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
import Foundation
import CryptoKit
import zlib
#if canImport(Darwin)
import Darwin
#else
import Glibc
#endif

/// Full AMD64 client, adapted from the locally tested Build99 installer.
/// Complete client, separate from Dock's intentionally smaller component set.
/// Only public metadata is shipped; all proprietary files come from Valve HTTPS.
struct Steam64Catalog: Codable, Sendable {
    struct Package: Codable, Sendable { let name: String; let file: String; let bytes: Int64; let sha256: String }
    struct File: Codable, Sendable { let bytes: Int64; let sha256: String }
    let schema: Int
    let version: String
    let manifestSHA256: String
    let origin: String
    let expandedBytes: Int64
    let packages: [Package]
    let files: [String: File]
    static let metadataSHA256 = "918ecb6e339088a923920dec0d3998d122e93dd4adf7940fefec01159cdbcc8b"
    static let version = "1769025840"
    static let origin = "https://client-update.akamai.steamstatic.com/"
    static let requiredPE = ["Program Files/Steam/steam.exe", "Program Files/Steam/steamclient64.dll", "Program Files/Steam/bin/cef/cef.win64/steamwebhelper.exe", "Program Files/Steam/bin/cef/cef.win64/libcef.dll"]
    var downloadBytes: Int64 { packages.reduce(0) { $0 + $1.bytes } }
    static func load(from url: URL? = Bundle.main.url(forResource: "Steam64Packages", withExtension: "json")) throws -> Self {
        guard let url else { throw Steam64InstallError.metadata }
        let data = try Data(contentsOf: url)
        guard data.count < 2_000_000, Steam64IO.digest(data) == metadataSHA256 else { throw Steam64InstallError.metadata }
        let value = try JSONDecoder().decode(Self.self, from: data)
        try value.validate()
        return value
    }
    func validate() throws {
        let names: Set<String> = ["tenfoot_images_all", "steamui_websrc_all", "resources_misc_all", "resources_hidpi_all", "resources_all", "strings_en_all", "strings_all", "public_all", "bins_hardware_all", "steamui_websrc_sounds_all", "steamui_websrc_movies_all", "bins_codecs_win64", "bins_misc_win64", "bins_hardware_win64", "bins_win64", "steam_win64", "bins_cef_win64", "bins_webhelpers_win64"]
        guard schema == 1, version == Self.version, origin == Self.origin,
              manifestSHA256 == "2ed4528edafa147aceb219a924f68e9d91227d81edba15d861c2c8e63942ff36",
              Set(packages.map(\.name)) == names, packages.count == names.count,
              Set(packages.map(\.file)).count == packages.count,
              expandedBytes > 0, expandedBytes <= 3 * 1024 * 1024 * 1024,
              !files.isEmpty, files.count < 20000,
              files.values.reduce(Int64(0), { $0 + $1.bytes }) == expandedBytes,
              Self.requiredPE.allSatisfy({ files[$0] != nil }) else { throw Steam64InstallError.metadata }
        for p in packages {
            guard p.file.range(of: #"^[A-Za-z0-9_.-]+$"#, options: .regularExpression) != nil,
                  p.bytes > 0, p.bytes < 1024 * 1024 * 1024, Self.validHash(p.sha256) else { throw Steam64InstallError.metadata }
        }
        var folded = Set<String>()
        for (name, file) in files {
            guard Steam64IO.validPath(name), !Steam64IO.isPrivate(name), folded.insert(name.lowercased()).inserted,
                  file.bytes >= 0, file.bytes <= 512 * 1024 * 1024, Self.validHash(file.sha256) else { throw Steam64InstallError.metadata }
        }
    }
    static func validHash(_ value: String) -> Bool { value.range(of: #"^[0-9a-f]{64}$"#, options: .regularExpression) != nil }
}

enum Steam64InstallError: LocalizedError {
    case metadata, unsafePath, archive, integrity, architecture, activeSession, runtime, space(Int64), source(Int), transaction, rollback
    var errorDescription: String? {
        switch self {
        case .metadata: return "Steam package metadata is missing or invalid. Install a complete iDeck build."
        case .unsafePath: return "An unsafe path or symbolic link was rejected. Existing Steam data was kept."
        case .archive: return "The Steam archive is malformed or exceeds safe extraction limits. Retry the download."
        case .integrity: return "Steam files do not match the complete pinned client. Retry; manual import remains available."
        case .architecture: return "This client has incompatible executable architecture. The compatible client was not installed."
        case .activeSession: return "Close and fully reopen iDeck before installing Steam. A Wine or JIT session has already started."
        case .runtime: return "Prepare the local runtime before installing Steam."
        case .space(let bytes): return "Free at least \(ByteCountFormatter.string(fromByteCount: bytes, countStyle: .file)) of storage, then retry. Existing Steam files were not changed."
        case .source(let status): return "Valve's pinned Steam package is unavailable (HTTP \(status)). Retry later or use manual import. No alternate client was substituted."
        case .transaction: return "An interrupted Steam installation needs recovery. Tap Repair Steam Files before launching."
        case .rollback: return "Steam repair was interrupted and could not fully roll back. Backups were retained; free storage and retry Repair Steam Files. Do not delete the Wine folder."
        }
    }
}
struct Steam64Progress: Sendable {
    enum Phase: String, Sendable {
        case existing = "Checking existing Steam installation"
        case checking = "Checking Steam package availability", downloading = "Downloading Steam client"
        case browser = "Downloading CEF/browser components", verifying = "Verifying downloaded files"
        case installing = "Installing Steam", compatibility = "Checking compatibility", complete = "Installation complete"
    }
    let phase: Phase
    var bytes: Int64 = 0
    var total: Int64 = 0
    var fraction: Double? { total > 0 ? min(1, Double(bytes) / Double(total)) : nil }
}

enum Steam64IO {
    static let fm = FileManager.default
    static func digest(_ data: Data) -> String { SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined() }
    static func hash(_ url: URL) throws -> String {
        let h = try FileHandle(forReadingFrom: url); defer { try? h.close() }
        var sha = SHA256()
        while let block = try h.read(upToCount: 1024 * 1024), !block.isEmpty { try Task.checkCancellation(); sha.update(data: block) }
        return sha.finalize().map { String(format: "%02x", $0) }.joined()
    }
    static func validPath(_ name: String) -> Bool { SteamRuntimeFiles.validPath(name) }
    static func isPrivate(_ name: String) -> Bool {
        let privateNames: Set<String> = ["config", "userdata", "steamapps", "logs", "appcache", "htmlcache", "dumps", "steam.cfg", "loginusers.vdf", "config.vdf", "localconfig.vdf"]
        return name.split(separator: "/").contains { privateNames.contains($0.lowercased()) || $0.lowercased().hasPrefix("ssfn") || $0.hasPrefix(".") }
    }
    static func path(_ name: String, root: URL) throws -> URL { try SteamRuntimeFiles.destination(name, under: root) }
    static func regular(_ url: URL, bytes: Int64) throws -> Bool {
        guard url.standardizedFileURL == url.resolvingSymlinksInPath() else { throw Steam64InstallError.unsafePath }
        guard fm.fileExists(atPath: url.path) else { return false }
        let a = try fm.attributesOfItem(atPath: url.path)
        guard a[.type] as? FileAttributeType == .typeRegular else { throw Steam64InstallError.unsafePath }
        return (a[.size] as? NSNumber)?.int64Value == bytes
    }
    static func verify(root: URL, catalog: Steam64Catalog) throws -> Bool {
        for (name, file) in catalog.files.sorted(by: { $0.key < $1.key }) {
            try Task.checkCancellation()
            let url = try path(name, root: root)
            guard try regular(url, bytes: file.bytes), try hash(url) == file.sha256 else { return false }
        }
        for name in Steam64Catalog.requiredPE {
            guard SteamUIExperiment.isX64PE(try path(name, root: root)) else { throw Steam64InstallError.architecture }
        }
        return true
    }
    static func copyPublic(source: URL, stage: URL, catalog: Steam64Catalog) throws {
        // Deliberately no recursive copy: unknown/auth/game/save files are excluded.
        for name in catalog.files.keys {
            try Task.checkCancellation()
            guard !isPrivate(name) else { throw Steam64InstallError.unsafePath }
            try replace(from: try path(name, root: source), to: try path(name, root: stage))
        }
    }
    static func available(_ url: URL) throws -> Int64 {
        #if os(iOS)
        if let value = try url.resourceValues(forKeys: [.volumeAvailableCapacityForImportantUsageKey]).volumeAvailableCapacityForImportantUsage { return value }
        #endif
        return (try fm.attributesOfFileSystem(forPath: url.path)[.systemFreeSize] as? NSNumber)?.int64Value ?? 0
    }
    static func requireSpace(_ bytes: Int64, at url: URL, available: Int64? = nil) throws {
        guard try available ?? Self.available(url) >= bytes else { throw Steam64InstallError.space(bytes) }
    }
    /// Same-volume streamed copy + POSIX atomic rename; never Data(contentsOf: largePE).
    static func replace(from source: URL, to target: URL) throws {
        let temp = target.deletingLastPathComponent().appendingPathComponent(".ideck-write-" + UUID().uuidString)
        try fm.createDirectory(at: target.deletingLastPathComponent(), withIntermediateDirectories: true)
        defer { try? fm.removeItem(at: temp) }
        try fm.copyItem(at: source, to: temp)
        guard rename(temp.path, target.path) == 0 else { throw POSIXError(POSIXErrorCode(rawValue: errno) ?? .EIO) }
    }
}

/// Bounded, file-backed ZIP reader. Never allocates the archive or a large PE in RAM.
/// Central/local contracts, CRC, path and per-file catalog hashes all must agree.
enum Steam64ZIP {
    static func extract(_ archive: URL, into root: URL, catalog: Steam64Catalog) throws {
        let h = try FileHandle(forReadingFrom: archive); defer { try? h.close() }
        let length = try h.seekToEnd()
        guard length >= 22, length < 1024 * 1024 * 1024 else { throw Steam64InstallError.archive }
        func read(_ offset: UInt64, _ count: Int) throws -> Data {
            guard offset <= length, count >= 0, UInt64(count) <= length - offset else { throw Steam64InstallError.archive }
            try h.seek(toOffset: offset)
            guard let d = try h.read(upToCount: count), d.count == count else { throw Steam64InstallError.archive }; return d
        }
        func u16(_ d: Data, _ p: Int) -> Int { Int(d[p]) | Int(d[p+1]) << 8 }
        func u32(_ d: Data, _ p: Int) -> Int { u16(d,p) | u16(d,p+2) << 16 }
        let tailOffset = length - min(length, 65557), tail = try read(tailOffset, Int(length - tailOffset))
        guard let end = stride(from: tail.count - 22, through: 0, by: -1).first(where: { u32(tail,$0) == 0x06054b50 && $0+22+u16(tail,$0+20) == tail.count }) else { throw Steam64InstallError.archive }
        let entries = u16(tail,end+10), centralSize = u32(tail,end+12), central = u32(tail,end+16)
        guard u16(tail,end+4) == 0, u16(tail,end+6) == 0, u16(tail,end+8) == entries,
              entries < 20000, centralSize <= 8 * 1024 * 1024, UInt64(central + centralSize) == tailOffset + UInt64(end) else { throw Steam64InstallError.archive }
        let table = try read(UInt64(central), centralSize)
        var cursor = 0, total: Int64 = 0, seen = Set<String>()
        for _ in 0..<entries {
            try Task.checkCancellation()
            guard cursor + 46 <= table.count, u32(table,cursor) == 0x02014b50 else { throw Steam64InstallError.archive }
            let flags = u16(table,cursor+8), method = u16(table,cursor+10), crc = UInt32(u32(table,cursor+16))
            let compressed = u32(table,cursor+20), size = u32(table,cursor+24), n = u16(table,cursor+28)
            let next = cursor + 46 + n + u16(table,cursor+30) + u16(table,cursor+32)
            let kind = (u32(table,cursor+38) >> 16) & 0xf000, local = u32(table,cursor+42)
            guard next <= table.count, flags & ~0x808 == 0, method == 0 || method == 8,
                  kind == 0 || kind == 0x8000 || kind == 0x4000,
                  let raw = String(data: table.subdata(in: cursor+46..<cursor+46+n), encoding: .utf8) else { throw Steam64InstallError.archive }
            let normalized = raw.replacingOccurrences(of: "\\", with: "/"), directory = normalized.hasSuffix("/")
            let name = "Program Files/Steam/" + (directory ? String(normalized.dropLast()) : normalized)
            guard Steam64IO.validPath(name), !Steam64IO.isPrivate(name), seen.insert(name.lowercased()).inserted,
                  size <= 512 * 1024 * 1024 else { throw Steam64InstallError.unsafePath }
            let header = try read(UInt64(local), 30)
            guard u32(header,0) == 0x04034b50, u16(header,6) == flags, u16(header,8) == method, u16(header,26) == n else { throw Steam64InstallError.archive }
            let body = local + 30 + n + u16(header,28)
            guard body <= central, compressed <= central - body, try read(UInt64(local+30), n) == Data(raw.utf8) else { throw Steam64InstallError.archive }
            if flags & 8 == 0 {
                guard u32(header,14) == Int(crc), u32(header,18) == compressed, u32(header,22) == size else { throw Steam64InstallError.archive }
            }
            cursor = next
            if directory { guard size == 0, compressed == 0 else { throw Steam64InstallError.archive }; continue }
            guard let expected = catalog.files[name], expected.bytes == size else { throw Steam64InstallError.integrity }
            total += Int64(size); guard total <= catalog.expandedBytes else { throw Steam64InstallError.archive }
            let dest = try Steam64IO.path(name, root: root)
            if FileManager.default.fileExists(atPath: dest.path) {
                guard try Steam64IO.regular(dest, bytes: expected.bytes), try Steam64IO.hash(dest) == expected.sha256 else { throw Steam64InstallError.integrity }
                continue // identical duplicates across Valve packages only
            }
            try FileManager.default.createDirectory(at: dest.deletingLastPathComponent(), withIntermediateDirectories: true)
            guard FileManager.default.createFile(atPath: dest.path, contents: nil) else { throw Steam64InstallError.archive }
            let out = try FileHandle(forWritingTo: dest)
            var success = false
            defer { try? out.close(); if !success { try? FileManager.default.removeItem(at: dest) } }
            var stream = z_stream(), sha = SHA256(), actualCRC: uLong = 0, outputCount = 0, remaining = compressed
            var output = [UInt8](repeating: 0, count: 65536)
            if method == 8 { guard inflateInit2_(&stream, -15, ZLIB_VERSION, Int32(MemoryLayout<z_stream>.size)) == Z_OK else { throw Steam64InstallError.archive } }
            defer { if method == 8 { inflateEnd(&stream) } }
            var position = UInt64(body), ended = method == 0
            repeat {
                try Task.checkCancellation()
                let count = min(65536, remaining), input = try read(position, count)
                position += UInt64(count); remaining -= count
                if method == 0 {
                    try out.write(contentsOf: input); sha.update(data: input)
                    actualCRC = input.withUnsafeBytes { crc32(actualCRC, $0.bindMemory(to: UInt8.self).baseAddress, UInt32(count)) }
                    outputCount += count
                } else {
                    try input.withUnsafeBytes { bytes in
                        stream.next_in = UnsafeMutablePointer(mutating: bytes.bindMemory(to: UInt8.self).baseAddress); stream.avail_in = UInt32(count)
                        repeat {
                            let status = output.withUnsafeMutableBufferPointer { buffer -> Int32 in
                                stream.next_out = buffer.baseAddress; stream.avail_out = UInt32(buffer.count)
                                return inflate(&stream, Z_NO_FLUSH)
                            }
                            let produced = output.count - Int(stream.avail_out)
                            if status == Z_BUF_ERROR && produced == 0 && stream.avail_in == 0 && remaining > 0 { break }
                            guard outputCount + produced <= size, status == Z_OK || status == Z_STREAM_END else { throw Steam64InstallError.archive }
                            let data = Data(output.prefix(produced)); try out.write(contentsOf: data); sha.update(data: data)
                            actualCRC = data.withUnsafeBytes { crc32(actualCRC, $0.bindMemory(to: UInt8.self).baseAddress, UInt32(produced)) }
                            outputCount += produced
                            if status == Z_STREAM_END { ended = true; break }
                            guard produced > 0 || stream.avail_in == 0 else { throw Steam64InstallError.archive }
                        } while stream.avail_in > 0 || stream.avail_out == 0
                    }
                }
                if ended && method == 8 { guard remaining == 0, stream.avail_in == 0 else { throw Steam64InstallError.archive }; break }
            } while remaining > 0
            let hash = sha.finalize().map { String(format: "%02x", $0) }.joined()
            guard ended, outputCount == size, UInt32(actualCRC) == crc, hash == expected.sha256 else { throw Steam64InstallError.integrity }
            try out.synchronize(); success = true
        }
        guard cursor == table.count else { throw Steam64InstallError.archive }
    }
}

/// Persistent per-file rollback plan. Journal is durable BEFORE the first write.
/// Account/game/save paths are never enumerated, replaced, moved or deleted.
enum Steam64Transaction {
    struct Entry: Codable { let name: String; let existed: Bool }
    struct Journal: Codable { let entries: [Entry]; let quarantine: [String] }
    static let journalName = "steam64-client-transaction.json"
    static let publicFolders: Set<String> = ["Program Files", "iDeckCEF64Crashpad"]
    static func journal(prefix: URL) -> URL { prefix.appendingPathComponent(journalName) }
    static func recover(prefix: URL, catalog: Steam64Catalog) throws {
        let fm = FileManager.default, record = journal(prefix: prefix)
        guard fm.fileExists(atPath: record.path) else { return }
        // Backup location is fixed, never accepted from editable journal payload.
        let transaction = prefix.appendingPathComponent("client-rollbacks/steam64-pending")
        guard record == record.resolvingSymlinksInPath(), transaction == transaction.resolvingSymlinksInPath() else { throw Steam64InstallError.unsafePath }
        let data = try Data(contentsOf: record, options: .mappedIfSafe)
        guard data.count < 4_000_000 else { throw Steam64InstallError.transaction }
        let plan = try JSONDecoder().decode(Journal.self, from: data)
        guard plan.entries.count == catalog.files.count, Set(plan.entries.map(\.name)) == Set(catalog.files.keys),
              Set(plan.quarantine).count == plan.quarantine.count else { throw Steam64InstallError.transaction }
        let target = prefix.appendingPathComponent("drive_c")
        // Cancellation must NOT interrupt recovery after mutation.
        for entry in plan.entries.reversed() {
            guard !Steam64IO.isPrivate(entry.name), entry.name.split(separator: "/").count == 1 || publicFolders.contains(String(entry.name.split(separator: "/").first ?? "")) else { throw Steam64InstallError.unsafePath }
            let dest = try Steam64IO.path(entry.name, root: target), saved = try Steam64IO.path(entry.name, root: transaction)
            if entry.existed {
                guard fm.fileExists(atPath: saved.path) else { throw Steam64InstallError.rollback }
                try Steam64IO.replace(from: saved, to: dest)
            } else if fm.fileExists(atPath: dest.path) { try fm.removeItem(at: dest) }
        }
        for name in plan.quarantine {
            guard ["Program Files/Steam/bin/cef/cef.win7", "Program Files/Steam/bin/cef/cef.win7x64", "Program Files/Steam/bin/cef/cef.win7.x64"].contains(name) else { throw Steam64InstallError.unsafePath }
            let saved = try Steam64IO.path("quarantine/" + name, root: transaction), dest = try Steam64IO.path(name, root: target)
            if fm.fileExists(atPath: saved.path) { try fm.moveItem(at: saved, to: dest) }
        }
        try fm.removeItem(at: record)
        let retained = transaction.deletingLastPathComponent().appendingPathComponent(UUID().uuidString)
        try fm.moveItem(at: transaction, to: retained)
    }
    static func install(source: URL, prefix: URL, catalog: Steam64Catalog, faultAfter: Int? = nil) throws {
        let fm = FileManager.default
        try recover(prefix: prefix, catalog: catalog)
        guard try Steam64IO.verify(root: source, catalog: catalog) else { throw Steam64InstallError.integrity }
        let target = prefix.appendingPathComponent("drive_c")
        let backup = try Steam64IO.path("client-rollbacks/steam64-pending", root: prefix)
        if fm.fileExists(atPath: backup.path) { // abandoned pre-journal public copies, keep as rollback evidence
            try fm.moveItem(at: backup, to: backup.deletingLastPathComponent().appendingPathComponent(UUID().uuidString))
        }
        try fm.createDirectory(at: backup, withIntermediateDirectories: true)
        var entries: [Entry] = []
        for name in catalog.files.keys.sorted() {
            let dest = try Steam64IO.path(name, root: target)
            let existed = fm.fileExists(atPath: dest.path)
            if existed {
                let a = try fm.attributesOfItem(atPath: dest.path)
                guard a[.type] as? FileAttributeType == .typeRegular else { throw Steam64InstallError.unsafePath }
                let saved = try Steam64IO.path(name, root: backup)
                try fm.createDirectory(at: saved.deletingLastPathComponent(), withIntermediateDirectories: true)
                try fm.copyItem(at: dest, to: saved)
            }
            entries.append(Entry(name: name, existed: existed))
        }
        let quarantine = ["Program Files/Steam/bin/cef/cef.win7", "Program Files/Steam/bin/cef/cef.win7x64", "Program Files/Steam/bin/cef/cef.win7.x64"].filter {
            fm.fileExists(atPath: target.appendingPathComponent($0).path)
        }
        for name in quarantine { _ = try Steam64IO.path(name, root: target) }
        let plan = Journal(entries: entries, quarantine: quarantine)
        let record = journal(prefix: prefix)
        try JSONEncoder().encode(plan).write(to: record, options: .atomic)
        let handle = try FileHandle(forWritingTo: record); try handle.synchronize(); try handle.close()
        do {
            for (index, entry) in entries.enumerated() {
                try Task.checkCancellation()
                if faultAfter == index { throw Steam64InstallError.transaction }
                try Steam64IO.replace(from: try Steam64IO.path(entry.name, root: source), to: try Steam64IO.path(entry.name, root: target))
            }
            for name in quarantine {
                let saved = try Steam64IO.path("quarantine/" + name, root: backup)
                try fm.createDirectory(at: saved.deletingLastPathComponent(), withIntermediateDirectories: true)
                try fm.moveItem(at: try Steam64IO.path(name, root: target), to: saved)
            }
            guard try Steam64IO.verify(root: target, catalog: catalog) else { throw Steam64InstallError.integrity }
            try Task.checkCancellation()
            try fm.removeItem(at: record) // commit point; no more cancellation/fallible writes to installed files
        } catch {
            do { try recover(prefix: prefix, catalog: catalog) } catch { throw Steam64InstallError.rollback }
            throw error
        }
        // Retain backup; a failed rename does not invalidate a completed install.
        try? fm.moveItem(at: backup, to: backup.deletingLastPathComponent().appendingPathComponent(UUID().uuidString))
    }
}

final class Steam64DownloadDelegate: NSObject, URLSessionDownloadDelegate, @unchecked Sendable {
    let limit: Int64
    let progress: @Sendable (Int64) -> Void
    private let progressLock = NSLock()
    private var lastReport: TimeInterval = 0
    init(limit: Int64, progress: @escaping @Sendable (Int64) -> Void) { self.limit = limit; self.progress = progress }
    static func authorized(_ url: URL?) -> Bool {
        guard let url else { return false }
        return url.scheme == "https" && url.host == "client-update.akamai.steamstatic.com" && (url.port == nil || url.port == 443) && url.user == nil && url.password == nil
    }
    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) {
        completionHandler(Self.authorized(request.url) && request.url?.path == task.originalRequest?.url?.path ? request : nil)
    }
    func urlSession(_ session: URLSession, downloadTask: URLSessionDownloadTask, didFinishDownloadingTo location: URL) { }
    func urlSession(_ session: URLSession, downloadTask: URLSessionDownloadTask, didWriteData bytesWritten: Int64, totalBytesWritten: Int64, totalBytesExpectedToWrite: Int64) {
        if totalBytesWritten > limit { downloadTask.cancel(); return }
        let now = ProcessInfo.processInfo.systemUptime
        progressLock.lock()
        let emit = now - lastReport >= 0.1 || totalBytesWritten == limit
        if emit { lastReport = now }
        progressLock.unlock()
        if emit { progress(totalBytesWritten) }
    }
}

actor Steam64Installer {
    static let shared = Steam64Installer()
    private var busy = false
    func verifyInstalled(prefix: URL) throws -> Bool {
        guard !busy else { return false }
        let prefix = prefix.deletingLastPathComponent().resolvingSymlinksInPath().appendingPathComponent(prefix.lastPathComponent)
        guard !FileManager.default.fileExists(atPath: Steam64Transaction.journal(prefix: prefix).path) else { return false }
        let catalog = try Steam64Components.composed(try Steam64Catalog.load())
        let primary = prefix.appendingPathComponent("drive_c")
        let client = primary
        return try Steam64IO.verify(root: client, catalog: catalog)
    }
    /// Caller's MainActor holds the launcher preparation lock for the entire operation.
    func run(prefix inputPrefix: URL, cache inputCache: URL, source: URL? = nil,
             sessionInactive: @Sendable () async -> Bool,
             progress: @escaping @Sendable (Steam64Progress) async -> Void) async throws -> Bool {
        // Resolve OS aliases in the trusted parent, but reject a symlink at wine/cache itself.
        let prefix = inputPrefix.deletingLastPathComponent().resolvingSymlinksInPath().appendingPathComponent(inputPrefix.lastPathComponent)
        let cache = inputCache.deletingLastPathComponent().resolvingSymlinksInPath().appendingPathComponent(inputCache.lastPathComponent)
        guard inputPrefix.lastPathComponent == "wine-steam64", !busy else { throw Steam64InstallError.activeSession }
        busy = true; defer { busy = false }
        guard await sessionInactive() else { throw Steam64InstallError.activeSession }
        guard FileManager.default.fileExists(atPath: prefix.appendingPathComponent("system.reg").path) else { throw Steam64InstallError.runtime }
        let catalog = try Steam64Catalog.load(), fm = FileManager.default
        let installedCatalog = try Steam64Components.composed(catalog)
        try Steam64Components.validateBundle()
        guard prefix == prefix.resolvingSymlinksInPath(), cache == cache.resolvingSymlinksInPath() else { throw Steam64InstallError.unsafePath }
        let recovered = fm.fileExists(atPath: Steam64Transaction.journal(prefix: prefix).path)
        try Steam64Transaction.recover(prefix: prefix, catalog: installedCatalog)
        let target = prefix.appendingPathComponent("drive_c")
        await progress(.init(phase: .existing))
        let existing = target
        if try Steam64IO.verify(root: existing, catalog: installedCatalog) { await progress(.init(phase: .complete)); return recovered }
        var backupBytes: Int64 = 0
        for name in catalog.files.keys {
            let file = try Steam64IO.path(name, root: target)
            if fm.fileExists(atPath: file.path) {
                let size = (try fm.attributesOfItem(atPath: file.path)[.size] as? NSNumber)?.int64Value ?? 0
                guard size >= 0, size < 4 * 1024 * 1024 * 1024 else { throw Steam64InstallError.integrity }
                backupBytes += size
            }
        }
        let required = catalog.downloadBytes + 2 * catalog.expandedBytes + backupBytes + 256 * 1024 * 1024
        try Steam64IO.requireSpace(required, at: prefix)
        try fm.createDirectory(at: cache, withIntermediateDirectories: true)
        let stage = cache.appendingPathComponent("stage-" + UUID().uuidString)
        defer { try? fm.removeItem(at: stage) }
        if let source {
            guard try Steam64IO.verify(root: source, catalog: catalog) else { throw Steam64InstallError.integrity }
        } else {
            let configuration = URLSessionConfiguration.ephemeral
            configuration.httpCookieStorage = nil; configuration.urlCredentialStorage = nil
            configuration.timeoutIntervalForRequest = 60; configuration.timeoutIntervalForResource = 1800
            let session = URLSession(configuration: configuration)
            defer { session.invalidateAndCancel() }
            await progress(.init(phase: .checking))
            // Fail before downloading large archives if any required fixed package disappeared.
            for p in catalog.packages {
                try Task.checkCancellation()
                let cached = try Steam64IO.path(p.sha256 + ".zip", root: cache)
                if try Steam64IO.regular(cached, bytes: p.bytes) && Steam64IO.hash(cached) == p.sha256 { continue }
                var request = URLRequest(url: URL(string: catalog.origin + p.file)!); request.httpMethod = "HEAD"
                let delegate = Steam64DownloadDelegate(limit: p.bytes, progress: { _ in })
                let (_, response) = try await session.data(for: request, delegate: delegate)
                guard let http = response as? HTTPURLResponse, http.statusCode == 200, Steam64DownloadDelegate.authorized(http.url) else { throw Steam64InstallError.source((response as? HTTPURLResponse)?.statusCode ?? 0) }
                if let length = http.value(forHTTPHeaderField: "Content-Length"), Int64(length) != p.bytes { throw Steam64InstallError.integrity }
            }
            var completed: Int64 = 0
            for p in catalog.packages {
                try Task.checkCancellation()
                let archive = try Steam64IO.path(p.sha256 + ".zip", root: cache)
                let phase: Steam64Progress.Phase = p.name.contains("cef") || p.name.contains("webhelpers") ? .browser : .downloading
                if !(try Steam64IO.regular(archive, bytes: p.bytes) && Steam64IO.hash(archive) == p.sha256) {
                    if fm.fileExists(atPath: archive.path) { try fm.removeItem(at: archive) }
                    let prior = completed, total = catalog.downloadBytes
                    let delegate = Steam64DownloadDelegate(limit: p.bytes) { bytes in
                        Task { await progress(.init(phase: phase, bytes: prior + bytes, total: total)) }
                    }
                    let (temporary, response) = try await session.download(from: URL(string: catalog.origin + p.file)!, delegate: delegate)
                    defer { try? fm.removeItem(at: temporary) }
                    guard let http = response as? HTTPURLResponse, http.statusCode == 200, Steam64DownloadDelegate.authorized(http.url) else { throw Steam64InstallError.source((response as? HTTPURLResponse)?.statusCode ?? 0) }
                    guard try Steam64IO.regular(temporary, bytes: p.bytes) else { throw Steam64InstallError.integrity }
                    await progress(.init(phase: .verifying, bytes: completed + p.bytes, total: catalog.downloadBytes))
                    guard try Steam64IO.hash(temporary) == p.sha256 else { throw Steam64InstallError.integrity }
                    try fm.moveItem(at: temporary, to: archive)
                }
                completed += p.bytes
                await progress(.init(phase: phase, bytes: completed, total: catalog.downloadBytes))
                try Steam64ZIP.extract(archive, into: stage, catalog: catalog)
            }
        }
        // A local source is a read-only fixture/import; never overlay into it.
        if let source {
            try Steam64IO.copyPublic(source: source, stage: stage, catalog: catalog)
        }
        try Steam64Components.stage(into: stage)
        guard await sessionInactive() else { throw Steam64InstallError.activeSession }
        await progress(.init(phase: .installing))
        try Steam64Transaction.install(source: stage, prefix: prefix, catalog: installedCatalog)
        await progress(.init(phase: .compatibility))
        guard !fm.fileExists(atPath: Steam64Transaction.journal(prefix: prefix).path), try Steam64IO.verify(root: target, catalog: installedCatalog) else { throw Steam64InstallError.integrity }
        await progress(.init(phase: .complete))
        return true
    }
}
