// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
import Foundation

// Experimental genuine Windows Steam UI. No Dock token transfer and no UI replica.
enum SteamUIExperiment {
    static let flag = "env.MADEIRA_EXPERIMENTAL_STEAM_UI"
    static let bigPictureFlag = "env.MADEIRA_EXPERIMENTAL_BIG_PICTURE"
    static let sessionKey = "MADEIRA_STEAM_UI_SESSION"
    static func callbackScheme(bundleID: String?) -> String {
        bundleID?.hasSuffix(".steamui") == true ? "madeira-steamui" : "madeira"
    }
    static var callbackScheme: String { callbackScheme(bundleID: Bundle.main.bundleIdentifier) }
    static func allowed(flag: String?, bundleID: String?) -> Bool {
        flag == "1" && bundleID?.hasSuffix(".steamui") == true
    }
    static var enabled: Bool {
        let productDefault = Bundle.main.object(forInfoDictionaryKey: "IDeckEnabled") as? Bool == true ? "1" : nil
        return allowed(flag: MadeiraConfig.get(flag) ?? productDefault, bundleID: Bundle.main.bundleIdentifier)
    }
    static func prepareProbe(prefix: URL, flag: String?, bundleID: String?, fls: Bool = false, reservation: Bool = false, x86CEF: Bool = false, keyedEvent: Bool = false, swiftshader: Bool = false) throws -> String {
        guard allowed(flag: flag, bundleID: bundleID) else { throw Failure.disabled }
        let drive = prefix.appendingPathComponent("drive_c")
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
        var batch: String {
            ["@echo off", "start \"\" \"C:\\windows\\system32\\services.exe\"",
             "if exist C:\\ideck-control.exe start \"\" C:\\ideck-control.exe",
             "cd /d \"\(windowsDirectory)\"",
             "\"\(windowsDirectory)\\steam.exe\" -no-cef-sandbox -cef-disable-gpu -nocrashmonitor\(bigPicture ? " -bigpicture" : "")\(accountChooser ? " steam://changeuser" : "")"]
                .joined(separator: "\r\n") + "\r\n"
        }
        var arguments: String { "/desktop=steamui,\(width)x\(height) cmd /c C:\\madeira-steam-ui.cmd" }
    }
    enum Failure: LocalizedError {
        case disabled, incompleteClient, incompleteProbe, invalidSize
        var errorDescription: String? {
            switch self {
            case .disabled: return "Steam UI requires the experimental .steamui app and its feature flag."
            case .incompleteClient: return "A complete 64-bit Windows Steam client, steamwebhelper and libcef are required in this experimental app's own prefix."
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
    static func prepare(prefix: URL, width: Int, height: Int, flag: String?, bundleID: String?, x86Client: Bool = false, bigPicture: Bool = false, bigPictureFlag: String? = nil, accountChooser: Bool = false, loginFirst: Bool = false) throws -> Plan {
        guard allowed(flag: flag, bundleID: bundleID) else { throw Failure.disabled }
        guard !bigPicture || bigPictureFlag == "1" else { throw Failure.disabled }
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
            let plan = Plan(windowsDirectory: "C:\\" + relative.replacingOccurrences(of: "/", with: "\\"), width: width, height: height, bigPicture: bigPicture && !(accountChooser || loginFirst), accountChooser: accountChooser)
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
    static func clientReady(prefix: URL) -> Bool {
        let client = prefix.appendingPathComponent("drive_c/Steam32BundleLab")
        return FileManager.default.fileExists(atPath: prefix.appendingPathComponent("system.reg").path) &&
            ["steam.exe", "steamclient.dll", "bin/cef/cef.win7/steamwebhelper.exe", "bin/cef/cef.win7/libcef.dll"]
                .allSatisfy { SteamUIExperiment.isX86PE(client.appendingPathComponent($0)) }
    }
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
    @Published var autoStart = UserDefaults.standard.object(forKey: "iDeckAutoStart") as? Bool ?? true {
        didSet { UserDefaults.standard.set(autoStart, forKey: "iDeckAutoStart") }
    }
    var setupDone: Bool { UserDefaults.standard.bool(forKey: "iDeckSetupComplete") }
    var prefix: URL { FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("wine") }
    func refresh() {
        ready = IDeckRules.clientReady(prefix: prefix)
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
                    guard let source = Bundle.main.resourceURL?.appendingPathComponent("Steam32OfficialClient"), fm.fileExists(atPath: source.path) else {
                        throw NSError(domain: "iDeck", code: 4, userInfo: [NSLocalizedDescriptionKey: "This build needs the verified official Steam client resources. See iDeck build instructions."])
                    }
                    try SteamUIExperiment.importBundledX86(source: source, prefix: target,
                        flag: MadeiraConfig.get(SteamUIExperiment.flag) ?? "1", bundleID: Bundle.main.bundleIdentifier)
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
        }
    }
}

struct IDeckLauncher: View {
    let start: () -> Void
    let account: () -> Void
    let setupJIT: () -> Void
    let diagnostics: () -> Void
    @ObservedObject private var state = IDeckState.shared
    @ObservedObject private var jit = JITCoordinator.shared
    @State private var selection = 2
    private func accept() {
        switch selection {
        case 0: if !state.ready { state.prepare() }
        case 1: setupJIT()
        case 2: if state.ready && !jit.busy { start() }
        case 3: if state.ready && !jit.busy { account() }
        default: state.autoStart.toggle()
        }
    }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                HStack(spacing: 14) {
                    Image(systemName: "gamecontroller.fill").font(.largeTitle).foregroundStyle(.cyan)
                    VStack(alignment: .leading) {
                        Text("iDeck").font(.largeTitle.bold())
                        Text("Your Steam library. On your iPhone.").foregroundStyle(.secondary)
                    }
                }
                Text("Complete setup once, then launch Steam Big Picture locally. Steam handles sign-in and remembers this device when you choose Remember me.")
                GroupBox("1 · Runtime & Steam") {
                    VStack(alignment: .leading, spacing: 12) {
                        Label(state.ready ? "Runtime ready" : "Prepare the local runtime", systemImage: state.ready ? "checkmark.circle.fill" : "shippingbox")
                        if !state.ready {
                            Button(state.preparing ? "Preparing…" : "Prepare iDeck") { state.prepare() }
                                .disabled(state.preparing).buttonStyle(.borderedProminent)
                            if state.preparing { ProgressView() }
                        }
                    }.frame(maxWidth: .infinity, alignment: .leading)
                }
                GroupBox("2 · Device & JIT") {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Use Madeira’s existing device pairing and JIT setup. iDeck requests JIT again when a new session needs it.")
                        Button("Configure pairing & JIT", action: setupJIT).buttonStyle(.bordered)
                        if let message = jit.status { Text(message).font(.caption).foregroundStyle(.secondary) }
                        if let message = jit.error { Text(message).foregroundStyle(.orange) }
                    }.frame(maxWidth: .infinity, alignment: .leading)
                }
                Button(action: start) {
                    Label(jit.busy ? "Enabling JIT…" : "Launch Steam Big Picture", systemImage: "play.fill")
                        .font(.headline).frame(maxWidth: .infinity).padding(12)
                }.buttonStyle(.borderedProminent).disabled(!state.ready || state.preparing || jit.busy)
                GroupBox("Steam account") {
                    VStack(alignment: .leading, spacing: 12) {
                        Text("Sign in or choose another account in Steam’s own account screen. Big Picture uses that same Steam session. iDeck does not store your password.")
                        Button("Sign in / Change Steam account", action: account)
                            .buttonStyle(.bordered).disabled(!state.ready || state.preparing || jit.busy)
                    }.frame(maxWidth: .infinity, alignment: .leading)
                }
                Toggle("Open Big Picture automatically next time", isOn: $state.autoStart)
                if let error = state.error { Text(error).foregroundStyle(.orange) }
                Text("Connect a controller, or tap directly on Steam. The floating iDeck button opens the keyboard, virtual controller and options.").foregroundStyle(.secondary)
                Text("Powered by Madeira · Genuine Windows Steam, not Linux SteamOS. This proof of concept uses Valve’s legacy 32-bit client; compatibility is experimental.").font(.caption).foregroundStyle(.secondary)
                Button("Advanced diagnostics", action: diagnostics).font(.caption)
            }.padding(24).frame(maxWidth: 660)
                .frame(maxWidth: .infinity)
        }.background(Color(.systemGroupedBackground))
        .onAppear {
            state.refresh()
            LibraryController.shared.configure(enabled: true, ownsInput: true)
        }
        .onDisappear { LibraryController.shared.configure(enabled: true, ownsInput: false) }
        .onReceive(LibraryController.shared.commands) { command in
            if command == "up" { selection = max(0, selection - 1) }
            if command == "down" { selection = min(4, selection + 1) }
            if command == "accept" { accept() }
        }
        .overlay(alignment: .bottom) {
            Text(["Controller: Prepare runtime", "Controller: Pairing & JIT", "Controller: Launch Big Picture", "Controller: Steam account", "Controller: Auto-start"][selection])
                .font(.caption).padding(8).background(.regularMaterial, in: Capsule()).padding(8)
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
