// SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
#import <Foundation/Foundation.h>
// Only isolated DOCK_STORAGE builds. Prefix metadata preparation, never
// Wine initialization, account transfer, license or exclusive-writer permission.
// Both URLs come from the host. The Documents URL is checked for validity; its contents are untouched.
BOOL LabBindWindowsLibrary(NSURL *root,NSURL *documents,BOOL *created,NSError **error);
