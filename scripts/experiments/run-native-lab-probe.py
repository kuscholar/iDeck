#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Madeira Converter Exception: see LICENSE-EXCEPTION.md
"""Run ONE explicit diagnostic in an already installed isolated native lab.
No installation, signing, JIT, unlock, credential entry or process termination.
Raw outputs/device identifiers stay in a new private .madeira-install folder.
Diagnostic markers, not console transport exit alone, determine the outcome.
"""
import argparse,datetime,json,re,subprocess,urllib.parse
from pathlib import Path
REPO=Path(__file__).resolve().parents[2]
BUNDLE='com.kuschqin.ideck.maclab.macprobe'
PROBES={'vm-range':('IDeckNativeVMRangeProbe','[ideck-vm-range] complete=1 cleanup=1 memory-written=0 cef-integrated=0'),'synthetic-helper':('IDeckSyntheticHelperProbe','[ideck-synthetic-helper] diagnostic-result=0 steam-entry=0 cef=0 process-emulation=0'),'helper-load':('IDeckNativeHelperLoadProbe','diagnostic-result=0 error-text=REDACTED')}
def installed_lab(apps):
 selected=[a for a in apps if a.get('bundleIdentifier')==BUNDLE]
 if len(selected)!=1:raise ValueError('Isolated lab not installed; working iDeck cannot substitute')
 app=selected[0]
 if app.get('bundleVersion') not in ('12','13'):raise ValueError('Only audited Builds12/13 are supported; re-audit other versions')
 url=urllib.parse.urlparse(app.get('url',''));path=urllib.parse.unquote(url.path)
 if url.scheme!='file' or url.netloc or not path.startswith('/private/var/containers/Bundle/Application/') or not path.rstrip('/').endswith('/Steam-iOS.app') or '..' in Path(path).parts:raise ValueError('Unexpected installed lab URL')
 return path.rstrip('/')
def diagnostic_complete(name,output):
 if name not in PROBES:return False
 lines=output.replace('\r','').splitlines()
 if name=='vm-range':return PROBES[name][1] in lines and any(x.startswith('[ideck-vm-range] inventory=1 ') for x in lines)
 if name=='synthetic-helper':return PROBES[name][1] in lines and '[ideck-synthetic-helper] kind=bundle loaded=1 fixture-verified=1 main-called=0' in lines
 return any(x.startswith('[ideck-helper-load] begin=1 native-path=verified preflight=arm64-MH_EXECUTE ') for x in lines) and any(x.startswith('[ideck-helper-load] loaded=0 rejects-main-executable=1 ') and PROBES[name][1] in x for x in lines)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--device',required=True);p.add_argument('--probe',choices=sorted(PROBES),required=True);p.add_argument('--artifacts',type=Path,required=True);a=p.parse_args()
 if not re.fullmatch(r'[A-Fa-f0-9-]{16,64}',a.device):raise ValueError('Explicit device identifier required')
 folder=a.artifacts.resolve();private=(REPO.parent/'.madeira-install').resolve()
 if not folder.is_relative_to(private) or folder==private:raise ValueError('Choose a new private .madeira-install subfolder')
 folder.mkdir(parents=True,exist_ok=False)
 report={'probe':a.probe,'bundle':BUNDLE,'sourceRevision':subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),'started':datetime.datetime.now(datetime.timezone.utc).isoformat(),'steamUISuccess':False,'status':'preflight'}
 def command(args,label,timeout=35):
  r=subprocess.run(['xcrun','devicectl']+args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout);(folder/(label+'.log')).write_text(r.stdout)
  if r.returncode:raise ValueError(label+' failed; inspect private log')
  return r.stdout
 try:
  details=folder/'device.json';command(['device','info','details','--device',a.device,'--timeout','15','--json-output',str(details)],'details');d=json.loads(details.read_text())['result'];hardware=d.get('hardwareProperties',{});props=d.get('deviceProperties',{})
  if hardware.get('reality')!='physical':raise ValueError('Physical device required; simulator result cannot substitute')
  report['model']=hardware.get('productType');report['os']=props.get('osVersionNumber')
  lock=command(['device','info','lockState','--device',a.device,'--timeout','12'],'lock')
  if not re.search(r'passcodeRequired:\s*false',lock):raise ValueError('Native unlock required; no launch attempted')
  apps=folder/'apps.json';command(['device','info','apps','--device',a.device,'--filter','bundleIdentifier == "'+BUNDLE+'"','--timeout','15','--json-output',str(apps)],'apps');path=installed_lab(json.loads(apps.read_text())['result']['apps'])
  processes=command(['device','info','processes','--device',a.device,'--timeout','15'],'processes')
  if '/Steam-iOS.app/steam_osx' in processes:raise ValueError('Existing lab session preserved; diagnostic not started')
  env={'STEAM_APP_BUNDLE_PATH':path+'/Mac',PROBES[a.probe][0]:'1'}
  output=command(['device','process','launch','--device',a.device,'--console','--timeout','25','--environment-variables',json.dumps(env),'--',BUNDLE,'-nobootstrapperupdate','-skipinitialbootstrap','-noarchrestart'],'launch',45)
  okay=diagnostic_complete(a.probe,output);report['status']='diagnostic-complete' if okay else 'inconclusive';report['explicitMarkerVerified']=okay
  print('Probe:',a.probe,'status:',report['status'],'Steam UI success: NOT CLAIMED')
  if not okay:raise ValueError('Expected complete diagnostic marker absent; do not infer success from console exit')
 except Exception as error:
  report['error']=str(error);report['status']='blocked-or-inconclusive' if report['status']=='preflight' else report['status'];print('Stopped:',str(error));raise
 finally:(folder/'report.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
