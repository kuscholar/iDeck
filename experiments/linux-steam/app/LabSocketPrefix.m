/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#import "LabSocketPrefix.h"
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

NSString *LabNativeSocketPrefix(NSString *temporaryDirectory) {
    if(!temporaryDirectory.isAbsolutePath)return nil;
    struct stat original;
    if(stat(temporaryDirectory.fileSystemRepresentation,&original)||!S_ISDIR(original.st_mode))return nil;
    NSMutableArray<NSString *> *candidates=[NSMutableArray arrayWithObject:temporaryDirectory];
    if([temporaryDirectory hasPrefix:@"/private/var/"])
        [candidates addObject:[temporaryDirectory substringFromIndex:@"/private".length]];
    for(NSString *directory in candidates) {
        struct stat candidate;
        if(stat(directory.fileSystemRepresentation,&candidate)||!S_ISDIR(candidate.st_mode)||
            original.st_dev!=candidate.st_dev||original.st_ino!=candidate.st_ino)continue;
        NSString *prefix=[directory stringByAppendingPathComponent:@"s"];
        char maximum[sizeof(((struct sockaddr_un *)0)->sun_path)];
        int n=snprintf(maximum,sizeof maximum,"%s%d.%u",prefix.fileSystemRepresentation,getpid(),UINT32_MAX);
        if(n>0&&(size_t)n<sizeof maximum)return prefix;
    }
    return nil;
}

char *LabCopyNativeSocketPrefix(NSString *temporaryDirectory) {
    NSString *selected=LabNativeSocketPrefix(temporaryDirectory);
    return selected?strdup(selected.fileSystemRepresentation):NULL;
}
