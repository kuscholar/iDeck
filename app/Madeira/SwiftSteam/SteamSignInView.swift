// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright 2026 125hz
// Madeira Converter Exception: see LICENSE-EXCEPTION.md

import SwiftUI
import UIKit

/// Steam sign-in sheet: account name + password with Steam Guard (a code and
/// in-app approval, offered together when Steam allows both), or a QR code
/// scanned with the Steam app (default on iPad). When signed in it shows the
/// account and Sign out.
struct SteamSignInView: View {
    @ObservedObject private var steam = SteamSignInModel.shared
    @Environment(\.dismiss) private var dismiss
    @State private var method: SteamSignInModel.SignInMethod = UIDevice.current.userInterfaceIdiom == .pad ? .qr : .password
    @State private var account = ""
    @State private var password = ""
    @State private var code = ""
    @FocusState private var focus: Field?
    private enum Field { case account, password, code }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    VStack(alignment: .leading, spacing: 8) {
                        Label("Sign in to Steam", systemImage: "person.crop.circle.fill").font(.title2.bold())
                        Text("Madeira keeps a Steam sign-in so it can start your Steam games with your own account.")
                            .foregroundStyle(.secondary)
                    }.padding(.vertical, 4)
                }
                if let name = steam.accountName {
                    signedInSection(name)
                } else if let prompt = steam.guardPrompt {
                    guardSection(prompt)
                } else {
                    Section {
                        Picker("Sign-in method", selection: $method) {
                            Text("Password").tag(SteamSignInModel.SignInMethod.password)
                            Text("QR code").tag(SteamSignInModel.SignInMethod.qr)
                        }.pickerStyle(.segmented)
                    }
                    if method == .password { passwordSection } else { qrSection }
                }
                if let error = steam.signInError {
                    Section { Label(error, systemImage: "exclamationmark.triangle.fill").foregroundStyle(.red) }
                }
                Section {
                    Text("Madeira signs in with Steam directly. Your password is sent only to Steam and is never stored. A sign-in token is kept in this device's Keychain until you sign out.")
                        .font(.footnote).foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Steam").navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(steam.signedIn ? "Done" : "Cancel") { steam.cancelSignIn(); dismiss() }
                }
            }
            .onAppear {
                steam.refresh(); steam.signInError = nil
                guard !steam.signedIn else { return }
                if method == .qr { steam.beginQR() } else { focus = .account }
            }
            .onChange(of: method) { _, value in
                steam.signInError = nil
                guard !steam.signedIn else { return }
                if value == .qr { steam.beginQR() } else { steam.cancelSignIn(); focus = .account }
            }
            .onChange(of: steam.accountName) { _, name in if name != nil { dismiss() } }
            .onChange(of: steam.guardPrompt) { _, prompt in if prompt?.codeType != nil { focus = .code } }
            .onDisappear { if !steam.signedIn { steam.cancelSignIn() } }
        }
    }

    private func signedInSection(_ name: String) -> some View {
        Section {
            LabeledContent("Account", value: name)
            Button("Sign out", role: .destructive) { steam.signOut() }
        } footer: {
            Text("Signing out removes the token from this device's Keychain.")
        }
    }

    private var passwordSection: some View {
        Section {
            TextField("Steam account name", text: $account)
                .textContentType(.username).textInputAutocapitalization(.never).autocorrectionDisabled()
                .focused($focus, equals: .account).submitLabel(.next).onSubmit { focus = .password }
            SecureField("Password", text: $password)
                .textContentType(.password).focused($focus, equals: .password)
                .submitLabel(.go).onSubmit(submit)
            Button(action: submit) {
                HStack {
                    Text("Sign in").fontWeight(.semibold)
                    if steam.signInBusy { Spacer(); ProgressView() }
                }
            }.disabled(account.trimmingCharacters(in: .whitespaces).isEmpty || password.isEmpty || steam.signInBusy)
        } footer: {
            Text("Use your Steam account name, which can differ from your email address.")
        }
    }

    private func submit() {
        guard !account.isEmpty, !password.isEmpty, !steam.signInBusy else { return }
        steam.signIn(account: account, password: password)
        password = ""
    }

    private func guardSection(_ prompt: SteamGuardPrompt) -> some View {
        Section {
            if let type = prompt.codeType {
                Text(type == .device
                     ? "Enter the Steam Guard code shown in the Steam app on your phone."
                     : "Enter the code Steam sent to your email" + (prompt.hint.isEmpty ? "." : " (\(prompt.hint))."))
                TextField("Code", text: $code)
                    .textContentType(.oneTimeCode).textInputAutocapitalization(.characters).autocorrectionDisabled()
                    .font(.title3.monospaced()).focused($focus, equals: .code)
                    .submitLabel(.go).onSubmit { steam.submitGuardCode(code) }
                Button {
                    steam.submitGuardCode(code)
                } label: {
                    HStack { Text("Continue").fontWeight(.semibold); if steam.signInBusy { Spacer(); ProgressView() } }
                }.disabled(code.trimmingCharacters(in: .whitespaces).count < 5 || steam.signInBusy)
            }
            if prompt.canApprove {
                HStack(spacing: 12) {
                    ProgressView()
                    Text(prompt.codeType == nil
                         ? "Approve this sign-in in the Steam app on your phone."
                         : "Or approve this sign-in in the Steam app.")
                        .foregroundStyle(.secondary)
                }
            }
            Button("Start over", role: .cancel) { code = ""; steam.cancelSignIn() }
        } header: { Text("Steam Guard") }
    }

    private var qrSection: some View {
        Section {
            if let image = steam.qrImage {
                Image(uiImage: image).interpolation(.none).resizable().scaledToFit()
                    .frame(maxWidth: 240).padding(12)
                    .background(Color.white, in: RoundedRectangle(cornerRadius: 14))
                    .frame(maxWidth: .infinity)
                    .accessibilityLabel("Steam sign-in QR code")
                Text("On another device, open the Steam app, go to Steam Guard, and scan this code.")
                if let link = steam.qrLink {
                    Button { UIApplication.shared.open(link) } label: {
                        Label("Open in the Steam app on this device", systemImage: "arrow.up.forward.app")
                    }
                }
                HStack(spacing: 12) { ProgressView(); Text("Waiting for approval…").foregroundStyle(.secondary) }
            } else if steam.signInBusy {
                HStack(spacing: 12) { ProgressView(); Text("Getting a sign-in code…").foregroundStyle(.secondary) }
            } else {
                Button("Get a new code") { steam.beginQR() }
            }
        }
    }
}
