#!/usr/bin/env python3
"""Run actual endpoint selection and connection retry/cleanup with scripted failures."""
from pathlib import Path
import subprocess,tempfile,os
r=Path(__file__).resolve().parents[2]
core=r/'app/Madeira/SwiftSteam/Core'
s=(core/'SteamConnection.swift').read_text()
def function(signature):
 a=s.index(signature);return s[a:s.index('\n    }',a)+6]
methods='\n'.join(function(x) for x in ['    func connect() async throws {','    private func clearTransport() {','    func disconnect() {','    private func handleDisconnect(task:'])
methods=methods.replace('task: URLSessionWebSocketTask', 'task: FakeTask')
error=(core/'SteamError.swift').read_text();servers=(core/'CMServerList.swift').read_text()
h=r'''
import Foundation
enum SteamLog {static func trace(_ s:String){}; static func event(_ s:String){}}
extension CMServerList {
 func seed(_ count:Int){servers=(0..<count).map{CMServer(host:"cm\($0).steampowered.com",port:443)};lastFetched=Date()}
 func failures()->[Int]{servers.map{$0.failCount}}
}
final class FakeTask {enum CloseCode{case goingAway};var cancelled=false;func cancel(with:CloseCode,reason:Data?){cancelled=true}}
final class FakeSession {var invalidated=false;func invalidateAndCancel(){invalidated=true}}
actor Harness {
 let serverList:CMServerList
 var currentEndpoint:String?,activeConnect:UUID?
 var webSocketTask:FakeTask?,urlSession:FakeSession?
 var attempts:[String]=[],tasks:[FakeTask]=[],sessions:[FakeSession]=[]
 var receives=0;var codes:[Int?];var disconnectHandler:((Error?)->Void)?
 init(_ list:CMServerList,_ codes:[Int?]){serverList=list;self.codes=codes}
 func scheduleReceive(_ task:FakeTask){receives+=1}
 private func connect(to server:CMServerList.CMServer) async throws {
  currentEndpoint=server.endpoint;attempts.append(server.endpoint)
  let task=FakeTask(),session=FakeSession();tasks.append(task);sessions.append(session);webSocketTask=task;urlSession=session
  let code=codes.removeFirst()
  if let code {throw NSError(domain:NSURLErrorDomain,code:code,userInfo:[NSLocalizedDescriptionKey:"secret-token",NSURLErrorFailingURLErrorKey:URL(string:"https://private.invalid/?secret-token")!])}
 }
'''+methods+r'''
 func staleDisconnect(){handleDisconnect(task:tasks[0],error:nil)}
 func status()->(Int,Int,Int,Int){(attempts.count,receives,tasks.filter{$0.cancelled}.count,sessions.filter{$0.invalidated}.count)}
}
@main struct Main {
 static func main() async throws {
  for code in [-1201,-1202,-1203,-1204,-1205,-1206,-999,-1009] {assert(!SteamCMTransportPolicy.canTryAnotherServer(URLError(URLError.Code(rawValue:code))))}
  assert(SteamCMTransportPolicy.canTryAnotherServer(URLError(.secureConnectionFailed)))
  let list=CMServerList();await list.seed(3)
  let h=Harness(list,[-1200,-1003,nil]);try await h.connect()
  let status=await h.status();assert(status.0==3&&status.1==1&&status.2==2&&status.3==2)
  await h.staleDisconnect();let afterStale=await h.status();assert(afterStale.2==2&&afterStale.3==2)
  let names=await h.attempts;assert(Set(names).count==3)
  let failed=await list.failures();assert(failed==[1,1,0])
  let trustList=CMServerList();await trustList.seed(3);let trust=Harness(trustList,[-1202,nil])
  do {try await trust.connect();fatalError("trust failure accepted")} catch {
   assert((error as? SteamError) == .transportFailed(domain:NSURLErrorDomain,code:-1202))
   assert(!error.localizedDescription.contains("secret-token"))
  }
  let ts=await trust.status();assert(ts.0==1&&ts.1==0&&ts.2==1&&ts.3==1)
  let singleList=CMServerList();await singleList.seed(1);let single=Harness(singleList,[-1200])
  do {try await single.connect();fatalError("same endpoint retried")} catch {
   assert((error as? SteamError) == .transportFailed(domain:NSURLErrorDomain,code:-1200))
  }
  let ss=await single.status();assert(ss.0==1&&ss.2==1)
  let cancelList=CMServerList();await cancelList.seed(3);let cancelled=Harness(cancelList,[-999,nil])
  do {try await cancelled.connect();fatalError("cancel ignored")} catch {assert(error is CancellationError)}
  let cs=await cancelled.status();assert(cs.0==1&&cs.1==0&&cs.2==1)
  let allList=CMServerList();await allList.seed(5);let all=Harness(allList,[-1200,-1200,-1200,nil])
  do {try await all.connect();fatalError("budget exceeded")} catch {
   assert((error as? SteamError) == .transportFailed(domain:NSURLErrorDomain,code:-1200))
  }
  let a=await all.status();assert(a.0==3&&a.2==3&&a.3==3)
  print("PASS: production distinct CM selection, 3-attempt bound, actual cleanup calls, success marking, certificate fail-closed, cancellation, preserved code and payload redaction")
 }
}
'''
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'test.swift').write_text(error+'\n'+servers+'\n'+h)
 subprocess.run(['swiftc','-parse-as-library',str(p/'test.swift'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
assert 'cont.resume(throwing: error)' in s
assert 'guard webSocketTask === task else { return }' in s
assert 'serverList.getServer(excluding: tried)' in s
assert 'didReceive challenge' not in s,'no TLS trust override may be added'
