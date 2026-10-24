#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 125hz
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""The wineserver's overwrite of a link to a read-only file (build/wineserver/fd_ios.c).

Madeira's C:\\windows\\system32 and syswow64 are symbolic links into the read-only app
bundle. An installer that copies its own build of a DLL over one of them used to get
access denied forever; open_fd now removes such a link and creates the file in its
place, but only for an overwrite (the old contents are discarded anyway).

Compiles the production helper block and the retry from open_fd, taken verbatim from
fd_ios.c, with minimal stand-ins for the server's device and inode tables, under
AddressSanitizer, and checks on real files in a temporary folder:
  * FILE_OVERWRITE_IF / FILE_SUPERSEDE / FILE_OVERWRITE with write access through a
    link to a read-only file: the link becomes a new empty regular file, the target
    is untouched;
  * no replacement (errno kept, link kept) when the disposition keeps the contents
    (FILE_OPEN, FILE_OPEN_IF), without write access, for a directory open, for a
    plain read-only file, a link to a directory, a dangling link, an error other than
    EACCES/EPERM/EROFS, or when the target file is open in the server;
  * MADEIRA_REPLACE_READONLY_LINK=0 turns it off;
  * log lines carry no file names and stop after 16.
Synthetic files only: no Wine, iOS or device.
"""
from pathlib import Path
import os, shutil, subprocess, sys, tempfile

root = Path(__file__).resolve().parents[2]
fd = (root / 'build/wineserver/fd_ios.c').read_text()
CC = os.environ.get('CC') or shutil.which('cc') or 'cc'
failures = 0


def require(condition, label):
    global failures
    print(('PASS: ' if condition else 'FAIL: ') + label)
    if not condition:
        failures += 1


start = fd.index('#ifdef WINE_IOS\n/* An overwrite of a file that is a symbolic link')
helpers = fd[start:fd.index('#endif\n', start) + len('#endif\n')]
retry_start = fd.index('        if (ios_replace_readonly_link( name, flags, access, options ) &&')
retry = fd[retry_start:fd.index('#endif\n', retry_start)]
open_fd = fd[fd.index('struct fd *open_fd('):]
open_fd = open_fd[:open_fd.index('\n}\n')]

# ------------------------------------------------------------------ static
require('if ((fd->unix_fd = open( name, rw_mode | (flags & ~O_TRUNC), *mode )) == -1)\n    {\n#ifdef WINE_IOS\n'
        '        if (ios_replace_readonly_link( name, flags, access, options ) &&' in open_fd,
        'open_fd: the replacement runs only inside the failed-open branch, first')
require(open_fd.index('ios_replace_readonly_link(') < open_fd.index('if (errno == EISDIR)'),
        "open_fd: upstream's directory retry and error mapping follow unchanged")
require(fd.count('ios_replace_readonly_link(') == 2 and helpers.count('unlink( name )') == 1,
        'one caller, one unlink')
log_line = helpers[helpers.index('fprintf( stderr, "[readonly-link]'):helpers.index(');', helpers.index('fprintf( stderr, "[readonly-link]'))]
require('name' not in log_line.replace('MADEIRA_REPLACE_READONLY_LINK', ''), 'the log line prints no file name')

harness = r'''
#define WINE_IOS 1
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

struct list { struct list *next, *prev; };
#define LIST_FOR_EACH_ENTRY(elem, list, type, field) \
    for ((elem) = (type *)((char *)(list)->next - offsetof(type, field)); \
         &(elem)->field != (list); \
         (elem) = (type *)((char *)(elem)->field.next - offsetof(type, field)))
#include <stddef.h>
static void list_init( struct list *l ) { l->next = l->prev = l; }
static int list_empty( const struct list *l ) { return l->next == l; }
static void list_add_head( struct list *l, struct list *e ) { e->next = l->next; e->prev = l; l->next->prev = e; l->next = e; }

#define INODE_HASH_SIZE 17
#define FILE_UNIX_WRITE_ACCESS 0x2
#define FILE_UNIX_READ_ACCESS 0x1
#define FILE_DIRECTORY_FILE 0x1
struct device { dev_t dev; struct list inode_hash[INODE_HASH_SIZE]; };
struct inode { struct list entry; ino_t ino; struct list open; };
static struct device test_device;
static int device_known;
static struct device *get_device( dev_t dev, int unix_fd )
{
    if (unix_fd != -1) abort();              /* the helper must never create a device */
    return device_known && dev == test_device.dev ? &test_device : NULL;
}
static void release_object( void *obj ) { (void)obj; }
'''

harness_main = r'''
static int check( int ok, const char *label ) { printf( "%s: %s\n", ok ? "PASS" : "FAIL", label ); return !ok; }
static int is_link( const char *p ) { struct stat st; return !lstat( p, &st ) && S_ISLNK( st.st_mode ); }
static int is_empty_file( const char *p ) { struct stat st; return !lstat( p, &st ) && S_ISREG( st.st_mode ) && st.st_size == 0; }

/* what open_fd does: first open, then the production retry */
static int attempt( const char *name, int flags, unsigned int access, unsigned int options, int forced_errno )
{
    struct { int unix_fd; } fdobj, *fd = &fdobj;
    mode_t m = 0666, *mode = &m;
    int rw_mode = (access & FILE_UNIX_WRITE_ACCESS) ? O_WRONLY : O_RDONLY;

    if ((fd->unix_fd = open( name, rw_mode | (flags & ~O_TRUNC), *mode )) == -1 || forced_errno)
    {
        if (forced_errno) { if (fd->unix_fd != -1) close( fd->unix_fd ); fd->unix_fd = -1; errno = forced_errno; }
RETRY
    }
    if (fd->unix_fd == -1) return -errno;
    close( fd->unix_fd );
    return 0;
}

int main( int argc, char **argv )
{
    int fails = 0, i, r;
    const char *dir = argv[1];
    char target[4096], link_[4096], plain[4096], dlink[4096], dangling[4096];
    struct stat st;

    if (argc > 2)   /* switch-off run */
    {
        snprintf( link_, sizeof(link_), "%s/off.dll", dir );
        r = attempt( link_, O_CREAT | O_TRUNC, FILE_UNIX_WRITE_ACCESS, 0, EACCES );
        fails += check( r == -EACCES && is_link( link_ ), "MADEIRA_REPLACE_READONLY_LINK=0: the link stays and the open fails" );
        return fails;
    }
    snprintf( target, sizeof(target), "%s/bundle/d3dx.dll", dir );
    snprintf( plain, sizeof(plain), "%s/plain.dll", dir );
    snprintf( dlink, sizeof(dlink), "%s/dirlink", dir );
    snprintf( dangling, sizeof(dangling), "%s/dangling.dll", dir );
    stat( target, &st );
    test_device.dev = st.st_dev;
    for (i = 0; i < INODE_HASH_SIZE; i++) list_init( &test_device.inode_hash[i] );

    /* the three truncating dispositions, forced EACCES so the check also runs as root */
    static const int trunc_flags[] = { O_CREAT | O_TRUNC /* FILE_OVERWRITE_IF, FILE_SUPERSEDE */, O_TRUNC /* FILE_OVERWRITE */ };
    for (i = 0; i < 2; i++)
    {
        snprintf( link_, sizeof(link_), "%s/farm%d.dll", dir, i );
        r = attempt( link_, trunc_flags[i], FILE_UNIX_WRITE_ACCESS | FILE_UNIX_READ_ACCESS, 0, EACCES );
        fails += check( r == 0 && is_empty_file( link_ ), i ? "FILE_OVERWRITE through a link: new empty regular file"
                                                            : "FILE_OVERWRITE_IF through a link: new empty regular file" );
    }
    fails += check( !stat( target, &st ) && st.st_size == 7, "the link target (bundle file) is untouched" );
    for (i = 0; i < 2; i++)
    {
        int errs[] = { EPERM, EROFS };
        snprintf( link_, sizeof(link_), "%s/farm%d.dll", dir, 2 + i );
        r = attempt( link_, O_CREAT | O_TRUNC, FILE_UNIX_WRITE_ACCESS, 0, errs[i] );
        fails += check( r == 0 && is_empty_file( link_ ), i ? "EROFS also replaces" : "EPERM also replaces" );
    }
    snprintf( link_, sizeof(link_), "%s/keep.dll", dir );
    r = attempt( link_, 0, FILE_UNIX_WRITE_ACCESS, 0, EACCES );
    fails += check( r == -EACCES && is_link( link_ ), "FILE_OPEN for write keeps the link and the error" );
    r = attempt( link_, O_CREAT, FILE_UNIX_WRITE_ACCESS, 0, EACCES );
    fails += check( r == -EACCES && is_link( link_ ), "FILE_OPEN_IF keeps the link and the error" );
    r = attempt( link_, O_CREAT | O_TRUNC, FILE_UNIX_READ_ACCESS, 0, EACCES );
    fails += check( r == -EACCES && is_link( link_ ), "no write access: link kept" );
    r = attempt( link_, O_CREAT | O_TRUNC, FILE_UNIX_WRITE_ACCESS, FILE_DIRECTORY_FILE, EACCES );
    fails += check( r == -EACCES && is_link( link_ ), "a directory open: link kept" );
    r = attempt( link_, O_CREAT | O_TRUNC, FILE_UNIX_WRITE_ACCESS, 0, ENOSPC );
    fails += check( r == -ENOSPC && is_link( link_ ), "another error (ENOSPC): link kept, error kept" );
    r = attempt( plain, O_CREAT | O_TRUNC, FILE_UNIX_WRITE_ACCESS, 0, EACCES );
    fails += check( r == -EACCES && !stat( plain, &st ) && st.st_size == 5, "a plain read-only file is not touched" );
    r = attempt( dlink, O_CREAT | O_TRUNC, FILE_UNIX_WRITE_ACCESS, 0, EACCES );
    fails += check( r == -EACCES && is_link( dlink ), "a link to a directory is kept" );
    r = attempt( dangling, O_TRUNC, FILE_UNIX_WRITE_ACCESS, 0, EACCES );
    fails += check( r == -EACCES && is_link( dangling ), "a dangling link is kept" );

    /* the target is open in the server: an inode with an open fd on its device */
    {
        static struct inode inode;
        static struct list open_fd_entry;
        stat( target, &st );
        inode.ino = st.st_ino; list_init( &inode.open ); list_add_head( &inode.open, &open_fd_entry );
        list_add_head( &test_device.inode_hash[st.st_ino % INODE_HASH_SIZE], &inode.entry );
        device_known = 1;
        r = attempt( link_, O_CREAT | O_TRUNC, FILE_UNIX_WRITE_ACCESS, 0, EACCES );
        fails += check( r == -EACCES && is_link( link_ ), "target open in the server (Windows: sharing violation): link kept" );
        list_init( &inode.open );
        r = attempt( link_, O_CREAT | O_TRUNC, FILE_UNIX_WRITE_ACCESS, 0, EACCES );
        fails += check( r == 0 && is_empty_file( link_ ), "same inode known but no longer open: replaced" );
    }
    /* the log stops after 16 lines */
    for (i = 0; i < 20; i++)
    {
        snprintf( link_, sizeof(link_), "%s/many%d.dll", dir, i );
        attempt( link_, O_CREAT | O_TRUNC, FILE_UNIX_WRITE_ACCESS, 0, EACCES );
    }
    return fails;
}
'''

with tempfile.TemporaryDirectory(prefix='madeira-readonly-link-') as tmp:
    tmp = Path(tmp)
    src = tmp / 'check.c'
    src.write_text(harness + helpers + harness_main.replace('RETRY', retry))
    exe = tmp / 'check'
    build = subprocess.run([CC, '-std=gnu11', '-Wall', '-Wno-unused-function', '-fsanitize=address,undefined', '-g',
                            '-o', str(exe), str(src)], capture_output=True, text=True)
    require(build.returncode == 0, 'the production helper and retry compile on the host')
    if build.returncode:
        sys.stdout.write(build.stderr[-4000:])
    else:
        def fresh(name):
            d = tmp / name
            (d / 'bundle').mkdir(parents=True)
            target = d / 'bundle/d3dx.dll'
            target.write_text('builtin'); target.chmod(0o444)
            for n in ['farm0.dll', 'farm1.dll', 'farm2.dll', 'farm3.dll', 'keep.dll', 'off.dll'] + [f'many{i}.dll' for i in range(20)]:
                (d / n).symlink_to(target)
            plain = d / 'plain.dll'; plain.write_text('plain'); plain.chmod(0o444)
            (d / 'dirlink').symlink_to(d / 'bundle', target_is_directory=True)
            (d / 'dangling.dll').symlink_to(d / 'missing.dll')
            return d
        d = fresh('on')
        env = dict(os.environ, ASAN_OPTIONS='detect_leaks=0')
        env.pop('MADEIRA_REPLACE_READONLY_LINK', None)
        run = subprocess.run([str(exe), str(d)], env=env, capture_output=True, text=True)
        sys.stdout.write(run.stdout)
        require(run.returncode == 0, 'replacement rules hold on real files')
        logs = [l for l in run.stderr.splitlines() if l.startswith('[readonly-link]')]
        require(len(logs) == 16, f'the log stops after 16 lines ({len(logs)})')
        require(all(str(tmp) not in l and '.dll' not in l for l in logs), 'log lines carry no names or paths')
        if run.returncode:
            sys.stdout.write(run.stderr[-3000:])
        d = fresh('off')
        run = subprocess.run([str(exe), str(d), 'off'], env=dict(env, MADEIRA_REPLACE_READONLY_LINK='0'),
                             capture_output=True, text=True)
        sys.stdout.write(run.stdout)
        require(run.returncode == 0 and '[readonly-link]' not in run.stderr, 'MADEIRA_REPLACE_READONLY_LINK=0: off')

if failures:
    print(f'check-readonly-link: {failures} FAILED')
    sys.exit(1)
print('check-readonly-link: PASS')
