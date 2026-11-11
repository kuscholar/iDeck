#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""HOST real loopback RFB tasks, held callbacks and interrupted handshake."""
import argparse,hashlib,json,socket,struct,subprocess,threading
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('control',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
out=a.output.resolve();assert str(out).startswith('/Volumes/easystore/') and not out.exists();out.mkdir(parents=True)
def exact(s,n):
    data=b''
    while len(data)<n:
        block=s.recv(n-len(data))
        if not block:raise EOFError
        data+=block
    return data
rows=[]
for mode in ['before-start','handshake-blocked','frame-held','input-held']:
    server=socket.socket();server.bind(('127.0.0.1',0));server.listen(1);server.settimeout(1);port=server.getsockname()[1];accepted=[];errors=[]
    def serve():
        try:
            s,_=server.accept();accepted.append(True)
            with s:
                s.settimeout(3)
                if mode=='handshake-blocked':
                    while s.recv(64):pass
                    return
                s.sendall(b'RFB 003.008\n');exact(s,12);s.sendall(b'\1\2');assert exact(s,1)==b'\2';s.sendall(bytes(16));exact(s,16);s.sendall(bytes(4));exact(s,1)
                s.sendall(struct.pack('!HH',32,16)+bytes(20));exact(s,20);header=exact(s,4);exact(s,struct.unpack('!H',header[2:])[0]*4);exact(s,10)
                s.sendall(b'\0\0\0\1'+struct.pack('!HHHHi',0,0,32,16,0)+bytes(2048))
                while s.recv(128):pass
        except (EOFError,ConnectionError):pass
        except (TimeoutError,socket.timeout):
            if mode!='before-start':errors.append('unexpected_timeout')
        except Exception as error:errors.append(type(error).__name__)
        finally:server.close()
    t=threading.Thread(target=serve);t.start()
    result=subprocess.run([str(a.control.resolve()),str(port),mode],capture_output=True,text=True,timeout=12);t.join(4)
    text=result.stdout+result.stderr;(out/(mode+'.log')).write_text(text)
    assert not t.is_alive() and result.returncode==0 and not errors,(mode,result.returncode,text,errors)
    assert bool(accepted)==(mode!='before-start'),(mode,accepted)
    rows.append(dict(mode=mode,status=result.returncode,peer_accepted=bool(accepted),log_sha256=hashlib.sha256(text.encode()).hexdigest()))
(out/'evidence.json').write_text(json.dumps(dict(scope='HOST actual socket/GCD lifetime controls; no iOS App/UI/Steam/game proof',tests=rows,control_sha256=hashlib.sha256(a.control.read_bytes()).hexdigest()),indent=2)+'\n')
print('Four actual RFB lifetime controls PASS; callback tasks must return before completion')
