#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Actual native mode policy and exact existing auto-start rule, not device UI."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args();out=a.output.resolve();repo=Path(__file__).resolve().parents[3];lab=repo/'experiments/linux-steam'
assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(mode=0o700,parents=True)
commands=[]
def run(cmd):
 commands.append([str(x) for x in cmd]);return subprocess.check_output(cmd,stderr=subprocess.STDOUT,text=True,timeout=180 if str(cmd[0])=='xcrun' else 20)
run(['xcrun','clang','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(lab/'app'),lab/'app/LabStartupMode.c',lab/'tools/cold-setup-policy-control.c','-o',out/'native'])
native=run([out/'native']);source=(repo/'app/Madeira/SteamUIExperiment.swift').read_text();start=source.index('    static func shouldAutoStart(');end=source.index('\n    }',start)+6;method=source[start:end]
start=source.index('    static func callbackScheme(');end=source.index('\n    }',start)+6;callback=source[start:end]
text='import Foundation\nenum SteamUIExperiment {\n'+callback+'\n}\nenum IDeckRules {\n'+method+'\n}\n'+'''let ordinary=IDeckRules.shouldAutoStart(setup:true,ready:true,automatic:true,arguments:["Madeira"])
let cold=IDeckRules.shouldAutoStart(setup:true,ready:true,automatic:true,arguments:["Madeira","madeira-linux-lab-setup"])
precondition(ordinary && !cold)
precondition(SteamUIExperiment.callbackScheme(bundleID:"com.kuschqin.ideck.freshtest",registeredSchemes:["ideck-linux-lab"])=="ideck-linux-lab")
print("PASS exact production auto-start rule excludes cold setup without changing stored preferences")
print("PASS exact callback selection returns the isolated Lab scheme after bundle-ID override")
''';(out/'main.swift').write_text(text)
run(['xcrun','swiftc','-module-cache-path',out/'module-cache',out/'main.swift','-o',out/'swift']);swift=run([out/'swift']);h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'evidence.json').write_text(json.dumps({'scope':'HOST actual mode policy + exact selected production auto-start rule, NOT UI/bootstrap/Linux exclusion on device/JIT/auth/game success','native_output':native,'swift_output':swift,'commands':commands,'native_policy_sha256':h(lab/'app/LabStartupMode.c'),'auto_rule_source_sha256':h(repo/'app/Madeira/SteamUIExperiment.swift'),'extracted_auto_rule_sha256':h(out/'main.swift')},indent=2)+'\n');print(native+swift)
