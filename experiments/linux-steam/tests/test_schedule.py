#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
import importlib.util
from pathlib import Path
import plistlib
import unittest

spec = importlib.util.spec_from_file_location('schedule', Path(__file__).parents[1] / 'tools/configure-schedule.py')
schedule = importlib.util.module_from_spec(spec)
spec.loader.exec_module(schedule)

class Schedule(unittest.TestCase):
    def test_interval_and_structured_argument_transport(self):
        prompt = 'Continue "quoted" text\nKeep literal $(data) and `text`.'
        value = schedule.launch_agent('/Applications/CLI.app/codex','00000000-0000-0000-0000-000000000001','/Volumes/easystore/project',prompt,'/Users/test/Library/Logs/iDeck')
        value = plistlib.loads(plistlib.dumps(value))
        self.assertEqual(value['StartInterval'],18300)
        self.assertFalse(value['RunAtLoad'])
        args = value['ProgramArguments']
        self.assertEqual(args[:3],['/bin/sh','-c',schedule.START])
        self.assertEqual(args[args.index('--message')+1],prompt)
        self.assertIn('"$@"',schedule.START)
        self.assertNotIn('WorkingDirectory',value)
        self.assertNotIn('eval',schedule.START)
        self.assertNotIn('python',str(args))

    def test_invalid_target_identity(self):
        with self.assertRaises(ValueError): schedule.launch_agent('/CLI','not-a-thread','/project','prompt','/logs')
        with self.assertRaises(ValueError): schedule.launch_agent('relative','00000000-0000-0000-0000-000000000001','/project','prompt','/logs')

if __name__ == '__main__': unittest.main()
