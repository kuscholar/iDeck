#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Post ONE fixed event to an explicitly enabled Lab, never authentication UI.

Notification acceptance is not delivery or interaction proof. Inspect actual
native acknowledgement and the physical screen. Does not control ordinary iDeck.
"""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--device',required=True,help='Exact paired device ID from private run configuration')
p.add_argument('--output',type=Path,required=True,help='New private directory on easystore')
p.add_argument('action',choices=['library','big-picture','left','right','up','down','activate','back','page-down'])
a=p.parse_args();out=a.output.resolve()
assert str(out).startswith('/Volumes/easystore/') and not out.exists()
out.mkdir(mode=0o700,parents=True)
cmd=['xcrun','devicectl','device','notification','post','--device',a.device,'--timeout','25','--name','com.kuschqin.ideck.linuxlab.test-input.'+a.action,'--json-output',str(out/'notification-private.json')]
with (out/'cli-private.log').open('x') as log:result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
(out/'receipt.json').write_text(json.dumps({'exit':result.returncode,'action':a.action,'scope':'Notification transport only; NOT input delivery/physical touch/Steam UI success'},indent=2)+'\n')
raise SystemExit(result.returncode)
