// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md

// Madeira's JIT helper: a classic app extension that Madeira starts by its bundle ID
// (app/Madeira/JITBuiltInHost.swift), so a sideloader's renamed install still finds it.
// One MadeiraJITRequest per extension request, answered when the request completes.

import Foundation
#if !targetEnvironment(simulator)
import StikJIT
#endif

#if targetEnvironment(simulator)
private struct DDIPaths {
    static func `default`(in directory: URL) -> DDIPaths { DDIPaths() }
}

private enum StikJIT {
    enum Script { case customBase64(String) }
    struct DeviceSecurityState { let isTXMPresent: Bool? }
    enum PreparationStage { case unavailable }
    enum JITReadiness {
        case unreachable(reason: String)
        case preparationFailed(reason: String)
        case ready(DeviceSecurityState)
    }

    static var isTXMPresent: Bool? { nil }
    static func prepareDevice(pairingFile: URL, paths: DDIPaths,
                              progress: (PreparationStage) -> Void) -> JITReadiness {
        .unreachable(reason: "Built-in JIT is available only on a physical device.")
    }
    static func enableJIT(targetPID: Int32, pairingFile: URL, ddiPaths: DDIPaths,
                          script: Script, forceScript: Bool,
                          preparationProgress: (PreparationStage) -> Void,
                          progress: (String) -> Void) throws {
        throw NSError(domain: "MadeiraJITHelper", code: 100,
                      userInfo: [NSLocalizedDescriptionKey:
                        "Built-in JIT is available only on a physical device."])
    }
    static func resetCachedDDI(at paths: DDIPaths) throws {}
}
#endif

private enum MadeiraJITWork {
    /// One request at a time, as the XPC handler ran them before.
    static let queue = DispatchQueue(label: "com.willfaust.madeora.jit-helper")

    static func handle(_ request: MadeiraJITRequest) -> MadeiraJITRequest.Response {
        let manager = FileManager.default
        let root = manager.urls(for: .libraryDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("StikJIT", isDirectory: true)
        let paths = DDIPaths.default(in: root)

        do {
            try manager.createDirectory(at: root, withIntermediateDirectories: true)
            if request.operation == .resetDDI {
                try StikJIT.resetCachedDDI(at: paths)
                return .init(success: true,
                             message: "Developer Disk Image cache reset.",
                             txmPresent: StikJIT.isTXMPresent)
            }

            guard let pairingData = request.pairingData, !pairingData.isEmpty else {
                throw NSError(domain: "MadeiraJITHelper", code: 1,
                              userInfo: [NSLocalizedDescriptionKey: "The pairing file was not provided."])
            }
            let pairingURL = root.appendingPathComponent("pairingFile-\(UUID().uuidString).plist")
            try pairingData.write(to: pairingURL, options: .atomic)
            defer { try? manager.removeItem(at: pairingURL) }

            switch request.operation {
            case .prepare:
                let readiness = StikJIT.prepareDevice(
                    pairingFile: pairingURL, paths: paths,
                    progress: { NSLog("[MadeiraJIT] prepare: %@", String(describing: $0)) })
                switch readiness {
                case .ready(let security):
                    return .init(success: true,
                                 message: "LocalDevVPN is reachable and the Developer Disk Image is ready.",
                                 txmPresent: security.isTXMPresent)
                case .unreachable(let reason), .preparationFailed(let reason):
                    return .init(success: false, message: reason,
                                 txmPresent: StikJIT.isTXMPresent)
                @unknown default:
                    return .init(success: false,
                                 message: "StikJIT returned an unknown preparation state.",
                                 txmPresent: StikJIT.isTXMPresent)
                }
            case .enable:
                guard let targetPID = request.targetPID,
                      let scriptBase64 = request.scriptBase64,
                      !scriptBase64.isEmpty else {
                    throw NSError(domain: "MadeiraJITHelper", code: 2,
                                  userInfo: [NSLocalizedDescriptionKey:
                                    "The target process or Madeira JIT script was not provided."])
                }
                try StikJIT.enableJIT(
                    targetPID: targetPID,
                    pairingFile: pairingURL,
                    ddiPaths: paths,
                    script: .customBase64(scriptBase64),
                    forceScript: true,
                    preparationProgress: {
                        NSLog("[MadeiraJIT] prepare: %@", String(describing: $0))
                    },
                    progress: { NSLog("[MadeiraJIT] %@", $0) })
                return .init(success: true,
                             message: "Madeira detached cleanly from its built-in JIT helper.",
                             txmPresent: StikJIT.isTXMPresent)
            case .resetDDI:
                preconditionFailure("Handled above")
            }
        } catch {
            return .init(success: false, message: error.localizedDescription,
                         txmPresent: StikJIT.isTXMPresent)
        }
    }
}

/// NSExtensionPrincipalClass (Info.plist). The request arrives as JSON in the first input
/// item; the response goes back as JSON in the item the request completes with. Enable
/// completes only when Madeira's script has detached, so the request, and this process,
/// last as long as the debugger does.
@objc(MadeiraJITHelperHandler)
final class MadeiraJITHelperHandler: NSObject, NSExtensionRequestHandling {
    func beginRequest(with context: NSExtensionContext) {
        let info = (context.inputItems.first as? NSExtensionItem)?.userInfo
        let data = info?[MadeiraJITRequest.itemKey] as? Data
        MadeiraJITWork.queue.async {
            let response: MadeiraJITRequest.Response
            if let data, let request = try? JSONDecoder().decode(MadeiraJITRequest.self, from: data) {
                response = MadeiraJITWork.handle(request)
            } else {
                response = .init(success: false, message: "Madeira's JIT helper received no request.",
                                 txmPresent: nil)
            }
            let item = NSExtensionItem()
            item.userInfo = [MadeiraJITRequest.Response.itemKey: (try? JSONEncoder().encode(response)) ?? Data()]
            context.completeRequest(returningItems: [item], completionHandler: nil)
        }
    }
}
