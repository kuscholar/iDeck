// SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
#import "LabWindowsLibrary.h"
#include <errno.h>
#ifndef IDECK_LAB_STEAM_WINDOWS_ROOT
#error Supply pinned SteamRuntimeFiles.relativeRoot, not an assumed client path
#endif
static BOOL fail(NSError **error,int code,NSString *message) {
    if(error)*error=[NSError errorWithDomain:@"iDeckLinuxLab" code:code userInfo:@{NSLocalizedDescriptionKey:message}];
    return NO;
}
static BOOL directory(NSURL *url,NSError **error) {
    NSFileManager *fm=NSFileManager.defaultManager;
    NSDictionary *info=[fm attributesOfItemAtPath:url.path error:nil];
    if(info)return [info[NSFileType] isEqual:NSFileTypeDirectory]||fail(error,ENOTDIR,@"Expected an existing Lab directory.");
    return [fm createDirectoryAtURL:url withIntermediateDirectories:NO attributes:@{NSFilePosixPermissions:@0700} error:error];
}
BOOL LabBindWindowsLibrary(NSURL *root,NSURL *documents,BOOL *created,NSError **error) {
    if(created)*created=NO;
    if(!root.isFileURL||!documents.isFileURL)return fail(error,EINVAL,@"Lab filesystem locations are unavailable.");
    NSFileManager *fm=NSFileManager.defaultManager;
    NSURL *prefix=[root URLByAppendingPathComponent:@"MadeiraPrefix" isDirectory:YES];
    NSURL *drive=[prefix URLByAppendingPathComponent:@"drive_c" isDirectory:YES];
    // Both native consumers use this dedicated prefix directly. An old
    // Documents alias can refer to the data container from a prior install.
    for (NSURL *location in @[prefix, drive]) {
        NSDictionary *info=[fm attributesOfItemAtPath:location.path error:error];
        if(!info)return NO;
        if(![info[NSFileType] isEqual:NSFileTypeDirectory])
            return fail(error,ENOTDIR,@"Expected a physical Lab prefix directory.");
    }
    NSString *client=@IDECK_LAB_STEAM_WINDOWS_ROOT;
    NSURL *folder=drive;
    for(NSString *part in [client componentsSeparatedByString:@"/"]) {
        folder=[folder URLByAppendingPathComponent:part isDirectory:YES];
        if(!directory(folder,error))return NO;
    }
    folder=[folder URLByAppendingPathComponent:@"steamapps" isDirectory:YES];
    if(!directory(folder,error))return NO;
    NSURL *settings=[folder URLByAppendingPathComponent:@"libraryfolders.vdf"];
    if(![fm attributesOfItemAtPath:settings.path error:nil]) {
        NSString *path=[[@"C:\\" stringByAppendingString:[client stringByReplacingOccurrencesOfString:@"/" withString:@"\\"]] stringByReplacingOccurrencesOfString:@"\\" withString:@"\\\\"];
        NSString *vdf=[NSString stringWithFormat:@"\"libraryfolders\"\n{\n\"0\" { \"path\" \"%@\" }\n\"1\" { \"path\" \"C:\\\\SteamLibrary\" }\n}\n",path];
        if(![[vdf dataUsingEncoding:NSUTF8StringEncoding] writeToURL:settings options:NSDataWritingWithoutOverwriting error:error])return NO;
        if(created)*created=YES;
    } // Preserve existing settings verbatim; real Dock discovery must verify them.
    return YES;
}
