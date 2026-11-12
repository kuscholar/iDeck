// SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
// Included ONLY in the explicitly configured private hybrid target.
import Foundation
import SwiftUI
import UIKit

@MainActor
@_cdecl("ideck_lab_madeira_setup_controller")
func ideckLabMadeiraSetupController() -> UnsafeMutableRawPointer {
    // Same native bootstrap and view/input lifecycle as MadeiraApp. No Linux,
    // game request, credential entry, JIT permission or session reset here.
    setenv("MTL_HUD_INSIGHTS_ENABLED", "0", 0)
    _ = ResolutionChoices.screen
    let view = ContentView()
        .modifier(ClaimGamepadEvents())
        .onAppear {
            GamepadInput.shared.start()
            HardwareInput.shared.start()
            JITNetworkShortcut.shared.restoreLeftover()
            NotificationCenter.default.post(name: Notification.Name("IDeckLinuxMadeiraSetupReady"), object: nil)
        }
    return Unmanaged.passRetained(UIHostingController(rootView: view)).toOpaque()
}

@MainActor
@_cdecl("ideck_lab_madeira_setup_open_url")
func ideckLabMadeiraSetupOpenURL(_ bytes: UnsafePointer<CChar>) {
    guard let url = URL(string: String(cString: bytes)) else { return }
    // UIKit scene callbacks route through the same handlers as MadeiraApp.
    // No raw URL logging or password/Guard automation.
    if !JITNetworkShortcut.shared.handle(url) { ShortcutRouter.shared.handle(url) }
}
