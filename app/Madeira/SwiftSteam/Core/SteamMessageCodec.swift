// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright 2026 Jfishin, 125hz
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
//
// Derived from Jfishin's Madeira Steam client, used in Madeira with the
// author's permission (see docs/STEAM_SIGNIN.md, "Provenance"). Adapted for
// the owned library and downloads (docs/STEAM_LIBRARY.md).

import Foundation

/// Encodes and decodes Steam3 wire format messages over WebSocket
///
/// **Protobuf wire format** (EMsg has 0x80000000 proto mask set):
/// ```
/// [4 bytes] EMsg (uint32 LE) | 0x80000000
/// [4 bytes] Header length (uint32 LE)
/// [N bytes] CMsgProtoBufHeader (protobuf)
/// [M bytes] Message body (protobuf)
/// ```
///
/// **Non-protobuf wire format** (old-style, used by ChannelEncrypt etc.):
/// ```
/// [4 bytes] EMsg (uint32 LE, no proto mask)
/// [8 bytes] targetJobID (uint64 LE, default 0xFFFFFFFFFFFFFFFF)
/// [8 bytes] sourceJobID (uint64 LE, default 0xFFFFFFFFFFFFFFFF)
/// [M bytes] Message body
/// ```
struct SteamMessageCodec {

    /// Size of the old-style MsgHdr (after EMsg): targetJobID(8) + sourceJobID(8)
    private static let msgHdrSize = 16

    // MARK: - Outgoing Message

    struct OutgoingMessage {
        let eMsg: EMsg
        let header: CMsgProtoBufHeader
        let body: Data

        /// Serialize to Steam3 wire format (protobuf)
        func serialize() -> Data {
            let headerData = header.serialize()

            var data = Data(capacity: 8 + headerData.count + body.count)

            // EMsg with protobuf mask
            var maskedEMsg = eMsg.masked.littleEndian
            data.append(Data(bytes: &maskedEMsg, count: 4))

            // Header length
            var headerLen = UInt32(headerData.count).littleEndian
            data.append(Data(bytes: &headerLen, count: 4))

            // Header
            data.append(headerData)

            // Body
            data.append(body)

            return data
        }
    }

    // MARK: - Incoming Message

    struct IncomingMessage {
        let eMsg: EMsg
        let rawEMsg: UInt32
        let isProtobuf: Bool
        let header: CMsgProtoBufHeader
        let body: Data
    }

    // MARK: - Decode

    /// Decode a raw binary message from the WebSocket.
    /// Handles both protobuf and non-protobuf (old-style) message formats.
    static func decode(_ data: Data) throws -> IncomingMessage {
        guard data.count >= 4 else {
            SteamLog.trace("Message too small (\(data.count) bytes)")
            throw SteamError.invalidMessage
        }

        // Read EMsg (first 4 bytes, little-endian)
        let rawEMsg = data.withUnsafeBytes { ptr -> UInt32 in
            ptr.loadUnaligned(fromByteOffset: 0, as: UInt32.self)
        }
        let rawEMsgLE = UInt32(littleEndian: rawEMsg)
        let isProtobuf = (rawEMsgLE & EMsg.protoMask) != 0
        let eMsgValue = rawEMsgLE & ~EMsg.protoMask

        if isProtobuf {
            return try decodeProtobuf(data: data, eMsgValue: eMsgValue)
        } else {
            return try decodeNonProtobuf(data: data, eMsgValue: eMsgValue)
        }
    }

    /// Decode a protobuf-format message
    private static func decodeProtobuf(data: Data, eMsgValue: UInt32) throws -> IncomingMessage {
        guard data.count >= 8 else {
            throw SteamError.invalidMessage
        }

        // Read header length (bytes 4-7)
        let headerLen = data.withUnsafeBytes { ptr -> UInt32 in
            ptr.loadUnaligned(fromByteOffset: 4, as: UInt32.self)
        }
        let headerLength = Int(UInt32(littleEndian: headerLen))

        guard headerLength >= 0, data.count >= 8 + headerLength else {
            SteamLog.trace("Invalid protobuf header length \(headerLength) for \(data.count) byte message (EMsg: \(eMsgValue))")
            throw SteamError.invalidMessage
        }

        let headerData = data.subdata(in: 8..<(8 + headerLength))
        let header = try CMsgProtoBufHeader.deserialize(from: headerData)
        let body = data.subdata(in: (8 + headerLength)..<data.count)

        let eMsg = EMsg(rawValue: eMsgValue)
        if eMsg == nil {
            SteamLog.trace("Unknown protobuf EMsg \(eMsgValue) (\(body.count) bytes body)")
        }

        return IncomingMessage(
            eMsg: eMsg ?? .multi,
            rawEMsg: eMsgValue,
            isProtobuf: true,
            header: header,
            body: body
        )
    }

    /// Decode a non-protobuf (old-style) message.
    ///
    /// Two header formats exist:
    ///
    /// **Extended header** (MsgHdrExtended, headerSize=36):
    /// `[4 EMsg][1 headerSize=36][2 headerVersion=2][8 targetJobID][8 sourceJobID][1 canary][8 steamID][4 sessionID][body]`
    ///
    /// **Simple header** (MsgHdr, headerSize=20):
    /// `[4 EMsg][8 targetJobID][8 sourceJobID][body]`
    ///
    /// Detect by reading byte 4: if it equals 36 and bytes 5-6 equal version 2, it's the extended header.
    private static func decodeNonProtobuf(data: Data, eMsgValue: UInt32) throws -> IncomingMessage {
        guard data.count >= 5 else {
            SteamLog.trace("Non-protobuf message too small: \(data.count) bytes (EMsg: \(eMsgValue))")
            throw SteamError.invalidMessage
        }

        // Detect extended header: byte[4]=headerSize=36, bytes[5-6]=headerVersion=2
        let possibleHeaderSize = Int(data[4])
        let possibleVersion: UInt16 = data.count >= 7
            ? data.withUnsafeBytes { UInt16(littleEndian: $0.loadUnaligned(fromByteOffset: 5, as: UInt16.self)) }
            : 0
        let isExtended = (possibleHeaderSize == 36 && possibleVersion == 2)
        let headerSize = isExtended ? 36 : 20

        guard data.count >= headerSize else {
            SteamLog.trace("Non-protobuf message smaller than header: \(data.count) < \(headerSize) (EMsg: \(eMsgValue))")
            throw SteamError.invalidMessage
        }

        var header = CMsgProtoBufHeader()

        if isExtended {
            // MsgHdrExtended layout:
            // [4 EMsg][1 headerSize][2 headerVersion][8 targetJobID][8 sourceJobID][1 canary][8 steamID][4 sessionID]
            header.jobidTarget = data.withUnsafeBytes {
                UInt64(littleEndian: $0.loadUnaligned(fromByteOffset: 7, as: UInt64.self))
            }
            header.jobidSource = data.withUnsafeBytes {
                UInt64(littleEndian: $0.loadUnaligned(fromByteOffset: 15, as: UInt64.self))
            }
            if data.count >= 32 {
                header.steamid = data.withUnsafeBytes {
                    UInt64(littleEndian: $0.loadUnaligned(fromByteOffset: 24, as: UInt64.self))
                }
            }
            if data.count >= 36 {
                header.clientSessionid = data.withUnsafeBytes {
                    Int32(bitPattern: UInt32(littleEndian: $0.loadUnaligned(fromByteOffset: 32, as: UInt32.self)))
                }
            }
        } else {
            // Simple MsgHdr layout: [4 EMsg][8 targetJobID][8 sourceJobID]
            header.jobidTarget = data.withUnsafeBytes {
                UInt64(littleEndian: $0.loadUnaligned(fromByteOffset: 4, as: UInt64.self))
            }
            header.jobidSource = data.withUnsafeBytes {
                UInt64(littleEndian: $0.loadUnaligned(fromByteOffset: 12, as: UInt64.self))
            }
        }

        let body = data.subdata(in: headerSize..<data.count)
        let eMsg = EMsg(rawValue: eMsgValue)
        SteamLog.trace("Non-protobuf EMsg \(eMsgValue) (header=\(headerSize)B, body=\(body.count)B)")

        return IncomingMessage(
            eMsg: eMsg ?? .multi,
            rawEMsg: eMsgValue,
            isProtobuf: false,
            header: header,
            body: body
        )
    }

    // MARK: - Encode

    /// Create an outgoing message
    static func encode(
        eMsg: EMsg,
        header: CMsgProtoBufHeader,
        body: Data
    ) -> Data {
        OutgoingMessage(eMsg: eMsg, header: header, body: body).serialize()
    }

    /// Create a service method call message
    static func encodeServiceMethod(
        method: SteamServiceMethod,
        body: Data,
        steamID: UInt64 = 0,
        sessionID: Int32 = 0,
        jobID: UInt64? = nil
    ) -> Data {
        var header = CMsgProtoBufHeader()
        header.steamid = steamID
        header.clientSessionid = sessionID
        header.targetJobName = method.rawValue
        if let jobID {
            header.jobidSource = jobID
        }

        return encode(eMsg: .serviceMethodCallFromClient, header: header, body: body)
    }

    /// Create a standard client message
    static func encodeClientMessage(
        eMsg: EMsg,
        body: Data,
        steamID: UInt64 = 0,
        sessionID: Int32 = 0,
        jobID: UInt64? = nil
    ) -> Data {
        var header = CMsgProtoBufHeader()
        header.steamid = steamID
        header.clientSessionid = sessionID
        if let jobID {
            header.jobidSource = jobID
        }

        return encode(eMsg: eMsg, header: header, body: body)
    }
}
