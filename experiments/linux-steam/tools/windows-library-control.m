// SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
#import "LabWindowsLibrary.h"
#include <stdio.h>
#include <errno.h>
#include <stdlib.h>
static void check(BOOL ok,const char *name){if(!ok){fprintf(stderr,"FAIL %s\n",name);exit(1);}}
int main(int argc,const char **argv){@autoreleasepool{
 if(argc!=3)return 2;
 NSURL *root=[NSURL fileURLWithPath:[NSString stringWithUTF8String:argv[1]] isDirectory:YES];
 NSURL *out=[NSURL fileURLWithPath:[NSString stringWithUTF8String:argv[2]] isDirectory:YES];
 NSURL *docs=[out URLByAppendingPathComponent:@"documents" isDirectory:YES];
 BOOL created=NO;NSError *error=nil;
 BOOL bound=LabBindWindowsLibrary(root,docs,&created,&error);
 if(!bound)fprintf(stderr,"prefix bind error code=%ld domain=%s message=%s\n",(long)error.code,error.domain.UTF8String,error.localizedDescription.UTF8String);
 check(bound&&created,"fresh prefix/library binding");
 NSURL *prefix=[root URLByAppendingPathComponent:@"MadeiraPrefix" isDirectory:YES];
 check([docs.path stringByAppendingPathComponent:@"wine"].length>0,"documents path");
 NSURL *alias=[docs URLByAppendingPathComponent:@"wine" isDirectory:YES];
 check([alias.URLByResolvingSymlinksInPath.path isEqual:prefix.URLByResolvingSymlinksInPath.path],"exact retained prefix alias");
 NSURL *file=[prefix URLByAppendingPathComponent:@"drive_c/" IDECK_LAB_STEAM_WINDOWS_ROOT @"/steamapps/libraryfolders.vdf"];
 NSMutableData *settings=[[NSData dataWithContentsOfURL:file]mutableCopy];check(settings!=nil,"real library settings");
 [settings appendData:[@"\n// Existing settings must remain byte-for-byte.\n" dataUsingEncoding:NSUTF8StringEncoding]];
 NSError *fixtureError=nil;BOOL updated=[settings writeToURL:file options:NSDataWritingAtomic error:&fixtureError];
 if(!updated)fprintf(stderr,"fixture write error code=%ld domain=%s message=%s\n",(long)fixtureError.code,fixtureError.domain.UTF8String,fixtureError.localizedDescription.UTF8String);
 check(updated,"fixture existing settings");
 created=YES;check(LabBindWindowsLibrary(root,docs,&created,&error)&&!created,"idempotent binding without rewriting");
 check([[NSData dataWithContentsOfURL:file]isEqualToData:settings],"existing settings preserved");
 NSURL *conflict=[out URLByAppendingPathComponent:@"existing-documents" isDirectory:YES];
 NSURL *old=[conflict URLByAppendingPathComponent:@"wine" isDirectory:YES];
 check([NSFileManager.defaultManager createDirectoryAtURL:old withIntermediateDirectories:YES attributes:nil error:&error],"existing native prefix fixture");
 NSURL *save=[old URLByAppendingPathComponent:@"keep-save"];NSData *body=[@"preserve" dataUsingEncoding:NSUTF8StringEncoding];check([body writeToURL:save atomically:YES],"existing save fixture");
 check(!LabBindWindowsLibrary(root,conflict,&created,&error)&&error.code==EEXIST,"existing prefix is not replaced");
 check([[NSData dataWithContentsOfURL:save]isEqualToData:body]&&[[NSData dataWithContentsOfURL:file]isEqualToData:settings],"save and settings retained");
 puts("PASS native prefix binding, C-contained library metadata, idempotence and existing-data retention; no Wine/Steam execution");return 0;
}}
