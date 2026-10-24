// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright 2026 Jfishin, 125hz
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
//
// The request construction comes from the per-flow helper in Jfishin's
// Madeira Steam client (used with the author's permission, see
// docs/STEAM_SIGNIN.md, "Provenance"); the shared transport and the
// x-eresult handling are 125hz's.

import Foundation

/// IAuthenticationService over HTTPS (api.steampowered.com), shared by the
/// QR and password flows.
///
/// Steam reports most authentication failures as HTTP 200 with an
/// `x-eresult` header and an empty body. The original port ignored that
/// header, so a wrong password or Steam Guard code turned into an empty
/// session followed by minutes of polling. The header is checked here and
/// mapped to a specific error. Request and response bodies are never logged.
enum SteamAuthAPI {
    static func call(_ method: String, body: Data, httpMethod: String = "POST") async throws -> Data {
        let baseURL = "https://api.steampowered.com/IAuthenticationService/\(method)/v1/"

        // Percent-encode the base64 string. Base64 contains +, /, = — all need encoding
        // whether sent as a form body (POST) or a query parameter (GET).
        let base64 = body.base64EncodedString()
        let encoded = base64.addingPercentEncoding(withAllowedCharacters: .alphanumerics) ?? base64

        var request: URLRequest
        if httpMethod == "GET" {
            request = URLRequest(url: URL(string: "\(baseURL)?input_protobuf_encoded=\(encoded)")!)
            request.httpMethod = "GET"
        } else {
            request = URLRequest(url: URL(string: baseURL)!)
            request.httpMethod = httpMethod
            request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
            request.httpBody = "input_protobuf_encoded=\(encoded)".data(using: .utf8)
        }
        request.timeoutInterval = 20
        request.cachePolicy = .reloadIgnoringLocalCacheData

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw SteamError.authenticationFailed("Steam did not respond. Check your internet connection.")
        }
        if http.statusCode == 429 { throw SteamError.rateLimited }
        guard http.statusCode == 200 else {
            throw SteamError.authenticationFailed("Steam sign-in is unavailable right now (HTTP \(http.statusCode)).")
        }
        if let text = http.value(forHTTPHeaderField: "x-eresult"), let code = UInt32(text), code != 1 {
            SteamLog.trace("\(method) eresult=\(code)")
            throw error(for: code)
        }
        return data
    }

    /// EResult values Steam returns from the authentication service.
    static func error(for code: UInt32) -> SteamError {
        switch code {
        case 5, 18: return .invalidCredentials               // InvalidPassword, AccountNotFound
        case 65, 88: return .authenticationFailed("That Steam Guard code is not correct. Try again with a new code.")
        case 84, 87: return .rateLimited                     // RateLimitExceeded, AccountLoginDeniedThrottle
        case 17: return .accountDisabled                     // Banned
        case 9, 27: return .authSessionExpired               // FileNotFound (expired session), Expired
        default: return .authenticationFailed("Steam refused the sign-in (code \(code)).")
        }
    }
}
