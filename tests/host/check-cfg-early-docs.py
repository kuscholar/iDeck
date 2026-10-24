#!/usr/bin/env python3
"""madeira.cfg is found by native readers that run before the guest starts.

Reproduces the app's start-up order on a POSIX host with the production code:
  1. the WineProcessBridge.m constructor (madeira_docs_dir_early, extracted from
     the source) runs before main() while HOME is still the app container;
  2. the in-app wineserver thread sets HOME to the Wine prefix (Documents/wine);
  3. madsync_enabled() (extracted from build/madsync/madsync.c) reads
     inproc-sync through the production build/madeira_cfg.h.
It also checks that the old order (no early MADEIRA_DOCS_DIR, no container home)
really loses the user's choice, i.e. that the test covers the bug.

No Wine, SDK, device or credentials are needed. Run with python3. When swiftc is
available it also checks that the Swift reader (app/Madeira/MadeiraConfig.swift)
and the C reader agree on a file with a UTF-8 byte-order mark and CRLF endings.
"""
import os, re, shutil, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CC = os.environ.get("CC") or shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
SWIFTC = os.environ.get("SWIFTC") or shutil.which("swiftc")


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


def between(text, start, end, include_end=False):
    i = text.index(start)
    j = text.index(end, i + len(start))
    return text[i:j + (len(end) if include_end else 0)]


madsync = read("build/madsync/madsync.c")
bridge = read("app/Madeira/WineProcessBridge.m")
f_enabled = between(madsync, "int madsync_enabled(void)", "\n}\n", include_end=True)
f_early = between(bridge, "static const char *g_madeira_docs_early", "__attribute__((constructor))")
assert "madeira_cfg_sync_engine() == MADEIRA_SYNC_MADSYNC" in f_enabled, "madsync only when madeira.cfg selects it"
assert "[madsync] config inproc-sync=" in f_enabled
assert "__attribute__((constructor)) static void madeira_docs_dir_ctor" in bridge
assert "[config-dir] early MADEIRA_DOCS_DIR=" in bridge

harness_c = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "madeira_cfg.h"
''' + f_enabled + "\n" + f_early + r'''
int main(int argc, char **argv)
{
    const char *early = "not-run", *prefix = getenv("TEST_PREFIX");
    int on;
    if (argc > 1 && !strcmp(argv[1], "ctor")) early = g_madeira_docs_early = madeira_docs_dir_early();
    if (prefix) setenv("HOME", prefix, 1);          /* WineServerBridge.m: HOME = Wine prefix */
    on = madsync_enabled();                        /* wineserver's first object */
    printf("early=%s madsync=%d dir=%s\n", early, on, madeira_cfg_dir_source());
    return 0;
}
'''

harness_swift = '''
import Foundation
print("SWIFT inproc-sync=\\(MadeiraConfig.get("inproc-sync") ?? "unset")")
'''

with tempfile.TemporaryDirectory(prefix="madeira-cfg-early-") as tmp:
    tmp = Path(tmp)
    (tmp / "c.c").write_text(harness_c, encoding="utf-8")
    subprocess.run([CC, "-std=gnu11", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function",
                    "-Wno-unused-parameter", "-I", str(ROOT / "build"),
                    str(tmp / "c.c"), "-o", str(tmp / "c")], check=True)

    def container(name, cfg=None, legacy=None):
        home = tmp / name
        docs = home / "Documents"
        (docs / "wine").mkdir(parents=True)
        if cfg is not None: (docs / "madeira.cfg").write_bytes(cfg)
        if legacy is not None: (docs / "madeira-inproc-sync.txt").write_text(legacy)
        return home

    def base_env(home):
        env = {k: v for k, v in os.environ.items()
               if k not in ("MADEIRA_DOCS_DIR", "CFFIXED_USER_HOME", "MADEIRA_CFG_EARLY_DOCS")}
        env["HOME"] = str(home)
        return env

    def launch(home, ctor=True, cffixed=True, extra=None):
        env = base_env(home)
        if cffixed: env["CFFIXED_USER_HOME"] = str(home)
        env.update(extra or {})
        env["TEST_PREFIX"] = str(home / "Documents" / "wine")
        r = subprocess.run([str(tmp / "c"), "ctor" if ctor else "none"], check=True, capture_output=True,
                           text=True, env=env)
        m = re.search(r"early=(\S+) madsync=(\d) dir=(\S+)", r.stdout)
        assert m, r.stdout + r.stderr
        return dict(early=m.group(1), madsync=int(m.group(2)), dir=m.group(3), log=r.stderr)

    def check(ok, what, r=None):
        if not ok: raise SystemExit("FAIL: " + what + ("\n" + repr(r) if r else ""))
        print("ok:", what)

    # -- default: fastsync, so madsync is off when nothing is configured --
    home = container("absent")
    r = launch(home)
    check(r["early"] == "set" and r["dir"] == "env" and r["madsync"] == 0,
          "no madeira.cfg: constructor exports MADEIRA_DOCS_DIR, madsync off (fastsync is the default)", r)
    check("inproc-sync=unset cfg=absent dir=env" in r["log"], "log names value, file and directory", r)
    home = container("nokey", cfg=b"# user file\npool = 896\n")
    r = launch(home)
    check(r["madsync"] == 0 and "cfg=present" in r["log"], "madeira.cfg without inproc-sync: madsync off (fastsync is the default)", r)

    # -- explicit choices are honoured although HOME is the prefix when they are read --
    home = container("off", cfg=b"# user file\ninproc-sync = 0\n")
    r = launch(home)
    check(r["madsync"] == 0 and "inproc-sync=0 cfg=present dir=env" in r["log"], "inproc-sync = 0 honoured", r)
    home = container("on", cfg=b"inproc-sync = 1\n")
    r = launch(home)
    check(r["madsync"] == 1, "inproc-sync = 1 honoured", r)
    home = container("legacy", legacy="1\n")
    r = launch(home)
    check(r["madsync"] == 1, "no madeira.cfg: legacy madeira-inproc-sync.txt still honoured", r)

    # -- the bug: the old order (HOME = prefix, no MADEIRA_DOCS_DIR) misses the file --
    home = container("old-order", cfg=b"inproc-sync = 1\n")
    r = launch(home, ctor=False, cffixed=False)
    check(r["madsync"] == 0 and r["dir"] == "home", "old order ignores inproc-sync = 1 (bug reproduced)", r)
    # the container home alone (no constructor) is enough
    r = launch(home, ctor=False, cffixed=True)
    check(r["madsync"] == 1 and r["dir"] == "container", "CFFIXED_USER_HOME anchor alone finds the file", r)

    # -- byte-order mark and CRLF --
    home = container("bom", cfg=b"\xef\xbb\xbfinproc-sync = 1\r\npool = 896\r\n")
    r = launch(home)
    check(r["madsync"] == 1, "BOM + CRLF: first key still found", r)

    # -- kill switches restore the old lookup --
    home = container("kill-env", cfg=b"inproc-sync = 1\n")
    r = launch(home, extra={"MADEIRA_CFG_EARLY_DOCS": "0"})
    check(r["early"] == "off-env" and r["madsync"] == 0 and r["dir"] == "home",
          "MADEIRA_CFG_EARLY_DOCS=0 restores the old lookup", r)
    home = container("kill-cfg", cfg=b"env.MADEIRA_CFG_EARLY_DOCS = 0\ninproc-sync = 1\n")
    r = launch(home)
    check(r["early"] == "off-cfg" and r["madsync"] == 0 and r["dir"] == "home",
          "env.MADEIRA_CFG_EARLY_DOCS = 0 in madeira.cfg also restores it", r)

    # -- an existing MADEIRA_DOCS_DIR is kept --
    other = container("other", cfg=b"inproc-sync = 1\n")
    home = container("preset")
    r = launch(home, extra={"MADEIRA_DOCS_DIR": str(other / "Documents")})
    check(r["early"] == "already-set" and r["madsync"] == 1, "an exported MADEIRA_DOCS_DIR is left alone", r)

    # -- Swift and C agree on a BOM file (optional) --
    if SWIFTC:
        cfg_swift = read("app/Madeira/MadeiraConfig.swift")
        docs_expr = "FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first"
        assert docs_expr in cfg_swift
        # Linux Foundation resolves .documentDirectory from the passwd home, not
        # $HOME; point the test copy at $HOME/Documents (what iOS returns).
        cfg_swift = cfg_swift.replace(
            docs_expr, 'URL(fileURLWithPath: ProcessInfo.processInfo.environment["HOME"]! + "/Documents")')
        (tmp / "MadeiraConfig.swift").write_text(cfg_swift, encoding="utf-8")
        (tmp / "main.swift").write_text(harness_swift, encoding="utf-8")
        subprocess.run([SWIFTC, str(tmp / "MadeiraConfig.swift"), str(tmp / "main.swift"), "-o", str(tmp / "s")],
                       check=True)
        home = tmp / "bom"
        out = subprocess.run([str(tmp / "s")], check=True, capture_output=True, text=True,
                             env=base_env(home)).stdout
        check("SWIFT inproc-sync=1" in out, "Swift reader agrees on the BOM + CRLF file", out)
    else:
        print("skip: swiftc not found, Swift/C BOM agreement not checked")

print("PASS: madeira.cfg read from Documents before HOME moves to the prefix")
