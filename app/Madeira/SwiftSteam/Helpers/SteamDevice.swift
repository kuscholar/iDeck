// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright 2026 Jfishin, 125hz
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
//
// Derived from Jfishin's Madeira Steam client, used in Madeira with the
// author's permission (see docs/STEAM_SIGNIN.md, "Provenance").

import Foundation
#if canImport(UIKit)
import UIKit
#endif

/// Cross-platform device name — `Host.current()` doesn't exist on iOS.
enum SteamDevice {
    static var name: String {
        #if canImport(UIKit)
        return UIDevice.current.name
        #else
        return Host.current().localizedName ?? "SwiftSteam"
        #endif
    }
}
