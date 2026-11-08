/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Actual Darwin sockets plus pinned LinuxRunner realfs_mknod, not a mock.
 */
#import <Foundation/Foundation.h>
#import "LabSocketPrefix.h"
#include "fs/real.h"
#include "kernel/fs.h"
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
void restore_termios(void) {}
static int failed;
static void check(const char *name,BOOL ok){printf("%s=%s\n",name,ok?"PASS":"FAIL");if(!ok)failed++;}
static int boundSocket(const char *path) {
    struct sockaddr_un a={.sun_family=AF_UNIX};if(strlen(path)>=sizeof a.sun_path)return -1;
    strcpy(a.sun_path,path);a.sun_len=sizeof a;int fd=socket(AF_UNIX,SOCK_STREAM,0);
    if(fd<0)return -1;if(bind(fd,(void *)&a,sizeof a)||listen(fd,1)){close(fd);return -1;}return fd;
}
static int connectSocket(const char *path) {
    struct sockaddr_un a={.sun_family=AF_UNIX};if(strlen(path)>=sizeof a.sun_path)return -1;
    strcpy(a.sun_path,path);a.sun_len=sizeof a;int fd=socket(AF_UNIX,SOCK_STREAM,0);
    if(fd<0)return -1;if(connect(fd,(void *)&a,sizeof a)){int saved=errno;close(fd);errno=saved;return -1;}return fd;
}
int main(int argc,char **argv){@autoreleasepool{
    if(argc!=2)return 2;char original[4096];if(!getcwd(original,sizeof original))return 2;
    NSFileManager *fm=NSFileManager.defaultManager;NSString *base=@(argv[1]);BOOL exists=[fm fileExistsAtPath:base];if(exists)return 2;
    NSString *ipc=[base stringByAppendingPathComponent:@"ipc"],*data=[base stringByAppendingPathComponent:@"data"];
    if(![fm createDirectoryAtPath:ipc withIntermediateDirectories:YES attributes:nil error:nil]||![fm createDirectoryAtPath:data withIntermediateDirectories:YES attributes:nil error:nil])return 2;
    NSString *prefix=LabNativeSocketPrefix(ipc);check("absolute-prefix-selected",prefix.isAbsolutePath);
    if(!prefix)return 3;
    struct mount mount={0};mount.root_fd=open(data.fileSystemRepresentation,O_RDONLY|O_DIRECTORY);if(mount.root_fd<0)return 3;
    if(chdir(ipc.fileSystemRepresentation))return 3;
    int listener=boundSocket("relative"),client=-1;check("relative-listener-created",listener>=0);
    int status=realfs_mknod(&mount,"/first-fifo",S_IFIFO|0600,0);
    char changed[4096];check("pinned-fifo-changes-native-cwd",status==0&&getcwd(changed,sizeof changed)&&strcmp(changed,ipc.fileSystemRepresentation));
    errno=0;client=connectSocket("relative");check("relative-connect-fails-after-fifo",client<0&&errno==ENOENT);if(client>=0)close(client);if(listener>=0)close(listener);
    if(chdir(ipc.fileSystemRepresentation))return 3;
    char *owned=NULL;@autoreleasepool{owned=LabCopyNativeSocketPrefix(ipc);}
    check("owned-prefix-survives-autorelease-pool",owned&&!strcmp(owned,prefix.fileSystemRepresentation));
    if(!owned)return 3;
    char absolute[sizeof(((struct sockaddr_un *)0)->sun_path)];
    int n=snprintf(absolute,sizeof absolute,"%sabsolute",owned);if(n<0||(size_t)n>=sizeof absolute)return 3;
    listener=boundSocket(absolute);check("absolute-listener-created",listener>=0);
    status=realfs_mknod(&mount,"/second-fifo",S_IFIFO|0600,0);client=connectSocket(absolute);
    int accepted=client>=0?accept(listener,NULL,NULL):-1;char byte=0;
    BOOL delivered=status==0&&client>=0&&accepted>=0&&write(client,"x",1)==1&&read(accepted,&byte,1)==1&&byte=='x';
    check("absolute-connect-survives-fifo-cwd-change",delivered);
    if(client>=0)close(client);if(accepted>=0)close(accepted);if(listener>=0)close(listener);close(mount.root_fd);free(owned);
    NSString *longDir=[ipc stringByAppendingPathComponent:[@"" stringByPaddingToLength:120 withString:@"x" startingAtIndex:0]];
    [fm createDirectoryAtPath:longDir withIntermediateDirectories:YES attributes:nil error:nil];
    check("oversized-existing-path-refused",LabNativeSocketPrefix(longDir)==nil);
    check("missing-path-not-created",LabNativeSocketPrefix([base stringByAppendingPathComponent:@"missing"])==nil);
    if(chdir(original))return 3;[fm removeItemAtPath:base error:nil];return failed?1:0;
}}
