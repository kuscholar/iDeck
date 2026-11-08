#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
"""Build pinned host-only Debian/fakefs tools; vendor source stays pristine."""
import argparse
from pathlib import Path
import subprocess

p=argparse.ArgumentParser(description=__doc__)
p.add_argument("source",type=Path)
p.add_argument("host_build",type=Path)
p.add_argument("output",type=Path)
a=p.parse_args()
src,host,out=a.source.resolve(),a.host_build.resolve(),a.output.resolve()
pin="d1419782da2e299fe22f1ddb85c70ae3d1e276b1"
assert subprocess.check_output(["git","-C",str(src),"rev-parse","HEAD"],text=True).strip()==pin
body=subprocess.check_output(["git","-C",str(src),"show",pin+":tools/fakefs.c"])
assert (src/"tools/fakefs.c").read_bytes()==body
(out/"source/tools").mkdir(parents=True,exist_ok=True)
(out/"source/tools/fakefs.c").write_bytes(body)
patch=Path(__file__).parents[1]/"patches/linuxrunner-fakefs-case-alias.patch"
subprocess.run(["/usr/bin/patch","--batch","-p1","-i",str(patch.resolve())],cwd=out/"source",check=True)
headers=src/"deps/libarchive/libarchive"
subprocess.run(["xcrun","clang","-DGUEST_ARM64=1","-DENGINE_ASBESTOS=1","-I",str(src),"-I",str(headers),
 str(src/"tools/fakefsify.c"),str(out/"source/tools/fakefs.c"),str(src/"util/fchdir.c"),str(host/"libfakefs.a"),
 "-larchive","-lsqlite3","-o",str(out/"fakefsify")],check=True)
subprocess.run(["xcrun","clang","-I",str(src),"-I",str(headers),str(src/"app/LinuxRunner/DebianBootstrap.c"),
 str(src/"tests/linuxrunner/debian-bootstrap-driver.c"),"-larchive","-o",str(out/"debian-bootstrap")],check=True)
print("Host bootstrap tools built; only same-inode case aliases accepted, no runtime/FEX change")
