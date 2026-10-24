// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright 2026 Jfishin, 125hz
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
//
// Derived from Jfishin's Madeira Steam client, used in Madeira with the
// author's permission (see docs/STEAM_SIGNIN.md, "Provenance"). Adapted for
// the owned library and downloads (docs/STEAM_LIBRARY.md).

import Foundation

/// App metadata parsed from Steam's product info (PICS).
struct SteamAppInfo {
    let appID: UInt32
    var name: String = ""
    var type: AppType = .game
    var installDir: String = ""
    var oslist: String = ""         // "macos", "windows", "macos,windows", etc.
    var depots: [DepotInfo] = []
    var buildID: UInt32 = 0
    var freeToDownload = false
    /// Apps owning depots this app installs through `depotfromapp`, so the
    /// install record names them the way Valve's client does.
    var sharedOwners: [UInt32: SharedOwner] = [:]
    /// Store artwork file names from `common.library_assets_full` and
    /// `common.header_image`. Newer apps publish them under a hashed folder, so
    /// the fixed legacy URL is missing for them. `parentID` names a demo's full game.
    var libraryCapsule: String?
    var libraryHero: String?
    var headerImage: String?
    var parentID: UInt32?
    /// Steam's launch configuration (`config.launch`), in Steam's order.
    /// SteamDirectStart and Madeira Dock select an installed Windows entry;
    /// Dock passes its original key to Valve's client.
    var launches: [SteamLaunchOption] = []
    /// Steam Auto-Cloud configuration (`ufs`): which files of the game are its
    /// saves, and where another platform keeps them. Empty for a game that
    /// only uses the Steam Cloud API (its files live in the user's `remote` folder).
    var saveFiles: [SaveFile] = []
    var rootOverrides: [RootOverride] = []

    /// One `ufs.savefiles` entry: `root` names a folder ("WinAppDataLocalLow",
    /// "GameInstall", ...), `path` a subfolder of it, `pattern` a wildcard.
    struct SaveFile: Equatable {
        var root: String
        var path: String
        var pattern: String
        var recursive: Bool
        /// Lower-cased platform names the entry is limited to; empty = all.
        var platforms: [String]
    }

    /// One `ufs.rootoverrides` entry: on `os`, files the cloud lists under
    /// `root` are kept under `useInstead` + `addPath`.
    struct RootOverride: Equatable {
        var root: String
        var os: String
        var useInstead: String
        var addPath: String
    }

    struct SharedOwner: Equatable {
        var name: String
        var installDir: String
        var buildID: UInt32
    }

    enum AppType: String {
        case game = "Game"
        case dlc = "DLC"
        case tool = "Tool"
        case demo = "Demo"
        case application = "Application"
        case music = "Music"
        case unknown = ""

        var isPlayable: Bool {
            self == .game || self == .demo || self == .application
        }

        /// PICS does not capitalize type names consistently (older apps send
        /// "game" rather than "Game"), so names match without case.
        init(pics raw: String) {
            if let exact = AppType(rawValue: raw) { self = exact; return }
            self = [AppType.game, .dlc, .tool, .demo, .application, .music]
                .first { $0.rawValue.caseInsensitiveCompare(raw) == .orderedSame } ?? .unknown
        }
    }

    struct DepotInfo {
        var depotID: UInt32
        var name: String = ""
        var maxSize: UInt64 = 0
        var oslist: String = ""     // "macos", "windows", etc.
        var osarch: String = ""     // "64", "32"
        var dlcAppID: UInt32? = nil
        var manifests: [String: UInt64] = [:]  // branch -> manifestID ("public" is default)
        /// Compressed download size from the modern manifests-dict format
        /// (`manifests.public.download`). 0 when PICS sent the legacy flat
        /// gid format or omitted it.
        var publicDownloadBytes: UInt64 = 0
        /// On-disk size from `manifests.public.size`. 0 when absent.
        var publicSizeBytes: UInt64 = 0
        /// `sharedinstall "1"` marks redistributable depots (DirectX, VC++
        /// runtimes) that live in Steam's common store, not the game dir;
        /// they are excluded from size math.
        var isSharedInstall: Bool = false
        /// `config.language`: empty for common content, otherwise one
        /// language pack ("english", "german", ...).
        var language: String = ""
        /// `config.lowviolence "1"`: regional alternate content.
        var lowViolence: Bool = false
        /// `depotfromapp`: the depot belongs to another app, and Valve's client
        /// installs it as that app ("required app N").
        var fromApp: UInt32? = nil

        /// Check if depot is for the specified OS
        func supports(os: String) -> Bool {
            oslist.isEmpty || oslist.lowercased().contains(os.lowercased())
        }

        /// Get the public branch manifest ID
        var publicManifestID: UInt64? {
            manifests["public"]
        }
    }

    // MARK: - Computed Properties

    /// Shared depots often omit manifests in the consuming app's PICS. Copies
    /// content metadata from the exact depot of its owner, keeping the
    /// consumer's own filters. Returns how many depots were completed.
    mutating func inheritDepots(from owners: [UInt32: SteamAppInfo]) -> Int {
        var changed = 0
        for index in depots.indices {
            let local = depots[index]
            guard local.publicManifestID == nil, let owner = local.fromApp,
                  let source = owners[owner]?.depots.first(where: { $0.depotID == local.depotID }),
                  source.publicManifestID != nil else { continue }
            depots[index].manifests = source.manifests
            depots[index].publicDownloadBytes = source.publicDownloadBytes
            depots[index].publicSizeBytes = source.publicSizeBytes
            if local.oslist.isEmpty { depots[index].oslist = source.oslist }
            if local.osarch.isEmpty { depots[index].osarch = source.osarch }
            if local.language.isEmpty { depots[index].language = source.language }
            depots[index].lowViolence = local.lowViolence || source.lowViolence
            changed += 1
        }
        return changed
    }

    var supportsWindows: Bool {
        oslist.lowercased().contains("windows") || oslist.isEmpty
    }

    /// The depots a Windows install takes: matching OS, architecture-neutral
    /// or matching osarch, common or requested-language content, no
    /// low-violence alternates, no DLC or shared redistributables, and only
    /// depots that publish a public manifest. A 64-bit selection falls back
    /// to 32-bit depots when the app only publishes those.
    func installDepots(os: String = "windows", arch: String = "64",
                       language: String = "english") -> [DepotInfo] {
        func select(_ arch: String) -> [DepotInfo] {
            depots.filter { d in
                d.supports(os: os) && d.dlcAppID == nil && !d.isSharedInstall &&
                d.publicManifestID != nil && !d.lowViolence &&
                (d.osarch.isEmpty || d.osarch == arch) &&
                (d.language.isEmpty || d.language.caseInsensitiveCompare(language) == .orderedSame)
            }.sorted { $0.depotID < $1.depotID }
        }
        let preferred = select(arch)
        if arch == "64", !preferred.contains(where: { $0.osarch == "64" }),
           depots.contains(where: { $0.osarch == "32" && $0.supports(os: os) }) {
            return select("32")
        }
        return preferred
    }

    /// Every depot with why it was or was not selected, for the install log
    /// ("sel", or the first failing rule). IDs and flags only.
    func depotSelectionSummary(os: String = "windows", arch: String = "64",
                               language: String = "english", limit: Int = 24) -> String {
        let chosen = Set(installDepots(os: os, arch: arch, language: language).map(\.depotID))
        return depots.sorted { $0.depotID < $1.depotID }.prefix(limit).map { d in
            let why = selectionRule(d, chosen: chosen, os: os, language: language)
            let from = d.fromApp.map { "<\($0)" } ?? ""
            return "\(d.depotID)[\(d.osarch.isEmpty ? "-" : d.osarch)]\(why)\(from)"
        }.joined(separator: ",")
    }

    /// "sel" or the first rule that left the depot out.
    private func selectionRule(_ d: DepotInfo, chosen: Set<UInt32>, os: String, language: String) -> String {
        if chosen.contains(d.depotID) { return "sel" }
        if !d.supports(os: os) { return "os" }
        if d.dlcAppID != nil { return "dlc" }
        if d.isSharedInstall { return "shared" }
        if d.publicManifestID == nil { return "nomanifest" }
        if d.lowViolence { return "lowviolence" }
        if !d.language.isEmpty && d.language.caseInsensitiveCompare(language) != .orderedSame { return "lang" }
        return "arch"
    }

    /// Owned apps that can be installed for Windows at all.
    var installableOnWindows: Bool {
        supportsWindows && type.isPlayable && !installDepots().isEmpty
    }

    /// Approximate compressed download size for a platform. Per depot it
    /// prefers the modern `manifests.public.download` figure (present for most
    /// apps since Valve's 2023 PICS change) and falls back to the legacy
    /// `maxsize`. DLC depots and `sharedinstall` redistributables are not part
    /// of the base install and are left out. Treat the figure as "about".
    func downloadSize(for os: String) -> UInt64 {
        installDepots(os: os).reduce(0) { total, d in
            let bytes = d.publicDownloadBytes > 0 ? d.publicDownloadBytes : d.maxSize
            guard bytes > 0 else { return total }
            // Sizes are parsed from untrusted PICS VDF strings with no bound:
            // saturate instead of trapping if a malformed depot overflows the sum.
            let (sum, overflow) = total.addingReportingOverflow(bytes)
            return overflow ? UInt64.max : sum
        }
    }

    // MARK: - Parsing

    /// Parse app info from a PICS text-VDF buffer.
    static func parse(appID: UInt32, from data: Data) -> SteamAppInfo? {
        let vdf = VDFParser.parseTextVDF(from: data)
        return parse(appID: appID, from: vdf)
    }

    /// Parse app info from a VDF dictionary
    static func parse(appID: UInt32, from vdf: [String: Any]) -> SteamAppInfo? {
        var info = SteamAppInfo(appID: appID)

        // Navigate to appinfo section
        let appInfo: [String: Any]
        if let nested = vdf["\(appID)"] as? [String: Any] {
            appInfo = nested
        } else if let nested = vdf["appinfo"] as? [String: Any] {
            appInfo = nested
        } else {
            appInfo = vdf
        }

        // Common section
        if let common = appInfo["common"] as? [String: Any] {
            info.name = common["name"] as? String ?? ""
            info.type = AppType(pics: common["type"] as? String ?? "")
            info.oslist = common["oslist"] as? String ?? ""
            info.freeToDownload = (common["freetodownload"] as? String) == "1"
            // Artwork names, English first, else any language.
            func asset(_ node: Any?) -> String? {
                guard let languages = node as? [String: Any] else { return nil }
                let value = (languages["english"] as? String) ?? languages.keys.sorted().compactMap { languages[$0] as? String }.first
                guard let value, !value.isEmpty, value.utf8.count <= 256, !value.contains(".."), !value.hasPrefix("/") else { return nil }
                return value
            }
            if let assets = common["library_assets_full"] as? [String: Any] {
                let capsule = assets["library_capsule"] as? [String: Any]
                info.libraryCapsule = asset(capsule?["image2x"]) ?? asset(capsule?["image"])
                info.libraryHero = asset((assets["library_hero"] as? [String: Any])?["image"])
            }
            info.headerImage = asset(common["header_image"])
            if let parent = (common["parent"] as? String).flatMap(UInt32.init), parent != 0, parent != info.appID {
                info.parentID = parent
            }
        }

        // Config section
        if let config = appInfo["config"] as? [String: Any] {
            info.installDir = config["installdir"] as? String ?? ""
            if let launch = config["launch"] as? [String: Any] {
                info.launches = SteamLaunchOption.parse(launch)
            }
        }

        // Depots section
        if let depots = appInfo["depots"] as? [String: Any] {
            for (key, depotData) in depots {
                guard let depotID = UInt32(key),
                      let depot = depotData as? [String: Any] else { continue }

                var di = DepotInfo(depotID: depotID)
                di.name = depot["name"] as? String ?? ""
                if let config = depot["config"] as? [String: Any] {
                    di.oslist = config["oslist"] as? String ?? ""
                    di.osarch = config["osarch"] as? String ?? ""
                    di.language = config["language"] as? String ?? ""
                    di.lowViolence = (config["lowviolence"] as? String) == "1"
                }
                if let maxSizeStr = depot["maxsize"] as? String, let maxSize = UInt64(maxSizeStr) {
                    di.maxSize = maxSize
                } else if let maxSize = depot["maxsize"] as? UInt32 {
                    di.maxSize = UInt64(maxSize)
                }
                // Text VDF leaves every leaf as a String, so that is checked
                // first; the UInt32 branch serves any binary-VDF caller.
                if let dlcStr = depot["dlcappid"] as? String, let dlc = UInt32(dlcStr) {
                    di.dlcAppID = dlc
                } else if let dlc = depot["dlcappid"] as? UInt32 {
                    di.dlcAppID = dlc
                }
                di.isSharedInstall = (depot["sharedinstall"] as? String) == "1"
                if let from = (depot["depotfromapp"] as? String).flatMap(UInt32.init), from != appID {
                    di.fromApp = from
                }
                if let manifests = depot["manifests"] as? [String: Any] {
                    for (branch, entry) in manifests {
                        if let gidStr = entry as? String, let gid = UInt64(gidStr) {
                            // Legacy flat format: branch -> gid string.
                            di.manifests[branch] = gid
                        } else if let gid = entry as? UInt64 {
                            di.manifests[branch] = gid
                        } else if let dict = entry as? [String: Any] {
                            // Modern format (2023+): branch -> { gid, size, download }.
                            // Most apps carry their sizes here now.
                            if let gidStr = dict["gid"] as? String, let gid = UInt64(gidStr) {
                                di.manifests[branch] = gid
                            }
                            if branch == "public" {
                                if let dStr = dict["download"] as? String, let d = UInt64(dStr) {
                                    di.publicDownloadBytes = d
                                }
                                if let sStr = dict["size"] as? String, let s = UInt64(sStr) {
                                    di.publicSizeBytes = s
                                }
                            }
                        }
                    }
                }
                info.depots.append(di)
            }

            // Build ID
            if let branches = depots["branches"] as? [String: Any],
               let publicBranch = branches["public"] as? [String: Any] {
                if let buildIDStr = publicBranch["buildid"] as? String, let buildID = UInt32(buildIDStr) {
                    info.buildID = buildID
                } else if let buildID = publicBranch["buildid"] as? UInt32 {
                    info.buildID = buildID
                }
            }
        }

        // Auto-Cloud section. Untrusted text: bounded, and only ever used to
        // form paths below known folders (SteamCloud validates each one).
        if let ufs = appInfo["ufs"] as? [String: Any] {
            func text(_ value: Any?) -> String {
                guard let string = value as? String, string.utf8.count <= 512 else { return "" }
                return string
            }
            func entries(_ node: Any?) -> [[String: Any]] {
                guard let dict = node as? [String: Any] else { return [] }
                return dict.keys.compactMap { key in Int(key).map { ($0, key) } }.sorted { $0.0 < $1.0 }
                    .prefix(64).compactMap { dict[$0.1] as? [String: Any] }
            }
            for entry in entries(ufs["savefiles"]) {
                let platforms = (entry["platforms"] as? [String: Any])?.values.compactMap { ($0 as? String)?.lowercased() } ?? []
                info.saveFiles.append(SaveFile(root: text(entry["root"]), path: text(entry["path"]),
                                               pattern: text(entry["pattern"]),
                                               recursive: (entry["recursive"] as? String) == "1",
                                               platforms: platforms.sorted()))
            }
            for entry in entries(ufs["rootoverrides"]) {
                info.rootOverrides.append(RootOverride(root: text(entry["root"]), os: text(entry["os"]),
                                                       useInstead: text(entry["useinstead"]), addPath: text(entry["addpath"])))
            }
        }

        guard !info.name.isEmpty else { return nil }

        return info
    }
}

/// One entry of an app's launch configuration (`config.launch.<n>` in its
/// product info): the program Valve's client would start, relative to the
/// install folder as Steam spells it, its arguments and working folder, the
/// entry's type and the platform, architecture and beta branch it is for.
/// Untrusted text: bounded here, and validated as a path by SteamDirectStart.
struct SteamLaunchOption: Codable, Hashable, Sendable {
    var executable: String
    /// The config.launch key, not the position in the filtered array. Nil in old caches.
    var index: UInt32? = nil
    var requiredDLC: String? = nil
    var arguments = ""
    var workingDir = ""
    /// "default", "none", "option1", "server", "editor", "vr", ... ("" when absent).
    var type = ""
    var oslist = ""
    var osarch = ""
    var betaKey = ""

    /// Entries in Steam's order (numeric keys), without those that name no
    /// program or carry oversized text; at most 32.
    static func parse(_ launch: [String: Any]) -> [SteamLaunchOption] {
        let keys: [(UInt32, String)] = launch.keys.compactMap { key in
            guard let index = UInt32(key), index <= UInt32(Int32.max) else { return nil }
            return (index, key)
        }.sorted { $0.0 < $1.0 }
        var options: [SteamLaunchOption] = []
        for (index, key) in keys.prefix(32) {
            guard let entry = launch[key] as? [String: Any], let executable = entry["executable"] as? String,
                  !executable.isEmpty, executable.utf8.count <= 512 else { continue }
            func text(_ value: Any?, limit: Int = 256) -> String? {
                guard let value else { return "" }
                guard let string = value as? String, string.utf8.count <= limit else { return nil }
                return string
            }
            let config = entry["config"] as? [String: Any] ?? [:]
            guard let arguments = text(entry["arguments"], limit: 2048), let workingDir = text(entry["workingdir"], limit: 512),
                  let type = text(entry["type"]), let oslist = text(config["oslist"]), let osarch = text(config["osarch"]),
                  let betaKey = text(config["betakey"]), let requiredDLC = text(config["ownsdlc"]) else { continue }
            options.append(SteamLaunchOption(executable: executable, index: index, requiredDLC: requiredDLC,
                                             arguments: arguments, workingDir: workingDir,
                                             type: type, oslist: oslist, osarch: osarch, betaKey: betaKey))
        }
        return options
    }
}
