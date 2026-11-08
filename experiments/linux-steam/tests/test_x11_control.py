#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Observer boundary tests with a mock executable; no Linux/UI/device proof."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

TOOL = Path(__file__).parents[1] / "tools/run-x11-control.py"


class Boundaries(unittest.TestCase):
    def fixture(self, folder):
        base = Path(folder)
        root = base / "root"
        (root / "data").mkdir(parents=True)
        (root / "meta.db").touch()
        cli = base / "mock-ish"
        cli.write_text("#!/bin/sh\nexit 0\n")
        cli.chmod(0o700)
        return root, cli, base / "output"

    def run_control(self, root, cli, output):
        return subprocess.run([sys.executable, str(TOOL), str(cli), str(root), str(output), "--steam"], capture_output=True)

    def test_login_state_refuses_before_any_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root, cli, output = self.fixture(folder)
            config = root / "data/Steam/config"
            config.mkdir(parents=True)
            (config / "loginusers.vdf").write_text("test fixture only")
            self.assertEqual(self.run_control(root, cli, output).returncode, 2)
            self.assertFalse(output.exists())

    def test_incomplete_root_refuses(self):
        with tempfile.TemporaryDirectory() as folder:
            root, cli, output = self.fixture(folder)
            (root / "meta.db").unlink()
            self.assertEqual(self.run_control(root, cli, output).returncode, 2)
            self.assertFalse(output.exists())

    def test_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root, cli, output = self.fixture(folder)
            output.mkdir()
            keep = output / "result.json"
            keep.write_text("preserve")
            self.assertEqual(self.run_control(root, cli, output).returncode, 2)
            self.assertEqual(keep.read_text(), "preserve")

    def test_zero_observer_exit_does_not_claim_steam_ui(self):
        with tempfile.TemporaryDirectory() as folder:
            root, cli, output = self.fixture(folder)
            self.assertEqual(self.run_control(root, cli, output).returncode, 0)
            result = json.loads((output / "result.json").read_text())
            self.assertEqual(result["display_session_returncode"], 0)
            self.assertTrue(result["steam_ui"].startswith("UNVERIFIED"))

    def test_excessive_observation_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root,cli,output=self.fixture(folder)
            result=subprocess.run([sys.executable,str(TOOL),str(cli),str(root),str(output),"--seconds","601"],capture_output=True)
            self.assertEqual(result.returncode,2)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
