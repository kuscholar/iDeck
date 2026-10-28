// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Capability diagnostic only: no filesystem property is overridden.
#import <Foundation/Foundation.h>
#import <fcntl.h>
#import <sys/stat.h>
#import <unistd.h>
#import <errno.h>
#import <stdio.h>

extern void IDeckSetCaseViewReady(int ready);

__attribute__((constructor)) static void CaseProbe(void) {
    @autoreleasepool {
        char folder[PATH_MAX];
        snprintf(folder, sizeof folder, "%s/ideck-case-probe.XXXXXX", NSTemporaryDirectory().fileSystemRepresentation);
        if (!mkdtemp(folder)) { fprintf(stderr,"[ideck-mac-case] fixture-create=failed\n"); return; }
        char exact[PATH_MAX], alias[PATH_MAX], renamed[PATH_MAX], renamedAlias[PATH_MAX];
        snprintf(exact,sizeof exact,"%s/MiXeD.txt",folder);snprintf(alias,sizeof alias,"%s/mixed.TXT",folder);
        snprintf(renamed,sizeof renamed,"%s/ReNaMeD.txt",folder);snprintf(renamedAlias,sizeof renamedAlias,"%s/renamed.TXT",folder);
        int fd=open(exact,O_CREAT|O_EXCL|O_RDWR,0600);struct stat first={0},second={0};
        int created=fd>=0; if(fd>=0){fstat(fd,&first);close(fd);}
        fd=open(alias,O_RDONLY);int readAlias=fd>=0;if(fd>=0){fstat(fd,&second);close(fd);}
        int same=readAlias && first.st_ino==second.st_ino;
        int exclusive=open(alias,O_CREAT|O_EXCL|O_WRONLY,0600);int collision=exclusive<0 && errno==EEXIST;if(exclusive>=0)close(exclusive);
        int dir=open(folder,O_RDONLY);fd=dir>=0?openat(dir,"MIXED.txt",O_RDONLY):-1;int relative=fd>=0;if(fd>=0)close(fd);if(dir>=0)close(dir);
        int renamedOK=rename(alias,renamed)==0;
        int statOK=stat(renamedAlias,&second)==0;
        int deleted=unlink(renamedAlias)==0;
        IDeckSetCaseViewReady(created && readAlias && same && collision && relative && renamedOK && statOK && deleted);
        fprintf(stderr,"[ideck-mac-case] create=%d alias-read=%d same-inode=%d exclusive-collision=%d openat=%d rename=%d alias-stat=%d alias-delete=%d\n",created,readAlias,same,collision,relative,renamedOK,statOK,deleted);
        // Only fixture names created above are removed, never Steam/user files.
        unlink(exact);unlink(alias);unlink(renamed);unlink(renamedAlias);rmdir(folder);
    }
}
