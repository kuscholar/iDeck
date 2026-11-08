/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#import "LabRootFS.h"
#include <errno.h>
#include <stdlib.h>
#if IDECK_LAB_STEAM_FRONTEND
#import <CommonCrypto/CommonDigest.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include "tools/fakefs.h"

static NSURL *failRoot(NSError **error, NSInteger code, NSString *message) {
    if (error) *error=[NSError errorWithDomain:@"iDeckLinuxLab.Root" code:code userInfo:@{NSLocalizedDescriptionKey:message}];
    return nil;
}
static BOOL digestSyntax(NSString *value) {
    return value.length==64 && [value rangeOfCharacterFromSet:[[NSCharacterSet characterSetWithCharactersInString:@"0123456789abcdef"] invertedSet]].location==NSNotFound;
}
NSURL *LabPrepareSteamRoot(NSURL *lab, NSURL *input, NSString *expected, NSError **error) {
    NSFileManager *fm=NSFileManager.defaultManager;
    if (!digestSyntax(expected)) return failRoot(error,EINVAL,@"This build has no verified Linux image pin; no guest started.");
    NSURL *root=[lab URLByAppendingPathComponent:@"LinuxSteamRootFS" isDirectory:YES];
    if ([fm fileExistsAtPath:root.path]) {
        NSString *pin=[NSString stringWithContentsOfURL:[root URLByAppendingPathComponent:@"install-image.sha256"] encoding:NSUTF8StringEncoding error:nil];
        BOOL directory=NO;
        if (![pin isEqual:expected] || ![fm fileExistsAtPath:[root URLByAppendingPathComponent:@"data"].path isDirectory:&directory] || !directory ||
            ![fm fileExistsAtPath:[root URLByAppendingPathComponent:@"meta.db"].path])
            return failRoot(error,EINVAL,@"An existing Linux root needs explicit review; it was preserved.");
        return root; // Steam updates/login remain in this app's own writable root.
    }
    if (![fm createDirectoryAtURL:lab withIntermediateDirectories:YES attributes:@{NSFilePosixPermissions:@0700} error:error]) return nil;
    NSURL *stage=[lab URLByAppendingPathComponent:[@"install-" stringByAppendingString:NSUUID.UUID.UUIDString] isDirectory:YES];
    if (![fm createDirectoryAtURL:stage withIntermediateDirectories:NO attributes:@{NSFilePosixPermissions:@0700} error:error]) return nil;
    NSURL *sealed=[stage URLByAppendingPathComponent:@"verified.tar.gz"];
    int source=open(input.fileSystemRepresentation,O_RDONLY|O_NOFOLLOW|O_NONBLOCK);
    struct stat before={0},after={0};
    BOOL ok=source>=0 && !fstat(source,&before) && S_ISREG(before.st_mode) && before.st_size>0 && (uint64_t)before.st_size<=4ULL*1024*1024*1024;
    int output=ok?open(sealed.fileSystemRepresentation,O_WRONLY|O_CREAT|O_EXCL,0600):-1;
    ok=ok&&output>=0;
    CC_SHA256_CTX hash; CC_SHA256_Init(&hash);
    unsigned char buffer[262144]; uint64_t bytes=0;
    while (ok) {
        ssize_t got=read(source,buffer,sizeof buffer);
        if (got<0) { if(errno==EINTR)continue;ok=NO;break; }
        if (!got) break;
        bytes+=(uint64_t)got;
        if(bytes>(uint64_t)before.st_size){ok=NO;break;}
        CC_SHA256_Update(&hash,buffer,(CC_LONG)got);
        size_t used=0;
        while(used<(size_t)got){ssize_t sent=write(output,buffer+used,(size_t)got-used);if(sent<0&&errno==EINTR)continue;if(sent<=0){ok=NO;break;}used+=(size_t)sent;}
    }
    if (ok) ok=!fstat(source,&after) && bytes==(uint64_t)before.st_size && before.st_size==after.st_size &&
        before.st_mtimespec.tv_sec==after.st_mtimespec.tv_sec && before.st_mtimespec.tv_nsec==after.st_mtimespec.tv_nsec && !fsync(output);
    if(source>=0)close(source);if(output>=0)close(output);
    unsigned char digest[CC_SHA256_DIGEST_LENGTH];CC_SHA256_Final(digest,&hash);
    NSMutableString *actual=[NSMutableString new];for(unsigned i=0;i<sizeof digest;i++)[actual appendFormat:@"%02x",digest[i]];
    if(!ok||![actual isEqual:expected]){
        [fm removeItemAtURL:stage error:nil];return failRoot(error,EIO,@"Linux image read or integrity check failed; existing data was preserved.");
    }
    NSURL *prepared=[stage URLByAppendingPathComponent:@"root" isDirectory:YES];
    struct fakefsify_error fsError={0};
    // The pinned FIFO helper changes process cwd; serialize before any guest
    // runs and restore our original cwd even if the import reports an error.
    int original=open(".",O_RDONLY|O_DIRECTORY);
    BOOL imported=original>=0 && fakefs_import(sealed.fileSystemRepresentation,prepared.fileSystemRepresentation,&fsError,(struct progress){0});
    BOOL restored=original>=0 && !fchdir(original);if(original>=0)close(original);
    NSDictionary *receipt=@{@"image_sha256":expected, @"imported":@(imported), @"cwd_restored":@(restored),
        @"error_type":@(fsError.type), @"error_code":@(fsError.code), @"source_line":@(fsError.line)};
    // Categorical metadata only; never archive paths, account data or payloads.
    NSData *receiptData=[NSJSONSerialization dataWithJSONObject:receipt options:NSJSONWritingPrettyPrinted error:nil];
    [receiptData writeToURL:[lab URLByAppendingPathComponent:@"last-root-import.json"] options:NSDataWritingAtomic error:nil];
    if(!imported||!restored){
        NSInteger code=fsError.code?:EIO;
        NSString *description=[NSString stringWithFormat:@"Linux image import failed (type %d, code %d, line %d, cwd %d). No guest started; restart the Lab before retrying.",fsError.type,fsError.code,fsError.line,restored];
        free(fsError.message);[fm removeItemAtURL:stage error:nil];
        return failRoot(error,code,description);
    }
    if (![expected writeToURL:[prepared URLByAppendingPathComponent:@"install-image.sha256"] atomically:YES encoding:NSUTF8StringEncoding error:error] ||
        ![fm moveItemAtURL:prepared toURL:root error:error]) { [fm removeItemAtURL:stage error:nil];return nil; }
    [fm removeItemAtURL:stage error:nil];
    return root;
}
#else
NSURL *LabPrepareSteamRoot(NSURL *lab, NSURL *input, NSString *expected, NSError **error) {
    (void)lab;(void)input;(void)expected;
    if(error)*error=[NSError errorWithDomain:@"iDeckLinuxLab.Root" code:ENOTSUP userInfo:@{NSLocalizedDescriptionKey:@"Steam frontend is not enabled in this Lab build."}];
    return nil;
}
#endif
