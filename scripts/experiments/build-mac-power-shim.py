#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Build fail-closed optional power registration only in isolated converted copy.
No private entitlement or native power-service request. No signing/deployment.
"""
import argparse,hashlib,json,plistlib,subprocess,tempfile
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--converted',type=Path,required=True);a=p.parse_args();root=a.converted.resolve();app=root/'Steam-iOS.app'
    if root.is_relative_to(REPO):raise ValueError('Private copy outside repository required')
    info=plistlib.loads((app/'Info.plist').read_bytes())
    if info.get('CFBundleIdentifier')!='com.kuschqin.ideck.maclab.macprobe' or info.get('SHIMMacRoot')!='Mac':raise ValueError('Isolated app only')
    generated=root/'shims/Shim_IOKit.m';source=REPO/'experiments/mac-arm-steam/power-registration.c';receipt=root/'ideck-power-shim.json';receipt.unlink(missing_ok=True)
    # Generated IOKit stub source must not already define this overridden symbol.
    if 'IORegisterForSystemPower' in generated.read_text():raise ValueError('Unexpected generated symbol collision')
    sdk=subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip()
    output=app/'Frameworks/libShim_IOKit.dylib'
    with tempfile.TemporaryDirectory(prefix='.ideck-power-',dir=root) as folder:
        pending=Path(folder)/output.name
        subprocess.run(['xcrun','--sdk','iphoneos','clang','-fobjc-arc','-target','arm64-apple-ios17.0','-Wall','-Wextra','-Wno-unused-parameter','-dynamiclib','-install_name','@rpath/'+output.name,'-framework','Foundation','-Wl,-reexport_library,'+sdk+'/System/Library/Frameworks/IOKit.framework/IOKit.tbd','-Wl,-reexport_framework,SystemConfiguration',str(generated),str(source),'-o',str(pending)],check=True)
        if b'registration=unsupported session=0 port=null notifier=0' not in pending.read_bytes():raise ValueError('Final marker missing')
        pending.replace(output)
    receipt.write_text(json.dumps({'state':'unsigned','mode':'unsupported macOS power registration fails closed; real IOKit re-exported','inputs':{str(source.relative_to(REPO)):sha(source),'generated/Shim_IOKit.m':sha(generated),str(Path(__file__).resolve().relative_to(REPO)):sha(Path(__file__))},'outputSha256':sha(output)},indent=2)+'\n')
    print('IOKit shim compiled with documented registration failure; re-sign required')
if __name__=='__main__':main()
