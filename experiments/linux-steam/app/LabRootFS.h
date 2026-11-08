/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#import <Foundation/Foundation.h>
/* Before guest startup, on a worker. Never replaces an existing root. Input is
 * a clean install image, not an account backup; expected digest comes from the
 * build, not from a user-supplied sidecar. No raw path/progress contents logged. */
NSURL *LabPrepareSteamRoot(NSURL *lab, NSURL *input, NSString *expected, NSError **error);
