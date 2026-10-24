// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright 2026 Jfishin, 125hz
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
//
// The sign-in model is adapted from the account model built around Jfishin's
// Madeira Steam client (used with the author's permission, see
// docs/STEAM_SIGNIN.md, "Provenance"); the public API is 125hz's.

import Foundation
import SwiftUI
import UIKit

/// The public face of Steam sign-in, for other parts of the app (Madeira Dock
/// is the first user). The sign-in token lives only in the iOS Keychain
/// (SteamTokenStore: this device only, available while unlocked).
enum SteamSignIn {
    /// Posted on the main queue after a sign-in is stored or removed.
    static let didChange = Notification.Name("MadeiraSteamSignInDidChange")

    /// `env.NAME` from madeira.cfg, then the process environment. "0" is off.
    static func flag(_ name: String, default fallback: Bool) -> Bool {
        guard let value = MadeiraConfig.get("env." + name) ?? ProcessInfo.processInfo.environment[name] else {
            return fallback
        }
        return value.trimmingCharacters(in: .whitespaces) != "0"
    }

    /// `env.MADEIRA_STEAM_SIGNIN = 0` hides the sign-in button.
    static var isEnabled: Bool { flag("MADEIRA_STEAM_SIGNIN", default: true) }

    static var isSignedIn: Bool { credentialsForDock() != nil }

    static var accountName: String? { credentialsForDock()?.accountName }

    /// The stored account name and refresh token, or nil when there is no
    /// usable sign-in. A token whose own expiry time has passed counts as
    /// none. Valve still decides whether the token is accepted.
    static func credentialsForDock() -> (accountName: String, refreshToken: String)? {
        guard let tokens = SteamTokenStore().loadTokens() else { return nil }
        return usable(accountName: tokens.accountName, refreshToken: tokens.refreshToken, now: Date())
    }

    static func signOut() {
        SteamTokenStore().clearTokens()
        SteamLog.event("[steam-signin] signed out")
        notifyChange()
    }

    /// Stores a sign-in. Returns false when the Keychain did not keep it.
    static func store(accountName: String, refreshToken: String, accessToken: String) -> Bool {
        let store = SteamTokenStore()
        store.saveTokens(accountName: accountName, refreshToken: refreshToken, accessToken: accessToken, steamID: 0)
        let saved = store.loadTokens()?.refreshToken == refreshToken
        notifyChange()
        return saved
    }

    /// Pure check behind `credentialsForDock()` (host-tested).
    static func usable(accountName: String, refreshToken: String, now: Date) -> (accountName: String, refreshToken: String)? {
        let name = accountName.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !name.isEmpty, !refreshToken.isEmpty else { return nil }
        if let expiry = expiry(of: refreshToken), expiry <= now { return nil }
        return (name, refreshToken)
    }

    /// The `exp` claim of a JWT, when there is one. Anything else is nil: the
    /// token is not validated here, only an expiry it states itself is honoured.
    static func expiry(of token: String) -> Date? {
        let parts = token.split(separator: ".", omittingEmptySubsequences: false)
        guard parts.count == 3, parts[1].utf8.count <= 8192 else { return nil }
        var encoded = String(parts[1]).replacingOccurrences(of: "-", with: "+").replacingOccurrences(of: "_", with: "/")
        encoded += String(repeating: "=", count: (4 - encoded.count % 4) % 4)
        guard let data = Data(base64Encoded: encoded),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let exp = json["exp"] as? NSNumber else { return nil }
        return Date(timeIntervalSince1970: exp.doubleValue)
    }

    private static func notifyChange() {
        DispatchQueue.main.async { NotificationCenter.default.post(name: didChange, object: nil) }
    }

    // MARK: Messages

    static func message(_ error: Error) -> String {
        if let steam = error as? SteamError, let text = steam.errorDescription { return text }
        if let url = error as? URLError {
            switch url.code {
            case .notConnectedToInternet, .networkConnectionLost: return "No internet connection. Connect and try again."
            case .timedOut: return "Steam did not respond in time. Try again."
            default: return "A network error occurred (\(url.code.rawValue)). Try again."
            }
        }
        return error.localizedDescription
    }

    /// Short, credential-free reason for the log.
    static func reason(_ error: Error) -> String {
        switch error {
        case SteamError.invalidCredentials: return "credentials"
        case SteamError.rateLimited: return "rate-limited"
        case SteamError.accountDisabled: return "disabled"
        case SteamError.authSessionExpired: return "expired"
        case SteamError.qrCodeExpired: return "qr-expired"
        case SteamError.rsaKeyFetchFailed: return "rsa"
        case SteamError.protobufError: return "protobuf"
        case SteamError.authenticationFailed: return "refused"
        case let url as URLError: return "url-\(url.code.rawValue)"
        default: return String(describing: type(of: error))
        }
    }
}

/// State of the sign-in sheet: password + Steam Guard (code or in-app
/// approval, offered together when Steam allows both) or a QR code.
@MainActor
final class SteamSignInModel: ObservableObject {
    static let shared = SteamSignInModel()

    enum SignInMethod: String { case password, qr }

    @Published private(set) var accountName: String?
    @Published private(set) var qrImage: UIImage?
    @Published private(set) var qrLink: URL?
    @Published private(set) var guardPrompt: SteamGuardPrompt?
    @Published private(set) var signInBusy = false
    @Published var signInError: String?

    private let credentials = SteamCredentialAuth()
    private let qr = SteamQRAuth()
    private var signInTask: Task<Void, Never>?

    var signedIn: Bool { accountName != nil }

    init() { refresh() }

    func refresh() { accountName = SteamSignIn.accountName }

    func beginQR() {
        cancelSignIn()
        signInBusy = true; signInError = nil
        qr.onNewChallenge = { [weak self] image, url in
            self?.qrImage = image; self?.qrLink = URL(string: url)
        }
        signInTask = Task { @MainActor in
            do {
                let image = try await qr.beginQRAuth()
                qrImage = image
                if case .showingQR(_, let url) = qr.authState { qrLink = URL(string: url) }
                signInBusy = false
                let tokens = try await qr.pollForConfirmation()
                finishSignIn(account: tokens.accountName, refresh: tokens.refreshToken, access: tokens.accessToken, method: "qr")
            } catch is CancellationError {
            } catch {
                if !Task.isCancelled { failSignIn(error, method: "qr") }
            }
        }
    }

    func signIn(account: String, password: String) {
        cancelSignIn()
        let name = account.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !name.isEmpty, !password.isEmpty else { return }
        signInBusy = true; signInError = nil
        signInTask = Task { @MainActor in
            do {
                let prompt = try await credentials.begin(username: name, password: password)
                guardPrompt = prompt
                signInBusy = prompt == nil
                let tokens = try await credentials.pollForTokens()
                finishSignIn(account: tokens.accountName, refresh: tokens.refreshToken, access: tokens.accessToken, method: "password")
            } catch is CancellationError {
            } catch {
                if !Task.isCancelled { failSignIn(error, method: "password") }
            }
        }
    }

    /// Submit a Steam Guard code; the running poll receives the tokens.
    func submitGuardCode(_ code: String) {
        guard let type = guardPrompt?.codeType, !code.trimmingCharacters(in: .whitespaces).isEmpty else { return }
        signInBusy = true; signInError = nil
        Task { @MainActor in
            do { try await credentials.submitSteamGuardCode(code, type: type) }
            catch { signInError = SteamSignIn.message(error); signInBusy = false }
        }
    }

    func cancelSignIn() {
        signInTask?.cancel(); signInTask = nil
        qr.cancel(); qr.onNewChallenge = nil
        qrImage = nil; qrLink = nil; guardPrompt = nil; signInBusy = false
    }

    func signOut() {
        cancelSignIn()
        SteamSignIn.signOut()
        refresh()
    }

    private func failSignIn(_ error: Error, method: String) {
        signInError = SteamSignIn.message(error)
        signInBusy = false; guardPrompt = nil; qrImage = nil; qrLink = nil
        SteamLog.event("[steam-signin] sign-in failed method=\(method) reason=\(SteamSignIn.reason(error))")
    }

    private func finishSignIn(account: String, refresh: String, access: String, method: String) {
        // This runs inside the sign-in task: clear its state without cancelling it.
        signInTask = nil; qr.onNewChallenge = nil
        qrImage = nil; qrLink = nil; guardPrompt = nil; signInBusy = false
        guard SteamSignIn.store(accountName: account, refreshToken: refresh, accessToken: access) else {
            signInError = "Steam accepted the sign-in, but Madeira could not save it in this device's Keychain. Check the app's signing and try again."
            SteamLog.event("[steam-signin] sign-in keychain-store failed method=\(method)")
            return
        }
        signInError = nil
        self.refresh()
        SteamLog.event("[steam-signin] signed in method=\(method)")
    }
}
