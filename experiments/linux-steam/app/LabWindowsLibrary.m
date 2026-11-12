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
    BOOL isDir=NO;
    if(![fm fileExistsAtPath:drive.path isDirectory:&isDir]||!isDir)return fail(error,ENOENT,@"Prepare the experimental Windows storage layout first.");
    if(!directory(documents,error))return NO;
    NSURL *alias=[documents URLByAppendingPathComponent:@"wine" isDirectory:YES];
    NSDictionary *old=[fm attributesOfItemAtPath:alias.path error:nil];
    if(old) {
        if(![old[NSFileType] isEqual:NSFileTypeSymbolicLink]||
           ![alias.URLByResolvingSymlinksInPath.path isEqual:prefix.URLByResolvingSymlinksInPath.path])
            return fail(error,EEXIST,@"Existing Windows prefix retained. No migration was performed.");
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
    if(!old&&![fm createSymbolicLinkAtURL:alias withDestinationURL:prefix error:error])return NO;
    return YES;
}
