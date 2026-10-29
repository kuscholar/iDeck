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

/// Complete client, separate from Dock's intentionally smaller component set.
/// Only public metadata is shipped; all proprietary files come from Valve HTTPS.
struct SteamClientCatalog: Codable, Sendable {
    struct Package: Codable, Sendable { let name: String; let file: String; let bytes: Int64; let sha256: String }
    struct File: Codable, Sendable { let bytes: Int64; let sha256: String }
    let schema: Int
    let version: String
    let manifestSHA256: String
    let origin: String
    let expandedBytes: Int64
    let packages: [Package]
    let files: [String: File]
    static let metadataSHA256 = "d44d58a17bd35d3b1a03b1adfd9a05d537251a4b986f02af43763d6c62ab934b"
    static let version = "1769731672"
    static let origin = "https://client-update.akamai.steamstatic.com/"
    static let requiredPE = ["steam.exe", "steamclient.dll", "bin/cef/cef.win7/steamwebhelper.exe", "bin/cef/cef.win7/libcef.dll"]
    var downloadBytes: Int64 { packages.reduce(0) { $0 + $1.bytes } }
    static func load(from url: URL? = Bundle.main.url(forResource: "SteamClientPackages", withExtension: "json")) throws -> Self {
        guard let url else { throw SteamClientError.metadata }
        let data = try Data(contentsOf: url)
        guard data.count < 2_000_000, SteamClientIO.digest(data) == metadataSHA256 else { throw SteamClientError.metadata }
        let value = try JSONDecoder().decode(Self.self, from: data)
        try value.validate()
        return value
    }
    func validate() throws {
        let names: Set<String> = ["tenfoot_images_all", "steamui_websrc_all", "resources_misc_all", "resources_hidpi_all", "resources_all", "strings_en_all", "strings_all", "public_all", "bins_hardware_all", "steamui_websrc_sounds_all", "steamui_websrc_movies_all", "bins_codecs_win32", "bins_misc_win32", "bins_hardware_win32", "bins_win32", "steam_win32", "bins_win64_win32", "bins_cef_win32", "bins_webhelpers_win32"]
        guard schema == 1, version == Self.version, origin == Self.origin,
              manifestSHA256 == "4b8aa78d95dd7a1475c7849c3e783b136452d34be67342b53728799d697c4823",
              Set(packages.map(\.name)) == names, packages.count == names.count,
              Set(packages.map(\.file)).count == packages.count,
              expandedBytes > 0, expandedBytes <= 3 * 1024 * 1024 * 1024,
              !files.isEmpty, files.count < 20000,
              files.values.reduce(Int64(0), { $0 + $1.bytes }) == expandedBytes,
              Self.requiredPE.allSatisfy({ files[$0] != nil }) else { throw SteamClientError.metadata }
        for p in packages {
            guard p.file.range(of: #"^[A-Za-z0-9_.-]+$"#, options: .regularExpression) != nil,
                  p.bytes > 0, p.bytes < 1024 * 1024 * 1024, Self.validHash(p.sha256) else { throw SteamClientError.metadata }
        }
        var folded = Set<String>()
        for (name, file) in files {
            guard SteamClientIO.validPath(name), !SteamClientIO.isPrivate(name), folded.insert(name.lowercased()).inserted,
                  file.bytes >= 0, file.bytes <= 512 * 1024 * 1024, Self.validHash(file.sha256) else { throw SteamClientError.metadata }
        }
    }
    static func validHash(_ value: String) -> Bool { value.range(of: #"^[0-9a-f]{64}$"#, options: .regularExpression) != nil }
}

enum SteamClientError: LocalizedError {
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
struct SteamClientProgress: Sendable {
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

enum SteamClientIO {
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
        guard url.standardizedFileURL == url.resolvingSymlinksInPath() else { throw SteamClientError.unsafePath }
        guard fm.fileExists(atPath: url.path) else { return false }
        let a = try fm.attributesOfItem(atPath: url.path)
        guard a[.type] as? FileAttributeType == .typeRegular else { throw SteamClientError.unsafePath }
        return (a[.size] as? NSNumber)?.int64Value == bytes
    }
    static func verify(root: URL, catalog: SteamClientCatalog) throws -> Bool {
        for (name, file) in catalog.files.sorted(by: { $0.key < $1.key }) {
            try Task.checkCancellation()
            let url = try path(name, root: root)
            guard try regular(url, bytes: file.bytes), try hash(url) == file.sha256 else { return false }
        }
        for name in SteamClientCatalog.requiredPE {
            guard SteamUIExperiment.isX86PE(try path(name, root: root)) else { throw SteamClientError.architecture }
        }
        return true
    }
    static func available(_ url: URL) throws -> Int64 {
        #if os(iOS)
        if let value = try url.resourceValues(forKeys: [.volumeAvailableCapacityForImportantUsageKey]).volumeAvailableCapacityForImportantUsage { return value }
        #endif
        return (try fm.attributesOfFileSystem(forPath: url.path)[.systemFreeSize] as? NSNumber)?.int64Value ?? 0
    }
    static func requireSpace(_ bytes: Int64, at url: URL, available: Int64? = nil) throws {
        guard try available ?? Self.available(url) >= bytes else { throw SteamClientError.space(bytes) }
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
enum SteamClientZIP {
    static func extract(_ archive: URL, into root: URL, catalog: SteamClientCatalog) throws {
        let h = try FileHandle(forReadingFrom: archive); defer { try? h.close() }
        let length = try h.seekToEnd()
        guard length >= 22, length < 1024 * 1024 * 1024 else { throw SteamClientError.archive }
        func read(_ offset: UInt64, _ count: Int) throws -> Data {
            guard offset <= length, count >= 0, UInt64(count) <= length - offset else { throw SteamClientError.archive }
            try h.seek(toOffset: offset)
            guard let d = try h.read(upToCount: count), d.count == count else { throw SteamClientError.archive }; return d
        }
        func u16(_ d: Data, _ p: Int) -> Int { Int(d[p]) | Int(d[p+1]) << 8 }
        func u32(_ d: Data, _ p: Int) -> Int { u16(d,p) | u16(d,p+2) << 16 }
        let tailOffset = length - min(length, 65557), tail = try read(tailOffset, Int(length - tailOffset))
        guard let end = stride(from: tail.count - 22, through: 0, by: -1).first(where: { u32(tail,$0) == 0x06054b50 && $0+22+u16(tail,$0+20) == tail.count }) else { throw SteamClientError.archive }
        let entries = u16(tail,end+10), centralSize = u32(tail,end+12), central = u32(tail,end+16)
        guard u16(tail,end+4) == 0, u16(tail,end+6) == 0, u16(tail,end+8) == entries,
              entries < 20000, centralSize <= 8 * 1024 * 1024, UInt64(central + centralSize) == tailOffset + UInt64(end) else { throw SteamClientError.archive }
        let table = try read(UInt64(central), centralSize)
        var cursor = 0, total: Int64 = 0, seen = Set<String>()
        for _ in 0..<entries {
            try Task.checkCancellation()
            guard cursor + 46 <= table.count, u32(table,cursor) == 0x02014b50 else { throw SteamClientError.archive }
            let flags = u16(table,cursor+8), method = u16(table,cursor+10), crc = UInt32(u32(table,cursor+16))
            let compressed = u32(table,cursor+20), size = u32(table,cursor+24), n = u16(table,cursor+28)
            let next = cursor + 46 + n + u16(table,cursor+30) + u16(table,cursor+32)
            let kind = (u32(table,cursor+38) >> 16) & 0xf000, local = u32(table,cursor+42)
            guard next <= table.count, flags & ~0x808 == 0, method == 0 || method == 8,
                  kind == 0 || kind == 0x8000 || kind == 0x4000,
                  let raw = String(data: table.subdata(in: cursor+46..<cursor+46+n), encoding: .utf8) else { throw SteamClientError.archive }
            let normalized = raw.replacingOccurrences(of: "\\", with: "/"), directory = normalized.hasSuffix("/")
            let name = directory ? String(normalized.dropLast()) : normalized
            guard SteamClientIO.validPath(name), !SteamClientIO.isPrivate(name), seen.insert(name.lowercased()).inserted,
                  size <= 512 * 1024 * 1024 else { throw SteamClientError.unsafePath }
            let header = try read(UInt64(local), 30)
            guard u32(header,0) == 0x04034b50, u16(header,6) == flags, u16(header,8) == method, u16(header,26) == n else { throw SteamClientError.archive }
            let body = local + 30 + n + u16(header,28)
            guard body <= central, compressed <= central - body, try read(UInt64(local+30), n) == Data(raw.utf8) else { throw SteamClientError.archive }
            if flags & 8 == 0 {
                guard u32(header,14) == Int(crc), u32(header,18) == compressed, u32(header,22) == size else { throw SteamClientError.archive }
            }
            cursor = next
            if directory { guard size == 0, compressed == 0 else { throw SteamClientError.archive }; continue }
            guard let expected = catalog.files[name], expected.bytes == size else { throw SteamClientError.integrity }
            total += Int64(size); guard total <= catalog.expandedBytes else { throw SteamClientError.archive }
            let dest = try SteamClientIO.path(name, root: root)
            if FileManager.default.fileExists(atPath: dest.path) {
                guard try SteamClientIO.regular(dest, bytes: expected.bytes), try SteamClientIO.hash(dest) == expected.sha256 else { throw SteamClientError.integrity }
                continue // identical duplicates across Valve packages only
            }
            try FileManager.default.createDirectory(at: dest.deletingLastPathComponent(), withIntermediateDirectories: true)
            guard FileManager.default.createFile(atPath: dest.path, contents: nil) else { throw SteamClientError.archive }
            let out = try FileHandle(forWritingTo: dest)
            var success = false
            defer { try? out.close(); if !success { try? FileManager.default.removeItem(at: dest) } }
            var stream = z_stream(), sha = SHA256(), actualCRC: uLong = 0, outputCount = 0, remaining = compressed
            var output = [UInt8](repeating: 0, count: 65536)
            if method == 8 { guard inflateInit2_(&stream, -15, ZLIB_VERSION, Int32(MemoryLayout<z_stream>.size)) == Z_OK else { throw SteamClientError.archive } }
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
                            guard outputCount + produced <= size, status == Z_OK || status == Z_STREAM_END else { throw SteamClientError.archive }
                            let data = Data(output.prefix(produced)); try out.write(contentsOf: data); sha.update(data: data)
                            actualCRC = data.withUnsafeBytes { crc32(actualCRC, $0.bindMemory(to: UInt8.self).baseAddress, UInt32(produced)) }
                            outputCount += produced
                            if status == Z_STREAM_END { ended = true; break }
                            guard produced > 0 || stream.avail_in == 0 else { throw SteamClientError.archive }
                        } while stream.avail_in > 0 || stream.avail_out == 0
                    }
                }
                if ended && method == 8 { guard remaining == 0, stream.avail_in == 0 else { throw SteamClientError.archive }; break }
            } while remaining > 0
            let hash = sha.finalize().map { String(format: "%02x", $0) }.joined()
            guard ended, outputCount == size, UInt32(actualCRC) == crc, hash == expected.sha256 else { throw SteamClientError.integrity }
            try out.synchronize(); success = true
        }
        guard cursor == table.count else { throw SteamClientError.archive }
    }
}

/// Persistent per-file rollback plan. Journal is durable BEFORE the first write.
/// Account/game/save paths are never enumerated, replaced, moved or deleted.
enum SteamClientTransaction {
    struct Entry: Codable { let name: String; let existed: Bool }
    struct Journal: Codable { let entries: [Entry]; let quarantine: [String] }
    static let journalName = "steam-client-transaction.json"
    static let publicFolders: Set<String> = ["bin", "clientui", "controller_base", "friends", "graphics", "public", "resource", "steam", "steamui", "tenfoot", "win64"]
    static func journal(prefix: URL) -> URL { prefix.appendingPathComponent(journalName) }
    static func recover(prefix: URL, catalog: SteamClientCatalog) throws {
        let fm = FileManager.default, record = journal(prefix: prefix)
        guard fm.fileExists(atPath: record.path) else { return }
        // Backup location is fixed, never accepted from editable journal payload.
        let transaction = prefix.appendingPathComponent("client-rollbacks/automatic-pending")
        guard record == record.resolvingSymlinksInPath(), transaction == transaction.resolvingSymlinksInPath() else { throw SteamClientError.unsafePath }
        let data = try Data(contentsOf: record, options: .mappedIfSafe)
        guard data.count < 4_000_000 else { throw SteamClientError.transaction }
        let plan = try JSONDecoder().decode(Journal.self, from: data)
        guard plan.entries.count == catalog.files.count, Set(plan.entries.map(\.name)) == Set(catalog.files.keys),
              Set(plan.quarantine).count == plan.quarantine.count else { throw SteamClientError.transaction }
        let target = prefix.appendingPathComponent("drive_c/Steam32BundleLab")
        // Cancellation must NOT interrupt recovery after mutation.
        for entry in plan.entries.reversed() {
            guard !SteamClientIO.isPrivate(entry.name), entry.name.split(separator: "/").count == 1 || publicFolders.contains(String(entry.name.split(separator: "/").first ?? "")) else { throw SteamClientError.unsafePath }
            let dest = try SteamClientIO.path(entry.name, root: target), saved = try SteamClientIO.path(entry.name, root: transaction)
            if entry.existed {
                guard fm.fileExists(atPath: saved.path) else { throw SteamClientError.rollback }
                try SteamClientIO.replace(from: saved, to: dest)
            } else if fm.fileExists(atPath: dest.path) { try fm.removeItem(at: dest) }
        }
        for name in plan.quarantine {
            guard ["bin/cef/cef.win64", "bin/cef/cef.win7x64", "bin/cef/cef.win7.x64"].contains(name) else { throw SteamClientError.unsafePath }
            let saved = try SteamClientIO.path("quarantine/" + name, root: transaction), dest = try SteamClientIO.path(name, root: target)
            if fm.fileExists(atPath: saved.path) { try fm.moveItem(at: saved, to: dest) }
        }
        try fm.removeItem(at: record)
        let retained = transaction.deletingLastPathComponent().appendingPathComponent(UUID().uuidString)
        try fm.moveItem(at: transaction, to: retained)
    }
    static func install(source: URL, prefix: URL, catalog: SteamClientCatalog, faultAfter: Int? = nil) throws {
        let fm = FileManager.default
        try recover(prefix: prefix, catalog: catalog)
        guard try SteamClientIO.verify(root: source, catalog: catalog) else { throw SteamClientError.integrity }
        let target = prefix.appendingPathComponent("drive_c/Steam32BundleLab")
        let backup = try SteamClientIO.path("client-rollbacks/automatic-pending", root: prefix)
        if fm.fileExists(atPath: backup.path) { // abandoned pre-journal public copies, keep as rollback evidence
            try fm.moveItem(at: backup, to: backup.deletingLastPathComponent().appendingPathComponent(UUID().uuidString))
        }
        try fm.createDirectory(at: backup, withIntermediateDirectories: true)
        var entries: [Entry] = []
        for name in catalog.files.keys.sorted() {
            let dest = try SteamClientIO.path(name, root: target)
            let existed = fm.fileExists(atPath: dest.path)
            if existed {
                let a = try fm.attributesOfItem(atPath: dest.path)
                guard a[.type] as? FileAttributeType == .typeRegular else { throw SteamClientError.unsafePath }
                let saved = try SteamClientIO.path(name, root: backup)
                try fm.createDirectory(at: saved.deletingLastPathComponent(), withIntermediateDirectories: true)
                try fm.copyItem(at: dest, to: saved)
            }
            entries.append(Entry(name: name, existed: existed))
        }
        let quarantine = ["bin/cef/cef.win64", "bin/cef/cef.win7x64", "bin/cef/cef.win7.x64"].filter {
            fm.fileExists(atPath: target.appendingPathComponent($0).path)
        }
        for name in quarantine { _ = try SteamClientIO.path(name, root: target) }
        let plan = Journal(entries: entries, quarantine: quarantine)
        let record = journal(prefix: prefix)
        try JSONEncoder().encode(plan).write(to: record, options: .atomic)
        let handle = try FileHandle(forWritingTo: record); try handle.synchronize(); try handle.close()
        do {
            for (index, entry) in entries.enumerated() {
                try Task.checkCancellation()
                if faultAfter == index { throw SteamClientError.transaction }
                try SteamClientIO.replace(from: try SteamClientIO.path(entry.name, root: source), to: try SteamClientIO.path(entry.name, root: target))
            }
            for name in quarantine {
                let saved = try SteamClientIO.path("quarantine/" + name, root: backup)
                try fm.createDirectory(at: saved.deletingLastPathComponent(), withIntermediateDirectories: true)
                try fm.moveItem(at: try SteamClientIO.path(name, root: target), to: saved)
            }
            guard try SteamClientIO.verify(root: target, catalog: catalog) else { throw SteamClientError.integrity }
            try Task.checkCancellation()
            try fm.removeItem(at: record) // commit point; no more cancellation/fallible writes to installed files
        } catch {
            do { try recover(prefix: prefix, catalog: catalog) } catch { throw SteamClientError.rollback }
            throw error
        }
        // Retain backup; a failed rename does not invalidate a completed install.
        try? fm.moveItem(at: backup, to: backup.deletingLastPathComponent().appendingPathComponent(UUID().uuidString))
    }
}

final class SteamClientDownloadDelegate: NSObject, URLSessionDownloadDelegate, @unchecked Sendable {
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

actor SteamClientInstaller {
    static let shared = SteamClientInstaller()
    private var busy = false
    func verifyInstalled(prefix: URL) throws -> Bool {
        guard !busy else { return false }
        let prefix = prefix.deletingLastPathComponent().resolvingSymlinksInPath().appendingPathComponent(prefix.lastPathComponent)
        guard !FileManager.default.fileExists(atPath: SteamClientTransaction.journal(prefix: prefix).path) else { return false }
        let catalog = try SteamClientCatalog.load()
        let primary = prefix.appendingPathComponent("drive_c/Steam32BundleLab")
        let client = FileManager.default.fileExists(atPath: primary.path) ? primary : prefix.appendingPathComponent("drive_c/Steam32Lab")
        return try SteamClientIO.verify(root: client, catalog: catalog)
    }
    /// Caller's MainActor holds the launcher preparation lock for the entire operation.
    func run(prefix inputPrefix: URL, cache inputCache: URL, source: URL? = nil,
             sessionInactive: @Sendable () async -> Bool,
             progress: @escaping @Sendable (SteamClientProgress) async -> Void) async throws -> Bool {
        // Resolve OS aliases in the trusted parent, but reject a symlink at wine/cache itself.
        let prefix = inputPrefix.deletingLastPathComponent().resolvingSymlinksInPath().appendingPathComponent(inputPrefix.lastPathComponent)
        let cache = inputCache.deletingLastPathComponent().resolvingSymlinksInPath().appendingPathComponent(inputCache.lastPathComponent)
        guard !busy else { throw SteamClientError.activeSession }
        busy = true; defer { busy = false }
        guard await sessionInactive() else { throw SteamClientError.activeSession }
        guard FileManager.default.fileExists(atPath: prefix.appendingPathComponent("system.reg").path) else { throw SteamClientError.runtime }
        let catalog = try SteamClientCatalog.load(), fm = FileManager.default
        guard prefix == prefix.resolvingSymlinksInPath(), cache == cache.resolvingSymlinksInPath() else { throw SteamClientError.unsafePath }
        let recovered = fm.fileExists(atPath: SteamClientTransaction.journal(prefix: prefix).path)
        try SteamClientTransaction.recover(prefix: prefix, catalog: catalog)
        let target = prefix.appendingPathComponent("drive_c/Steam32BundleLab")
        await progress(.init(phase: .existing))
        let existing = fm.fileExists(atPath: target.path) ? target : prefix.appendingPathComponent("drive_c/Steam32Lab")
        if try SteamClientIO.verify(root: existing, catalog: catalog) { await progress(.init(phase: .complete)); return recovered }
        var backupBytes: Int64 = 0
        for name in catalog.files.keys {
            let file = try SteamClientIO.path(name, root: target)
            if fm.fileExists(atPath: file.path) {
                let size = (try fm.attributesOfItem(atPath: file.path)[.size] as? NSNumber)?.int64Value ?? 0
                guard size >= 0, size < 4 * 1024 * 1024 * 1024 else { throw SteamClientError.integrity }
                backupBytes += size
            }
        }
        let required = catalog.downloadBytes + 2 * catalog.expandedBytes + backupBytes + 256 * 1024 * 1024
        try SteamClientIO.requireSpace(required, at: prefix)
        try fm.createDirectory(at: cache, withIntermediateDirectories: true)
        let stage = cache.appendingPathComponent("stage-" + UUID().uuidString)
        defer { try? fm.removeItem(at: stage) }
        if let source {
            guard try SteamClientIO.verify(root: source, catalog: catalog) else { throw SteamClientError.integrity }
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
                let cached = try SteamClientIO.path(p.sha256 + ".zip", root: cache)
                if try SteamClientIO.regular(cached, bytes: p.bytes) && SteamClientIO.hash(cached) == p.sha256 { continue }
                var request = URLRequest(url: URL(string: catalog.origin + p.file)!); request.httpMethod = "HEAD"
                let delegate = SteamClientDownloadDelegate(limit: p.bytes, progress: { _ in })
                let (_, response) = try await session.data(for: request, delegate: delegate)
                guard let http = response as? HTTPURLResponse, http.statusCode == 200, SteamClientDownloadDelegate.authorized(http.url) else { throw SteamClientError.source((response as? HTTPURLResponse)?.statusCode ?? 0) }
                if let length = http.value(forHTTPHeaderField: "Content-Length"), Int64(length) != p.bytes { throw SteamClientError.integrity }
            }
            var completed: Int64 = 0
            for p in catalog.packages {
                try Task.checkCancellation()
                let archive = try SteamClientIO.path(p.sha256 + ".zip", root: cache)
                let phase: SteamClientProgress.Phase = p.name.contains("cef") || p.name.contains("webhelpers") ? .browser : .downloading
                if !(try SteamClientIO.regular(archive, bytes: p.bytes) && SteamClientIO.hash(archive) == p.sha256) {
                    if fm.fileExists(atPath: archive.path) { try fm.removeItem(at: archive) }
                    let prior = completed, total = catalog.downloadBytes
                    let delegate = SteamClientDownloadDelegate(limit: p.bytes) { bytes in
                        Task { await progress(.init(phase: phase, bytes: prior + bytes, total: total)) }
                    }
                    let (temporary, response) = try await session.download(from: URL(string: catalog.origin + p.file)!, delegate: delegate)
                    defer { try? fm.removeItem(at: temporary) }
                    guard let http = response as? HTTPURLResponse, http.statusCode == 200, SteamClientDownloadDelegate.authorized(http.url) else { throw SteamClientError.source((response as? HTTPURLResponse)?.statusCode ?? 0) }
                    guard try SteamClientIO.regular(temporary, bytes: p.bytes) else { throw SteamClientError.integrity }
                    await progress(.init(phase: .verifying, bytes: completed + p.bytes, total: catalog.downloadBytes))
                    guard try SteamClientIO.hash(temporary) == p.sha256 else { throw SteamClientError.integrity }
                    try fm.moveItem(at: temporary, to: archive)
                }
                completed += p.bytes
                await progress(.init(phase: phase, bytes: completed, total: catalog.downloadBytes))
                try SteamClientZIP.extract(archive, into: stage, catalog: catalog)
            }
        }
        guard await sessionInactive() else { throw SteamClientError.activeSession }
        await progress(.init(phase: .installing))
        try SteamClientTransaction.install(source: source ?? stage, prefix: prefix, catalog: catalog)
        await progress(.init(phase: .compatibility))
        guard !fm.fileExists(atPath: SteamClientTransaction.journal(prefix: prefix).path), try SteamClientIO.verify(root: target, catalog: catalog) else { throw SteamClientError.integrity }
        await progress(.init(phase: .complete))
        return true
    }
}
