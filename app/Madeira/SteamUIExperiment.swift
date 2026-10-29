// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
import Foundation

// Experimental genuine Windows Steam UI. No Dock token transfer and no UI replica.
enum SteamUIExperiment {
    static let flag = "env.MADEIRA_EXPERIMENTAL_STEAM_UI"
    static let bigPictureFlag = "env.MADEIRA_EXPERIMENTAL_BIG_PICTURE"
    static let sessionKey = "MADEIRA_STEAM_UI_SESSION"
    // Re-signing can change the bundle ID without changing the registered
    // schemes. Use the installed Info.plist contract, never infer a scheme
    // from an old experimental bundle suffix.
    static func callbackScheme(bundleID: String?, registeredSchemes: [String]) -> String? {
        let schemes = registeredSchemes.filter {
            $0.range(of: #"^[A-Za-z][A-Za-z0-9+.-]*$"#, options: .regularExpression) != nil
        }
        if let bundleID, let own = schemes.first(where: { $0.caseInsensitiveCompare(bundleID) == .orderedSame }) { return own }
        return schemes.first(where: { $0 == "madeira-steamui" }) ?? schemes.first(where: { $0 == "madeira" }) ?? schemes.first
    }
    static var callbackScheme: String? {
        let types = Bundle.main.object(forInfoDictionaryKey: "CFBundleURLTypes") as? [[String: Any]] ?? []
        return callbackScheme(bundleID: Bundle.main.bundleIdentifier,
            registeredSchemes: types.flatMap { $0["CFBundleURLSchemes"] as? [String] ?? [] })
    }
    static func allowed(flag: String?, bundleID: String?, product: Bool = Bundle.main.object(forInfoDictionaryKey: "IDeckEnabled") as? Bool == true) -> Bool {
        guard flag == "1", let bundleID, !bundleID.isEmpty else { return false }
        return product || bundleID.hasSuffix(".steamui")
    }
    static var enabled: Bool {
        let productDefault = Bundle.main.object(forInfoDictionaryKey: "IDeckEnabled") as? Bool == true ? "1" : nil
        return allowed(flag: MadeiraConfig.get(flag) ?? productDefault, bundleID: Bundle.main.bundleIdentifier)
    }
    static func prepareProbe(prefix: URL, flag: String?, bundleID: String?, fls: Bool = false, reservation: Bool = false, x86CEF: Bool = false, keyedEvent: Bool = false, swiftshader: Bool = false, platform: Bool = false) throws -> String {
        guard allowed(flag: flag, bundleID: bundleID) else { throw Failure.disabled }
        let drive = prefix.appendingPathComponent("drive_c")
        if platform {
            guard isX86PE(drive.appendingPathComponent("platform32-probe.exe")) else { throw Failure.incompleteProbe }
            return "/c C:\\platform32-probe.exe"
        }
        if swiftshader {
            guard isX86PE(drive.appendingPathComponent("swiftshader32-probe.exe")) else { throw Failure.incompleteProbe }
            return "/c C:\\swiftshader32-probe.exe"
        }
        if keyedEvent {
            guard isX86PE(drive.appendingPathComponent("steam-ui-keyed-event32.exe")) else { throw Failure.incompleteProbe }
            return "/c C:\\steam-ui-keyed-event32.exe"
        }
        if reservation {
            guard isX64PE(drive.appendingPathComponent("steam-ui-reservation-probe.exe")) else { throw Failure.incompleteProbe }
            let batch = "@echo off\r\necho reservation-diagnostic-begin > C:\\madeira-reservation-results.txt\r\nC:\\steam-ui-reservation-probe.exe --isolated-reserve-only >> C:\\madeira-reservation-results.txt 2>&1\r\necho reservation-exit=%errorlevel% >> C:\\madeira-reservation-results.txt\r\n"
            try batch.write(to: drive.appendingPathComponent("madeira-reservation-probe.cmd"), atomically: true, encoding: .utf8)
            return "/c C:\\madeira-reservation-probe.cmd"
        }
        if x86CEF {
            guard isX86PE(drive.appendingPathComponent("Steam32Probe/bin/cef/cef.win7/madeira-chrome-elf32-probe.exe")) else { throw Failure.incompleteProbe }
            guard ["chrome_elf.dll", "libcef.dll"].allSatisfy({ isX86PE(drive.appendingPathComponent("Steam32Probe/bin/cef/cef.win7/" + $0)) }) else { throw Failure.incompleteProbe }
            let batch = "@echo off\r\necho x86-cef-diagnostic-begin > C:\\madeira-x86-cef-results.txt\r\nC:\\Steam32Probe\\bin\\cef\\cef.win7\\madeira-chrome-elf32-probe.exe >> C:\\madeira-x86-cef-results.txt 2>&1\r\necho x86-cef-exit=%errorlevel% >> C:\\madeira-x86-cef-results.txt\r\n"
            try batch.write(to: drive.appendingPathComponent("madeira-x86-cef-probe.cmd"), atomically: true, encoding: .utf8)
            return "/c C:\\madeira-x86-cef-probe.cmd"
        }
        if fls {
            guard isX64PE(drive.appendingPathComponent("steam-ui-fls-probe.exe")) else { throw Failure.incompleteProbe }
            let batch = "@echo off\r\necho fls-diagnostic-begin > C:\\madeira-fls-results.txt\r\nC:\\steam-ui-fls-probe.exe >> C:\\madeira-fls-results.txt 2>&1\r\necho fls-exit=%errorlevel% >> C:\\madeira-fls-results.txt\r\n"
            try batch.write(to: drive.appendingPathComponent("madeira-fls-probe.cmd"), atomically: true, encoding: .utf8)
            return "/c C:\\madeira-fls-probe.cmd"
        }
        guard ["steam-ui-atomic-probe.exe", "steam-ui-process-probe.exe"].allSatisfy({ isX64PE(drive.appendingPathComponent($0)) })
        else { throw Failure.incompleteProbe }
        let elfProbe = "Program Files (x86)/Steam/bin/cef/cef.win64/madeira-chrome-elf-probe.exe"
        guard isX64PE(drive.appendingPathComponent(elfProbe)) else { throw Failure.incompleteProbe }
        let lines = ["@echo off", "echo diagnostic-begin > C:\\madeira-probe-results.txt",
            "C:\\steam-ui-atomic-probe.exe >> C:\\madeira-probe-results.txt 2>&1",
            "echo atomic-exit=%errorlevel% >> C:\\madeira-probe-results.txt",
            "C:\\steam-ui-process-probe.exe >> C:\\madeira-probe-results.txt 2>&1",
            "echo process-exit=%errorlevel% >> C:\\madeira-probe-results.txt",
            "\"C:\\\(elfProbe.replacingOccurrences(of: "/", with: "\\"))\" >> C:\\madeira-probe-results.txt 2>&1",
            "echo elf-exit=%errorlevel% >> C:\\madeira-probe-results.txt"]
        try (lines.joined(separator: "\r\n") + "\r\n").write(to: drive.appendingPathComponent("madeira-runtime-probes.cmd"), atomically: true, encoding: .utf8)
        return "/c C:\\madeira-runtime-probes.cmd"
    }
    struct Plan {
        let windowsDirectory: String
        let width: Int
        let height: Int
        let bigPicture: Bool
        var accountChooser = false
        var frozenX86 = false
        var ratatanThreadTest = false
        var batch: String {
            ["@echo off", "start \"\" \"C:\\windows\\system32\\services.exe\"",
             "if exist C:\\ideck-control.exe start \"\" C:\\ideck-control.exe",
             "cd /d \"\(windowsDirectory)\"",
             "\"\(windowsDirectory)\\steam.exe\" -no-cef-sandbox -cef-disable-gpu -nocrashmonitor\(frozenX86 ? " -nobootstrapperupdate -skipinitialbootstrap" : "")\(bigPicture ? " -bigpicture" : "")\(accountChooser ? " steam://changeuser" : "")\(ratatanThreadTest ? " -applaunch 2949320 -job-worker-count 2 -background-job-worker-count 2" : "")"]
                .joined(separator: "\r\n") + "\r\n"
        }
        var arguments: String { "/desktop=steamui,\(width)x\(height) cmd /c C:\\madeira-steam-ui.cmd" }
    }
    enum Failure: LocalizedError {
        case disabled, incompleteClient, incompleteProbe, invalidSize
        var errorDescription: String? {
            switch self {
            case .disabled: return "Steam UI requires the experimental .steamui app and its feature flag."
            case .incompleteClient: return "Steam client or browser files are missing or incompatible. Return to the iDeck launcher and choose Repair Steam files."
            case .incompleteProbe: return "All x64 runtime probes must be present in the experimental app's own drive_c and matching CEF directory."
            case .invalidSize: return "Unsupported experimental desktop size."
            }
        }
    }
    static func isX64PE(_ url: URL) -> Bool { isPE(url, machine: 0x8664) }
    static func isX86PE(_ url: URL) -> Bool { isPE(url, machine: 0x014c) }
    private static func isPE(_ url: URL, machine: UInt16) -> Bool {
        guard url.standardizedFileURL.path == url.resolvingSymlinksInPath().standardizedFileURL.path,
              let handle = try? FileHandle(forReadingFrom: url) else { return false }
        defer { try? handle.close() }
        guard let data = try? handle.read(upToCount: 4096), data.count >= 64,
              data[0] == 0x4d, data[1] == 0x5a else { return false }
        let p = Int(data[60]) | Int(data[61]) << 8 | Int(data[62]) << 16 | Int(data[63]) << 24
        guard p >= 64, p <= data.count - 6 else { return false }
        return data[p..<p+4].elementsEqual([0x50, 0x45, 0, 0]) && data[p+4] == UInt8(machine & 255) && data[p+5] == UInt8(machine >> 8)
    }
    static func importBundledX86(source: URL, prefix: URL, flag: String?, bundleID: String?) throws {
        guard allowed(flag: flag, bundleID: bundleID) else { throw Failure.disabled }
        guard source.standardizedFileURL.path == source.resolvingSymlinksInPath().standardizedFileURL.path,
              ["steam.exe", "steamclient.dll", "bin/cef/cef.win7/steamwebhelper.exe", "bin/cef/cef.win7/libcef.dll"].allSatisfy({ isX86PE(source.appendingPathComponent($0)) }) else { throw Failure.incompleteClient }
        let target = prefix.appendingPathComponent("drive_c/Steam32BundleLab")
        // Never overwrite a previous client, prefix, login cache or save.
        guard !FileManager.default.fileExists(atPath: target.path) else { return }
        guard target.deletingLastPathComponent().standardizedFileURL.path == target.deletingLastPathComponent().resolvingSymlinksInPath().standardizedFileURL.path else { throw Failure.incompleteClient }
        let temporary = target.deletingLastPathComponent().appendingPathComponent(".steam32-import-" + UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: temporary) }
        try FileManager.default.copyItem(at: source, to: temporary)
        try FileManager.default.moveItem(at: temporary, to: target)
    }
    /// Explicit maintenance only: restore verified public client resources after
    /// an architecture-triggered client upgrade. Never copy account/game data.
    static func restorePinnedX86(source: URL, prefix: URL, flag: String?, bundleID: String?) throws -> URL {
        guard allowed(flag: flag, bundleID: bundleID) else { throw Failure.disabled }
        guard try source.resourceValues(forKeys: [.isSymbolicLinkKey]).isSymbolicLink != true else { throw Failure.incompleteClient }
        let source = source.resolvingSymlinksInPath()
        let fm = FileManager.default
        guard source.standardizedFileURL == source.resolvingSymlinksInPath(),
              ["steam.exe", "steamclient.dll", "bin/cef/cef.win7/steamwebhelper.exe", "bin/cef/cef.win7/libcef.dll"].allSatisfy({ isX86PE(source.appendingPathComponent($0)) }) else { throw Failure.incompleteClient }
        let target = prefix.resolvingSymlinksInPath().appendingPathComponent("drive_c/Steam32BundleLab")
        guard target.path == target.resolvingSymlinksInPath().path, fm.fileExists(atPath: target.path) else { throw Failure.incompleteClient }
        let publicFolders: Set<String> = ["bin", "clientui", "controller_base", "friends", "graphics", "public", "resource", "steam", "steamui", "tenfoot", "win64"]
        let privateNames: Set<String> = ["config", "userdata", "steamapps", "logs", "appcache", "htmlcache", "dumps", "steam.cfg", "loginusers.vdf", "config.vdf", "localconfig.vdf"]
        guard let files = fm.enumerator(atPath: source.path) else { throw Failure.incompleteClient }
        var resources: [String] = []
        for case let relative as String in files {
            let file = source.appendingPathComponent(relative)
            let components = relative.split(separator: "/").map(String.init)
            guard let first = components.first else { continue }
            if components.contains(where: { privateNames.contains($0.lowercased()) || $0.lowercased().hasPrefix("ssfn") }) || first.lowercased().hasPrefix("ssfn") || first.hasPrefix(".") || (components.count > 1 && !publicFolders.contains(first)) {
                files.skipDescendants(); continue
            }
            let values = try file.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey])
            guard values.isSymbolicLink != true else { throw Failure.incompleteClient }
            if values.isRegularFile == true { resources.append(relative) }
        }
        guard Set(resources).isSuperset(of: ["steam.exe", "steamclient.dll", "bin/cef/cef.win7/steamwebhelper.exe", "bin/cef/cef.win7/libcef.dll"]) else { throw Failure.incompleteClient }
        // Validate every destination before changing anything; exclude symlink traversal.
        for name in resources {
            let destination = target.appendingPathComponent(name)
            guard destination.standardizedFileURL == destination.resolvingSymlinksInPath() else { throw Failure.incompleteClient }
        }
        let backup = prefix.appendingPathComponent("client-rollbacks/" + UUID().uuidString)
        try fm.createDirectory(at: backup, withIntermediateDirectories: true)
        for name in resources {
            let destination = target.appendingPathComponent(name), saved = backup.appendingPathComponent(name)
            if fm.fileExists(atPath: destination.path) {
                try fm.createDirectory(at: saved.deletingLastPathComponent(), withIntermediateDirectories: true)
                try fm.copyItem(at: destination, to: saved)
            }
        }
        var written: [String] = []
        var moved: [String] = []
        do {
            for name in resources {
                let destination = target.appendingPathComponent(name)
                try fm.createDirectory(at: destination.deletingLastPathComponent(), withIntermediateDirectories: true)
                written.append(name)
                try Data(contentsOf: source.appendingPathComponent(name)).write(to: destination, options: .atomic)
            }
            for folder in ["bin/cef/cef.win64", "bin/cef/cef.win7x64", "bin/cef/cef.win7.x64"] {
                let extra = target.appendingPathComponent(folder)
                if fm.fileExists(atPath: extra.path), !fm.fileExists(atPath: source.appendingPathComponent(folder).path) {
                    let saved = backup.appendingPathComponent(folder)
                    try fm.createDirectory(at: saved.deletingLastPathComponent(), withIntermediateDirectories: true)
                    try fm.moveItem(at: extra, to: saved)
                    moved.append(folder)
                }
            }
            guard IDeckRules.clientIssues(prefix: prefix).isEmpty else { throw Failure.incompleteClient }
        } catch {
            // Best-effort rollback after a failed write. Keep the complete public
            // backup even if low storage also prevents a rollback write.
            for name in written.reversed() {
                let destination = target.appendingPathComponent(name), saved = backup.appendingPathComponent(name)
                if fm.fileExists(atPath: saved.path) {
                    if let data = try? Data(contentsOf: saved) { try? data.write(to: destination, options: .atomic) }
                } else { try? fm.removeItem(at: destination) }
            }
            for folder in moved.reversed() {
                try? fm.moveItem(at: backup.appendingPathComponent(folder), to: target.appendingPathComponent(folder))
            }
            throw error
        }
        return backup
    }
    static func prepare(prefix: URL, width: Int, height: Int, flag: String?, bundleID: String?, x86Client: Bool = false, bigPicture: Bool = false, bigPictureFlag: String? = nil, accountChooser: Bool = false, loginFirst: Bool = false, ratatanThreadTest: Bool = false) throws -> Plan {
        guard allowed(flag: flag, bundleID: bundleID) else { throw Failure.disabled }
        guard !bigPicture || bigPictureFlag == "1" else { throw Failure.disabled }
        guard !ratatanThreadTest || (x86Client && !accountChooser && !loginFirst) else { throw Failure.disabled }
        guard (640...3840).contains(width), (360...2160).contains(height) else { throw Failure.invalidSize }
        let drive = prefix.appendingPathComponent("drive_c")
        for relative in (x86Client ? ["Steam32BundleLab", "Steam32Lab"] : ["Program Files (x86)/Steam", "Program Files/Steam"]) {
            let root = drive.appendingPathComponent(relative)
            guard root.standardizedFileURL.path == root.resolvingSymlinksInPath().standardizedFileURL.path,
                  isPE(root.appendingPathComponent("steam.exe"), machine: x86Client ? 0x014c : 0x8664),
                  isPE(root.appendingPathComponent(x86Client ? "steamclient.dll" : "steamclient64.dll"), machine: x86Client ? 0x014c : 0x8664) else { continue }
            let hasCEF = (x86Client ? ["bin/cef/cef.win7"] : ["bin/cef/cef.win7x64", "bin/cef/cef.win64", "bin/cef"]).contains { folder in
                let cef = root.appendingPathComponent(folder)
                return isPE(cef.appendingPathComponent("steamwebhelper.exe"), machine: x86Client ? 0x014c : 0x8664) && isPE(cef.appendingPathComponent("libcef.dll"), machine: x86Client ? 0x014c : 0x8664)
            }
            guard hasCEF else { continue }
            let plan = Plan(windowsDirectory: "C:\\" + relative.replacingOccurrences(of: "/", with: "\\"), width: width, height: height, bigPicture: bigPicture && !(accountChooser || loginFirst), accountChooser: accountChooser, frozenX86: x86Client, ratatanThreadTest: ratatanThreadTest)
            try plan.batch.write(to: drive.appendingPathComponent("madeira-steam-ui.cmd"), atomically: true, encoding: .utf8)
            return plan
        }
        throw Failure.incompleteClient
    }
    // Only categorical new-log evidence leaves the reader, never raw lines.
    static func milestones(in text: String) -> Set<String> {
        var found = Set<String>()
        if text.contains("ChromeMainDelegate") { found.insert("cef-initialization-reported") }
        if text.contains("BrowserReady") { found.insert("browser-ready-reported") }
        return found
    }
}

enum IDeckCommand: String {
    case steamMenu = "menu", exitGame = "exit-game", changeAccount = "change-account", bigPicture = "big-picture"
}

enum IDeckOverlayPosition {
    static func center(size: CGSize, saved: CGPoint, left: CGFloat, top: CGFloat, right: CGFloat, bottom: CGFloat) -> CGPoint {
        let minX=left+32, minY=top+32
        let maxX=max(minX,size.width-right-32), maxY=max(minY,size.height-bottom-32)
        let candidate = saved.x >= 0 && saved.y >= 0 && saved.x.isFinite && saved.y.isFinite
            ? CGPoint(x:saved.x*size.width,y:saved.y*size.height) : CGPoint(x:maxX,y:minY)
        return CGPoint(x:min(maxX,max(minX,candidate.x)),y:min(maxY,max(minY,candidate.y)))
    }
}

// Observe only new categorical Steam login transitions; never export log payloads.
struct IDeckLoginObservation {
    let file: URL
    private var offset: UInt64 = 0
    private var identity: UInt64?
    private var partial = ""
    init(file: URL) {
        self.file = file
        let attributes = try? FileManager.default.attributesOfItem(atPath: file.path)
        offset = (attributes?[.size] as? NSNumber)?.uint64Value ?? 0
        identity = (attributes?[.systemFileNumber] as? NSNumber)?.uint64Value
    }
    mutating func succeeded() -> Bool {
        guard let attributes = try? FileManager.default.attributesOfItem(atPath: file.path),
              let handle = try? FileHandle(forReadingFrom: file) else { return false }
        defer { try? handle.close() }
        let size = (attributes[.size] as? NSNumber)?.uint64Value ?? 0
        let currentIdentity = (attributes[.systemFileNumber] as? NSNumber)?.uint64Value
        if size < offset || currentIdentity != identity { offset = 0; partial = "" }
        identity = currentIdentity
        do {
            try handle.seek(toOffset: offset)
            guard let data = try handle.read(upToCount: 16384), !data.isEmpty else { return false }
            offset += UInt64(data.count)
            let lines = (partial + String(decoding: data, as: UTF8.self)).components(separatedBy: "\n")
            partial = String((lines.last ?? "").suffix(8192))
            return lines.dropLast().contains { IDeckRules.loginSucceeded($0) }
        } catch { return false }
    }
}

// Foundation-only lifecycle policy, shared by the launcher and host checks.
enum IDeckRules {
    static func loginSucceeded(_ line: String) -> Bool {
        line.trimmingCharacters(in: .whitespacesAndNewlines).range(of:
            #"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] \[ [A-Za-z]+ \] SetLoginState: Success - OK$"#,
            options: .regularExpression) != nil
    }
    static func shouldAutoStart(setup: Bool, ready: Bool, automatic: Bool, arguments: [String]) -> Bool {
        setup && ready && automatic && !arguments.contains { $0.hasPrefix("madeira-") }
    }
    static func runtimeReady(prefix: URL) -> Bool {
        FileManager.default.fileExists(atPath: prefix.appendingPathComponent("system.reg").path)
    }
    static let clientFiles = ["steam.exe", "steamclient.dll", "bin/cef/cef.win7/steamwebhelper.exe", "bin/cef/cef.win7/libcef.dll"]
    static func clientIssues(prefix: URL) -> [String] {
        if FileManager.default.fileExists(atPath: prefix.appendingPathComponent("steam-client-transaction.json").path) { return ["Interrupted Steam installation: use Repair Steam Files before launching."] }
        let fm = FileManager.default
        let folders = ["Steam32BundleLab", "Steam32Lab"]
        let reports = folders.map { folder -> [String] in
            let root = prefix.appendingPathComponent("drive_c/" + folder)
            return clientFiles.compactMap { name in
                let file = root.appendingPathComponent(name)
                if !fm.fileExists(atPath: file.path) { return folder + "/" + name + ": missing" }
                if SteamUIExperiment.isX64PE(file) { return folder + "/" + name + ": unsupported 64-bit client update" }
                return SteamUIExperiment.isX86PE(file) ? nil : folder + "/" + name + ": invalid or unsafe file"
            }
        }
        if reports.contains(where: { $0.isEmpty }) { return [] }
        // Prefer the installed product client; avoid irrelevant missing fallback files.
        return fm.fileExists(atPath: prefix.appendingPathComponent("drive_c/Steam32BundleLab").path) ? reports[0] : reports[1]
    }
    static func steamClientReady(prefix: URL) -> Bool { clientIssues(prefix: prefix).isEmpty }
    static func clientReady(prefix: URL) -> Bool {
        runtimeReady(prefix: prefix) && steamClientReady(prefix: prefix)
    }
}


// Observations, never a persisted "setup complete" flag, determine each checkmark.
enum IDeckPrerequisite: String, CaseIterable, Identifiable {
    case runtime, steam, signing, pairing, connection, jit
    var id: String { rawValue }
    var title: String {
        switch self {
        case .runtime: return "Local runtime"
        case .steam: return "Steam & browser files"
        case .signing: return "Development signing"
        case .pairing: return "JIT setup"
        case .connection: return "Device connection"
        case .jit: return "JIT for this session"
        }
    }
}
struct IDeckPrerequisiteResult: Identifiable {
    enum Status { case unchecked, checking, passed, needsAction }
    let id: IDeckPrerequisite
    var status: Status
    var detail: String
}
struct IDeckPreflight {
    let runtime: Bool
    let steam: Bool
    let signing: Bool?
    let builtIn: Bool
    let helper: Bool
    let paired: Bool
    let externalJIT: Bool
    let connection: Bool
    let jitReady: Bool
    let freshSession: Bool

    var results: [IDeckPrerequisiteResult] {
        func result(_ id: IDeckPrerequisite, _ passed: Bool, _ yes: String, _ no: String) -> IDeckPrerequisiteResult {
            .init(id: id, status: passed ? .passed : .needsAction, detail: passed ? yes : no)
        }
        let configured = jitReady || (builtIn && helper && paired)
        return [
            result(.runtime, runtime, "The local Windows runtime is prepared.", "Prepare the local runtime first. Existing files are preserved."),
            result(.steam, steam, "The complete pinned Steam and CEF file set was verified.", "Add a complete compatible Windows Steam client, including its browser files."),
            result(.signing, signing == true || jitReady, "This copy permits the debugging required by JIT.", signing == false ? "Re-sign with a development profile that allows debugging." : "Signing could not be verified. Enable JIT to verify this session."),
            result(.pairing, configured, jitReady ? "JIT is confirmed for this session." : "Built-in helper and a saved pairing file are present. Activation verifies the pairing.", builtIn ? (helper ? "Pair this device or import its pairing file in JIT setup." : "The built-in JIT helper is unavailable. Check JIT setup.") : (externalJIT ? "StikDebug is installed. Enable JIT to verify its external pairing." : "Install StikDebug or select Built-in StikJIT in JIT setup.")),
            result(.connection, connection || jitReady, connection ? "The device's local debug connection is reachable." : "JIT is already active; reconnect when enabling a new session.", "Connect LocalDevVPN, then check again."),
            result(.jit, jitReady && freshSession, "JIT is active and a fresh Steam session can start.", !freshSession ? "A session is active or has already used this app run. Reopen iDeck before a new launch." : "Enable JIT, return to iDeck, then check again.")
        ]
    }
    var canLaunch: Bool { results.allSatisfy { $0.status == .passed } }
}

@MainActor
final class SteamUIEvidence {
    static let shared = SteamUIEvidence()
    private var timer: Timer?
    private var offsets: [URL: UInt64] = [:]
    private var reported = Set<String>()
    private var ticks = 0
    private var firstPresent: UInt64 = 0
    private var sawRunning = false
    func start(prefix: URL, bigPicture: Bool = false) {
        timer?.invalidate(); offsets = [:]; reported = []; ticks = 0; sawRunning = false
        firstPresent = winios_surface_present_count()
        for base in ["Program Files (x86)/Steam", "Program Files/Steam", "Steam32Lab", "Steam32BundleLab"] {
            for file in ["logs/cef_log.txt", "logs/webhelper.txt", "logs/console_log.txt"] {
                let url = prefix.appendingPathComponent("drive_c/" + base + "/" + file)
                let size = (try? FileManager.default.attributesOfItem(atPath: url.path)[.size] as? NSNumber)?.uint64Value ?? 0
                offsets[url] = size
            }
        }
        LogStore.shared.log(bigPicture ? "[steam-ui] experiment-begin genuine Big Picture; evidence excludes credential payloads" : "[steam-ui] experiment-begin login-only; evidence excludes credential payloads")
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            MainActor.assumeIsolated { self?.poll() }
        }
    }
    private func poll() {
        ticks += 1
        let running = wine_process_is_running() != 0
        if running { sawRunning = true }
        for (url, offset) in Array(offsets) {
            guard let handle = try? FileHandle(forReadingFrom: url) else { continue }
            defer { try? handle.close() }
            guard let end = try? handle.seekToEnd() else { continue }
            let begin = end < offset ? 0 : offset
            guard end > begin else { continue }
            // Read a bounded tail; it is not a complete CEF trace or success oracle.
            try? handle.seek(toOffset: max(begin, end > 65536 ? end - 65536 : 0))
            if let bytes = try? handle.read(upToCount: 65536) {
                for event in SteamUIExperiment.milestones(in: String(decoding: bytes, as: UTF8.self)) where reported.insert(event).inserted {
                    LogStore.shared.log("[steam-ui] " + event)
                }
            }
            offsets[url] = end
        }
        if winios_surface_present_count() > firstPresent, reported.insert("host-surface-present").inserted {
            LogStore.shared.log("[steam-ui] host-surface-present (not proof of CEF content or interaction)")
        }
        if (sawRunning && !running) || ticks >= 600 {
            timer?.invalidate(); timer = nil
            LogStore.shared.log("[steam-ui] observation-ended running=\(running ? 1 : 0) seconds=\(ticks)")
        }
    }
}

// iDeck is an isolated product shell around the genuine local Steam runtime.
// Authentication remains entirely inside Valve's client and its existing prefix.
#if canImport(SwiftUI) && canImport(UIKit)
import SwiftUI
import UIKit

@MainActor final class IDeckState: ObservableObject {
    static let shared = IDeckState()
    private init() {
        // Present the new account entry once; subsequent auto-start remains opt-in.
        if !UserDefaults.standard.bool(forKey: "iDeckAccountLauncherV1") {
            autoStart = false
            UserDefaults.standard.set(false, forKey: "iDeckAutoStart")
            UserDefaults.standard.set(true, forKey: "iDeckAccountLauncherV1")
        }
    }
    static var enabled: Bool {
        SteamUIExperiment.enabled && MadeiraConfig.flag("MADEIRA_IDECK", fallback: Bundle.main.object(forInfoDictionaryKey: "IDeckEnabled") as? Bool == true)
    }
    @Published var running = false
    @Published var preparing = false
    @Published var error: String?
    @Published var menu = false
    var menuRect = CGRect.zero
    @Published var ready = false
    @Published private(set) var steamIntegrityVerified = false
    @Published var autoStart = UserDefaults.standard.object(forKey: "iDeckAutoStart") as? Bool ?? true {
        didSet { UserDefaults.standard.set(autoStart, forKey: "iDeckAutoStart") }
    }
    @Published private(set) var checkingPrerequisites = false
    @Published private(set) var lastChecked: Date?
    @Published private(set) var prerequisites = IDeckPrerequisite.allCases.map {
        IDeckPrerequisiteResult(id: $0, status: .unchecked, detail: "Not checked yet")
    }
    var prerequisitesPassed: Bool {
        !repairRequiresRestart && !checkingPrerequisites && prerequisites.allSatisfy { $0.status == .passed }
    }
    var bundledRuntimeAvailable: Bool {
        guard let root = Bundle.main.resourceURL else { return false }
        return ["aarch64-windows/cmd.exe", "aarch64-windows/explorer.exe", "i386-windows/ntdll.dll"]
            .allSatisfy { FileManager.default.fileExists(atPath: root.appendingPathComponent($0).path) }
            && SteamUIExperiment.isX64PE(root.appendingPathComponent("ideck-control.exe"))
    }
    var bundledSteamAvailable: Bool {
        guard let source = Bundle.main.resourceURL?.appendingPathComponent("Steam32OfficialClient") else { return false }
        return FileManager.default.fileExists(atPath: source.path)
    }
    private func preflight(connection: Bool) -> IDeckPreflight {
        let signing = SigningStatus.current
        let helper = Bundle.main.builtInPlugInsURL?.appendingPathComponent(MadeiraBuiltInJIT.helperFile)
        return IDeckPreflight(
            runtime: bundledRuntimeAvailable && IDeckRules.runtimeReady(prefix: prefix),
            steam: steamIntegrityVerified && IDeckRules.steamClientReady(prefix: prefix),
            signing: signing.known ? signing.debuggable : nil,
            builtIn: JITCoordinator.shared.resolvedMethod == .builtIn,
            helper: MadeiraBuiltInJIT.isAvailable && helper.map { FileManager.default.fileExists(atPath: $0.path) } == true,
            paired: JITPairingFileStore.isImported,
            externalJIT: StikJITHelper.isAvailable,
            connection: connection, jitReady: StikJITHelper.ready,
            freshSession: !repairRequiresRestart && !running && wine_process_is_running() == 0 && wineserver_is_running() == 0 && !StikJITHelper.poolTaken)
    }
    func checkPrerequisites() {
        guard !checkingPrerequisites, !preparing else { return }
        checkingPrerequisites = true
        prerequisites = IDeckPrerequisite.allCases.map { .init(id: $0, status: .unchecked, detail: "Waiting to check") }
        Task { @MainActor in
            var connection = false
            for (index, step) in IDeckPrerequisite.allCases.enumerated() {
                prerequisites[index] = .init(id: step, status: .checking, detail: "Checking…")
                await Task.yield()
                if step == .steam && !running && wine_process_is_running() == 0 && wineserver_is_running() == 0 && !StikJITHelper.poolTaken {
                    // Hash all public resources off the UI executor, using the installer's exact rules.
                    steamIntegrityVerified = (try? await SteamClientInstaller.shared.verifyInstalled(prefix: prefix)) == true
                }
                if step == .connection {
                    connection = await withCheckedContinuation { continuation in
                        LoopbackProbe.check { result in continuation.resume(returning: result.reachable) }
                    }
                }
                prerequisites[index] = preflight(connection: connection).results[index]
                if step == .runtime && !bundledRuntimeAvailable {
                    prerequisites[index].detail = "Runtime files are missing from this installation. Reinstall iDeck."
                }
            }
            // Re-evaluate together so a JIT handoff during a check cannot leave stale green rows.
            prerequisites = preflight(connection: connection).results
            if !bundledRuntimeAvailable {
                prerequisites[0].detail = "Runtime files are missing from this installation. Reinstall iDeck."
            }
            if !IDeckRules.steamClientReady(prefix: prefix) {
                prerequisites[1].detail = IDeckRules.clientIssues(prefix: prefix).joined(separator: "\n") + "\nRepair Steam files below. Account data and games are preserved."
            }
            if IDeckRules.steamClientReady(prefix: prefix) && !steamIntegrityVerified {
                prerequisites[1] = .init(id: .steam, status: .needsAction, detail: "The complete pinned Steam/CEF client could not be verified. Use Repair Steam Files; accounts and games are preserved.")
            }
            refresh()
            lastChecked = Date()
            checkingPrerequisites = false
        }
    }
    var setupDone: Bool { UserDefaults.standard.bool(forKey: "iDeckSetupComplete") }
    var prefix: URL { FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("wine") }
    func refresh() {
        ready = steamIntegrityVerified && IDeckRules.clientReady(prefix: prefix)
    }
    @Published private(set) var repairRequiresRestart = false
    var canRepairSteam: Bool {
        !preparing && !running && wine_process_is_running() == 0 && wineserver_is_running() == 0 && !StikJITHelper.poolTaken
    }
    @Published private(set) var steamInstallProgress: SteamClientProgress?
    private var steamInstallTask: Task<Void, Never>?
    var steamInstallActive: Bool { steamInstallTask != nil }
    var steamInstallActionTitle: String {
        FileManager.default.fileExists(atPath: prefix.appendingPathComponent("drive_c/Steam32BundleLab").path)
            ? "Repair Steam Files" : "Download & Install Steam"
    }
    func cancelSteamInstall() { steamInstallTask?.cancel() }
    private func publishSteamProgress(_ value: SteamClientProgress) {
        guard steamInstallTask != nil else { return }
        func order(_ phase: SteamClientProgress.Phase) -> Int {
            switch phase {
            case .existing, .checking: return 0
            case .downloading, .browser, .verifying: return 1
            case .installing: return 2
            case .compatibility: return 3
            case .complete: return 4
            }
        }
        if let current = steamInstallProgress, order(value.phase) < order(current.phase) { return }
        steamInstallProgress = value
    }
    func repairSteam() { installSteam(manual: true) }
    func installSteam(manual: Bool = false) {
        guard Self.enabled, canRepairSteam, !repairRequiresRestart, !checkingPrerequisites, !JITCoordinator.shared.busy else { return }
        preparing = true; error = nil; autoStart = false
        steamInstallProgress = .init(phase: .checking)
        let target = prefix
        let cache = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0].appendingPathComponent("SteamClientDownloadCache")
        let bundleSource = Bundle.main.resourceURL?.appendingPathComponent("Steam32OfficialClient")
        let imported = target.deletingLastPathComponent().appendingPathComponent("Steam32OfficialRepair")
        let source = manual ? [bundleSource, imported].compactMap { $0 }.first { FileManager.default.fileExists(atPath: $0.path) } : nil
        if manual && source == nil {
            preparing = false; steamInstallProgress = nil
            error = "No manual repair source found. Use Download & Install Steam, or copy a complete matching client to iDeck/Steam32OfficialRepair."
            return
        }
        steamInstallTask = Task {
            do {
                let changed = try await SteamClientInstaller.shared.run(prefix: target, cache: cache, source: source,
                    sessionInactive: { await MainActor.run {
                        !IDeckState.shared.running && wine_process_is_running() == 0 && wineserver_is_running() == 0 && !StikJITHelper.poolTaken && !JITCoordinator.shared.busy
                    } }, progress: { value in await MainActor.run { IDeckState.shared.publishSteamProgress(value) } })
                steamIntegrityVerified = true
                repairRequiresRestart = changed
                if changed {
                    error = "Steam installation verified. Accounts, games and saves were preserved. Fully close and reopen iDeck before enabling JIT or launching Steam."
                }
                LogStore.shared.log("[steam-client-install] complete verified public client; restart=\(changed ? 1 : 0)")
            } catch is CancellationError {
                steamInstallProgress = nil; error = "Steam installation cancelled. Existing files were preserved or rolled back. Verified package downloads are cached; tap Retry."
            } catch let failure as URLError where failure.code == .cancelled {
                steamInstallProgress = nil; error = "Download cancelled or interrupted. Tap Retry; verified packages are cached. Existing Steam files were kept."
            } catch {
                steamInstallProgress = nil
                // Never surface request URLs, response bodies or account payloads.
                if let known = error as? SteamClientError { self.error = known.localizedDescription }
                else { self.error = "Steam installation did not complete. Check your connection and free storage, then tap Retry. Existing data and rollback copies were kept. Manual import is also available." }
                LogStore.shared.log("[steam-client-install] failed; retry/manual recovery available", level: .error)
            }
            steamInstallTask = nil; preparing = false
            checkPrerequisites()
        }
    }
    @Published var controlReady = false
    @Published var controlBusy = false
    @Published var controlStatus: String?
    @Published var accountSetup = false
    private var loginObservation: IDeckLoginObservation?
    private var loginConfirmed = false
    func beginLoginObservation(client: URL, enabled: Bool) {
        accountSetup = enabled; loginConfirmed = false
        loginObservation = enabled ? IDeckLoginObservation(file: client.appendingPathComponent("logs/steamui_login.txt")) : nil
    }
    private func advanceLogin() {
        guard accountSetup else { return }
        if loginObservation?.succeeded() == true {
            loginConfirmed = true
            LogStore.shared.log("[ideck-account] Steam reported Success/OK; no account payload recorded")
        }
        if loginConfirmed && controlReady && !controlBusy {
            command(.bigPicture)
            if controlBusy { accountSetup = false; loginObservation = nil; loginConfirmed = false }
        }
    }
    private var controlTimer: Timer?
    private var requestID: String?
    private var requestedAt = Date.distantPast
    func installControl() throws {
        guard let source=Bundle.main.resourceURL?.appendingPathComponent("ideck-control.exe"), SteamUIExperiment.isX64PE(source) else {
            throw NSError(domain:"iDeck",code:10,userInfo:[NSLocalizedDescriptionKey:"iDeck control helper is missing from this build."])
        }
        let drive=prefix.appendingPathComponent("drive_c")
        try Data(contentsOf:source).write(to:drive.appendingPathComponent("ideck-control.exe"),options:.atomic)
        for name in ["ideck-command.txt","ideck-command-result.txt","ideck-focus-status.txt","ideck-input-status.txt"] { try? FileManager.default.removeItem(at:drive.appendingPathComponent(name)) }
        controlReady=false;controlBusy=false;requestID=nil;controlStatus=nil
    }
    func observeControl() {
        controlTimer?.invalidate()
        controlTimer=Timer.scheduledTimer(withTimeInterval:0.25,repeats:true) { [weak self] _ in
            MainActor.assumeIsolated { self?.pollControl() }
        }
    }
    func command(_ action: IDeckCommand) {
        guard Self.enabled, running, controlReady, !controlBusy else { return }
        let id=UUID().uuidString.lowercased()
        do {
            try Data("\(id) \(action.rawValue)\n".utf8).write(to:prefix.appendingPathComponent("drive_c/ideck-command.txt"),options:.atomic)
            requestID=id;requestedAt=Date();controlBusy=true;controlStatus="Sending to Steam…";menu=false
        } catch { controlStatus="Could not send the Steam action." }
    }
    private func pollControl() {
        defer { advanceLogin() }
        if controlBusy && Date().timeIntervalSince(requestedAt)>30 {
            controlBusy=false;requestID=nil;controlStatus="Steam did not confirm the action."
        }
        let file=prefix.appendingPathComponent("drive_c/ideck-command-result.txt")
        if let data=try? Data(contentsOf:file), data.count<=128 {
            let fields=String(decoding:data,as:UTF8.self).split(whereSeparator: { $0.isWhitespace })
            if fields.count==2 {
                if fields[0]=="ready" && fields[1]=="ready" { controlReady=true }
                if let id=requestID, fields[0]==id {
                    let result=String(fields[1])
                    switch result {
                    case "close-requested": controlStatus="Closing game. Confirm any save prompt in the game.";return
                    case "menu-requested", "big-picture-requested": controlStatus=nil
                    case "account-ui-requested": controlStatus="Choose your account in Steam. iDeck never enters credentials."
                    case "returned-to-steam": controlStatus=nil
                    case "no-game": controlStatus="No running Steam game window was found."
                    case "multiple-games": controlStatus="Focus the game you want to close, then try again."
                    case "game-close-pending": controlStatus="The game is still open. Confirm its save/exit prompt."
                    case "steam-window-unavailable": controlStatus="Steam’s window is not ready yet."
                    case "busy": controlStatus="A game exit is already pending."
                    default: controlStatus="Steam could not complete this action."
                    }
                    controlBusy=false;requestID=nil
                }
            }
        }
        if controlBusy && Date().timeIntervalSince(requestedAt)>30 {
            controlBusy=false;requestID=nil;controlStatus="Steam did not confirm the action."
        }
    }
    func prepare() {
        guard Self.enabled, !preparing, !running, wine_process_is_running() == 0 else { return }
        preparing = true; error = nil
        let target = prefix
        Task {
            do {
                try await Task.detached(priority: .userInitiated) {
                    let fm = FileManager.default
                    if !fm.fileExists(atPath: target.appendingPathComponent("system.reg").path) {
                        guard let archive = Bundle.main.path(forResource: "prefix-template", ofType: "tar.gz") else {
                            throw NSError(domain: "iDeck", code: 1, userInfo: [NSLocalizedDescriptionKey: "The runtime template is missing from this build."])
                        }
                        // Never extract over an existing prefix with user data.
                        if fm.fileExists(atPath: target.path), !(try fm.contentsOfDirectory(atPath: target.path)).isEmpty {
                            throw NSError(domain: "iDeck", code: 2, userInfo: [NSLocalizedDescriptionKey: "An incomplete runtime exists. It has been preserved; use diagnostics before repairing it."])
                        }
                        try fm.createDirectory(at: target, withIntermediateDirectories: true)
                        guard madeira_extract_prefix_tgz(archive, target.path) == 0 else {
                            throw NSError(domain: "iDeck", code: 3, userInfo: [NSLocalizedDescriptionKey: "Runtime preparation failed. Your files have been preserved."])
                        }
                    }
                    if !IDeckRules.steamClientReady(prefix: target),
                       let source = Bundle.main.resourceURL?.appendingPathComponent("Steam32OfficialClient"), fm.fileExists(atPath: source.path) {
                        try SteamUIExperiment.importBundledX86(source: source, prefix: target,
                            flag: MadeiraConfig.get(SteamUIExperiment.flag) ?? "1", bundleID: Bundle.main.bundleIdentifier)
                    }
                }.value
                for (key, value) in [SteamUIExperiment.flag: "1", SteamUIExperiment.bigPictureFlag: "1",
                    "env.MADEIRA_GDI_SHARED_SECTION": "1", "env.MADEIRA_STEAM_UI_ALLOW_CRASHPAD": "1",
                    "env.MADEIRA_STEAM_UI_STRICT_RESERVATIONS": "1", "env.MADEIRA_FRONTEND": "0",
                    "env.MADEIRA_CONTROLS_XBOX_DEFAULT": "1", "pool-split": "1", "pool-low": "1"] {
                    guard MadeiraConfig.set(key, value) else {
                        throw NSError(domain: "iDeck", code: 5, userInfo: [NSLocalizedDescriptionKey: "Could not save runtime settings."])
                    }
                }
                refresh()
                if ready { UserDefaults.standard.set(true, forKey: "iDeckSetupComplete") }
            } catch { self.error = error.localizedDescription }
            preparing = false
            checkPrerequisites()
        }
    }
}

struct IDeckLauncher: View {
    let start: () -> Void
    let account: () -> Void
    let setupJIT: () -> Void
    let enableJIT: () -> Void
    let diagnostics: () -> Void
    @ObservedObject private var state = IDeckState.shared
    @ObservedObject private var jit = JITCoordinator.shared
    @Environment(\.scenePhase) private var scenePhase
    @State private var selection = 0
    @State private var showSetupHelp = false
    private var launchEnabled: Bool { state.prerequisitesPassed && !state.preparing && !jit.busy }
    private var passedCount: Int { state.prerequisites.filter { $0.status == .passed }.count }
    private var sessionAvailable: Bool {
        !state.running && wine_process_is_running() == 0 && wineserver_is_running() == 0 && !StikJITHelper.poolTaken
    }
    private func act(on step: IDeckPrerequisite) {
        guard !state.checkingPrerequisites, !state.preparing, !jit.busy else { return }
        switch step {
        case .runtime: if state.bundledRuntimeAvailable { state.prepare() } else { showSetupHelp = true }
        case .steam: state.installSteam()
        case .signing, .pairing: setupJIT()
        case .connection: LocalDevVPN.open()
        case .jit: if sessionAvailable { enableJIT() } else { diagnostics() }
        }
    }
    private func actionTitle(_ step: IDeckPrerequisite) -> String {
        switch step {
        case .runtime: return state.bundledRuntimeAvailable ? "Prepare runtime" : "Setup instructions"
        case .steam: return state.steamInstallActionTitle
        case .signing, .pairing: return "Open JIT setup"
        case .connection: return LocalDevVPN.actionTitle
        case .jit: return sessionAvailable ? "Enable JIT" : "View diagnostics"
        }
    }
    private func accept() {
        switch selection {
        case 0: state.checkPrerequisites()
        case 1...6:
            let row = state.prerequisites[selection - 1]
            if row.status == .needsAction { act(on: row.id) }
        case 7: if launchEnabled { start() }
        case 8: if launchEnabled { account() }
        default: state.autoStart.toggle()
        }
    }
    private func stepRow(_ row: IDeckPrerequisiteResult, number: Int) -> some View {
        HStack(alignment: .top, spacing: 14) {
            VStack(spacing: 6) {
                Group {
                    switch row.status {
                    case .passed: Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
                    case .needsAction: Image(systemName: "exclamationmark.circle.fill").foregroundStyle(.orange)
                    case .checking: ProgressView().frame(width: 28, height: 28)
                    case .unchecked:
                        Text("\(number)").font(.caption.bold()).frame(width: 28, height: 28)
                            .background(Color.secondary.opacity(0.12), in: Circle())
                    }
                }.font(.title2).frame(width: 30, height: 30).accessibilityHidden(true)
                if number < state.prerequisites.count {
                    Rectangle().fill(row.status == .passed ? Color.green.opacity(0.4) : Color.secondary.opacity(0.2))
                        .frame(width: 2).frame(minHeight: 42)
                }
            }
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text(row.id.title).font(.headline)
                    Spacer()
                    if row.status == .passed { Text("Ready").font(.caption).foregroundStyle(.green) }
                }
                Text(row.detail).font(.subheadline).foregroundStyle(.secondary).fixedSize(horizontal: false, vertical: true)
                if row.id == .steam, let progress = state.steamInstallProgress {
                    Text(progress.phase.rawValue).font(.subheadline.weight(.semibold))
                    if let fraction = progress.fraction {
                        ProgressView(value: fraction)
                        Text("\(ByteCountFormatter.string(fromByteCount: progress.bytes, countStyle: .file)) / \(ByteCountFormatter.string(fromByteCount: progress.total, countStyle: .file)) · \(Int(fraction * 100))%")
                            .font(.caption).monospacedDigit()
                    } else if state.steamInstallActive { ProgressView() }
                    if state.steamInstallActive { Button("Cancel") { state.cancelSteamInstall() } }
                }
                if row.status == .needsAction {
                    Button(actionTitle(row.id)) { act(on: row.id) }
                        .buttonStyle(.bordered).disabled(state.checkingPrerequisites || state.preparing || jit.busy)
                }
            }.padding(.bottom, 20)
        }
        .padding(10)
        .background(selection == number ? Color.accentColor.opacity(0.08) : Color.clear, in: RoundedRectangle(cornerRadius: 14))
        .id(number)
        .accessibilityElement(children: .contain)
    }
    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    HStack(spacing: 14) {
                        Image(systemName: "gamecontroller.fill").font(.largeTitle).foregroundStyle(.cyan)
                        VStack(alignment: .leading) {
                            Text("iDeck").font(.largeTitle.bold())
                            Text("Your Steam library. On your iPhone.").foregroundStyle(.secondary)
                        }
                    }
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Before you launch").font(.title2.bold())
                        Text("Follow the steps below. A green checkmark means the condition was verified on this device.")
                            .font(.subheadline).foregroundStyle(.secondary)
                        Button { state.checkPrerequisites() } label: {
                            HStack {
                                if state.checkingPrerequisites { ProgressView().tint(.white) }
                                Label(state.checkingPrerequisites ? "Checking prerequisites…" : "Check all prerequisites", systemImage: "checklist")
                            }.frame(maxWidth: .infinity).padding(8)
                        }.buttonStyle(.borderedProminent)
                            .disabled(state.checkingPrerequisites || state.preparing || jit.busy).id(0)
                        if let checked = state.lastChecked, !state.checkingPrerequisites {
                            HStack {
                                Text("\(passedCount) of \(state.prerequisites.count) ready")
                                Spacer()
                                Text(checked, style: .time)
                            }.font(.caption).foregroundStyle(.secondary)
                        }
                        if state.prerequisitesPassed {
                            Label("All prerequisites are ready. You can launch Steam.", systemImage: "checkmark.seal.fill")
                                .foregroundStyle(.green).font(.subheadline)
                        } else if !state.checkingPrerequisites,
                                  let next = state.prerequisites.first(where: { $0.status == .needsAction }) {
                            Text("Next: \(next.id.title)").font(.subheadline.weight(.semibold))
                        }
                    }
                    VStack(spacing: 0) {
                        ForEach(Array(state.prerequisites.enumerated()), id: \.element.id) { index, row in
                            stepRow(row, number: index + 1)
                        }
                    }
                    GroupBox("Steam recovery") {
                        VStack(alignment: .leading, spacing: 10) {
                            Text("Repair missing or incompatible Steam/browser program files without deleting accounts, games or saves. Replaced public files are backed up. Close Steam and reopen iDeck first if a session has already started.").font(.caption).foregroundStyle(.secondary)
                            Button(state.steamInstallActionTitle) { state.installSteam() }
                                .buttonStyle(.borderedProminent).disabled(!state.canRepairSteam || jit.busy || state.checkingPrerequisites || state.repairRequiresRestart)
                            Text("Downloads the complete pinned legacy client directly from Valve. This older Windows client is unsupported by Valve; continued sign-in is not guaranteed. No Steam files are bundled.").font(.caption).foregroundStyle(.secondary)
                            Link("Steam Subscriber Agreement", destination: URL(string: "https://store.steampowered.com/subscriber_agreement/")!)
                            Button("Use manual repair/import instead") { state.repairSteam() }
                                .buttonStyle(.bordered).disabled(!state.canRepairSteam || jit.busy || state.checkingPrerequisites || state.repairRequiresRestart)
                        }
                    }
                    if state.preparing && !state.steamInstallActive { ProgressView("Preparing runtime…") }
                    if let progress = state.steamInstallProgress {
                        GroupBox("Steam installation") {
                            VStack(alignment: .leading, spacing: 10) {
                                Text(progress.phase.rawValue).font(.headline)
                                if let fraction = progress.fraction {
                                    ProgressView(value: fraction)
                                    Text("\(ByteCountFormatter.string(fromByteCount: progress.bytes, countStyle: .file)) / \(ByteCountFormatter.string(fromByteCount: progress.total, countStyle: .file)) · \(Int(fraction * 100))%")
                                        .font(.caption).monospacedDigit()
                                } else if state.steamInstallActive { ProgressView() }
                                if state.steamInstallActive { Button("Cancel") { state.cancelSteamInstall() } }
                            }.frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }
                    if state.error != nil && !state.preparing && !state.repairRequiresRestart {
                        Button("Retry Steam download") { state.installSteam() }
                            .disabled(!state.canRepairSteam || jit.busy || state.checkingPrerequisites)
                    }
                    if let message = jit.status { Text(message).font(.caption).foregroundStyle(.secondary) }
                    if let message = jit.error { Text(message).foregroundStyle(.orange) }
                    if let error = state.error { Text(error).foregroundStyle(.orange) }
                    Button(action: start) {
                        Label(jit.busy ? "Enabling JIT…" : "Launch Steam Big Picture", systemImage: "play.fill")
                            .font(.headline).frame(maxWidth: .infinity).padding(12)
                    }.buttonStyle(.borderedProminent).disabled(!launchEnabled).id(7)
                    GroupBox("Steam account") {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("Sign in or change accounts in Steam after launch. Account login is verified by Steam, after these device checks.")
                                .font(.subheadline).foregroundStyle(.secondary)
                            Button("Sign in / Change Steam account", action: account)
                                .buttonStyle(.bordered).disabled(!launchEnabled)
                        }.frame(maxWidth: .infinity, alignment: .leading)
                    }.id(8)
                    Toggle("Open Big Picture automatically next time", isOn: $state.autoStart).id(9)
                    Text("Connect a controller, or tap directly on Steam. The floating iDeck button opens the keyboard, virtual controller and options.")
                        .font(.subheadline).foregroundStyle(.secondary)
                    Text("Powered by Madeira · Genuine Windows Steam. Compatibility is experimental.")
                        .font(.caption).foregroundStyle(.secondary)
                    Button("Advanced diagnostics", action: diagnostics).font(.caption)
                }.padding(24).padding(.bottom, 48).frame(maxWidth: 660).frame(maxWidth: .infinity)
            }.background(Color(.systemGroupedBackground))
                .onChange(of: selection) { _, value in
                    withAnimation { proxy.scrollTo(value, anchor: .center) }
                }
        }
        .onAppear {
            state.checkPrerequisites()
            LibraryController.shared.configure(enabled: true, ownsInput: true)
        }
        .onChange(of: scenePhase) { _, phase in
            if phase == .active { state.checkPrerequisites() }
            if phase == .background && state.steamInstallActive { state.cancelSteamInstall() }
        }
        .onChange(of: jit.busy) { _, busy in if !busy { state.checkPrerequisites() } }
        .onDisappear { LibraryController.shared.configure(enabled: true, ownsInput: false) }
        .onReceive(LibraryController.shared.commands) { command in
            guard !showSetupHelp else { return }
            if command == "up" { selection = max(0, selection - 1) }
            if command == "down" { selection = min(9, selection + 1) }
            if command == "accept" { accept() }
        }
        .overlay(alignment: .bottom) {
            Text((["Check prerequisites"] + IDeckPrerequisite.allCases.map(\.title) + ["Launch Steam", "Steam account", "Auto-start"])[selection])
                .font(.caption).padding(8).background(.regularMaterial, in: Capsule()).padding(8).allowsHitTesting(false)
        }
        .sheet(isPresented: $showSetupHelp, onDismiss: { state.checkPrerequisites() }) {
            NavigationStack {
                Form {
                    Section("Runtime") {
                        Text("Prepare runtime creates the local environment without replacing existing files. Missing app runtime files require a complete iDeck build.")
                    }
                    Section("Steam client") {
                        Text("Tap Download & Install Steam after preparing the runtime. It downloads and verifies the full pinned client directly from Valve. If the official source is unavailable, put the complete matching client in Files → iDeck → Steam32OfficialRepair and use manual repair.")
                        Text("Steam, steamclient.dll, steamwebhelper and libcef must belong to the same compatible 32-bit client. A single steam.exe is insufficient.")
                        Link("Read setup instructions", destination: URL(string: "https://github.com/kuscholar/iDeck/blob/main/docs/GETTING_STARTED.md")!)
                    }
                    Section("Account") { Text("Complete sign-in and Steam Guard inside Steam. These checks never read your password or verify account login.") }
                }.navigationTitle("Setup help")
                    .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { showSetupHelp = false } } }
            }
        }
    }
}

struct IDeckHUD: View {
    @ObservedObject private var state = IDeckState.shared
    @ObservedObject private var controls = TouchControlsModel.shared
    @State private var showSettings = false
    @State private var confirmExit = false
    @State private var selection = 0
    @State private var dragBase: CGPoint?
    @State private var drag = CGSize.zero
    @AppStorage("iDeckHUDx") private var savedX = -1.0
    @AppStorage("iDeckHUDy") private var savedY = -1.0
    private let labels=["Keyboard","Virtual controller","Arrange controls","Steam menu","Exit game → Steam","Auto-start","Settings","Done"]
    private func keyboard() { state.menu=false;MetalBackedView.toggleKeyboard() }
    private func activate() {
        switch selection {
        case 0: keyboard()
        case 1: controls.visible.toggle()
        case 2: controls.visible=true;controls.editing=true;state.menu=false
        case 3: state.command(state.accountSetup ? .bigPicture : .steamMenu)
        case 4: confirmExit=true
        case 5: state.autoStart.toggle()
        case 6: showSettings=true
        default: state.menu=false
        }
    }
    var body: some View {
        GeometryReader { geo in
            let insets=geo.safeAreaInsets
            let resting=IDeckOverlayPosition.center(size:geo.size,saved:CGPoint(x:savedX,y:savedY),left:insets.leading,top:insets.top,right:insets.trailing,bottom:insets.bottom)
            let current=dragBase.map { CGPoint(x:$0.x+drag.width,y:$0.y+drag.height) } ?? resting
            ZStack(alignment:.topTrailing) {
                if state.menu {
                    Color.black.opacity(0.65).ignoresSafeArea().onTapGesture { state.menu=false }
                    ScrollViewReader { reader in
                        ScrollView {
                            VStack(alignment:.leading,spacing:14) {
                                HStack { Text("iDeck").font(.title2.bold());Spacer();Button("Done") { state.menu=false } }
                                ForEach(Array(labels.enumerated()),id:\.offset) { index,label in
                                    Button {
                                        selection=index;activate()
                                    } label: {
                                        HStack { Text(index==3 && state.accountSetup ? "Enter Big Picture" : label);Spacer();
                                            if index==1 { Image(systemName:controls.visible ? "checkmark.circle.fill":"circle") }
                                            if index==5 { Image(systemName:state.autoStart ? "checkmark.circle.fill":"circle") }
                                        }.frame(maxWidth:.infinity,alignment:.leading).padding(9)
                                            .background(selection==index ? Color.cyan.opacity(0.18):Color.clear,in:RoundedRectangle(cornerRadius:8))
                                    }.id(index).disabled((3...4).contains(index) && (!state.controlReady || state.controlBusy))
                                }
                                if !state.controlReady { Text("Connecting Steam controls…").font(.caption) }
                                if let message=state.controlStatus { Text(message).font(.caption).foregroundStyle(.secondary) }
                            }.padding(20)
                        }.frame(width:min(390,max(240,geo.size.width-32)),height:min(560,max(180,geo.size.height-insets.top-insets.bottom-24)))
                            .background(.regularMaterial,in:RoundedRectangle(cornerRadius:24))
                            .padding(.top,max(insets.top,12)).padding(.trailing,max(insets.trailing,12))
                            .onChange(of:selection) { _,value in reader.scrollTo(value,anchor:.center) }
                    }
                } else {
                    Button { state.menu=true } label: {
                        Image(systemName:"line.3.horizontal").font(.title3.bold()).frame(width:48,height:48)
                    }.buttonStyle(.plain).background(.regularMaterial,in:Circle())
                        .accessibilityLabel("iDeck options — drag to move")
                        .onGeometryChange(for:CGRect.self) { $0.frame(in:.global) } action: { state.menuRect=$0 }
                        .highPriorityGesture(DragGesture(minimumDistance:8).onChanged { value in
                            if dragBase==nil { dragBase=resting };drag=value.translation
                        }.onEnded { value in
                            let origin=dragBase ?? resting
                            let point=CGPoint(x:origin.x+value.translation.width,y:origin.y+value.translation.height)
                            let clamped=IDeckOverlayPosition.center(size:geo.size,saved:CGPoint(x:point.x/max(1,geo.size.width),y:point.y/max(1,geo.size.height)),left:insets.leading,top:insets.top,right:insets.trailing,bottom:insets.bottom)
                            savedX=clamped.x/max(1,geo.size.width);savedY=clamped.y/max(1,geo.size.height);dragBase=nil;drag = .zero
                        })
                        .position(current)
                }
            }.frame(width:geo.size.width,height:geo.size.height,alignment:.topTrailing)
        }.preferredColorScheme(.dark)
        .onAppear { LibraryController.shared.configure(enabled:true,ownsInput:state.menu) }
        .onChange(of:state.menu) { _,open in LibraryController.shared.configure(enabled:true,ownsInput:open) }
        .onChange(of:controls.visible) { _,visible in
            if visible && !controls.controls.contains(where: { $0.action.padName.map(TouchPadAction.supported) ?? false }) {
                ControlPresetsModel.shared.load(ControlPresetLayout.xboxID,screen:ControlPresetsModel.currentScreen(),reason:"ideck-controller-overlay")
            }
        }
        .confirmationDialog("Exit the running game and return to Steam?",isPresented:$confirmExit,titleVisibility:.visible) {
            Button("Exit game",role:.destructive) { state.command(.exitGame) }
        } message: { Text("The game receives a normal close request. Confirm any save prompt inside the game.") }
        .sheet(isPresented:$showSettings) { AllSettingsView() }
        .onReceive(LibraryController.shared.commands) { command in
            if command=="menu" { state.menu.toggle() }
            if command=="back" { state.menu=false }
            if state.menu && !showSettings {
                if command=="up" { selection=max(0,selection-1) }
                if command=="down" { selection=min(labels.count-1,selection+1) }
                if command=="accept" { activate() }
            }
        }
    }
}

#endif
