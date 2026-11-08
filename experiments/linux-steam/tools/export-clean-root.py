#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Export a STOPPED, unauthenticated fakefs as a portable Linux tar, not a
native directory copy. Fakefs symlinks/device metadata and hardlinks are kept;
host bindings, runtime sockets, Steam/browser/login state are excluded. This is
an installation image, never an app-account migration. Output stays private.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sqlite3
import stat
import struct
import subprocess
import tarfile
import tempfile
import shutil

OMIT = ('/tmp', '/run', '/proc', '/sys', '/dev', '/control', '/var/log',
        '/Steam/config', '/Steam/userdata', '/Steam/logs', '/Steam/dumps', '/Steam/appcache',
        '/root/.steam', '/root/.steampid', '/root/.steampath', '/root/.cache', '/root/.local', '/root/.config')


def excluded(path):
    return any(path == x or path.startswith(x + '/') for x in OMIT)


def canonical(raw):
    path = raw.decode('utf-8') if isinstance(raw, bytes) else raw
    if path == '': return path
    if not isinstance(path, str) or not path.startswith('/') or any(ord(c) < 32 for c in path):
        raise ValueError('invalid fakefs path')
    if str(PurePosixPath(path)) != path or '..' in PurePosixPath(path).parts or len(path.encode()) > 4095:
        raise ValueError('noncanonical fakefs path')
    return path


def opened(rootfd, path):
    # Every native parent is pinned without following host symlinks. Linux
    # symlinks are represented by regular payload files, handled as such below.
    parent = os.dup(rootfd)
    try:
        parts = PurePosixPath(path).parts[1:]
        for part in parts[:-1]:
            nextfd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            os.close(parent); parent = nextfd
        return os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    finally:
        os.close(parent)


def _export(root, output, omit_missing_manuals=False):
    root, output = root.resolve(), output.resolve()
    if root in output.parents: raise ValueError('never write the source root')
    if output.exists() or output.with_suffix(output.suffix + '.json').exists():
        raise ValueError('output must be new')
    for name in ['Steam/config/loginusers.vdf', 'root/.steam/config/loginusers.vdf']:
        if (root/'data'/name).exists(): raise ValueError('account-state guard: use a fresh unauthenticated root')
    if not (root/'data').is_dir() or not (root/'meta.db').is_file(): raise ValueError('fakefs required')
    db = sqlite3.connect((root/'meta.db').as_uri() + '?mode=ro', uri=True)
    if db.execute('pragma user_version').fetchone()[0] != 3: raise ValueError('unpinned metadata schema')
    version = db.execute('pragma data_version').fetchone()[0]
    records = list(db.execute('select path, inode, stat from paths join stats using(inode) order by path'))
    if len(records) > 200000: raise ValueError('image entry limit')
    image = []; seen = {}; total = 0; missing_manuals = []
    rootfd = os.open(root/'data', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        with tarfile.open(output, 'x:gz', format=tarfile.PAX_FORMAT) as archive:
            for raw, inode, metadata in records:
                path = canonical(raw)
                if excluded(path): continue
                if len(metadata) != 16: raise ValueError('unpinned stat layout')
                mode, uid, gid, device = struct.unpack('<IIII', metadata)
                item = tarfile.TarInfo('.' + path)
                # Linux filenames are validated UTF-8 bytes. Per-entry PAX BINARY
                # preserves those bytes without platform-locale transcoding;
                # a global hdrcharset header is not sufficient in pinned libarchive.
                item.pax_headers = {'hdrcharset': 'BINARY'}
                item.mode = stat.S_IMODE(mode); item.uid = uid; item.gid = gid
                item.mtime = 0
                report = dict(path=path, mode=mode, uid=uid, gid=gid)
                if stat.S_ISDIR(mode):
                    item.type = tarfile.DIRTYPE
                    archive.addfile(item)
                elif stat.S_ISREG(mode) or stat.S_ISLNK(mode):
                    try:
                        fd = opened(rootfd, path)
                    except FileNotFoundError:
                        optional_manual = stat.S_ISLNK(mode) or (stat.S_ISREG(mode) and not mode & 0o111)
                        if omit_missing_manuals and path.startswith('/usr/share/man/') and optional_manual:
                            missing_manuals.append(path)
                            continue
                        raise
                    with os.fdopen(fd, 'rb') as source:
                        before = os.fstat(source.fileno())
                        if not stat.S_ISREG(before.st_mode): raise ValueError('unexpected native payload type')
                        if stat.S_ISLNK(mode):
                            if before.st_size > 4095: raise ValueError('link size')
                            target = source.read().decode('utf-8')
                            if not target or '\0' in target: raise ValueError('invalid Linux link')
                            item.type = tarfile.SYMTYPE; item.linkname = target
                            report['linux_symlink'] = target
                            archive.addfile(item)
                        else:
                            if before.st_size > 512*1024*1024: raise ValueError('file size bound')
                            digest = hashlib.file_digest(source, 'sha256').hexdigest() if hasattr(hashlib, 'file_digest') else None
                            if digest is None:
                                h = hashlib.sha256()
                                while chunk := source.read(1024*1024): h.update(chunk)
                                digest = h.hexdigest()
                            source.seek(0)
                            if inode in seen:
                                first, size, oldhash = seen[inode]
                                if size != before.st_size or oldhash != digest: raise ValueError('inconsistent hardlink payload')
                                item.type = tarfile.LNKTYPE; item.linkname = first
                                report['hardlink'] = first
                                archive.addfile(item)
                            else:
                                total += before.st_size
                                if total > 8*1024*1024*1024: raise ValueError('image size bound')
                                item.size = before.st_size; report['sha256'] = digest
                                seen[inode] = (item.name, item.size, digest)
                                archive.addfile(item, source)
                        after = os.fstat(source.fileno())
                        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                            raise ValueError('source changed during export')
                elif stat.S_ISCHR(mode) or stat.S_ISBLK(mode):
                    item.type = tarfile.CHRTYPE if stat.S_ISCHR(mode) else tarfile.BLKTYPE
                    item.devmajor = (device >> 8) & 0xfff
                    item.devminor = (device & 0xff) | ((device >> 12) & 0xfffff00)
                    archive.addfile(item)
                elif stat.S_ISFIFO(mode):
                    item.type = tarfile.FIFOTYPE; archive.addfile(item)
                elif stat.S_ISSOCK(mode):
                    continue  # Runtime socket names are never installation content.
                else:
                    raise ValueError('unqualified entry type')
                image.append(report)
        if db.execute('pragma data_version').fetchone()[0] != version: raise ValueError('metadata changed during export')
    finally:
        os.close(rootfd); db.close()
    h = hashlib.sha256()
    with output.open('rb') as stream:
        while chunk := stream.read(1024*1024): h.update(chunk)
    report = dict(scope='clean private Linux install image, no account migration', sha256=h.hexdigest(),
                  bytes=output.stat().st_size, payload_bytes=total, excluded=list(OMIT), omitted_missing_manuals=missing_manuals, entries=image)
    output.with_suffix(output.suffix + '.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def export(root, output, omit_missing_manuals=False):
    root, output = root.resolve(), output.resolve()
    receipt = output.with_suffix(output.suffix + '.json')
    if root in output.parents or output.exists() or receipt.exists():
        raise ValueError('use new output outside source root')
    stage = Path(tempfile.mkdtemp(prefix='linux-root-stage-', dir=output.parent))
    image = stage/'image.tar.gz'
    published = False
    try:
        result = _export(root, image, omit_missing_manuals=omit_missing_manuals)
        # Same-filesystem, atomic, non-overwriting publication only after all
        # data/metadata checks pass. A failed import image is never advertised.
        os.link(image, output, follow_symlinks=False)
        published = True
        os.link(image.with_suffix('.gz.json'), receipt, follow_symlinks=False)
        return result
    except Exception:
        if published and output.exists() and output.lstat().st_ino == image.lstat().st_ino:
            output.unlink()  # Only this job's newly published inode.
        raise
    finally:
        shutil.rmtree(stage)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root', type=Path); p.add_argument('output', type=Path)
    p.add_argument('--omit-missing-manuals', action='store_true', help='record missing non-executable manual files/symlinks only; required files still fail')
    a = p.parse_args()
    rows = subprocess.check_output(['ps', '-axo', 'comm='], text=True).splitlines()
    if any(Path(x.strip()).name in {'ish', 'ish-tcp-view', 'ish-pipe-observer'} for x in rows):
        p.error('stop all Lab runtimes before exporting')
    r = export(a.root, a.output, omit_missing_manuals=a.omit_missing_manuals)
    print(json.dumps({k:r[k] for k in ['scope','sha256','bytes','payload_bytes']}))
