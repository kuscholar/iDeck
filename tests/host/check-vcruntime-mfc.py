#!/usr/bin/env python3
"""MFC from the VC++ redistributable (mfc140.dll, mfc140u.dll); no Wine runs.

Horizon Zero Dawn imports mfc140.dll and stopped at once with c0000135 (build
466, log 12:51:47). The workflow now takes MFC's two DLLs from the same
VC_redist.x64.exe it takes the C++ runtime from; WineProcessBridge.m links
every DLL of that folder into system32, and env.MADEIRA_MFC = 0 leaves MFC out.
Checks:
  - the workflow wants the twelve runtime DLLs plus mfc140.dll and mfc140u.dll,
    counts against the length of that list, and the report expects 14;
  - the payload names the search uses pick each MFC DLL and nothing else
    (not mfc140u for mfc140, not the language or managed MFC DLLs);
  - WineProcessBridge.m: MFC is linked like the rest unless MADEIRA_MFC=0,
    which also removes a link left from an earlier session; read from the
    environment the game's file was exported into before the links are made;
  - tools/fetch-vcruntime.md lists both; the catalog lists env.MADEIRA_MFC,
    on by default.
"""
from pathlib import Path
import fnmatch, re, sys

root = Path(__file__).resolve().parents[2]
ok = True


def check(what, cond):
    global ok
    print(("ok   " if cond else "FAIL ") + what)
    ok &= bool(cond)


# The fetch step exists only in the fork's workflow; upstream has no .github
# (the DLLs are fetched by hand there, tools/fetch-vcruntime.md).
wf_file = root / ".github/workflows/build-ipa.yml"
step = None
if wf_file.exists():
    wf = wf_file.read_text()
    step = wf[wf.index("- name: Fetch the VC++ runtime DLLs from Microsoft"):]
    step = step[:step.index("\n      - name:", 10)]
    want = re.search(r'WANT="([^"]+)"', step)
    names = want.group(1).split() if want else []
    check("the workflow wants the 12 runtime DLLs and MFC's two",
          len(names) == 14 and names[-2:] == ["mfc140.dll", "mfc140u.dll"] and "vcruntime140.dll" in names)
    check("counts follow the list", "NWANT=$(echo $WANT | wc -w | tr -d ' ')" in step
          and '[ "$FOUND" -eq "$NWANT" ] && break' in step and "recovered $FOUND of $NWANT" in step
          and "of 12" not in step)
    report = wf[wf.index("- name: Report vcruntime contents"):]
    report = report[:report.index("\n      - name:", 10)]
    check("the report expects 14", 'of 14' in report and '-lt 14' in report)

# The search: find -iname "$base.dll*" -o -iname "F_CENTRAL_${base}_*", case-insensitive.
payload = ["mfc140.dll_amd64", "mfc140.dll_arm64", "mfc140u.dll_amd64", "mfc140enu.dll_amd64",
           "mfcm140.dll_amd64", "mfcm140u.dll_amd64", "F_CENTRAL_mfc140u_x64", "MFC140.DLL_AMD64",
           "vcruntime140.dll_amd64"]


def found(base):
    pats = [base + ".dll*", "F_CENTRAL_%s_*" % base]
    return sorted(f for f in payload if any(fnmatch.fnmatch(f.lower(), p.lower()) for p in pats))


check("mfc140 finds only mfc140's payloads", found("mfc140") == ["MFC140.DLL_AMD64", "mfc140.dll_amd64", "mfc140.dll_arm64"])
check("mfc140u finds only mfc140u's payloads", found("mfc140u") == ["F_CENTRAL_mfc140u_x64", "mfc140u.dll_amd64"])
if step is not None:
    check("the arm64 build is then refused by the PE machine check", "== 0x8664" in step and "is_x64" in step)

m = (root / "app/Madeira/WineProcessBridge.m").read_text()
blk = m[m.index('const char *mfcEnv = getenv("MADEIRA_MFC");'):]
blk = blk[:blk.index('LOG("Symlinked %d MS VC++ Runtime DLLs')]
check("MFC is off only for MADEIRA_MFC=0", "BOOL mfcOff = mfcEnv && mfcEnv[0] == '0';" in blk)
check("off: the link is removed and the DLL skipped",
      re.search(r'if \(mfcOff\) \{\s*\[fm removeItemAtPath:dst error:nil\];.*?continue;', blk, re.S) is not None)
check("on: MFC goes through the same symlink as the runtime DLLs",
      blk.index('hasPrefix:@"mfc"') < blk.index("createSymbolicLinkAtPath:dst withDestinationPath:src"))
check("the game's env lines are exported before the links are made",
      m.index('const char *gameCfg = getenv("MADEIRA_CFG_GAME");') < m.index('const char *mfcEnv = getenv("MADEIRA_MFC");'))
doc = (root / "tools/fetch-vcruntime.md").read_text()
check("tools/fetch-vcruntime.md lists MFC", "mfc140.dll" in doc and "mfc140u.dll" in doc and "Fourteen files" in doc)
cat = (root / "app/Madeira/ConfigCatalog.generated.swift").read_text()
check("catalog lists env.MADEIRA_MFC, on by default",
      re.search(r'key: "env.MADEIRA_MFC".*kind: \.bool, defaultValue: "1"', cat) is not None)

print("PASS" if ok else "FAILED")
sys.exit(0 if ok else 1)
