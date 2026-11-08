#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""One bounded loopback observer for this paired Lab's app-local RFB port.

Protocol reference: libimobiledevice/libusbmuxd src/libusbmuxd.c (ListDevices,
Connect/htons). No pairing-record, credential, trust or lock operations. This is
host development tooling; Linux Steam and the product display run on the iPad.
"""
import argparse,json,plistlib,re,selectors,socket,struct,time
from pathlib import Path
MAX_PACKET=1024*1024
REMOTE_PORT=5993

def exact(stream,count):
    result=bytearray()
    while len(result)<count:
        chunk=stream.recv(count-len(result))
        if not chunk:raise EOFError('mux reply ended')
        result.extend(chunk)
    return bytes(result)

def request(stream,kind,tag=1,device=None):
    if kind not in ('ListDevices','Connect'):raise ValueError('unsupported mux operation')
    body={'MessageType':kind,'ProgName':'iDeckLinuxLab','ClientVersionString':'iDeck Linux Lab','kLibUSBMuxVersion':3}
    if kind=='Connect':
        if type(device) is not int or not 1<=device<=0xffffffff:raise ValueError('invalid device')
        body.update(DeviceID=device,PortNumber=socket.htons(REMOTE_PORT))
    packet=plistlib.dumps(body);stream.sendall(struct.pack('<IIII',16+len(packet),1,8,tag)+packet)
    size,version,kind_id,reply_tag=struct.unpack('<IIII',exact(stream,16))
    if not 16<=size<=MAX_PACKET or (version,kind_id,reply_tag)!=(1,8,tag):raise ValueError('invalid mux reply framing')
    reply=plistlib.loads(exact(stream,size-16))
    if not isinstance(reply,dict):raise ValueError('invalid mux reply')
    return reply

def choose_device(reply,udid):
    matches=[]
    for item in reply.get('DeviceList',[]):
        if not isinstance(item,dict):continue
        props=item.get('Properties')
        if not isinstance(props,dict) or not isinstance(props.get('SerialNumber'),str):continue
        if props['SerialNumber'].casefold()==udid.casefold() and props.get('ConnectionType') in ('USB','Network'):matches.append(item)
    matches.sort(key=lambda x:x.get('Properties',{}).get('ConnectionType')!='USB')
    if not matches:raise ValueError('selected device unavailable')
    item=matches[0]
    if type(item.get('DeviceID')) is not int or not 1<=item['DeviceID']<=0xffffffff:raise ValueError('invalid device identifier')
    return item['DeviceID'],item.get('Properties',{}).get('ConnectionType','unknown')

def mux():
    s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);s.settimeout(5)
    try:s.connect('/var/run/usbmuxd');return s
    except BaseException:s.close();raise

def relay(left,right,seconds=60,byte_limit=64*1024*1024):
    if not 0<seconds<=60 or not 0<byte_limit<=64*1024*1024:raise ValueError('invalid bounds')
    peers={left:right,right:left};pending={left:bytearray(),right:bytearray()};eof=set();closed_write=set();counts={left:0,right:0}
    deadline=time.monotonic()+seconds;reason='deadline';capacity=1024*1024
    for s in peers:s.setblocking(False)
    with selectors.DefaultSelector() as poll:
        while time.monotonic()<deadline:
            for key in list(poll.get_map().values()):poll.unregister(key.fileobj)
            for s,peer in peers.items():
                if s in eof and not pending[peer] and peer not in closed_write:
                    try:peer.shutdown(socket.SHUT_WR)
                    except OSError:pass
                    closed_write.add(peer)
                events=(selectors.EVENT_READ if s not in eof and len(pending[peer])<capacity else 0)
                if pending[s]:events|=selectors.EVENT_WRITE
                if events:poll.register(s,events)
            if len(eof)==2 and not any(pending.values()):reason='eof';break
            if not poll.get_map():reason='closed';break
            for key,events in poll.select(min(.2,max(0,deadline-time.monotonic()))):
                s=key.fileobj;peer=peers[s]
                try:
                    if events&selectors.EVENT_READ:
                        data=s.recv(65536)
                        if not data:eof.add(s)
                        else:
                            counts[s]+=len(data)
                            if counts[s]>byte_limit:return {'reason':'byte-cap','client_bytes':counts[left],'server_bytes':counts[right]}
                            pending[peer].extend(data)
                    if events&selectors.EVENT_WRITE and pending[s]:
                        sent=s.send(pending[s]);del pending[s][:sent]
                except BlockingIOError:pass
                except (ConnectionResetError,BrokenPipeError):return {'reason':'closed','client_bytes':counts[left],'server_bytes':counts[right]}
    return {'reason':reason,'client_bytes':counts[left],'server_bytes':counts[right]}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--udid',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--seconds',type=int,default=60);a=p.parse_args()
    if not re.fullmatch(r'[0-9A-Fa-f-]{20,48}',a.udid) or not 1<=a.seconds<=60:p.error('invalid device or duration')
    base=Path('/Volumes/easystore/GitHub/FunProjects/.madeira-install/linux-steam-ipad').resolve();out=a.output.resolve()
    if base not in out.parents or out.exists():p.error('use a new private task artifact directory')
    out.mkdir(mode=0o700,parents=True);report={'remote_port':REMOTE_PORT,'loopback_only':True,'pair_record_operations':False};start=time.monotonic()
    try:
        with mux() as control:device,transport=choose_device(request(control,'ListDevices'),a.udid)
        report['transport']=transport
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
            listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(a.seconds);port=listener.getsockname()[1]
            with (out/'ready.json').open('x') as f:json.dump({'port':port,'remote_port':REMOTE_PORT},f)
            print(json.dumps({'ready':True,'port':port,'remote_port':REMOTE_PORT}),flush=True)
            local,_=listener.accept()
            with local,mux() as remote:
                reply=request(remote,'Connect',tag=2,device=device)
                if reply.get('MessageType')!='Result' or reply.get('Number')!=0:raise ConnectionError('app port connection refused')
                report.update(relay(local,remote,seconds=max(.01,a.seconds-(time.monotonic()-start))))
    except Exception as error:report.update(reason='error',error_type=type(error).__name__)
    report['elapsed_seconds']=round(time.monotonic()-start,3)
    with (out/'result.json').open('x') as f:json.dump(report,f,indent=2)
    print(json.dumps(report));return int(report.get('reason')=='error')
if __name__=='__main__':raise SystemExit(main())
