// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright 2026 Jfishin, 125hz
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
//
// Derived from Jfishin's Madeira Steam client, used in Madeira with the
// author's permission (see docs/STEAM_SIGNIN.md, "Provenance").

import Foundation
import CoreImage
#if canImport(AppKit)
import AppKit
typealias SteamImage = NSImage
#elseif canImport(UIKit)
import UIKit
typealias SteamImage = UIImage
#endif

/// Handles QR code authentication flow with Steam via HTTPS Steam Web API.
/// Auth uses api.steampowered.com directly — no CM WebSocket connection needed for this step.
/// The refresh token it returns is kept in the Keychain by SteamSignInModel.
@MainActor
class SteamQRAuth {

    enum QRAuthState: Equatable {
        case idle
        case generating
        case showingQR(image: SteamImage, url: String)
        case polling
        case success(accountName: String)
        case expired
        case failed(String)
    }

    private(set) var authState: QRAuthState = .idle
    /// Madeira: called when Steam rotates the challenge during polling, so the
    /// interface can replace the displayed code (and its same-device link).
    var onNewChallenge: ((SteamImage, String) -> Void)?

    // Auth session state
    private var clientID: UInt64 = 0
    private var requestIDData: Data = Data()
    private var pollInterval: Double = 5.0

    // MARK: - Public API

    /// Start QR auth: calls Steam HTTPS API, returns QR code image.
    /// Follow with pollForConfirmation() to wait for user to scan.
    func beginQRAuth() async throws -> SteamImage {
        authState = .generating

        var request = CAuthentication_BeginAuthSessionViaQR_Request()
        request.deviceFriendlyName = SteamDevice.name
        request.platformType = 1  // k_EAuthTokenPlatformType_SteamClient: a token the Steam client can use

        let responseData = try await callSteamAuthAPI(method: "BeginAuthSessionViaQR", body: request.serialize())
        let response = try CAuthentication_BeginAuthSessionViaQR_Response.deserialize(from: responseData)

        guard !response.challengeURL.isEmpty else {
            authState = .failed("No challenge URL received")
            throw SteamError.authenticationFailed("Empty challenge URL from Steam")
        }

        clientID = response.clientID
        requestIDData = response.requestID
        pollInterval = Double(response.interval > 0 ? response.interval : 5.0)

        let qrImage = generateQRCode(from: response.challengeURL)
        authState = .showingQR(image: qrImage, url: response.challengeURL)
        return qrImage
    }

    /// Poll Steam HTTPS API until user scans QR. Returns tokens on success.
    func pollForConfirmation() async throws -> (refreshToken: String, accessToken: String, accountName: String) {
        authState = .polling

        let maxAttempts = 120  // ~10 minutes at 5-second intervals
        for _ in 0..<maxAttempts {
            try Task.checkCancellation()
            var pollRequest = CAuthentication_PollAuthSessionStatus_Request()
            pollRequest.clientID = clientID
            pollRequest.requestID = requestIDData

            let responseData = try await callSteamAuthAPI(method: "PollAuthSessionStatus", body: pollRequest.serialize())
            let pollResponse = try CAuthentication_PollAuthSessionStatus_Response.deserialize(from: responseData)

            // Update client ID if it changed (Steam may rotate it)
            if pollResponse.newClientID != 0 {
                clientID = pollResponse.newClientID
            }

            // Update QR image if challenge URL changed
            if !pollResponse.newChallengeURL.isEmpty {
                let newImage = generateQRCode(from: pollResponse.newChallengeURL)
                authState = .showingQR(image: newImage, url: pollResponse.newChallengeURL)
                onNewChallenge?(newImage, pollResponse.newChallengeURL)
            }

            if !pollResponse.refreshToken.isEmpty && !pollResponse.accessToken.isEmpty {
                let accountName = pollResponse.accountName
                authState = .success(accountName: accountName)
                return (refreshToken: pollResponse.refreshToken, accessToken: pollResponse.accessToken, accountName: accountName)
            }

            try await Task.sleep(nanoseconds: UInt64(pollInterval * 1_000_000_000))
        }

        authState = .expired
        throw SteamError.qrCodeExpired
    }

    func cancel() {
        authState = .idle
        clientID = 0
        requestIDData = Data()
    }

    // MARK: - HTTPS Steam Auth API

    /// POST to IAuthenticationService HTTPS endpoint.
    /// Steam returns a binary protobuf response when input_protobuf_encoded is used.
    func callSteamAuthAPI(method: String, body: Data) async throws -> Data {
        // Madeira: shared transport; checks Steam's x-eresult header.
        try await SteamAuthAPI.call(method, body: body)
    }

    // MARK: - QR Code Generation

    private func generateQRCode(from string: String) -> SteamImage {
        let data = string.data(using: .ascii)
        let filter = CIFilter(name: "CIQRCodeGenerator")!
        filter.setValue(data, forKey: "inputMessage")
        filter.setValue("M", forKey: "inputCorrectionLevel")

        let scale = CGAffineTransform(scaleX: 8, y: 8)
        guard let ciImage = filter.outputImage else {
            #if canImport(AppKit)
            return NSImage(size: NSSize(width: 200, height: 200))
            #else
            return UIImage()
            #endif
        }
        let scaledImage = ciImage.transformed(by: scale)

        #if canImport(AppKit)
        let rep = NSCIImageRep(ciImage: scaledImage)
        let nsImage = NSImage(size: rep.size)
        nsImage.addRepresentation(rep)
        return nsImage
        #else
        // UIImage(ciImage:) stays CIImage-backed and renders blank in SwiftUI —
        // materialize to a CGImage.
        guard let cg = CIContext().createCGImage(scaledImage, from: scaledImage.extent) else {
            return UIImage()
        }
        return UIImage(cgImage: cg)
        #endif
    }
}
