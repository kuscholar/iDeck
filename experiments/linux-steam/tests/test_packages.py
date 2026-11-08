#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
import importlib.util
import hashlib
import io
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location("packages", Path(__file__).parents[1] / "tools/steam_packages.py")
packages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packages)


class Packages(unittest.TestCase):
    def test_resume_and_ignored_range(self):
        data = b"abcdef"
        record = dict(file="fixture.zip.abc", size=len(data), sha256=hashlib.sha256(data).hexdigest())
        for status, payload in [(206, b"def"), (200, data)]:
            with tempfile.TemporaryDirectory() as t:
                cache = Path(t)
                (cache / "fixture.zip.abc.partial").write_bytes(b"abc")
                class Reply(io.BytesIO): pass
                response = Reply(payload)
                response.status = status
                response.headers = {"Content-Range": "bytes 3-5/6"}
                with patch.object(packages.OPENER, "open", return_value=response) as opening:
                    output = packages.acquire(record, cache)
                    self.assertEqual(opening.call_args[0][0].get_header("Range"), "bytes=3-")
                self.assertEqual(output.read_bytes(), data)
                self.assertFalse((cache / "fixture.zip.abc.partial").exists())
                with patch.object(packages.OPENER, "open", side_effect=AssertionError("verified cache must not refetch")):
                    self.assertEqual(packages.acquire(record, cache), output)

    def test_complete_bad_cache_is_not_installed(self):
        data = b"abcdef"
        record = dict(file="fixture.zip.abc", size=len(data), sha256=hashlib.sha256(data).hexdigest())
        with tempfile.TemporaryDirectory() as t:
            cache = Path(t)
            (cache / "fixture.zip.abc.partial").write_bytes(b"broken")
            with self.assertRaises(ValueError): packages.acquire(record, cache)
            self.assertFalse((cache / "fixture.zip.abc").exists())
            self.assertFalse((cache / "fixture.zip.abc.partial").exists())

    def test_platform_filter(self):
        def block(name):
            return '"%s" { "file" "bins.zip.abc" "sha2" "%s" "size" "12" }' % (name, "a" * 64)
        self.assertEqual(len(packages.packages(block("bins_linuxarm64_linuxarm64") + block("bins_steamrt_linuxarm64"))), 1)
        with self.assertRaises(ValueError): packages.packages(block("bins_steamrt_linuxarm64"))
        with self.assertRaises(ValueError): packages.packages(block("bins_linuxarm64_linuxarm64").replace('"12"', '"0"'))

    def archive(self, folder, members):
        p = folder / "fixture.zip"
        with zipfile.ZipFile(p, "w") as z:
            for name, value, mode in members:
                info = zipfile.ZipInfo(name); info.external_attr = mode << 16
                z.writestr(info, value)
        return p

    def test_official_separator_and_relative_link(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            archive = self.archive(p, [("steamrtarm64\\libs/lib.so.1", b"ELF", stat.S_IFREG | 0o700),
                                       ("steamrtarm64\\libs/lib.so", b"lib.so.1", stat.S_IFLNK | 0o777)])
            packages.extract_verified(archive, p / "stage")
            self.assertEqual((p / "stage/steamrtarm64/libs/lib.so").read_bytes(), b"ELF")
            with self.assertRaises(ValueError): packages.extract_verified(archive, p / "stage")

    def test_parent_link_stays_inside_same_package(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)
            archive = self.archive(p, [("steamrtarm64/libav.so", b"ELF", stat.S_IFREG | 0o700),
                                       ("steamrtarm64/video/libav.so", b"../libav.so", stat.S_IFLNK | 0o777)])
            packages.extract_verified(archive, p / "stage")
            self.assertEqual((p / "stage/steamrtarm64/video/libav.so").read_bytes(), b"ELF")

    def test_hostile_zip_rejected_before_creation(self):
        for members in [
            [("../escape", b"bad", stat.S_IFREG)],
            [("..\\escape", b"bad", stat.S_IFREG)],
            [("/absolute", b"bad", stat.S_IFREG)],
            [("a", b"../../escape", stat.S_IFLNK)],
            [("a", b"/escape", stat.S_IFLNK)],
            [("a", b"missing", stat.S_IFLNK)],
            [("A", b"x", stat.S_IFREG), ("a", b"y", stat.S_IFREG)],
            [("a", b"b", stat.S_IFLNK), ("b", b"x", stat.S_IFREG), ("a/c", b"z", stat.S_IFREG)]
        ]:
            with tempfile.TemporaryDirectory() as t:
                p = Path(t); archive = self.archive(p, members)
                with self.assertRaises(ValueError): packages.extract_verified(archive, p / "stage")
                self.assertFalse((p / "stage").exists())


if __name__ == "__main__": unittest.main()
