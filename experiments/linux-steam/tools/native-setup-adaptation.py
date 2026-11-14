#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Keep the native setup reached from a Linux Lab argument user-driven."""
OLD = '!arguments.contains { $0.hasPrefix("madeira-") }'
NEW = '!arguments.contains { $0.hasPrefix("madeira-") || $0.hasPrefix("linux-") }'
def patched(source):
    assert source.count(OLD)==1,'Pinned native auto-start policy changed'
    return source.replace(OLD,NEW)
