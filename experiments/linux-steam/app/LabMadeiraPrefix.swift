// SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
import Foundation

// Only the isolated Lab compiles this adapter. Its default Windows
// prefix lives beside the Linux root and does not use Documents/wine.
enum LabMadeiraPrefix {
    static func canonical(_ prefix: URL, documents: URL, linuxRoot: URL) -> URL {
        let binding = documents.appendingPathComponent("wine", isDirectory: true)
        guard prefix.standardizedFileURL == binding.standardizedFileURL else { return prefix }
        return linuxRoot.appendingPathComponent("MadeiraPrefix", isDirectory: true)
            .resolvingSymlinksInPath().standardizedFileURL
    }

    static func canonical(_ prefix: URL) -> URL {
        let fm = FileManager.default
        let documents = fm.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let root = fm.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("iDeckLinuxLab/LinuxSteamRootFS", isDirectory: true)
        return canonical(prefix, documents: documents, linuxRoot: root)
    }
}
