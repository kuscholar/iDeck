#!/usr/bin/env python3
"""Exercise the actual file tail: pause parsing, keep raw data, skip backlog."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
main = r'''
import Foundation
let path = CommandLine.arguments[1]
try Data().write(to:URL(fileURLWithPath:path))
let lock = NSLock(), visible = DispatchSemaphore(value:0), future = DispatchSemaphore(value:0)
var hiddenCount = 0
let tail = LogTail(path:path) { line in
 if line == "visible" { visible.signal() }
 else if line == "future" { future.signal() }
 else if line == "hidden" { lock.lock();hiddenCount += 1;lock.unlock() }
}
func append(_ text:String) throws {
 let file = try FileHandle(forWritingTo:URL(fileURLWithPath:path))
 try file.seekToEnd();try file.write(contentsOf:Data(text.utf8));try file.close()
}
tail.start()
try append("visible\n")
precondition(visible.wait(timeout:.now()+4) == .success)
tail.setDisplayPaused(true);tail.setDisplayPaused(true)
Thread.sleep(forTimeInterval:0.3)
let bulk = String(repeating:"hidden\n",count:20000)
try append(bulk)
Thread.sleep(forTimeInterval:0.4)
lock.lock();let beforeResume = hiddenCount;lock.unlock();precondition(beforeResume == 0)
tail.setDisplayPaused(false);tail.setDisplayPaused(false)
Thread.sleep(forTimeInterval:0.3)
try append("future\n")
precondition(future.wait(timeout:.now()+4) == .success)
lock.lock();let afterResume = hiddenCount;lock.unlock();precondition(afterResume == 0)
tail.setDisplayPaused(true)
Thread.sleep(forTimeInterval:0.15)
tail.stop()
Thread.sleep(forTimeInterval:0.2)
let raw = try String(contentsOfFile:path,encoding:.utf8)
precondition(raw == "visible\n"+bulk+"future\n")
print("PASS actual LogTail: hidden lines unparsed, raw capture intact, resume skips backlog, repeated pause and paused stop balanced")
'''
with tempfile.TemporaryDirectory() as temp:
    p = Path(temp)
    (p/'main.swift').write_text(main)
    subprocess.run(['swiftc', str(root/'app/Madeira/LogTail.swift'), str(p/'main.swift'),
                    '-o', str(p/'check')], check=True)
    subprocess.run([str(p/'check'), str(p/'runtime.txt')], check=True, timeout=15)

view = (root/'app/Madeira/ContentView.swift').read_text()
assert '.onChange(of: ideck.running, initial: true)' in view
hook = view.split('.onChange(of: ideck.running, initial: true)', 1)[1].split('.onReceive(', 1)[0]
assert 'if IDeckState.enabled {' in hook and 'logStore.setDisplayActive(!running)' in hook
