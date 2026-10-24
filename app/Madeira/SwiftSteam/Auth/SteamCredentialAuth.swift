// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright 2026 Jfishin, 125hz
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
//
// Derived from Jfishin's Madeira Steam client, used in Madeira with the
// author's permission (see docs/STEAM_SIGNIN.md, "Provenance").

import Foundation
import Security

/// What Steam Guard asks for after the password is accepted.
struct SteamGuardPrompt: Equatable {
    /// A code can be typed: from the Steam mobile app (.device) or email (.email).
    var codeType: SteamGuardType?
    /// The sign-in can also be approved directly in the Steam mobile app or
    /// from a link in email; polling picks that up without a code.
    var canApprove: Bool
    /// Steam's hint for email codes (for example the address domain).
    var hint: String
}

/// Handles account name + password + Steam Guard authentication via the
/// Steam HTTPS Web API. The refresh token it returns is what Valve's own
/// client accepts for a later sign-in (see SteamSignIn.credentialsForDock()).
///
/// Madeira: the flow is split into begin / submit code / poll so the
/// interface can offer a code field and in-app approval at the same time.
/// The original port only looked at the first allowed confirmation, which
/// hid the code option whenever Steam listed app approval first. The password
/// is encrypted with Steam's RSA key before it leaves the device and is not
/// stored.
@MainActor
class SteamCredentialAuth {

    // Auth session state
    private var clientID: UInt64 = 0
    private var requestIDData: Data = Data()
    private var pollInterval: Double = 5.0
    private var steamID: UInt64 = 0
    private(set) var accountName = ""

    // MARK: - Public API

    /// Start a password sign-in. Returns nil when Steam needs no further
    /// confirmation; otherwise the Steam Guard options to present. In both
    /// cases call `pollForTokens()` next.
    func begin(username: String, password: String) async throws -> SteamGuardPrompt? {
        accountName = username

        // Step 1: Get RSA public key for password encryption
        var rsaRequest = CAuthentication_GetPasswordRSAPublicKey_Request()
        rsaRequest.accountName = username

        // GetPasswordRSAPublicKey is the one IAuthenticationService method that requires GET.
        let rsaData = try await SteamAuthAPI.call("GetPasswordRSAPublicKey", body: rsaRequest.serialize(), httpMethod: "GET")
        let rsaResponse = try CAuthentication_GetPasswordRSAPublicKey_Response.deserialize(from: rsaData)

        guard !rsaResponse.publicKeyMod.isEmpty else {
            throw SteamError.invalidCredentials
        }

        // Step 2: Encrypt password with Steam's RSA public key
        let encryptedPassword = try encryptPassword(
            password: password,
            modulus: rsaResponse.publicKeyMod,
            exponent: rsaResponse.publicKeyExp
        )

        // Step 3: Begin auth session
        var beginRequest = CAuthentication_BeginAuthSessionViaCredentials_Request()
        beginRequest.accountName = username
        beginRequest.encryptedPassword = encryptedPassword
        beginRequest.encryptionTimestamp = rsaResponse.timestamp
        beginRequest.deviceFriendlyName = SteamDevice.name
        beginRequest.platformType = 1  // k_EAuthTokenPlatformType_SteamClient: a token the Steam client can use
        beginRequest.persistence = 1   // Persistent session

        let beginData = try await SteamAuthAPI.call("BeginAuthSessionViaCredentials", body: beginRequest.serialize())
        let beginResponse = try CAuthentication_BeginAuthSessionViaCredentials_Response.deserialize(from: beginData)
        guard beginResponse.clientID != 0 else { throw SteamError.invalidCredentials }

        clientID = beginResponse.clientID
        steamID = beginResponse.steamid
        requestIDData = beginResponse.requestID
        pollInterval = Double(beginResponse.interval > 0 ? beginResponse.interval : 5.0)

        // Step 4: Steam Guard. k_EAuthSessionGuardType: 1 none, 2 email code,
        // 3 device code, 4 device confirmation, 5 email confirmation.
        let types = Set(beginResponse.allowedConfirmations.map(\.confirmationType))
        if types.isEmpty || types == [1] { return nil }
        let codeType: SteamGuardType? = types.contains(3) ? .device : (types.contains(2) ? .email : nil)
        let hint = beginResponse.allowedConfirmations.first(where: { $0.confirmationType == 2 }).map(\.associatedMessage) ?? ""
        return SteamGuardPrompt(codeType: codeType, canApprove: types.contains(4) || types.contains(5), hint: hint)
    }

    /// Submit a Steam Guard code. Polling (already running or started next)
    /// then receives the tokens.
    func submitSteamGuardCode(_ code: String, type: SteamGuardType) async throws {
        var updateRequest = CAuthentication_UpdateAuthSessionWithSteamGuardCode_Request()
        updateRequest.clientID = clientID
        updateRequest.steamid = steamID
        updateRequest.code = code.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        updateRequest.codeType = type == .email ? 2 : 3

        _ = try await SteamAuthAPI.call("UpdateAuthSessionWithSteamGuardCode", body: updateRequest.serialize())
    }

    /// Poll until Steam issues tokens (after a code, an in-app approval, or
    /// immediately when no confirmation is needed). Cancel the task to stop.
    func pollForTokens() async throws -> (refreshToken: String, accessToken: String, accountName: String) {
        let deadline = Date().addingTimeInterval(5 * 60)
        while Date() < deadline {
            try Task.checkCancellation()
            var pollRequest = CAuthentication_PollAuthSessionStatus_Request()
            pollRequest.clientID = clientID
            pollRequest.requestID = requestIDData

            let responseData = try await SteamAuthAPI.call("PollAuthSessionStatus", body: pollRequest.serialize())
            let pollResponse = try CAuthentication_PollAuthSessionStatus_Response.deserialize(from: responseData)

            if pollResponse.newClientID != 0 {
                clientID = pollResponse.newClientID
            }

            if !pollResponse.refreshToken.isEmpty && !pollResponse.accessToken.isEmpty {
                let name = pollResponse.accountName.isEmpty ? accountName : pollResponse.accountName
                return (refreshToken: pollResponse.refreshToken, accessToken: pollResponse.accessToken, accountName: name)
            }

            try await Task.sleep(nanoseconds: UInt64(max(1, pollInterval) * 1_000_000_000))
        }
        throw SteamError.authSessionExpired
    }

    // MARK: - RSA Password Encryption

    private func encryptPassword(password: String, modulus: String, exponent: String) throws -> String {
        guard let modulusData = Data(hexString: modulus),
              let exponentData = Data(hexString: exponent) else {
            throw SteamError.rsaKeyFetchFailed
        }

        let passwordData = Data(password.utf8)
        let keyData = buildRSAPublicKeyDER(modulus: modulusData, exponent: exponentData)

        let attributes: [String: Any] = [
            kSecAttrKeyType as String: kSecAttrKeyTypeRSA,
            kSecAttrKeyClass as String: kSecAttrKeyClassPublic,
            kSecAttrKeySizeInBits as String: modulusData.count * 8,
        ]

        var error: Unmanaged<CFError>?
        guard let publicKey = SecKeyCreateWithData(keyData as CFData, attributes as CFDictionary, &error) else {
            throw SteamError.rsaKeyFetchFailed
        }

        guard let encrypted = SecKeyCreateEncryptedData(publicKey, .rsaEncryptionPKCS1, passwordData as CFData, &error) else {
            throw SteamError.rsaKeyFetchFailed
        }

        return (encrypted as Data).base64EncodedString()
    }

    private func buildRSAPublicKeyDER(modulus: Data, exponent: Data) -> Data {
        func lengthField(_ length: Int) -> Data {
            if length < 128 {
                return Data([UInt8(length)])
            } else if length < 256 {
                return Data([0x81, UInt8(length)])
            } else {
                return Data([0x82, UInt8(length >> 8), UInt8(length & 0xFF)])
            }
        }

        func integerField(_ data: Data) -> Data {
            var bytes = Data([0x02])
            var payload = data
            if let first = payload.first, first & 0x80 != 0 {
                payload.insert(0x00, at: 0)
            }
            bytes.append(contentsOf: lengthField(payload.count))
            bytes.append(payload)
            return bytes
        }

        let modulusField = integerField(modulus)
        let exponentField = integerField(exponent)

        var rsaKeyBody = Data([0x30])
        let bodyLen = modulusField.count + exponentField.count
        rsaKeyBody.append(contentsOf: lengthField(bodyLen))
        rsaKeyBody.append(modulusField)
        rsaKeyBody.append(exponentField)

        return rsaKeyBody
    }
}

// MARK: - Data Hex Extension

extension Data {
    init?(hexString: String) {
        let hex = hexString.lowercased()
        guard hex.count % 2 == 0 else { return nil }

        var data = Data(capacity: hex.count / 2)
        var index = hex.startIndex
        while index < hex.endIndex {
            let nextIndex = hex.index(index, offsetBy: 2)
            guard let byte = UInt8(hex[index..<nextIndex], radix: 16) else { return nil }
            data.append(byte)
            index = nextIndex
        }
        self = data
    }

    var hexString: String {
        map { String(format: "%02x", $0) }.joined()
    }
}
