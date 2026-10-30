#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
import importlib.util,unittest
from pathlib import Path
p=Path(__file__).resolve().parents[2]/'scripts/experiments/run-native-lab-probe.py';s=importlib.util.spec_from_file_location('runner',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def app(version='12',bundle=m.BUNDLE,url='file:///private/var/containers/Bundle/Application/FIXTURE/Steam-iOS.app/'):
 return dict(bundleIdentifier=bundle,bundleVersion=version,url=url)
class Tests(unittest.TestCase):
 def test_installed_exact_lab(self):self.assertTrue(m.installed_lab([app()]).endswith('/Steam-iOS.app'))
 def test_audited13_accepted(self):self.assertTrue(m.installed_lab([app(version='13')]).endswith('/Steam-iOS.app'))
 def test_ordinary_app_refused(self):
  with self.assertRaises(ValueError):m.installed_lab([app(bundle='com.kuschqin.madeira.steamui')])
 def test_old_or_future_build_refused(self):
  for n in ['11','14']:
   with self.assertRaises(ValueError):m.installed_lab([app(version=n)])
 def test_bad_urls(self):
  for u in ['https://example.com/Steam-iOS.app','file://remote/private/var/containers/Bundle/Application/A/Steam-iOS.app','file:///private/var/containers/Bundle/Application/A/../Steam-iOS.app']:
   with self.assertRaises(ValueError):m.installed_lab([app(url=u)])
 def test_transport_exit_not_proof(self):self.assertFalse(m.diagnostic_complete('synthetic-helper','The app terminated with the exit code 0.'))
 def test_synthetic_requires_exact_verified_fixture(self):
  line=m.PROBES['synthetic-helper'][1];self.assertFalse(m.diagnostic_complete('synthetic-helper',line));self.assertTrue(m.diagnostic_complete('synthetic-helper','[ideck-synthetic-helper] kind=bundle loaded=1 fixture-verified=1 main-called=0\n'+line))
 def test_vm_requires_inventory_and_cleanup(self):
  line=m.PROBES['vm-range'][1];self.assertFalse(m.diagnostic_complete('vm-range',line));self.assertTrue(m.diagnostic_complete('vm-range','[ideck-vm-range] inventory=1 regions=12\n'+line));self.assertFalse(m.diagnostic_complete('vm-range','[ideck-vm-range] inventory=1 regions=12\n'+line.replace('cleanup=1','cleanup=0')))
 def test_helper_old_unverified_path_refused(self):self.assertFalse(m.diagnostic_complete('helper-load','[ideck-helper-load] begin=1 entry-called=0\n[ideck-helper-load] loaded=0 rejects-main-executable=1 diagnostic-result=0 error-text=REDACTED'))
if __name__=='__main__':unittest.main()
