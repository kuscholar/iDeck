#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Portable installation-image contracts; no device/runtime claims."""
import importlib.util
from pathlib import Path
import sqlite3
import stat
import struct
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('clean_root', Path(__file__).parents[1]/'tools/export-clean-root.py')
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)


class PortableImage(unittest.TestCase):
    def fixture(self, folder):
        root = Path(folder)/'root'; (root/'data').mkdir(parents=True)
        db = sqlite3.connect(root/'meta.db')
        db.executescript('pragma user_version=3; create table paths(path blob primary key,inode integer); create table stats(inode integer primary key,stat blob);')
        self.add(db, '', 1, stat.S_IFDIR|0o755)
        return root, db, Path(folder)/'image.tar.gz'

    def add(self, db, path, inode, mode):
        db.execute('insert or ignore into stats values(?,?)', (inode, struct.pack('<IIII', mode, 0, 0, 0)))
        db.execute('insert into paths values(?,?)', (path.encode(), inode)); db.commit()

    def test_real_content_hardlink_and_linux_symlink(self):
        with tempfile.TemporaryDirectory() as folder:
            root, db, output = self.fixture(folder)
            for path, inode, mode, payload in [('/hello',2,stat.S_IFREG|0o755,b'Linux ELF fixture'),('/alias',2,stat.S_IFREG|0o755,b'Linux ELF fixture'),('/link',3,stat.S_IFLNK|0o777,b'/hello')]:
                (root/'data'/path[1:]).write_bytes(payload); self.add(db,path,inode,mode)
            db.close(); result = module.export(root,output)
            with tarfile.open(output) as archive:
                items = archive.getmembers(); links = [x for x in items if x.islnk()]
                self.assertEqual(len(links),1)
                self.assertTrue(archive.getmember('./link').issym())
                self.assertEqual(archive.getmember('./link').linkname,'/hello')
                self.assertEqual(archive.extractfile('./hello').read(), b'Linux ELF fixture')
            self.assertEqual(result['payload_bytes'],len(b'Linux ELF fixture'))

    def test_unicode_name_bytes_declared_per_entry(self):
        with tempfile.TemporaryDirectory() as folder:
            root, db, output = self.fixture(folder)
            name='/copyright-\u00e9.txt'
            (root/'data'/name[1:]).write_bytes(b'public fixture')
            self.add(db,name,2,stat.S_IFREG|0o644); db.close()
            module.export(root,output)
            with tarfile.open(output) as archive:
                item=archive.getmember('.'+name)
                self.assertEqual(item.pax_headers.get('hdrcharset'),'BINARY')
                self.assertEqual(archive.extractfile(item).read(),b'public fixture')

    def test_browser_and_host_binding_state_omitted(self):
        with tempfile.TemporaryDirectory() as folder:
            root, db, output = self.fixture(folder)
            # No actual secret or external target: omitted DB paths need no reads.
            self.add(db,'/Steam/config/htmlcache/session',2,stat.S_IFREG|0o600)
            self.add(db,'/control/test',3,stat.S_IFREG|0o755)
            self.add(db,'/tmp/.X99-lock',4,stat.S_IFREG|0o600)
            db.close(); module.export(root,output)
            with tarfile.open(output) as archive: self.assertEqual(archive.getnames(),['.'])

    def test_account_configuration_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root, db, output = self.fixture(folder); db.close()
            config = root/'data/Steam/config'; config.mkdir(parents=True)
            (config/'loginusers.vdf').touch()
            with self.assertRaises(ValueError): module.export(root,output)
            self.assertFalse(output.exists())

    def test_traversal_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root, db, output = self.fixture(folder)
            self.add(db,'/../outside',2,stat.S_IFREG|0o600); db.close()
            with self.assertRaises(ValueError): module.export(root,output)
            self.assertFalse(output.exists())
            self.assertFalse(list(Path(folder).glob('linux-root-stage-*')))

    def test_native_parent_symlink_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root, db, output = self.fixture(folder)
            outside = Path(folder)/'outside'; outside.mkdir(); (outside/'file').write_bytes(b'not read')
            (root/'data/escape').symlink_to(outside, target_is_directory=True)
            self.add(db,'/escape/file',2,stat.S_IFREG|0o600); db.close()
            with self.assertRaises(OSError): module.export(root,output)

    def test_inconsistent_hardlink_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root, db, output = self.fixture(folder)
            for name, payload in [('a',b'a'),('b',b'b')]:
                (root/'data'/name).write_bytes(payload); self.add(db,'/'+name,2,stat.S_IFREG|0o644)
            db.close()
            with self.assertRaises(ValueError): module.export(root,output)

    def test_existing_output_and_source_root_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root, db, output = self.fixture(folder); db.close(); output.write_bytes(b'preserve')
            with self.assertRaises(ValueError): module.export(root,output)
            self.assertEqual(output.read_bytes(),b'preserve')
            with self.assertRaises(ValueError): module.export(root,root/'bad.tar.gz')

    def test_missing_manual_opt_in_never_skips_required_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root, db, output = self.fixture(folder)
            self.add(db,'/usr/share/man/man7/PAM.7.gz',2,stat.S_IFREG|0o644); db.close()
            with self.assertRaises(FileNotFoundError): module.export(root,output)
            result = module.export(root,output,omit_missing_manuals=True)
            self.assertEqual(result['omitted_missing_manuals'],['/usr/share/man/man7/PAM.7.gz'])
        with tempfile.TemporaryDirectory() as folder:
            root, db, output = self.fixture(folder)
            self.add(db,'/usr/share/man/man7/pam.7.gz',2,stat.S_IFLNK|0o777); db.close()
            result = module.export(root,output,omit_missing_manuals=True)
            self.assertEqual(result['omitted_missing_manuals'],['/usr/share/man/man7/pam.7.gz'])
        with tempfile.TemporaryDirectory() as folder:
            root, db, output = self.fixture(folder)
            self.add(db,'/usr/lib/required.so',2,stat.S_IFREG|0o644); db.close()
            with self.assertRaises(FileNotFoundError): module.export(root,output,omit_missing_manuals=True)


if __name__ == '__main__': unittest.main()
