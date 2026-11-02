#!/usr/bin/env python3
"""Exercise the production numeric writer on actual files and concurrent threads.

No Wine, Mach VM, Valve binaries, credentials or device operations.
"""
from pathlib import Path
import json
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = r'''
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
static int evidence_clock(clockid_t id,struct timespec *t) {
 (void)id;if(getenv("CLOCK_FAILURE"))return -1;t->tv_sec=123;t->tv_nsec=456;return 0;
}
#define IDECK_CEF64_LEASE_CLOCK evidence_clock
#include "cef64_lease_file.h"
static void event(unsigned n,int layout) {
 errno=EDOM;
 ideck_cef64_lease_file(layout,n%3,n%20,0x1111f0000,0x7140000000,0x20000000,
                       0x10000,0x10000,0x8002,0,1,176,180);
 assert(errno==EDOM);
}
static void *worker(void *unused) {
 (void)unused;for(unsigned i=0;i<500;i++)event(i,1);return NULL;
}
int main(int argc,char **argv) {
 assert(argc==2);char path[4096],other[4096];
 snprintf(path,sizeof(path),"%s/drive_c/ideck-cef64-leases-%ld-123-456.txt",getenv("WINEPREFIX"),(long)getpid());
 snprintf(other,sizeof(other),"%s/drive_c/untouched.txt",getenv("WINEPREFIX"));
 if(!strcmp(argv[1],"symlink")) {
  FILE *f=fopen(other,"w");assert(f);fputs("UNTOUCHED",f);fclose(f);assert(!symlink(other,path));
 } else if(!strcmp(argv[1],"existing")) {
  FILE *f=fopen(path,"w");assert(f);fputs("UNTOUCHED",f);fclose(f);
 }
 if(!strcmp(argv[1],"concurrent")) {
  pthread_t t[8];for(unsigned i=0;i<8;i++)assert(!pthread_create(t+i,NULL,worker,NULL));
  for(unsigned i=0;i<8;i++)assert(!pthread_join(t[i],NULL));
 } else {
  event(0,strcmp(argv[1],"layout-off")!=0);
  if(!strcmp(argv[1],"replace")) {
   assert(!rename(path,other));FILE *f=fopen(path,"w");assert(f);fputs("UNTOUCHED",f);fclose(f);
  } else if(!strcmp(argv[1],"truncate")) { assert(!truncate(path,0)); }
  event(1,strcmp(argv[1],"layout-off")!=0);
 }
 puts("PASS errno and bounded writer execution");return 0;
}
'''
with tempfile.TemporaryDirectory(prefix="ideck-lease-evidence-") as td:
    td = Path(td)
    c, binary = td / "test.c", td / "test"
    c.write_text(source)
    subprocess.run(["clang", "-std=c11", "-Wall", "-Wextra", "-Werror", "-pthread",
                    "-fsanitize=address,undefined", "-I", str(root / "build/ntdll-unix"),
                    str(c), "-o", str(binary)], check=True)
    flags = ["MADEIRA_STEAM_UI_SESSION", "MADEIRA_CEF64_LEASE_TRACE", "MADEIRA_CEF64_LEASE_FILE"]
    def run(mode="basic", changes=None, suffix="wine-steam64"):
        directory = td / str(len(list(td.iterdir()))) / suffix
        drive = directory / "drive_c"
        drive.mkdir(parents=True)
        env = {**os.environ, **dict.fromkeys(flags, "1"), "WINEPREFIX": str(directory),
               "UBSAN_OPTIONS": "halt_on_error=1"}
        for key, value in (changes or {}).items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value
        subprocess.run([str(binary), mode], check=True, env=env, stdout=subprocess.DEVNULL)
        return drive, list(drive.glob("ideck-cef64-leases-*"))

    for key in flags:
        for bad in [None, "0", "11", "true", "1 "]:
            assert not run(changes={key: bad})[1]
    assert not run("layout-off")[1]
    assert not run(suffix="wine")[1]
    assert not run(changes={"CLOCK_FAILURE": "1"})[1]
    drive, files = run()
    rows = [json.loads(line) for line in files[0].read_text().splitlines()]
    assert [r["event"] for r in rows] == ["adopt", "refuse"]
    assert [r["seq"] for r in rows] == [1, 2]
    assert rows[0]["owner"] == "0x1111f0000" and rows[0]["remaining"] == 1
    assert files[0].stat().st_mode & 0o777 == 0o600
    assert set(rows[0]) == {"seq", "seconds", "nanos", "event", "slot", "owner", "base",
                           "size", "requested", "resolved", "type", "status", "remaining", "pid", "tid"}
    for mode in ["existing", "symlink", "replace"]:
        drive, files = run(mode)
        assert files[0].read_text() == "UNTOUCHED"
        if mode == "symlink":
            assert files[0].is_symlink() and (drive / "untouched.txt").read_text() == "UNTOUCHED"
        if mode == "replace":
            assert len((drive / "untouched.txt").read_text().splitlines()) == 1
    assert run("truncate")[1][0].stat().st_size == 0
    drive, files = run("concurrent")
    rows = [json.loads(line) for line in files[0].read_text().splitlines()]
    assert files[0].stat().st_size <= 512 * 1024
    assert rows[-1] == {"event": "budget-exhausted", "complete": False}
    assert 2 < len(rows) < 4097
    assert [r["seq"] for r in rows[:-1]] == list(range(1, len(rows)))
print("PASS production writer ASan/UBSan: gates, privacy schema, errno, no overwrite/symlink/replacement/truncation, concurrent budget and JSON framing")
