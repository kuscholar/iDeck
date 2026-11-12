// SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
import Foundation

// The Lab owns this one binding. Production installers still check every
// destination normally; an unrelated prefix is returned without adaptation.
enum LabMadeiraPrefix {
    static func canonical(_ prefix: URL, documents: URL, linuxRoot: URL) -> URL {
        let binding = documents.appendingPathComponent("wine", isDirectory: true)
        let expected = linuxRoot.appendingPathComponent("MadeiraPrefix", isDirectory: true)
            .resolvingSymlinksInPath().standardizedFileURL
        guard prefix.standardizedFileURL == binding.standardizedFileURL,
              binding.resolvingSymlinksInPath().standardizedFileURL == expected else { return prefix }
        return expected
    }

    static func canonical(_ prefix: URL) -> URL {
        let fm = FileManager.default
        let documents = fm.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let root = fm.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("iDeckLinuxLab/LinuxSteamRootFS", isDirectory: true)
        return canonical(prefix, documents: documents, linuxRoot: root)
    }
}
