// SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
#import <Foundation/Foundation.h>
// Only isolated DOCK_STORAGE builds. Prefix metadata/alias preparation, never
// Wine initialization, account transfer, license or exclusive-writer permission.
// Native root and Documents URLs come from the host, not a guest IPC frame.
BOOL LabBindWindowsLibrary(NSURL *root,NSURL *documents,BOOL *created,NSError **error);
