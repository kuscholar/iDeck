// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
import Foundation

enum Steam64SetupError: LocalizedError {
    case components, unsupported, configurationChanged, previousSetup, restart
    var errorDescription: String? {
        switch self {
        case .components: return "This build is missing the verified Steam64 compatibility components. Install a complete iDeck release; Steam was not switched."
        case .unsupported: return "This device/signing layout cannot provide the address range required by this Steam64 build. Switching to 64-bit cannot enlarge it. Existing Steam data was kept."
        case .configurationChanged: return "Settings changed during setup. Reopen iDeck and retry; your current settings were preserved."
        case .previousSetup: return "A previous Steam64 switch needs attention. Reopen iDeck, then use Return to previous environment. Your accounts, games and saves are retained."
        case .restart: return "Steam64 setup is complete. Fully close and reopen iDeck before checking prerequisites and enabling JIT. Sign in through Steam when asked; the old account and games remain in the previous environment."
        }
    }
}

/// Open-source programs only. Valve files always come from its pinned HTTPS packages.
/// Pin bytes as well as hashes; a header/machine match alone cannot authorize a component.
enum Steam64Components {
    struct Item { let resource: String; let destination: String; let bytes: Int64; let sha256: String }
    static let items = [
        Item(resource: "chrome_elf.dll", destination: "Program Files/Steam/bin/cef/cef.win64/chrome_elf.dll", bytes: 1666560, sha256: "673584661cd0044b186e40286b3d57a099b45002d3fc50f334ae1d3d14bc7621"),
        Item(resource: "crashpad_handler.exe", destination: "iDeckCEF64Crashpad/crashpad_handler.exe", bytes: 25614848, sha256: "76303a50b472a8a97c7d336564f00498ab5d34104d1f5c994056125528d8fd11"),
        Item(resource: "config_guard.exe", destination: "iDeckCEF64Crashpad/config_guard.exe", bytes: 91136, sha256: "0d7e0e45215c94da469d1c167aaa3533e2a9c563d4acc5f13b567860011a5640")
    ]
    static var resourceRoot: URL? { Bundle.main.resourceURL?.appendingPathComponent("Steam64Compatibility") }
    static let configPath = "Program Files/Steam/bin/cef/cef.win64/crash_reporter.cfg"
    // Keep genuine CEF/Valve crash reporting. No report/credential data is shipped.
    static let config = Data(("[Config]\nExternalHandler=C:\\iDeckCEF64Crashpad\\crashpad_handler.exe\nProductName=cefwebhelper\nProductVersion=1769025840\nServerURL=https://crash.steampowered.com/submit\nRateLimitEnabled=true\nMaxUploadsPerDay=5\n\n[CrashKeys]\nVendor=small\nUserID=small\nBuildID=small\nPlatform=small\nSteamUniverse=small\n").replacingOccurrences(of: "\n", with: "\r\n").utf8)
    static func validateRuntime(root: URL? = Bundle.main.resourceURL) throws {
        guard let root else { throw Steam64SetupError.components }
        let translator = try Steam64IO.path("arm64ec-windows/xtajit64.dll", root: root)
        guard try Steam64IO.regular(translator, bytes: 5435392), SteamUIExperiment.isX64PE(translator),
              try Steam64IO.hash(translator) == "a3365a0d47f02efab8b31f4ae178e742769bcb827fd87c41c5db49de25ee590c" else { throw Steam64SetupError.components }
    }
    static func validateBundle(root input: URL? = resourceRoot) throws {
        guard let root = input else { throw Steam64SetupError.components }
        for item in items {
            let source = try Steam64IO.path(item.resource, root: root)
            guard try Steam64IO.regular(source, bytes: item.bytes), try Steam64IO.hash(source) == item.sha256,
                  SteamUIExperiment.isX64PE(source) else { throw Steam64SetupError.components }
        }
        for notice in ["PROVENANCE.json", "notices/CHROMIUM-LICENSE", "notices/CRASHPAD-LICENSE", "notices/MINI_CHROMIUM-LICENSE", "notices/ZLIB-LICENSE", "notices/LLVM-MINGW-LICENSE", "notices/IDeck-LICENSE", "notices/IDeck-EXCEPTION"] {
            let file = try Steam64IO.path(notice, root: root)
            let values = try file.resourceValues(forKeys: [.isRegularFileKey, .fileSizeKey])
            guard values.isRegularFile == true, (values.fileSize ?? 0) > 0 else { throw Steam64SetupError.components }
        }
    }
    static func composed(_ official: Steam64Catalog) throws -> Steam64Catalog {
        var files = official.files
        for item in items { files[item.destination] = .init(bytes: item.bytes, sha256: item.sha256) }
        files[configPath] = .init(bytes: Int64(config.count), sha256: Steam64IO.digest(config))
        return .init(schema: official.schema, version: official.version, manifestSHA256: official.manifestSHA256,
                     origin: official.origin, expandedBytes: files.values.reduce(0) { $0 + $1.bytes }, packages: official.packages, files: files)
    }
    static func stage(into stage: URL, resources: URL? = resourceRoot) throws {
        try validateBundle(root: resources)
        guard let resources else { throw Steam64SetupError.components }
        for item in items { try Steam64IO.replace(from: try Steam64IO.path(item.resource, root: resources), to: try Steam64IO.path(item.destination, root: stage)) }
        let target = try Steam64IO.path(configPath, root: stage)
        try FileManager.default.createDirectory(at: target.deletingLastPathComponent(), withIntermediateDirectories: true)
        try config.write(to: target, options: .atomic)
    }
}

/// Activation is a single atomic config write, AFTER the full composed client is verified.
/// A durable receipt is written first. Legacy prefix/auth/game files are never copied.
enum Steam64Profile {
    static let receiptName = "steam64-setup-receipt.json"
    struct Receipt: Codable { let before: Data?; let after: Data; let schema: Int }
    // Necessary address-range test only. Native constructor still must acquire every
    // disjoint, backed hold on next app launch; this does not promise free capacity.
    static func eligible(mapEnd: UInt64?) -> Bool { (mapEnd ?? 0) >= 0x8000000000 }
    static let settings: [String: String] = {
        var result = ["steam-runtime": "steam64", "pool": "704", "pool-low": "1", "pool-low-margin": "256", "pool-mid": "1", "pool-split": "1",
            "env.MADEIRA_EXPERIMENTAL_STEAM_UI": "1", "env.MADEIRA_EXPERIMENTAL_BIG_PICTURE": "1", "env.MADEIRA_GDI_SHARED_SECTION": "1",
            "env.MADEIRA_STEAM_UI_ALLOW_CRASHPAD": "1", "env.MADEIRA_STEAM_UI_STRICT_RESERVATIONS": "1"]
        let enabled = ["CEF64_CRASH_POOLS", "CEF64_EIGHTH_TABLE", "CEF64_EXTERNAL_CRASHPAD", "CEF64_FEX_PACK", "CEF64_FOUR_TABLES", "CEF64_IMAGE_SPILL", "CEF64_KEEP_LOW_POOL", "CEF64_LIBCEF_DATA_ONLY", "CEF64_MULTI_TABLES", "CEF64_NEAR_CODE", "CEF64_NINTH_TAIL_TABLE", "CEF64_ROOT_STORE", "CEF64_SEVENTH_TABLE", "CEF64_SIX_TABLES", "CEF64_SOURCE_LAYOUT", "CEF64_SPLIT_LAYOUT", "CEF64_STANDALONE_LAYOUT", "CEF64_TABLES_FROM_ARENA", "CEF64_TWELVE_TABLES", "CPU_COUNT", "FEX_DECODER_COMPACT", "POOL_LOW_IMAGES", "STEAM_UI_SESSION", "STEAM_UI_STRICT_RESERVATIONS", "THREAD_STACK_SPILL", "X64_IMAGE_NOCOPY", "CEF64_LEASE_FILE", "CEF64_LEASE_TRACE", "STEAM64_GAME_LAUNCH_DIAGNOSTICS", "STEAM64_INPUT_DIAGNOSTICS"]
        for key in enabled { result["steam64.env.MADEIRA_" + key] = "1" }
        for key in ["CEF64_COMPACT_SOURCE_POOLS", "CEF64_EXACT_POOL_B", "CEF64_WIDE_ARENA", "JIT_DUMP", "STEAM64_DIRECT_CEF32", "LEAN_DIAG"] { result["steam64.env.MADEIRA_" + key] = "0" }
        result["steam64.env.MADEIRA_FEX_IR_HALF_MIB"] = "2"
        result["steam64.env.MADEIRA_SMALL_STACK_EXES"] = "steam.exe"
        result["steam64.env.MADEIRA_JITLESS"] = "1"
        return result
    }()
    static func editing(_ original: Data?, values: [String: String], removing keys: Set<String>) throws -> Data {
        guard original == nil || String(data: original!, encoding: .utf8) != nil else { throw Steam64SetupError.configurationChanged }
        let text = original.flatMap { String(data: $0, encoding: .utf8) } ?? ""
        var lines = text.components(separatedBy: "\n").filter { line in
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            guard !trimmed.hasPrefix("#"), let equal = trimmed.firstIndex(of: "=") else { return true }
            return !keys.contains(trimmed[..<equal].trimmingCharacters(in: .whitespaces))
        }
        lines += values.sorted(by: { $0.key < $1.key }).map { "\($0.key) = \($0.value)" }
        return Data((lines.joined(separator: "\n") + "\n").utf8)
    }
    static func read(_ file: URL) throws -> Data? {
        guard file.standardizedFileURL == file.resolvingSymlinksInPath() else { throw Steam64InstallError.unsafePath }
        guard FileManager.default.fileExists(atPath: file.path) else { return nil }
        guard try file.resourceValues(forKeys: [.isRegularFileKey, .fileSizeKey]).isRegularFile == true,
              (try file.resourceValues(forKeys: [.fileSizeKey]).fileSize ?? Int.max) < 1024 * 1024 else { throw Steam64SetupError.configurationChanged }
        return try Data(contentsOf: file)
    }
    static func activate(config: URL, expected: Data?, mapEnd: UInt64?, prefix: URL, catalog: Steam64Catalog) throws {
        guard eligible(mapEnd: mapEnd) else { throw Steam64SetupError.unsupported }
        guard (expected?.count ?? 0) <= 128 * 1024, try read(config) == expected else { throw Steam64SetupError.configurationChanged }
        guard !FileManager.default.fileExists(atPath: Steam64Transaction.journal(prefix: prefix).path),
              try Steam64IO.verify(root: prefix.appendingPathComponent("drive_c"), catalog: Steam64Components.composed(catalog)) else { throw Steam64InstallError.integrity }
        let record = config.deletingLastPathComponent().appendingPathComponent(receiptName)
        var original = expected
        if let saved = try read(record) {
            let receipt = try JSONDecoder().decode(Receipt.self, from: saved)
            let currentValues = MadeiraConfig.parse(String(decoding: expected ?? Data(), as: UTF8.self))
            let installedValues = MadeiraConfig.parse(String(decoding: receipt.after, as: UTF8.self))
            guard receipt.schema == 1, expected == receipt.before || settings.keys.allSatisfy({ currentValues[$0] == installedValues[$0] }) else { throw Steam64SetupError.configurationChanged }
            original = receipt.before // Repair/retry must retain the FIRST pre-upgrade selection.
        }
        let after = try editing(expected, values: settings, removing: Set(settings.keys))
        try JSONEncoder().encode(Receipt(before: original, after: after, schema: 1)).write(to: record, options: .atomic)
        // Re-check after receipt I/O; no async gap between compare and atomic write.
        guard (expected?.count ?? 0) <= 128 * 1024, try read(config) == expected else { throw Steam64SetupError.configurationChanged }
        try after.write(to: config, options: .atomic)
    }
    static func restore(config: URL) throws {
        let record = config.deletingLastPathComponent().appendingPathComponent(receiptName)
        guard let bytes = try read(record) else { throw Steam64SetupError.previousSetup }
        let observed = try read(config)
        let receipt = try JSONDecoder().decode(Receipt.self, from: bytes)
        guard receipt.schema == 1 else { throw Steam64SetupError.previousSetup }
        if observed == receipt.before { try FileManager.default.removeItem(at: record); return }
        guard let current = observed else { throw Steam64SetupError.configurationChanged }
        let currentValues = MadeiraConfig.parse(String(decoding: current, as: UTF8.self))
        let installedValues = MadeiraConfig.parse(String(decoding: receipt.after, as: UTF8.self))
        let beforeValues = MadeiraConfig.parse(String(decoding: receipt.before ?? Data(), as: UTF8.self))
        if settings.keys.allSatisfy({ currentValues[$0] == beforeValues[$0] }) {
            // Recovery after config restoration succeeded but receipt removal failed.
            try FileManager.default.removeItem(at: record); return
        }
        // Never undo a user's later edit to a controlled key. Unrelated preferences survive.
        guard settings.keys.allSatisfy({ currentValues[$0] == installedValues[$0] }) else { throw Steam64SetupError.configurationChanged }
        let previous = beforeValues.filter { settings[$0.key] != nil }
        let restored = try editing(current, values: previous, removing: Set(settings.keys))
        try restored.write(to: config, options: .atomic)
        try FileManager.default.removeItem(at: record)
    }
}
