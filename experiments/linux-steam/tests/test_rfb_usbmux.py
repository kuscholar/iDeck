# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
import importlib.util,plistlib,socket,struct,threading,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('lab_mux',Path(__file__).parents[1]/'tools/forward-lab-rfb.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class MuxControl(unittest.TestCase):
 def exchange(self,kind,response,device=None,bad_header=None):
  a,b=socket.socketpair();seen={}
  def server():
   try:
    size,version,msg,tag=struct.unpack('<IIII',m.exact(b,16));seen.update(plistlib.loads(m.exact(b,size-16)));body=plistlib.dumps(response);header=bad_header or (16+len(body),1,8,tag);b.sendall(struct.pack('<IIII',*header)+body)
   finally:b.close()
  t=threading.Thread(target=server);t.start()
  try:return m.request(a,kind,device=device),seen
  finally:a.close();t.join(timeout=2)
 def test_list_only(self):
  reply,seen=self.exchange('ListDevices',{'DeviceList':[]});self.assertEqual(reply,{'DeviceList':[]});self.assertEqual(seen['MessageType'],'ListDevices');self.assertNotIn('PairRecordID',seen)
 def test_connect_fixed_network_port(self):
  reply,seen=self.exchange('Connect',{'MessageType':'Result','Number':0},device=7);self.assertEqual(seen['PortNumber'],socket.htons(5993));self.assertEqual(seen['DeviceID'],7)
 def test_bad_tag_rejected(self):
  with self.assertRaises(ValueError):self.exchange('ListDevices',{},bad_header=(16,1,8,99))
 def test_oversize_rejected(self):
  with self.assertRaises(ValueError):self.exchange('ListDevices',{},bad_header=(m.MAX_PACKET+1,1,8,1))
 def test_pair_record_request_impossible(self):
  with self.assertRaises(ValueError):m.request(None,'ReadPairRecord')
 def test_exact_device_usb_preferred(self):
  rows=[{'DeviceID':3,'Properties':{'SerialNumber':'abc','ConnectionType':'Network'}},{'DeviceID':4,'Properties':{'SerialNumber':'ABC','ConnectionType':'USB'}},{'DeviceID':5,'Properties':{'SerialNumber':'abc2','ConnectionType':'USB'}}]
  self.assertEqual(m.choose_device({'DeviceList':rows},'abc'),(4,'USB'))
  with self.assertRaises(ValueError):m.choose_device({'DeviceList':rows},'ab')
 def test_invalid_connect_id_refused(self):
  for value in [True,0,-1,1<<32]:
   with self.assertRaises(ValueError):m.request(None,'Connect',device=value)
 def test_bounds_refused_before_transport(self):
  for seconds,limit in [(61,1),(0,1),(1,0),(1,65*1024*1024)]:
   with self.assertRaises(ValueError):m.relay(None,None,seconds=seconds,byte_limit=limit)
 def test_byte_cap_stops_transfer(self):
  client,left=socket.socketpair();right,server=socket.socketpair();result=[]
  def host():
   with left,right:result.append(m.relay(left,right,seconds=1,byte_limit=32))
  t=threading.Thread(target=host);t.start()
  with client,server:client.sendall(b'x'*64);t.join(timeout=2)
  self.assertFalse(t.is_alive());self.assertEqual(result[0]['reason'],'byte-cap')
 def test_bidirectional_binary_relay(self):
  client,left=socket.socketpair();right,server=socket.socketpair();results=[];sent=b'\x00test\xff'*30000
  def host():
   with left,right:results.append(m.relay(left,right,seconds=3))
  def remote():
   with server:
    data=bytearray()
    while len(data)<len(sent):
     chunk=server.recv(min(65536,len(sent)-len(data)))
     if not chunk:raise EOFError('fixture ended early')
     data.extend(chunk)
    server.sendall(data[::-1]);server.shutdown(socket.SHUT_WR)
  h=threading.Thread(target=host);r=threading.Thread(target=remote);h.start();r.start()
  with client:
   client.settimeout(4);client.sendall(sent);client.shutdown(socket.SHUT_WR);got=bytearray()
   while True:
    data=client.recv(65536)
    if not data:break
    got.extend(data)
  h.join(timeout=4);r.join(timeout=4);self.assertFalse(h.is_alive() or r.is_alive());self.assertEqual(got,sent[::-1]);self.assertEqual(results[0]['client_bytes'],len(sent));self.assertEqual(results[0]['server_bytes'],len(sent));self.assertEqual(results[0]['reason'],'eof')
if __name__=='__main__':unittest.main()
