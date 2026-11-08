/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#import <Foundation/Foundation.h>
/* Absolute app-owned socket prefix, independent of mutable native cwd.
 * Only the existing /private/var -> /var alias may shorten a path, and only
 * after verifying both directory paths identify the same inode/device. */
NSString *LabNativeSocketPrefix(NSString *temporaryDirectory);

/* malloc-owned bytes; the caller must keep them for every guest thread using
 * sock_tmp_prefix. NSString representation bytes do not outlive their pool. */
char *LabCopyNativeSocketPrefix(NSString *temporaryDirectory);
