// SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
import Foundation

/// An immutable request matched to Madeira's real installed-game model.
/// This is NOT ownership, authentication, a storage lease, JIT readiness or
/// permission to start Wine. The future coordinator must retain those gates
/// and ask Valve's Windows client to resolve a supported launch option.
struct LabDockSelection {
    let game: DockGame
    let executable: String
    let workingDirectory: String
    let arguments: [String]

    /// Return the actual config.launch key, never the filtered array offset.
    /// Options must come from the native Steam product-info request for this
    /// AppID. No default0 fallback or guest-provided launch-option identity.
    func launchOption(appID: Int, options: [SteamLaunchOption]) throws -> UInt32 {
        guard appID == game.id, options.count <= 32 else { throw Failure.invalid }
        let install = game.windowsInstallPath
        func absolute(_ relative: String) -> String? {
            let path = relative.replacingOccurrences(of: "/", with: "\\")
            guard !path.hasPrefix("\\"), path.utf8.count <= 512,
                  !path.unicodeScalars.contains(where: { $0.value < 32 || ":\"<>|?*".unicodeScalars.contains($0) }) else { return nil }
            let parts = path.split(separator: "\\", omittingEmptySubsequences: false)
            guard !parts.contains("..") else { return nil }
            let tail = parts.filter { !$0.isEmpty && $0 != "." }.joined(separator: "\\")
            return tail.isEmpty ? install : install + "\\" + tail
        }
        var matches: [UInt32] = []
        for option in options {
            guard let index = option.index, index <= UInt32(Int32.max), option.betaKey.isEmpty,
                  option.requiredDLC == nil || option.requiredDLC == "" || option.requiredDLC == "0",
                  !["server", "editor", "vr", "othervr", "openvroverlay", "osvr", "manual"].contains(option.type.lowercased()),
                  option.oslist.isEmpty || option.oslist.lowercased().split(separator: ",").contains(where: { $0.trimmingCharacters(in: .whitespaces) == "windows" }),
                  let exe = absolute(option.executable), exe.caseInsensitiveCompare(executable) == .orderedSame,
                  let argv = Self.argumentVector(option.arguments), argv == Array(arguments.dropFirst()) else { continue }
            let defaultFolder = String(exe.prefix(upTo: exe.lastIndex(of: "\\")!))
            let folder = option.workingDir.isEmpty ? defaultFolder : absolute(option.workingDir)
            if folder?.caseInsensitiveCompare(workingDirectory) == .orderedSame { matches.append(index) }
        }
        guard matches.count == 1 else { throw matches.isEmpty ? Failure.mismatched : Failure.ambiguous }
        return matches[0]
    }

    /// Windows-style argument tail (not argv0): backslashes before quotes and
    /// doubled quotes inside quotes. Refuse unterminated/oversized text rather
    /// than silently changing the captured Linux argument boundaries.
    static func argumentVector(_ text: String) -> [String]? {
        guard text.utf8.count <= 4096, !text.contains("\0"), !text.contains("\r"), !text.contains("\n") else { return nil }
        let chars = Array(text); var i = 0; var result: [String] = []
        func space(_ c: Character) -> Bool { c == " " || c == "\t" }
        while i < chars.count {
            while i < chars.count && space(chars[i]) { i += 1 }
            if i == chars.count { break }
            var token = ""; var quoted = false
            while i < chars.count && (quoted || !space(chars[i])) {
                var slashes = 0
                while i < chars.count && chars[i] == "\\" { slashes += 1; i += 1 }
                if i < chars.count && chars[i] == "\"" {
                    token += String(repeating: "\\", count: slashes / 2)
                    if slashes % 2 == 1 { token += "\""; i += 1 }
                    else if quoted && i + 1 < chars.count && chars[i + 1] == "\"" { token += "\""; i += 2 }
                    else { quoted.toggle(); i += 1 }
                } else {
                    token += String(repeating: "\\", count: slashes)
                    if i < chars.count && (quoted || !space(chars[i])) { token.append(chars[i]); i += 1 }
                }
            }
            guard !quoted, result.count < 31 else { return nil }
            result.append(token)
        }
        return result
    }

    enum Failure: Error { case invalid, missing, ambiguous, incomplete, mismatched }

    static func resolve(appID: UInt32, install: String, executable: String,
                        workingDirectory: String, arguments: [String],
                        installedGames: [DockGame]) throws -> LabDockSelection {
        guard appID > 0, appID < UInt32.max, !install.isEmpty,
              !arguments.isEmpty, arguments.count <= 32,
              arguments.reduce(0, { $0 + $1.utf8.count + 1 }) <= 4096,
              [install, executable, workingDirectory].allSatisfy({ !$0.isEmpty && $0.utf8.count < 1024 }),
              ([install, executable, workingDirectory] + arguments).allSatisfy({ !$0.contains("\0") }) else {
            throw Failure.invalid
        }
        // Require exactly one authoritative install record. Never choose the
        // first duplicate or fabricate a DockGame from guest metadata.
        let matches = installedGames.filter { $0.id == Int(appID) }
        guard !matches.isEmpty else { throw Failure.missing }
        guard matches.count == 1 else { throw Failure.ambiguous }
        let game = matches[0]
        guard game.installed else { throw Failure.incomplete }
        guard game.library == "SteamLibrary/steamapps",
              game.windowsInstallPath.caseInsensitiveCompare(install) == .orderedSame else { throw Failure.mismatched }
        func contained(_ path: String, allowRoot: Bool) -> Bool {
            let prefix = install + "\\"
            guard path.caseInsensitiveCompare(install) != .orderedSame || allowRoot else { return false }
            if allowRoot && path.caseInsensitiveCompare(install) == .orderedSame { return true }
            guard path.lowercased().hasPrefix(prefix.lowercased()) else { return false }
            let tail = String(path.dropFirst(prefix.count))
            return !tail.isEmpty && tail.split(separator: "\\", omittingEmptySubsequences: false).allSatisfy {
                !$0.isEmpty && $0 != "." && $0 != ".." && !$0.contains("/") && !$0.contains(":")
            }
        }
        guard contained(executable, allowRoot: false), contained(workingDirectory, allowRoot: true),
              executable.lowercased().hasSuffix(".exe"),
              arguments[0].caseInsensitiveCompare(executable) == .orderedSame else { throw Failure.mismatched }
        // Never flatten into MADEIRA_ARGS or silently discard launch options.
        // These bytes still need authoritative Valve launch-option matching.
        return LabDockSelection(game: game, executable: executable,
                                workingDirectory: workingDirectory, arguments: arguments)
    }
}
