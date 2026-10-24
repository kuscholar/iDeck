// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright 2026 Jfishin, 125hz
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
//
// Derived from Jfishin's Madeira Steam client, used in Madeira with the
// author's permission (see docs/STEAM_SIGNIN.md, "Provenance").

import Foundation
import Security

/// Securely stores Steam authentication tokens in the Keychain
class SteamTokenStore {
    private let serviceName = "madeira.steam.tokens"

    struct StoredTokens: Codable {
        var accountName: String
        var refreshToken: String
        var accessToken: String
        var steamID: UInt64
        var savedAt: Date
    }

    // MARK: - Public API

    /// Save tokens to Keychain
    func saveTokens(accountName: String, refreshToken: String, accessToken: String, steamID: UInt64) {
        let tokens = StoredTokens(
            accountName: accountName,
            refreshToken: refreshToken,
            accessToken: accessToken,
            steamID: steamID,
            savedAt: Date()
        )

        guard let data = try? JSONEncoder().encode(tokens) else {
            SteamLog.trace("Failed to encode tokens for storage")
            return
        }

        // Delete existing entry first
        deleteKeychainItem()

        // Add new entry
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: serviceName,
            kSecAttrAccount as String: "steam_tokens",
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        ]

        let status = SecItemAdd(query as CFDictionary, nil)
        if status == errSecSuccess {
            SteamLog.trace("Tokens saved to Keychain")
        } else {
            SteamLog.trace("Failed to save tokens to Keychain: \(status)")
        }
    }

    /// Load tokens from Keychain
    func loadTokens() -> StoredTokens? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: serviceName,
            kSecAttrAccount as String: "steam_tokens",
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        guard status == errSecSuccess,
              let data = result as? Data,
              let tokens = try? JSONDecoder().decode(StoredTokens.self, from: data) else {
            return nil
        }

        return tokens
    }

    /// Clear all stored tokens (sign out)
    func clearTokens() {
        deleteKeychainItem()
        SteamLog.trace("Tokens cleared from Keychain")
    }

    /// Check if we have stored tokens
    var hasTokens: Bool {
        loadTokens() != nil
    }

    // MARK: - Private

    private func deleteKeychainItem() {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: serviceName,
            kSecAttrAccount as String: "steam_tokens"
        ]
        SecItemDelete(query as CFDictionary)
    }
}
