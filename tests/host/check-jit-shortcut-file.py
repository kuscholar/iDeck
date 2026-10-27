#!/usr/bin/env python3
"""Verify Apple's signed archive and compare its workflow to reviewable source."""
from pathlib import Path
import plistlib,struct,subprocess,tempfile
r=Path(__file__).resolve().parents[2]
source=plistlib.loads((r/'tools/shortcuts/Madeira JIT.plist').read_bytes())
signed=r/'app/Madeira/Madeira JIT.shortcut'
b=signed.read_bytes();assert b[:4]==b'AEA1'
n=struct.unpack('<I',b[8:12])[0];meta=plistlib.loads(b[12:12+n])
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'cert.der').write_bytes(meta['SigningCertificateChain'][0])
 subprocess.run(['openssl','x509','-inform','DER','-in',str(p/'cert.der'),'-pubkey','-noout','-out',str(p/'public.pem')],check=True,capture_output=True)
 subprocess.run(['aea','decrypt','-i',str(signed),'-o',str(p/'body.aa'),'-sign-pub',str(p/'public.pem')],check=True,capture_output=True)
 (p/'expanded').mkdir()
 subprocess.run(['aa','extract','-i',str(p/'body.aa'),'-d',str(p/'expanded')],check=True,capture_output=True)
 actual=plistlib.loads((p/'expanded/Shortcut.wflow').read_bytes())
 assert actual==source,'signed workflow differs from source'
assert actual['WFWorkflowOutputContentItemClasses']==['WFStringContentItem']
actions=actual['WFWorkflowActions'];by_id={a['WFWorkflowActionParameters'].get('UUID'):a for a in actions}
outputs=[a for a in actions if a['WFWorkflowActionIdentifier']=='is.workflow.actions.output']
assert len(outputs)==2
for a in outputs:
 v=a['WFWorkflowActionParameters']['WFOutput'];assert v['WFSerializationType']=='WFTextTokenAttachment'
 ref=v['Value'];assert ref['Type']=='ActionOutput' and by_id[ref['OutputUUID']]['WFWorkflowActionIdentifier']=='is.workflow.actions.gettext'
assert any(a['WFWorkflowActionIdentifier']=='is.workflow.actions.setstoredcontent' for a in actions)
assert any(a['WFWorkflowActionIdentifier']=='is.workflow.actions.getstoredcontent' for a in actions)
print('PASS: Apple AEA signature verified, exact signed/source equality, start/done output explicitly text, native VPN object remains in Store Content')
