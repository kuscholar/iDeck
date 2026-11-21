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
refresh_modes=['full-refresh','refresh-partial-reply','refresh-silent','refresh-empty-reply']
rows=[]
for mode in ['before-start','handshake-blocked','frame-held','input-held','wake-wire',*refresh_modes]:
    server=socket.socket();server.bind(('127.0.0.1',0));server.listen(1);server.settimeout(1);port=server.getsockname()[1];accepted=[];errors=[]
    received_wake=[];refresh_requests=[];partial_reply_sent=[]
    def serve():
        try:
            s,_=server.accept();accepted.append(True)
            with s:
                s.settimeout(3)
                if mode=='handshake-blocked':
                    while s.recv(64):pass
                    return
                s.sendall(b'RFB 003.008\n');exact(s,12);s.sendall(b'\1\2');assert exact(s,1)==b'\2';s.sendall(bytes(16));exact(s,16);s.sendall(bytes(4));exact(s,1)
                s.sendall(struct.pack('!HH',32,16)+bytes(20));exact(s,20);header=exact(s,4);exact(s,struct.unpack('!H',header[2:])[0]*4)
                initial=exact(s,10)
                frame_header=b'\0\0\0\1'+struct.pack('!HHHHi',0,0,32,16,0)
                s.sendall(frame_header+bytes(2048))
                if mode in refresh_modes:
                    assert struct.unpack('!BBHHHH',initial)==(3,0,0,0,32,16)
                    # Stay idle after the first update until the same viewer
                    # asks once for the full extent again.
                    for _ in range(2):
                        request=struct.unpack('!BBHHHH',exact(s,10))
                        assert request[0]==3 and request[2:]==(0,0,32,16)
                        refresh_requests.append(request[1])
                    assert sorted(refresh_requests)==[0,1]
                    if mode=='full-refresh':
                        s.sendall(frame_header+bytes([0x5a])*2048)
                    elif mode=='refresh-partial-reply':
                        s.sendall(frame_header+bytes([0x5a])*256)
                        partial_reply_sent.append(True)
                    elif mode=='refresh-empty-reply':
                        s.sendall(bytes(4))
                if mode=='wake-wire':
                    while len(received_wake)<3:
                        msg=exact(s,1)
                        if msg==b'\3':
                            exact(s,9) # FramebufferUpdateRequest can interleave.
                        else:
                            assert msg==b'\5'
                            received_wake.append(struct.unpack('!BHH',exact(s,5)))
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
    row=dict(mode=mode,status=result.returncode,peer_accepted=bool(accepted),log_sha256=hashlib.sha256(text.encode()).hexdigest())
    if mode=='wake-wire':
        assert received_wake==[(0,7,7),(1,15,7),(0,15,7)],received_wake
        assert 'move_press_release_written=3' in text
        row['received_pointer_packets']=received_wake
    if mode=='full-refresh':
        assert sorted(refresh_requests)==[0,1] and 'second_frame=1 same_connection=1' in text
        row['post_first_frame_requests']=refresh_requests
    if mode=='refresh-partial-reply':
        assert partial_reply_sent and sorted(refresh_requests)==[0,1]
        row['partial_reply_bytes']=256
    if mode in refresh_modes[1:]:
        expected={'refresh-partial-reply':(2,1),'refresh-silent':(1,1),'refresh-empty-reply':(2,2)}[mode]
        assert sorted(refresh_requests)==[0,1]
        assert f'started={expected[0]} decoded={expected[1]} published=1 reader_drained=1' in text
        row.update(started=expected[0],decoded=expected[1],published=1)
    rows.append(row)
(out/'evidence.json').write_text(json.dumps(dict(scope='HOST actual socket/GCD lifetime controls; no iOS App/UI/Steam/game proof',tests=rows,control_sha256=hashlib.sha256(a.control.read_bytes()).hexdigest()),indent=2)+'\n')
print('Four RFB lifetime controls plus wake and full/partial/silent/empty refresh loopback controls PASS')
