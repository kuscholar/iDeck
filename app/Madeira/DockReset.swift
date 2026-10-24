//
//  DockReset.swift
//  Madeira
//
//  madeira-bcd: what "Reset one-time installs" takes out of the prefix (owner's
//  decision 2026-10-12, his spec of 2026-10-07). The Reset used to forget only
//  that the installers had run. Their files stayed, so the installers found
//  everything in place and ended within half a second (RDR2, log 2026-10-12
//  08:13), and a new user's first install was never replayed. Now the game's
//  next Dock start also removes what a Rockstar game's one-time installs put
//  into the prefix:
//  - the Rockstar Games Launcher and Social Club: their folders under Program
//    Files and ProgramData, their registry keys and uninstall entries, and the
//    Rockstar Service;
//  - the Microsoft Visual C++ 2015-2022 runtimes the launcher's installer adds,
//    x86 and x64: uninstall entries, Windows Installer registrations, Burn
//    dependency keys, the Package Cache, and the DLLs they wrote into system32
//    and syswow64 (Madeira's own DLLs there are links into the app and stay);
//  - the Vulkan runtime from RDR2's install script (its vulkan-1.dll had taken
//    the place of Madeira's own in system32).
//  Keys a fresh prefix already has go back to the template's values instead of
//  away: prefix-template.tar.gz marks VC++ 14.42 installed. With sign-out the
//  launcher's and Social Club's sign-in data goes too.
//  Nothing is deleted. Folders and files move into
//  Documents/madeira-reset-backup/<time>-app<id>/drive_c/, next to copies of
//  system.reg and user.reg taken before the change and a list of what moved.
//  The game, its Steam files and its saves are never touched. Only while no
//  session runs: the wineserver keeps the registry in memory while one does.
//

import Foundation

enum DockReset {
    /// What one reset did, for the log.
    struct Summary: Equatable {
        var moved: [String] = []        // drive_c-relative paths now in the backup
        var entries: [String] = []      // uninstall entries removed, by display name
        var keys = 0                    // registry keys removed
        var values = 0                  // registry values removed
        var restored = 0                // keys put back with the template's values
        var backup = ""                 // the backup folder, relative to Documents
        var failures: [String] = []
    }

    /// The fresh prefix's system.reg. The app sets it to read prefix-template.tar.gz
    /// (templateRegistry); nil leaves the VC++ markers as they are.
    nonisolated(unsafe) static var baselineProvider: () -> String? = { nil }

    // MARK: What the one-time installs put in

    /// An uninstall entry or Windows Installer product of the chain, by its display name:
    /// the Rockstar Games Launcher and Social Club, the Visual C++ 2015-2022 (v14)
    /// runtimes, the Vulkan runtime.
    static func isChain(_ displayName: String) -> Bool {
        let name = displayName.lowercased()
        if name.hasPrefix("rockstar games") { return true }
        if name.hasPrefix("vulkan run time libraries") || name.hasPrefix("vulkan runtime") { return true }
        if name.contains("visual c++") { return ["2015", "2017", "2019", "2022"].contains { name.contains($0) } }
        return false
    }

    /// A Burn dependency provider of the v14 runtimes ("Microsoft.VS.VC_RuntimeMinimumVSU_amd64,v14",
    /// "VC,redist.x64,amd64,14.40,bundle"), lowercased or not.
    static func isRuntimeProvider(_ provider: String) -> Bool {
        let name = provider.lowercased()
        return (name.hasPrefix("microsoft.vs.vc_runtime") && name.hasSuffix(",v14"))
            || (name.hasPrefix("vc,redist.") && name.contains(",14."))
    }

    /// Folders the chain installs, relative to drive_c (matched without regard to case).
    static let folders = [
        "Program Files/Rockstar Games/Launcher", "Program Files/Rockstar Games/Social Club",
        "Program Files (x86)/Rockstar Games/Launcher", "Program Files (x86)/Rockstar Games/Social Club",
        "ProgramData/Rockstar Games",
        "Program Files/VulkanRT", "Program Files (x86)/VulkanRT",
    ]

    /// Sign-in data under each drive_c/users/<name>; moved with sign-out only. The games'
    /// own folders next to them (settings, saves) stay.
    static let userFolders = [
        "AppData/Local/Rockstar Games/Launcher", "AppData/Local/Rockstar Games/Social Club",
        "Documents/Rockstar Games/Launcher", "Documents/Rockstar Games/Social Club",
    ]

    /// A runtime file the chain writes into system32 or syswow64. Only regular files of
    /// these names move: Madeira's own are links into the app, linked again every session.
    static func isRuntimeFile(_ name: String) -> Bool {
        let file = name.lowercased()
        guard file.hasSuffix(".dll") || file.hasSuffix(".exe") else { return false }
        return ["msvcp140", "vcruntime140", "concrt140", "vccorlib140", "vcomp140", "vcamp140",
                "mfc140", "mfcm140", "vulkan-1", "vulkaninfo"].contains { file.hasPrefix($0) }
    }

    /// Registry paths, lowercased with single backslashes. A key below `views` is matched in
    /// the 64-bit view and in Wow6432Node.
    static let views = ["software\\", "software\\wow6432node\\"]
    static let classes = ["software\\classes\\", "software\\classes\\wow6432node\\", "software\\wow6432node\\classes\\"]
    static let rockstarKeys = ["rockstar games\\launcher", "rockstar games\\rockstar games social club",
                               "rockstar games\\social club"]
    static let runtimeMarkers = "microsoft\\visualstudio\\14.0\\vc\\runtimes"
    static let installerUserData = "software\\microsoft\\windows\\currentversion\\installer\\userdata\\s-1-5-18\\"
    static let services = "system\\currentcontrolset\\services\\"

    /// The Windows Installer form of a {GUID} product code: each of the first three groups
    /// reversed, the last eight bytes with their two hex digits swapped; uppercase. nil when
    /// `code` is not a braced GUID.
    static func packed(_ code: String) -> String? {
        guard code.hasPrefix("{"), code.hasSuffix("}") else { return nil }
        let hex = Array(code.uppercased().filter { $0 != "{" && $0 != "}" && $0 != "-" })
        guard hex.count == 32, hex.allSatisfy({ $0.isHexDigit }) else { return nil }
        var out = String(hex[0..<8].reversed()) + String(hex[8..<12].reversed()) + String(hex[12..<16].reversed())
        var index = 16
        while index < 32 { out.append(hex[index + 1]); out.append(hex[index]); index += 2 }
        return out
    }

    /// The braced GUID of a packed code (the packing undoes itself); nil when not 32 hex digits.
    static func unpacked(_ code: String) -> String? {
        let hex = code.uppercased()
        guard hex.count == 32, hex.allSatisfy({ $0.isHexDigit }), let plain = packed("{" + hex + "}") else { return nil }
        let c = Array(plain)
        return "{" + String(c[0..<8]) + "-" + String(c[8..<12]) + "-" + String(c[12..<16]) + "-"
            + String(c[16..<20]) + "-" + String(c[20..<32]) + "}"
    }

    // MARK: Wine's .reg text

    /// A Wine .reg file as lines: "[Key\\Path] <time>" headers, value lines (a hex value may
    /// continue on lines that start with two spaces), blank separators.
    struct RegText {
        struct Section {
            let path: String            // unescaped, lowercased
            let range: Range<Int>       // the header and its lines up to the next header
        }

        var lines: [String]
        init(_ text: String) { lines = text.components(separatedBy: "\n") }
        var text: String { lines.joined(separator: "\n") }

        /// The key path of a header line ("[Software\\Foo] 1776969662"), unescaped; nil for any
        /// other line.
        static func path(_ line: String) -> String? {
            guard line.hasPrefix("["), let close = line.lastIndex(of: "]") else { return nil }
            return String(line[line.index(after: line.startIndex)..<close]).replacingOccurrences(of: "\\\\", with: "\\")
        }

        func sections() -> [Section] {
            var result: [Section] = []
            var current: (path: String, start: Int)?
            for (index, line) in lines.enumerated() {
                guard let path = Self.path(line) else { continue }
                if let current { result.append(Section(path: current.path, range: current.start..<index)) }
                current = (path.lowercased(), index)
            }
            if let current { result.append(Section(path: current.path, range: current.start..<lines.count)) }
            return result
        }

        /// A `"name"=value` line split into the unescaped name and the value as written.
        static func value(_ line: String) -> (name: String, raw: Substring)? {
            guard line.hasPrefix("\"") else { return nil }
            var name = ""
            var escaping = false
            var index = line.index(after: line.startIndex)
            while index < line.endIndex {
                let character = line[index]
                if escaping { name.append(character); escaping = false }
                else if character == "\\" { escaping = true }
                else if character == "\"" {
                    let after = line.index(after: index)
                    guard after < line.endIndex, line[after] == "=" else { return nil }
                    return (name, line[line.index(after: after)...])
                } else { name.append(character) }
                index = line.index(after: index)
            }
            return nil
        }

        static func unescape(_ text: String) -> String {
            var out = ""
            var escaping = false
            for character in text {
                if escaping { out.append(character); escaping = false }
                else if character == "\\" { escaping = true }
                else { out.append(character) }
            }
            return out
        }

        /// A string value (`"..."` or `str(2):"..."`) of a section, unescaped; nil when absent.
        func string(_ name: String, in range: Range<Int>) -> String? {
            let wanted = name.lowercased()
            for index in range {
                guard let parsed = Self.value(lines[index]), parsed.name.lowercased() == wanted else { continue }
                var raw = parsed.raw
                if raw.hasPrefix("str(2):") { raw = raw.dropFirst("str(2):".count) }
                guard raw.count >= 2, raw.hasPrefix("\""), raw.hasSuffix("\"") else { return nil }
                return Self.unescape(String(raw.dropFirst().dropLast()))
            }
            return nil
        }

        /// A dword value of a section; nil when absent.
        func dword(_ name: String, in range: Range<Int>) -> UInt32? {
            let wanted = name.lowercased()
            for index in range {
                guard let parsed = Self.value(lines[index]), parsed.name.lowercased() == wanted,
                      parsed.raw.hasPrefix("dword:") else { continue }
                return UInt32(parsed.raw.dropFirst("dword:".count).trimmingCharacters(in: .whitespaces), radix: 16)
            }
            return nil
        }

        /// Removes every section whose (lowercased) path `remove` selects, its lines up to the
        /// next header included. Returns how many went.
        @discardableResult
        mutating func removeSections(where remove: (String) -> Bool) -> Int {
            var kept: [String] = []
            kept.reserveCapacity(lines.count)
            var removed = 0
            var dropping = false
            for line in lines {
                if let path = Self.path(line) {
                    dropping = remove(path.lowercased())
                    if dropping { removed += 1 }
                }
                if !dropping { kept.append(line) }
            }
            lines = kept
            return removed
        }

        /// Removes the values named in `names` (lowercased) from the sections `select` picks, with
        /// their continuation lines. A section left with no value goes as well. Returns the values
        /// and the sections removed.
        mutating func removeValues(named names: Set<String>, where select: (String) -> Bool) -> (values: Int, sections: Int) {
            var out: [String] = []
            out.reserveCapacity(lines.count)
            var values = 0, sections = 0
            var index = 0
            while index < lines.count {
                guard let path = Self.path(lines[index]), select(path.lowercased()) else {
                    out.append(lines[index]); index += 1; continue
                }
                var end = index + 1
                while end < lines.count, Self.path(lines[end]) == nil { end += 1 }
                var body: [String] = []
                var kept = 0, dropped = 0
                var continuing = false
                for line in lines[(index + 1)..<end] {
                    if continuing {
                        if line.hasPrefix("  ") { continue }
                        continuing = false
                    }
                    if let parsed = Self.value(line), names.contains(parsed.name.lowercased()) {
                        dropped += 1
                        continuing = line.hasSuffix("\\")
                        continue
                    }
                    if line.hasPrefix("\"") || line.hasPrefix("@") { kept += 1 }
                    body.append(line)
                }
                values += dropped
                if dropped > 0 && kept == 0 { sections += 1 }
                else { out.append(lines[index]); out += body }
                index = end
            }
            lines = out
            return (values, sections)
        }

        /// Replaces the key `root` (lowercased) and everything below it with the baseline's
        /// sections for it, which go at the end of the file (Wine reads sections in any
        /// order). Returns the sections removed and the sections put back.
        mutating func restore(_ root: String, from baseline: RegText) -> (removed: Int, restored: Int) {
            let inTree: (String) -> Bool = { $0 == root || $0.hasPrefix(root + "\\") }
            let removed = removeSections(where: inTree)
            var block: [String] = []
            var restored = 0
            var copying = false
            for line in baseline.lines {
                if let path = Self.path(line) {
                    copying = inTree(path.lowercased())
                    if copying { restored += 1 }
                }
                if copying { block.append(line) }
            }
            if !block.isEmpty {
                while let last = lines.last, last.trimmingCharacters(in: .whitespaces).isEmpty { lines.removeLast() }
                lines.append("")
                lines += block
                if let last = lines.last, !last.isEmpty { lines.append("") }
            }
            return (removed, restored)
        }
    }

    /// Whether `path` is one of `roots` or below one of them (lowercased paths).
    static func within(_ path: String, _ roots: Set<String>) -> Bool {
        if roots.contains(path) { return true }
        var end = path.endIndex
        while let slash = path[..<end].lastIndex(of: "\\") {
            if roots.contains(String(path[..<slash])) { return true }
            end = slash
        }
        return false
    }

    // MARK: Finding and stripping the chain's registry entries

    /// The chain's registry entries in system.reg.
    struct Found {
        var entries: [String] = []          // uninstall display names
        var roots: Set<String> = []         // uninstall keys (lowercased paths)
        var packed: Set<String> = []        // Windows Installer product codes, packed, uppercase
        var guids: Set<String> = []         // braced GUIDs, uppercase (Package Cache folders)
        var providers: Set<String> = []     // Burn dependency providers, lowercased
        var paths: [String] = []            // Windows paths: bundle caches, cached packages
    }

    static func scan(_ reg: RegText) -> Found {
        var found = Found()
        let sections = reg.sections()
        let uninstall = views.map { $0 + "microsoft\\windows\\currentversion\\uninstall\\" }
        for section in sections {
            guard let root = uninstall.first(where: { section.path.hasPrefix($0) }) else { continue }
            let child = String(section.path.dropFirst(root.count))
            guard !child.isEmpty, !child.contains("\\") else { continue }
            let display = reg.string("DisplayName", in: section.range) ?? ""
            guard isChain(display) else { continue }
            found.entries.append(display)
            found.roots.insert(section.path)
            if let code = packed(child) {
                found.guids.insert(child.uppercased())
                if reg.dword("WindowsInstaller", in: section.range) == 1 { found.packed.insert(code) }
            }
            if let cache = reg.string("BundleCachePath", in: section.range) { found.paths.append(cache) }
            if let provider = reg.string("BundleProviderKey", in: section.range) { found.providers.insert(provider.lowercased()) }
        }
        // Products of the chain by their own name: a runtime package hidden from the list of
        // programs may have no uninstall entry.
        for section in sections {
            for base in classes {
                let root = base + "installer\\products\\"
                guard section.path.hasPrefix(root) else { continue }
                let child = String(section.path.dropFirst(root.count))
                guard child.count == 32, !child.contains("\\"),
                      isChain(reg.string("ProductName", in: section.range) ?? "") else { continue }
                found.packed.insert(child.uppercased())
            }
        }
        for code in found.packed {
            if let guid = unpacked(code) { found.guids.insert(guid) }
            let key = installerUserData + "products\\" + code.lowercased() + "\\installproperties"
            if let section = sections.first(where: { $0.path == key }),
               let package = reg.string("LocalPackage", in: section.range) { found.paths.append(package) }
        }
        return found
    }

    /// Removes the chain's keys and values from system.reg's text and puts the VC++ markers
    /// back to the template's values (left as they are without a template).
    static func strip(_ reg: inout RegText, _ found: Found, baseline: RegText?) -> (keys: Int, values: Int, restored: Int) {
        var roots = found.roots
        for code in found.packed.map({ $0.lowercased() }) {
            for base in classes {
                roots.insert(base + "installer\\products\\" + code)
                roots.insert(base + "installer\\features\\" + code)
            }
            roots.insert(installerUserData + "products\\" + code)
        }
        for view in views { for key in rockstarKeys { roots.insert(view + key) } }
        let guids = Set(found.guids.map { $0.lowercased() })
        for section in reg.sections() {
            for base in classes {
                let root = base + "installer\\dependencies\\"
                guard section.path.hasPrefix(root) else { continue }
                let child = String(section.path.dropFirst(root.count)).components(separatedBy: "\\")[0]
                if found.providers.contains(child) || guids.contains(child) || isRuntimeProvider(child) {
                    roots.insert(root + child)
                }
            }
            if section.path.hasPrefix(services) {
                let child = String(section.path.dropFirst(services.count))
                let image = (reg.string("ImagePath", in: section.range) ?? "").lowercased()
                if !child.isEmpty, !child.contains("\\"),
                   child == "rockstar service" || image.contains("\\rockstar games\\launcher\\") {
                    roots.insert(section.path)
                }
            }
        }
        var keys = reg.removeSections { within($0, roots) }
        var values = 0
        let codes = Set(found.packed.map { $0.lowercased() })
        if !codes.isEmpty {
            let holders = classes.map { $0 + "installer\\upgradecodes\\" } + [installerUserData + "components\\"]
            let result = reg.removeValues(named: codes) { path in holders.contains { path.hasPrefix($0) } }
            values = result.values
            keys += result.sections
        }
        var restored = 0
        if let baseline {
            for view in views {
                let result = reg.restore(view + runtimeMarkers, from: baseline)
                keys += result.removed
                restored += result.restored
            }
        }
        return (keys, values, restored)
    }

    // MARK: Files

    /// A drive_c-relative path as it is on disk (each part matched without regard to case),
    /// staying inside drive_c; nil when it does not exist.
    static func resolve(_ relative: String, drive: URL) -> String? {
        let fm = FileManager.default
        var current = drive
        var parts: [String] = []
        for part in relative.split(separator: "/").map(String.init) {
            guard !part.isEmpty, part != ".", part != ".." else { return nil }
            var name = part
            if !fm.fileExists(atPath: current.appendingPathComponent(part).path) {
                guard let names = try? fm.contentsOfDirectory(atPath: current.path),
                      let match = names.first(where: { $0.caseInsensitiveCompare(part) == .orderedSame }) else { return nil }
                name = match
            }
            current.appendPathComponent(name)
            parts.append(name)
        }
        guard !parts.isEmpty, inside(current, drive: drive) else { return nil }
        return parts.joined(separator: "/")
    }

    static func inside(_ url: URL, drive: URL) -> Bool {
        url.resolvingSymlinksInPath().standardizedFileURL.path
            .hasPrefix(drive.resolvingSymlinksInPath().standardizedFileURL.path + "/")
    }

    /// "C:\A\B" -> "A/B"; nil for another drive or a path with "." or "..".
    static func relative(_ windowsPath: String) -> String? {
        guard windowsPath.count > 3, windowsPath.prefix(3).uppercased() == "C:\\" else { return nil }
        let parts = windowsPath.dropFirst(3).split(separator: "\\").map(String.init)
        guard !parts.isEmpty, !parts.contains("."), !parts.contains("..") else { return nil }
        return parts.joined(separator: "/")
    }

    /// What moves into the backup, drive_c-relative as on disk: the chain's folders, its
    /// Package Cache folders and cached packages, the runtime files in system32 and
    /// syswow64 that are not Madeira's links, and with sign-out the sign-in data. Never
    /// anything of Steam's.
    static func targets(drive: URL, found: Found, signOut: Bool) -> [String] {
        let fm = FileManager.default
        var paths = folders.compactMap { resolve($0, drive: drive) }
        for windowsPath in found.paths {
            guard let path = relative(windowsPath) else { continue }
            let parts = path.split(separator: "/").map(String.init)
            if parts.count >= 3, parts[0].lowercased() == "programdata", parts[1].lowercased() == "package cache" {
                if let folder = resolve(parts[0..<3].joined(separator: "/"), drive: drive) { paths.append(folder) }
            } else if parts.count == 3, parts[0].lowercased() == "windows", parts[1].lowercased() == "installer",
                      let file = resolve(path, drive: drive) {
                paths.append(file)
            }
        }
        if let cache = resolve("ProgramData/Package Cache", drive: drive) {
            let names = (try? fm.contentsOfDirectory(atPath: drive.appendingPathComponent(cache).path)) ?? []
            for name in names.sorted() where found.guids.contains(where: { name.uppercased().hasPrefix($0) }) {
                paths.append(cache + "/" + name)
            }
        }
        for folder in ["windows/system32", "windows/syswow64"] {
            guard let directory = resolve(folder, drive: drive) else { continue }
            let base = drive.appendingPathComponent(directory)
            let names = (try? fm.contentsOfDirectory(atPath: base.path)) ?? []
            for name in names.sorted() where isRuntimeFile(name) {
                guard let attributes = try? fm.attributesOfItem(atPath: base.appendingPathComponent(name).path),
                      let type = attributes[.type] as? FileAttributeType, type == .typeRegular else { continue }
                paths.append(directory + "/" + name)
            }
        }
        if signOut, let users = resolve("users", drive: drive) {
            let names = (try? fm.contentsOfDirectory(atPath: drive.appendingPathComponent(users).path)) ?? []
            for user in names.sorted() where user.lowercased() != "public" && !user.hasPrefix(".") {
                for folder in userFolders {
                    if let path = resolve(users + "/" + user + "/" + folder, drive: drive) { paths.append(path) }
                }
            }
        }
        // Once each, never inside another target, never Steam's.
        var chosen: [String] = []
        for path in paths.sorted(by: { $0.count < $1.count }) {
            let lower = path.lowercased()
            guard !lower.contains("steamapps"), !lower.hasPrefix("program files (x86)/steam"),
                  !lower.hasPrefix("program files/steam"),
                  !chosen.contains(where: { lower == $0.lowercased() || lower.hasPrefix($0.lowercased() + "/") }) else { continue }
            chosen.append(path)
        }
        return chosen
    }

    // MARK: The reset

    /// Takes the chain out of the prefix (see the top of the file). `drive` is drive_c,
    /// `prefix` holds system.reg and user.reg, `documents` receives the backup. Only while
    /// no session runs.
    static func clean(drive: URL, prefix: URL, documents: URL, appID: Int, signOut: Bool,
                      baseline: String?, now: Date = Date()) -> Summary {
        var summary = Summary()
        let fm = FileManager.default
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyyMMdd-HHmmss"
        let name = formatter.string(from: now) + "-app\(appID)"
        let backup = documents.appendingPathComponent("madeira-reset-backup", isDirectory: true)
            .appendingPathComponent(name, isDirectory: true)
        summary.backup = "madeira-reset-backup/" + name
        let systemFile = prefix.appendingPathComponent("system.reg")
        let userFile = prefix.appendingPathComponent("user.reg")
        guard let systemData = try? Data(contentsOf: systemFile), !systemData.isEmpty else {
            summary.failures.append("system.reg could not be read"); return summary
        }
        // The registry files as they were, before anything changes.
        do {
            try fm.createDirectory(at: backup, withIntermediateDirectories: true)
            for file in [systemFile, userFile] where fm.fileExists(atPath: file.path) {
                try fm.copyItem(at: file, to: backup.appendingPathComponent(file.lastPathComponent))
            }
        } catch {
            summary.failures.append("backup: " + error.localizedDescription); return summary
        }

        var system = RegText(String(decoding: systemData, as: UTF8.self))
        let found = scan(system)
        summary.entries = found.entries
        let paths = targets(drive: drive, found: found, signOut: signOut)
        let files = backup.appendingPathComponent("drive_c", isDirectory: true)
        for path in paths {
            let destination = files.appendingPathComponent(path)
            do {
                try fm.createDirectory(at: destination.deletingLastPathComponent(), withIntermediateDirectories: true)
                try fm.moveItem(at: drive.appendingPathComponent(path), to: destination)
                summary.moved.append(path)
            } catch {
                summary.failures.append(path + ": " + error.localizedDescription)
            }
        }

        let counts = strip(&system, found, baseline: baseline.map { RegText($0) })
        summary.keys = counts.keys
        summary.values = counts.values
        summary.restored = counts.restored
        if counts.keys + counts.values + counts.restored > 0 {
            do { try Data(system.text.utf8).write(to: systemFile, options: .atomic) }
            catch { summary.failures.append("system.reg: " + error.localizedDescription) }
        }
        if signOut, let userData = try? Data(contentsOf: userFile), !userData.isEmpty {
            var user = RegText(String(decoding: userData, as: UTF8.self))
            var roots = Set<String>()
            for view in views { for key in rockstarKeys { roots.insert(view + key) } }
            let removed = user.removeSections { within($0, roots) }
            if removed > 0 {
                summary.keys += removed
                do { try Data(user.text.utf8).write(to: userFile, options: .atomic) }
                catch { summary.failures.append("user.reg: " + error.localizedDescription) }
            }
        }

        var list = ["Madeira Dock reset of app \(appID), " + name, "",
                    "Moved here from drive_c (put a folder back to undo):"]
        list += summary.moved.map { "  " + $0 }
        list += ["", "Uninstall entries removed from system.reg:"] + summary.entries.map { "  " + $0 }
        list += ["", "Registry: \(summary.keys) keys and \(summary.values) values removed, \(summary.restored) keys set back to a new prefix's values.",
                 "system.reg and user.reg here are the files as they were before the reset."]
        if !summary.failures.isEmpty { list += ["", "Failed:"] + summary.failures.map { "  " + $0 } }
        try? Data((list.joined(separator: "\n") + "\n").utf8).write(to: backup.appendingPathComponent("reset.txt"))
        return summary
    }

    // MARK: Madeira's vulkan-1.dll stand-in

    /// A Vulkan runtime installer (one of RDR2's one-time installs) writes Khronos's loader
    /// into system32 as a regular file. A Dock session links Madeira's arm64ec files there
    /// only where nothing is, so that loader stayed, and RDR2 loaded it instead of the
    /// stand-in every earlier run had used (log 2026-10-12 08:13). iOS has no Vulkan driver;
    /// the stand-in answers as Khronos's loader does on a PC without one. Before a Dock
    /// start, while no session runs, the loader moves into the backup folder and the session
    /// links the stand-in again (a direct launch relinks it every session anyway). Nothing
    /// moves without the stand-in in the app, or when the file is a link. Returns the
    /// drive_c-relative path moved, nil when nothing moved.
    static func restoreStandIn(drive: URL, documents: URL, standIn: URL?, now: Date = Date()) -> String? {
        let fm = FileManager.default
        guard let standIn, fm.fileExists(atPath: standIn.path),
              let path = resolve("windows/system32/vulkan-1.dll", drive: drive) else { return nil }
        let file = drive.appendingPathComponent(path)
        guard let attributes = try? fm.attributesOfItem(atPath: file.path),
              let type = attributes[.type] as? FileAttributeType, type == .typeRegular else { return nil }
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyyMMdd-HHmmss"
        let destination = documents.appendingPathComponent("madeira-reset-backup", isDirectory: true)
            .appendingPathComponent(formatter.string(from: now) + "-vulkan-loader", isDirectory: true)
            .appendingPathComponent("drive_c", isDirectory: true).appendingPathComponent(path)
        do {
            try fm.createDirectory(at: destination.deletingLastPathComponent(), withIntermediateDirectories: true)
            try fm.moveItem(at: file, to: destination)
        } catch {
            return nil
        }
        return path
    }

    /// The fresh prefix's system.reg from the app's prefix-template.tar.gz, unpacked into a
    /// temporary folder with `extract` (madeira_extract_prefix_tgz: archive, destination ->
    /// 0 on success). nil when it cannot be read.
    static func templateRegistry(extract: (String, String) -> Int32) -> String? {
        guard let archive = Bundle.main.path(forResource: "prefix-template", ofType: "tar.gz") else { return nil }
        let fm = FileManager.default
        let folder = fm.temporaryDirectory.appendingPathComponent("madeira-template-" + UUID().uuidString, isDirectory: true)
        defer { try? fm.removeItem(at: folder) }
        guard (try? fm.createDirectory(at: folder, withIntermediateDirectories: true)) != nil,
              extract(archive, folder.path) == 0,
              let data = try? Data(contentsOf: folder.appendingPathComponent("system.reg")), !data.isEmpty else { return nil }
        return String(decoding: data, as: UTF8.self)
    }
}
