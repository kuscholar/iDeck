#!/usr/bin/env python3
from pathlib import Path
import tempfile,subprocess
root=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'main.swift').write_text('''import Foundation
let marker="# Isolated reserve-only contract test; no CEF observer"
let original=marker+"\\npool = 384\\npool-low = 1\\nenv.KEEP = 1\\n"
let result=MadeiraConfig.restoredProductBudget(original)!
assert(MadeiraConfig.parse(result)["pool"] == nil)
assert(MadeiraConfig.parse(result)["pool-low"] == "1")
assert(MadeiraConfig.parse(result)["env.KEEP"] == "1")
assert(MadeiraConfig.restoredProductBudget(result) == nil)
assert(MadeiraConfig.restoredProductBudget("pool = 384\\n") == nil)
assert(MadeiraConfig.restoredProductBudget(marker+"\\npool = 608\\n") == nil)
assert(MadeiraConfig.restoredProductBudget(original+"pool = 720\\n") == nil)
print("PASS exact experiment-marker migration, preservation, user overrides and idempotence")
''')
 subprocess.run(['swiftc','-module-cache-path',str(p/'cache'),str(root/'app/Madeira/MadeiraConfig.swift'),str(p/'main.swift'),'-o',str(p/'check')],check=True);subprocess.run([str(p/'check')],check=True)
