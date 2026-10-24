#!/usr/bin/env python3
"""Packed shader cache (madeira-d3d12/src/unix/madeira_sc_pack.c), opt-in
through madeira.cfg d3d12-shader-pack = 1; no device.

1. Compiles madeira_sc_pack.c on the host (-Wall -Werror, AddressSanitizer
   and UndefinedBehaviorSanitizer) with a small harness and runs it:
   store/load round trip; 3000 keys; reopening rebuilds the index from the
   records; torn tails (a payload or a header cut short, a reservation that
   was never written in front of a complete record, a damaged last payload)
   are cut on open and the pack stays usable; damage further in is a miss at
   load, never wrong bytes; a build-id mismatch, another kind or a damaged
   header starts a fresh pack; loose files move in and are unlinked; the size
   bound drops a generation; 8 threads store and load concurrently, with and
   without generation drops. The concurrent part runs again under
   ThreadSanitizer.
2. Cuts the DXBC and DXIL cache code out of madeira_ir_unix.mm (the .mm
   itself needs Apple's SDK) and runs it against a temporary Documents
   directory, one process per launch: switch off writes and reads the loose
   files and creates no pack; switch on moves those loose entries into the
   packs as they are looked up, unlinks them and stores new conversions in
   the packs only, byte for byte what the loose writer writes; a later launch
   serves everything from the packs; switch off again ignores and leaves the
   packs alone; another build empties them; the game's own file sets the
   switch like madeira.cfg.
3. Source checks: the switch is read once with default 0, every pack path
   sits behind it and in front of the unchanged loose code, the build
   scripts compile the new file, and the settings catalog lists the key.

Needs cc and c++ on PATH.
"""
from pathlib import Path
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

root = Path(__file__).resolve().parents[2]
unix_dir = root / 'madeira-d3d12/src/unix'
pack_c = unix_dir / 'madeira_sc_pack.c'
unix = (unix_dir / 'madeira_ir_unix.mm').read_text()
pack_src = pack_c.read_text()
build_sh = (root / 'build/dxmt-ios/build.sh').read_text()
roundtrip_sh = (root / 'build/madeira-d3d12/build-ir-roundtrip.sh').read_text()
catalog = (root / 'app/Madeira/ConfigCatalog.generated.swift').read_text()
gen = (root / 'build/tools/gen-config-catalog.py').read_text()
cc = os.environ.get('CC') or shutil.which('cc') or shutil.which('clang') or shutil.which('gcc')
cxx = os.environ.get('CXX') or shutil.which('c++') or shutil.which('clang++') or shutil.which('g++')
failures = []


def check(cond, what):
    print(('PASS: ' if cond else 'FAIL: ') + what)
    if not cond:
        failures.append(what)


def between(text, start, end):
    i = text.index(start)
    return text[i:text.index(end, i)]


def body(text, signature):
    i = text.index(signature)
    j = text.index('{', i)
    depth = 0
    for k in range(j, len(text)):
        depth += {'{': 1, '}': -1}.get(text[k], 0)
        if depth == 0:
            return text[i:k + 1]
    raise SystemExit('unbalanced ' + signature)


def clean_env(docs, game=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith(('MADEIRA_', 'DXMT_'))}
    env['MADEIRA_DOCS_DIR'] = str(docs)
    env['UBSAN_OPTIONS'] = 'halt_on_error=1:print_stacktrace=1'
    if game:
        env['MADEIRA_CFG_GAME'] = str(game)
    return env


# ---------------------------------------------------------------------------
# 1. the pack on its own
# ---------------------------------------------------------------------------
UNIT = r'''
#define _DEFAULT_SOURCE
#include "madeira_sc_pack.h"

#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#define HDR 128u
#define REC 40u
#define BUILD "converter 0123456789abcdef"
#define CAP (256ull << 20)

static int fails;
#define CHECK(c, ...) do { if (!(c)) { fails++; printf("FAIL %s:%d: ", __func__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)
#define DONE(what) do { if (fails == f0) printf("PASS: %s\n", what); } while (0)

static const char *dir;

static void pack_path(const char *name, char *out, size_t cap) { snprintf(out, cap, "%s/%s.mdpk", dir, name); }
static size_t plen(uint64_t key) { return (size_t)(1 + (key * 2654435761u) % 9000u); }
static void fill(uint64_t key, unsigned char *b, size_t n)
{
    uint64_t x = key * 0x9e3779b97f4a7c15ull + 0x1234567ull;
    for (size_t i = 0; i < n; i++) { x ^= x << 13; x ^= x >> 7; x ^= x << 17; b[i] = (unsigned char)(x >> 24); }
}
static int put_n(struct mad_pack *p, uint64_t key, size_t n)
{
    unsigned char b[9001];
    fill(key, b, n);
    return mad_pack_put(p, key, b, n);
}
/* 1 if the pack serves exactly key's n bytes */
static int has_n(struct mad_pack *p, uint64_t key, size_t n)
{
    unsigned char b[9001];
    void *d = NULL;
    size_t got = 0;
    int ok;
    if (!mad_pack_get(p, key, &d, &got)) return 0;
    fill(key, b, n);
    ok = got == n && !memcmp(d, b, n);
    free(d);
    return ok;
}
#define put_key(p, k) put_n(p, k, plen(k))
#define has_key(p, k) has_n(p, k, plen(k))
static struct mad_pack_stats st(struct mad_pack *p) { struct mad_pack_stats s; mad_pack_get_stats(p, &s); return s; }
static long long fsize(const char *path) { struct stat s; return stat(path, &s) ? -1 : (long long)s.st_size; }
static void write_at(const char *path, long long off, const void *b, size_t n)
{
    int fd = open(path, O_WRONLY);
    CHECK(fd >= 0 && pwrite(fd, b, n, (off_t)off) == (ssize_t)n, "write %s", path);
    if (fd >= 0) close(fd);
}
static void read_at(const char *path, long long off, void *b, size_t n)
{
    int fd = open(path, O_RDONLY);
    CHECK(fd >= 0 && pread(fd, b, n, (off_t)off) == (ssize_t)n, "read %s", path);
    if (fd >= 0) close(fd);
}
static void flip(const char *path, long long off)
{
    unsigned char c = 0;
    read_at(path, off, &c, 1);
    c ^= 0x40;
    write_at(path, off, &c, 1);
}
static struct mad_pack *open_pack(const char *name, const char *build, uint64_t cap)
{
    return mad_pack_open(dir, name, MAD_PACK_KIND_DXBC, build, cap);
}

static void test_round_trip(void)
{
    int f0 = fails;
    char path[1024];
    void *d = NULL;
    size_t n = 0;
    struct mad_pack *p = open_pack("basic", BUILD, CAP);
    pack_path("basic", path, sizeof path);
    CHECK(p != NULL, "open");
    if (!p) return;
    CHECK(st(p).entries == 0 && st(p).bytes == HDR && fsize(path) == HDR, "a new pack is its header");
    CHECK(!mad_pack_get(p, 42, &d, &n) && !d && !n, "an unknown key misses");
    CHECK(mad_pack_put(p, 42, "hello", 5), "put");
    CHECK(mad_pack_get(p, 42, &d, &n) && n == 5 && !memcmp(d, "hello", 5), "round trip");
    free(d);
    CHECK(mad_pack_put(p, 42, "other", 5), "storing a stored key succeeds");
    CHECK(mad_pack_get(p, 42, &d, &n) && n == 5 && !memcmp(d, "hello", 5), "and keeps the first record");
    free(d);
    CHECK(st(p).bytes == HDR + REC + 5 && fsize(path) == HDR + REC + 5, "one record, no duplicate");
    CHECK(!mad_pack_put(p, 43, "", 0) && !mad_pack_put(p, 43, NULL, 5), "empty payloads are refused");
    CHECK(st(p).hits == 2 && st(p).misses == 1 && st(p).stored == 1, "counters");
    mad_pack_close(p);
    DONE("store/load round trip; a key is stored once");
}

static void test_many(void)
{
    int f0 = fails;
    uint64_t k, total = HDR;
    struct mad_pack *p = open_pack("many", BUILD, CAP);
    CHECK(p != NULL, "open");
    if (!p) return;
    for (k = 1; k <= 3000; k++) { CHECK(put_key(p, k), "put %llu", (unsigned long long)k); total += REC + plen(k); }
    for (k = 1; k <= 3000; k++) CHECK(has_key(p, k), "get %llu", (unsigned long long)k);
    CHECK(st(p).entries == 3000 && st(p).bytes == total, "3000 entries in %llu bytes", (unsigned long long)st(p).bytes);
    mad_pack_close(p);
    p = open_pack("many", BUILD, CAP);   /* the next process: the index comes from the records */
    CHECK(p && st(p).entries == 3000 && st(p).bytes == total && !st(p).torn, "reopened with every entry");
    if (!p) return;
    for (k = 1; k <= 3000; k++) CHECK(has_key(p, k), "get %llu after reopening", (unsigned long long)k);
    CHECK(!has_key(p, 3001), "and nothing else");
    mad_pack_close(p);
    DONE("3000 keys of 1..9000 bytes; reopening rebuilds the index by scanning the records");
}

static void test_torn(void)
{
    int f0 = fails;
    char path[1024], donor[1024];
    unsigned char zeros[REC + 100], rec51[REC + 9001];
    size_t r51 = REC + plen(51);
    struct mad_pack *p;
    long long good;
    uint64_t k;
    pack_path("torn", path, sizeof path);
    pack_path("donor", donor, sizeof donor);
    memset(zeros, 0, sizeof zeros);
    /* a complete record of key 51 from another pack of the same kind and build */
    p = open_pack("donor", BUILD, CAP);
    CHECK(p && put_key(p, 51), "donor");
    mad_pack_close(p);
    read_at(donor, HDR, rec51, r51);

    p = open_pack("torn", BUILD, CAP);
    CHECK(p != NULL, "open");
    if (!p) return;
    for (k = 1; k <= 50; k++) CHECK(put_key(p, k), "put");
    good = (long long)st(p).bytes;
    mad_pack_close(p);

    /* killed inside the last payload */
    CHECK(truncate(path, good - 3) == 0, "cut");
    p = open_pack("torn", BUILD, CAP);
    CHECK(p && st(p).entries == 49 && st(p).torn == REC + plen(50) - 3, "a payload cut short: its record is dropped");
    CHECK(fsize(path) == good - (long long)(REC + plen(50)), "and cut off the file");
    CHECK(p && !has_key(p, 50) && has_key(p, 49) && has_key(p, 1), "the others stay");
    CHECK(p && put_key(p, 50), "the pack takes new records");
    mad_pack_close(p);
    p = open_pack("torn", BUILD, CAP);
    CHECK(p && st(p).entries == 50 && !st(p).torn && has_key(p, 50), "and keeps them");
    mad_pack_close(p);

    /* killed inside a record header */
    CHECK(truncate(path, good - (long long)plen(50) - REC + 10) == 0, "cut");
    p = open_pack("torn", BUILD, CAP);
    CHECK(p && st(p).entries == 49 && st(p).torn == 10, "a header cut short: dropped");
    CHECK(p && put_key(p, 50), "put");
    mad_pack_close(p);

    /* two appends in flight: the first never written (zeros), the second complete */
    {
        int fd = open(path, O_WRONLY | O_APPEND);
        CHECK(fd >= 0 && write(fd, zeros, sizeof zeros) == (ssize_t)sizeof zeros &&
              write(fd, rec51, r51) == (ssize_t)r51, "append");
        if (fd >= 0) close(fd);
    }
    p = open_pack("torn", BUILD, CAP);
    CHECK(p && st(p).entries == 50 && st(p).torn == sizeof zeros + r51, "the pack ends at the hole");
    CHECK(p && has_key(p, 50) && !has_key(p, 51), "the record behind the hole goes with it");
    CHECK(fsize(path) == good, "cut at the hole");
    mad_pack_close(p);

    /* the file grew but the last payload never reached the disk */
    flip(path, good - 1);
    p = open_pack("torn", BUILD, CAP);
    CHECK(p && st(p).entries == 49 && st(p).torn == REC + plen(50), "a damaged last payload fails its checksum on open");
    CHECK(p && has_key(p, 49) && !has_key(p, 50), "and only that record goes");
    mad_pack_close(p);
    DONE("torn tails (payload or header cut short, a never-written reservation before a complete record, "
         "a damaged last payload) are cut on open and the pack stays usable");
}

static void test_damage_inside(void)
{
    int f0 = fails;
    char path[1024];
    struct mad_pack *p;
    pack_path("many", path, sizeof path);
    flip(path, HDR + REC + 7);   /* key 1's payload, at the start of a 13 MB pack */
    p = open_pack("many", BUILD, CAP);
    CHECK(p && st(p).entries == 3000 && !st(p).torn, "damage outside the tail window is not looked for on open");
    if (!p) return;
    CHECK(!has_key(p, 1) && st(p).bad == 1, "a load refuses it");
    CHECK(!has_key(p, 1) && st(p).bad == 1, "and does not read it again");
    CHECK(put_key(p, 1) && has_key(p, 1), "the next store replaces it");
    CHECK(has_key(p, 2), "neighbours are fine");
    mad_pack_close(p);
    p = open_pack("many", BUILD, CAP);
    CHECK(p && st(p).entries == 3000 && has_key(p, 1), "the later record wins after reopening");
    mad_pack_close(p);
    DONE("damage inside the file is a miss at load (checksum), never wrong bytes; the next store replaces it");
}

static void test_build(void)
{
    int f0 = fails;
    char path[1024];
    unsigned char junk[HDR];
    struct mad_pack *p;
    pack_path("many", path, sizeof path);
    p = open_pack("many", "converter fedcba9876543210", CAP);
    CHECK(p && st(p).entries == 0 && st(p).bytes == HDR && fsize(path) == HDR, "another build's pack is emptied");
    CHECK(p && !has_key(p, 2), "its entries are gone");
    CHECK(p && put_key(p, 7), "put");
    mad_pack_close(p);
    p = open_pack("many", "converter fedcba9876543210", CAP);
    CHECK(p && st(p).entries == 1 && has_key(p, 7), "the new build's entries persist");
    mad_pack_close(p);
    p = mad_pack_open(dir, "many", MAD_PACK_KIND_DXIL, "converter fedcba9876543210", CAP);
    CHECK(p && st(p).entries == 0, "a pack of the other kind is not read");
    mad_pack_close(p);
    memset(junk, 0xab, sizeof junk);
    write_at(path, 0, junk, sizeof junk);
    p = open_pack("many", BUILD, CAP);
    CHECK(p && st(p).entries == 0 && fsize(path) == HDR, "a damaged header starts the pack afresh");
    mad_pack_close(p);
    DONE("a build-id mismatch (or another kind, or a damaged header) starts a fresh pack");
}

static void test_migration(void)
{
    int f0 = fails;
    char loose[1024];
    unsigned char b[9001];
    void *d = NULL;
    size_t n = 0;
    uint64_t key = 0xabcdef;
    struct mad_pack *p = open_pack("migrate", BUILD, CAP);
    CHECK(p != NULL, "open");
    if (!p) return;
    snprintf(loose, sizeof loose, "%s/0000000000abcdef.mdsc", dir);
    fill(key, b, plen(key));
    for (int round = 0; round < 2; round++) {   /* the second: another thread moved the same entry in first */
        FILE *f = fopen(loose, "wb");
        CHECK(f && fwrite(b, 1, plen(key), f) == plen(key), "write the loose file");
        if (f) fclose(f);
        CHECK(mad_pack_read_file(loose, MAD_PACK_MAX_PAYLOAD, &d, &n) && n == plen(key) && !memcmp(d, b, n), "read it");
        CHECK(mad_pack_adopt(p, key, d, n, loose), "adopt");
        CHECK(access(loose, F_OK) != 0 && errno == ENOENT, "the loose file is gone");
        free(d);
        d = NULL;
    }
    CHECK(has_key(p, key) && st(p).migrated == 2 && st(p).entries == 1 && st(p).stored == 1,
          "one entry; both loose copies removed");
    mad_pack_close(p);
    p = open_pack("migrate", BUILD, CAP);
    CHECK(p && has_key(p, key), "the moved entry persists");
    mad_pack_close(p);
    CHECK(!mad_pack_read_file(loose, 100, &d, &n) && !d && !n, "a missing loose file is not read");
    { FILE *f = fopen(loose, "wb"); if (f) fclose(f); }
    CHECK(!mad_pack_read_file(loose, 100, &d, &n), "nor an empty one");
    { FILE *f = fopen(loose, "wb"); if (f) { fwrite(b, 1, 101, f); fclose(f); } }
    CHECK(!mad_pack_read_file(loose, 100, &d, &n), "nor one over the limit");
    CHECK(mad_pack_read_file(loose, 101, &d, &n) && n == 101 && !memcmp(d, b, 101), "one at the limit is");
    free(d);
    unlink(loose);
    DONE("migration: a loose file moves into the pack and is unlinked; the entry persists");
}

static void test_cap(void)
{
    int f0 = fails;
    char path[1024];
    const uint64_t cap = HDR + 10 * (REC + 1000);
    static unsigned char big[2 * 10 * (REC + 1000)];
    struct mad_pack *p = open_pack("cap", BUILD, cap);
    uint64_t k;
    pack_path("cap", path, sizeof path);
    CHECK(p != NULL, "open");
    if (!p) return;
    for (k = 1; k <= 25; k++) CHECK(put_n(p, k, 1000), "put %llu", (unsigned long long)k);
    CHECK(st(p).drops == 2 && st(p).entries == 5, "two generations dropped, %llu entries left", (unsigned long long)st(p).entries);
    CHECK(st(p).bytes == HDR + 5 * (REC + 1000) && fsize(path) == (long long)st(p).bytes, "the file is the last generation");
    for (k = 1; k <= 20; k++) CHECK(!has_n(p, k, 1000), "dropped %llu", (unsigned long long)k);
    for (k = 21; k <= 25; k++) CHECK(has_n(p, k, 1000), "kept %llu", (unsigned long long)k);
    memset(big, 1, sizeof big);
    CHECK(!mad_pack_put(p, 99, big, (size_t)cap), "an entry larger than the bound is refused");
    CHECK(st(p).drops == 2, "without dropping anything");
    mad_pack_close(p);
    p = open_pack("cap", BUILD, cap);
    CHECK(p && st(p).entries == 5 && has_n(p, 25, 1000), "the new generation persists");
    mad_pack_close(p);
    DONE("size bound: an append past it drops the generation and a new one starts; the file never passes it");
}

#define THREADS 8
#define PER 1000
#define SHARED 200
struct worker { struct mad_pack *p; int t, bad, drop; };
static void *worker_run(void *arg)
{
    struct worker *w = (struct worker *)arg;
    for (int i = 0; i < PER; i++) {
        uint64_t key = (uint64_t)w->t * PER + (uint64_t)i + 1, other;
        void *d;
        size_t n;
        if (w->drop) {   /* a small bound: generations drop while the others read and write */
            if (!put_n(w->p, key, 1000)) w->bad++;
            if (mad_pack_get(w->p, key, &d, &n)) {   /* may be gone already, but never wrong */
                unsigned char b[1000];
                fill(key, b, 1000);
                if (n != 1000 || memcmp(d, b, 1000)) w->bad++;
                free(d);
            }
            continue;
        }
        if (!put_key(w->p, key)) w->bad++;
        if (i % 4 == 0 && !put_key(w->p, 100000 + (uint64_t)(i / 4 + w->t) % SHARED)) w->bad++;
        if (i % 3 == 0 && !has_key(w->p, (uint64_t)w->t * PER + (uint64_t)(i / 2) + 1)) w->bad++;
        other = 100000 + (uint64_t)(i * 7 + w->t) % SHARED;
        if (i % 7 == 0 && mad_pack_get(w->p, other, &d, &n)) {   /* may not be stored yet, but never wrong */
            unsigned char b[9001];
            fill(other, b, plen(other));
            if (n != plen(other) || memcmp(d, b, n)) w->bad++;
            free(d);
        }
    }
    return NULL;
}

static void run_workers(struct mad_pack *p, int drop)
{
    struct worker w[THREADS];
    pthread_t th[THREADS];
    for (int t = 0; t < THREADS; t++) {
        w[t].p = p; w[t].t = t; w[t].bad = 0; w[t].drop = drop;
        CHECK(!pthread_create(&th[t], NULL, worker_run, &w[t]), "thread");
    }
    for (int t = 0; t < THREADS; t++) {
        pthread_join(th[t], NULL);
        CHECK(!w[t].bad, "thread %d: %d failed operations", t, w[t].bad);
    }
}

static void test_concurrent(void)
{
    int f0 = fails;
    uint64_t k;
    struct mad_pack *p = open_pack("threads", BUILD, CAP);
    CHECK(p != NULL, "open");
    if (!p) return;
    run_workers(p, 0);
    for (k = 1; k <= THREADS * PER; k++) CHECK(has_key(p, k), "key %llu", (unsigned long long)k);
    for (k = 100000; k < 100000 + SHARED; k++) CHECK(has_key(p, k), "shared key %llu", (unsigned long long)k);
    CHECK(st(p).entries == THREADS * PER + SHARED, "%llu entries", (unsigned long long)st(p).entries);
    mad_pack_close(p);
    p = open_pack("threads", BUILD, CAP);
    CHECK(p && st(p).entries == THREADS * PER + SHARED && !st(p).torn, "reopened intact");
    for (k = 1; p && k <= THREADS * PER; k++) CHECK(has_key(p, k), "key %llu after reopening", (unsigned long long)k);
    mad_pack_close(p);
    DONE("8 threads storing and loading at once (200 keys stored by several): every entry intact, before and after reopening");
}

static void test_concurrent_drop(void)
{
    int f0 = fails;
    char path[1024];
    const uint64_t cap = HDR + 64 * (REC + 1000);
    struct mad_pack *p = open_pack("drops", BUILD, cap);
    struct mad_pack_stats s;
    uint64_t k, live = 0;
    pack_path("drops", path, sizeof path);
    CHECK(p != NULL, "open");
    if (!p) return;
    run_workers(p, 1);
    s = st(p);
    CHECK(s.drops > 0 && s.entries <= 64 && s.bytes <= cap && fsize(path) == (long long)s.bytes,
          "%llu drops, %llu entries, %llu bytes", (unsigned long long)s.drops, (unsigned long long)s.entries,
          (unsigned long long)s.bytes);
    for (k = 1; k <= THREADS * PER; k++) live += has_n(p, k, 1000);
    CHECK(live == s.entries, "every indexed entry reads back (%llu of %llu)", (unsigned long long)live, (unsigned long long)s.entries);
    mad_pack_close(p);
    p = open_pack("drops", BUILD, cap);
    CHECK(p && st(p).entries == s.entries && !st(p).torn, "reopened intact");
    mad_pack_close(p);
    DONE("8 threads against a small bound: generations drop under load, the file stays under the bound and intact");
}

int main(int argc, char **argv)
{
    if (argc < 2) return 2;
    dir = argv[1];
    if (argc > 2 && !strcmp(argv[2], "concurrent")) {
        test_concurrent();
        test_concurrent_drop();
    } else {
        test_round_trip();
        test_many();
        test_torn();
        test_damage_inside();
        test_build();
        test_migration();
        test_cap();
        test_concurrent();
        test_concurrent_drop();
    }
    printf("%d failures\n", fails);
    return fails != 0;
}
'''

# ---------------------------------------------------------------------------
# 2. the converter service's cache code, cut out of madeira_ir_unix.mm
# ---------------------------------------------------------------------------
REGION_DXBC = between(unix, '#define MAD_SC_MAGIC', '/* ml1032/ml1033: VS/PS interpolant zero-fill')
REGION_DXIL = between(unix, 'static pthread_once_t g_dxc_once = PTHREAD_ONCE_INIT;',
                      '/* Pipelines are created from several threads at once')

SERVICE_PRELUDE = r'''
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#include "madeira_cfg.h"
#include "madeira_ir_abi.h"
#include "unix/madeira_dxil_cache.h"
#include "unix/madeira_sc_pack.h"
#define MADEIRA_IR_CONVERTER_ID TEST_CONVERTER_ID
static struct { int ident_ok; } g_ir;   /* mad_dxc_init_once reads the converter's identity */
'''

SERVICE_HARNESS = r'''
static int fails;
#define CHECK(c, ...) do { if (!(c)) { fails++; printf("FAIL %s:%d: ", __func__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)
static const char *docs, *ref;

struct conv {
    madeira_ir_convert_args a;
    madeira_ir_air_range r1[8], r2[8];
    unsigned char lib[4096];
    char entry[MADEIRA_IR_ENTRY_MAX];
    uint64_t len;
};

/* What compiling DXBC shader k left in the arguments. */
static void make(uint64_t k, conv *c)
{
    memset(c, 0, sizeof *c);
    c->len = 100 + (k * 37) % 3000;
    for (uint64_t i = 0; i < c->len; i++) c->lib[i] = (unsigned char)(k * 31 + i * 7);
    c->a.ret_backend = MADEIRA_IR_BACKEND_AIRCONV;
    c->a.ret_cb_table_bind = 29 + (uint32_t)(k % 2); c->a.ret_arg_table_bind = 30; c->a.ret_arg_qwords = (uint32_t)k;
    c->a.ret_air_nranges = (uint32_t)(k % 4);
    for (uint32_t i = 0; i < c->a.ret_air_nranges; i++) {
        c->r1[i].type = i % 4; c->r1[i].range_id = (uint32_t)k + i; c->r1[i].lower_bound = i;
        c->r1[i].size = 1; c->r1[i].ptr_offset = 2 * i;
    }
    c->a.ret_air_slot_mask = (uint32_t)k; c->a.ret_vs_input_count = (uint32_t)(k % 5);
    c->a.ret_tg_size[0] = (uint32_t)k; c->a.ret_tg_size[1] = 2; c->a.ret_tg_size[2] = 1;
    c->a.ret_cb_table_bind2 = c->a.ret_arg_table_bind2 = ~0u;
    if (k % 3 == 0) {   /* a tessellation object function: the hull's range set too */
        c->a.ret_air_nranges2 = 2;
        for (uint32_t i = 0; i < 2; i++) { c->r2[i].type = 1; c->r2[i].range_id = 100 + i; c->r2[i].lower_bound = 5 + i; c->r2[i].size = 1; }
        c->a.out_air_ranges2 = (uint64_t)(uintptr_t)c->r2;
        c->a.ret_cb_table_bind2 = 29; c->a.ret_arg_table_bind2 = 30; c->a.ret_arg_qwords2 = 4;
        c->a.ret_threads_per_patch = 3; c->a.ret_tess_out_prim = 2; c->a.ret_max_potential_factor = 64;
    }
    snprintf(c->entry, sizeof c->entry, "mdc_%016llx", (unsigned long long)k);
}

static void store(uint64_t k)
{
    conv c;
    make(k, &c);
    mad_sc_store(k, &c.a, c.r1, c.entry, c.lib, c.len);
}

/* ml1146: ranges counted but not handed over -- never stored, packed or not. */
static void store_without_ranges(uint64_t k)
{
    conv c;
    make(k, &c);
    c.a.ret_air_nranges = 2;
    mad_sc_store(k, &c.a, NULL, c.entry, c.lib, c.len);
}

/* A lookup as the converter makes one: the sizing call, then the fill call.
 * 0 on a miss; 1 when every output equals what the compile produced. */
static int load(uint64_t k)
{
    conv w;
    madeira_ir_convert_args a;
    madeira_ir_air_range r1[8], r2[8];
    unsigned char lib[4096];
    char entry[MADEIRA_IR_ENTRY_MAX] = "";
    int r;
    make(k, &w);
    memset(&a, 0, sizeof a); memset(r1, 0, sizeof r1); memset(r2, 0, sizeof r2);
    a.out_air_ranges = (uint64_t)(uintptr_t)r1; a.air_range_cap = 8;
    a.out_air_ranges2 = (uint64_t)(uintptr_t)r2; a.air_range_cap2 = 8;
    a.out_entry = (uint64_t)(uintptr_t)entry;
    r = mad_sc_load(k, &a, r1);
    if (!r) return 0;
    CHECK(r == 2 && a.ret_len == w.len && a.ret_status == MADEIRA_IR_BUFFER_TOO_SMALL, "key %llu: sizing call", (unsigned long long)k);
    a.out_buf = (uint64_t)(uintptr_t)lib; a.out_cap = sizeof lib;
    r = mad_sc_load(k, &a, r1);
    CHECK(r == 1, "key %llu: fill call", (unsigned long long)k);
    if (r != 1) return 0;
    CHECK(!memcmp(lib, w.lib, w.len) && a.ret_status == MADEIRA_IR_OK && a.ret_backend == w.a.ret_backend &&
          a.ret_cb_table_bind == w.a.ret_cb_table_bind && a.ret_arg_table_bind == w.a.ret_arg_table_bind &&
          a.ret_arg_qwords == w.a.ret_arg_qwords && a.ret_air_nranges == w.a.ret_air_nranges &&
          a.ret_air_slot_mask == w.a.ret_air_slot_mask && a.ret_vs_input_count == w.a.ret_vs_input_count &&
          !memcmp(a.ret_tg_size, w.a.ret_tg_size, sizeof a.ret_tg_size) &&
          a.ret_air_nranges2 == w.a.ret_air_nranges2 && a.ret_cb_table_bind2 == w.a.ret_cb_table_bind2 &&
          a.ret_arg_table_bind2 == w.a.ret_arg_table_bind2 && a.ret_arg_qwords2 == w.a.ret_arg_qwords2 &&
          a.ret_threads_per_patch == w.a.ret_threads_per_patch && a.ret_tess_out_prim == w.a.ret_tess_out_prim &&
          a.ret_max_potential_factor == w.a.ret_max_potential_factor &&
          !memcmp(r1, w.r1, sizeof r1) && !memcmp(r2, w.r2, sizeof r2) && !strcmp(entry, w.entry),
          "key %llu: every output of the compile comes back", (unsigned long long)k);
    return 1;
}

/* A DXIL entry as the converter builds it (key k, check ~k). */
static void *dxil_blob(uint64_t k, size_t *len)
{
    madeira_ir_loc locs[3];
    madeira_ir_vs_input vs[1];
    unsigned char lib[2000];
    mad_dxc_parts p;
    memset(locs, 0, sizeof locs); memset(vs, 0, sizeof vs); memset(&p, 0, sizeof p);
    for (uint32_t i = 0; i < 3; i++) { locs[i].type = i; locs[i].slot = (uint32_t)k + i; locs[i].size = 8; }
    snprintf(vs[0].name, sizeof vs[0].name, "POSITION");
    for (int i = 0; i < 2000; i++) lib[i] = (unsigned char)(k + (uint64_t)i * 3);
    p.stage = 1; p.entry = "main0"; p.note = "";
    p.locs = locs; p.nlocs = 3; p.vsin = vs; p.nvsin = 1; p.vs_input_count = 1;
    p.lib = lib; p.lib_len = 500 + k % 1000;
    return mad_dxc_blob_build(k, ~k, &p, len);
}

static int dxil_same(const void *got, size_t n, uint64_t k)
{
    size_t len = 0;
    void *want = dxil_blob(k, &len);
    int ok = want && n == len && !memcmp(got, want, len);
    free(want);
    return ok;
}

static void dxil_store(uint64_t k)
{
    size_t len = 0;
    void *b = dxil_blob(k, &len);
    mad_dxc_store(k, b, len);
    free(b);
}

/* The converter's DXIL lookup with the switch off (madeira_ir_convert_impl). */
static int dxil_load_loose(uint64_t k)
{
    char path[1200];
    void *b = NULL;
    size_t n = 0;
    int ok = mad_sc_path_ext(k, MAD_DXC_EXT, path, sizeof path) && mad_dxc_file_load(path, k, ~k, &b, &n);
    ok = ok && dxil_same(b, n, k);
    free(b);
    return ok;
}

static int dxil_load_pack(uint64_t k, uint64_t check)
{
    void *b = NULL;
    size_t n = 0;
    int ok = mad_dxc_pack_load(mad_dxc_pack(), k, check, &b, &n) && dxil_same(b, n, k);
    free(b);
    return ok;
}

static int exists(const char *base, uint64_t k, const char *ext)
{
    char path[1200];
    snprintf(path, sizeof path, "%s/shadercache/%016llx.%s", base, (unsigned long long)k, ext);
    return access(path, F_OK) == 0;
}

static int same_as_reference(uint64_t k)
{
    char path[1200];
    void *loose = NULL, *packed = NULL;
    size_t nl = 0, np = 0;
    int ok;
    snprintf(path, sizeof path, "%s/shadercache/%016llx.mdsc", ref, (unsigned long long)k);
    ok = mad_pack_read_file(path, 1u << 20, &loose, &nl) && mad_pack_get(g_sc_pack_dxbc, k, &packed, &np) &&
         nl == np && !memcmp(loose, packed, nl);
    free(loose);
    free(packed);
    return ok;
}

/* The first process of a fresh directory prunes in the background (it records
 * the build when done); let it finish before the next launch. */
static void settle(const char *base)
{
    char path[1200], got[128];
    snprintf(path, sizeof path, "%s/shadercache/.mdsc-build", base);
    for (int i = 0; i < 300; i++) {
        int fd = open(path, O_RDONLY);
        ssize_t n = fd >= 0 ? read(fd, got, sizeof got - 1) : -1;
        if (fd >= 0) close(fd);
        if (n > 0) { got[n] = 0; if (!strcmp(got, MAD_SC_BUILD)) return; }
        usleep(10000);
    }
}

int main(int argc, char **argv)
{
    const char *mode = argv[1];
    uint64_t k;
    mad_pack_stats s;
    docs = argv[2]; ref = argv[3];
    g_ir.ident_ok = 1;
    if (!strcmp(mode, "switch")) { printf("switch=%d\n", mad_sc_pack_on()); return 0; }
    pthread_once(&g_dxc_once, mad_dxc_init_once);

    if (!strcmp(mode, "loose")) {   /* switch off: what every launch did before */
        CHECK(!mad_sc_pack_on() && !mad_sc_pack_dxbc() && !mad_dxc_pack(), "the switch is off");
        for (k = 1; k <= 40; k++) store(k);
        store_without_ranges(1000);
        for (k = 1; k <= 40; k++) CHECK(exists(docs, k, "mdsc") && load(k), "loose DXBC entry %llu", (unsigned long long)k);
        CHECK(!exists(docs, 1000, "mdsc") && !load(1000), "ml1146 still refuses an entry without its ranges");
        for (k = 501; k <= 520; k++) dxil_store(k);
        for (k = 501; k <= 520; k++) CHECK(exists(docs, k, "mdxc") && dxil_load_loose(k), "loose DXIL entry %llu", (unsigned long long)k);
        settle(docs);
        /* reference bytes: the loose writer's output for the entries the packed run stores itself */
        setenv("MADEIRA_DOCS_DIR", ref, 1);
        for (k = 41; k <= 60; k++) store(k);
    } else if (!strcmp(mode, "pack")) {   /* the first launch with the switch on */
        CHECK(mad_sc_pack_on() && mad_sc_pack_dxbc() && mad_dxc_pack(), "the switch is on and both packs open");
        for (k = 1; k <= 40; k++) CHECK(load(k) && !exists(docs, k, "mdsc"), "DXBC entry %llu moved into the pack", (unsigned long long)k);
        for (k = 41; k <= 60; k++) store(k);
        store_without_ranges(1000);
        for (k = 41; k <= 60; k++) CHECK(!exists(docs, k, "mdsc") && load(k), "new DXBC entry %llu: pack only", (unsigned long long)k);
        for (k = 41; k <= 60; k++) CHECK(same_as_reference(k), "packed DXBC entry %llu is byte for byte the loose file", (unsigned long long)k);
        CHECK(!load(1000), "ml1146 refuses the entry without ranges in the pack too");
        for (k = 501; k <= 520; k++) CHECK(dxil_load_pack(k, ~k) && !exists(docs, k, "mdxc"), "DXIL entry %llu moved into the pack", (unsigned long long)k);
        for (k = 521; k <= 530; k++) dxil_store(k);
        for (k = 521; k <= 530; k++) CHECK(!exists(docs, k, "mdxc") && dxil_load_pack(k, ~k), "new DXIL entry %llu: pack only", (unsigned long long)k);
        CHECK(!dxil_load_pack(521, ~521ull ^ 1), "a DXIL entry whose check hash differs is not served");
        mad_pack_get_stats(g_sc_pack_dxbc, &s);
        CHECK(s.entries == 60 && s.migrated == 40, "DXBC pack: %llu entries, %llu moved in", (unsigned long long)s.entries, (unsigned long long)s.migrated);
        mad_pack_get_stats(g_dxc_pack, &s);
        CHECK(s.entries == 30 && s.migrated == 20, "DXIL pack: %llu entries, %llu moved in", (unsigned long long)s.entries, (unsigned long long)s.migrated);
    } else if (!strcmp(mode, "again")) {   /* the next launch: everything from the packs */
        for (k = 1; k <= 60; k++) CHECK(load(k) && !exists(docs, k, "mdsc"), "DXBC entry %llu from the pack", (unsigned long long)k);
        for (k = 501; k <= 530; k++) CHECK(dxil_load_pack(k, ~k), "DXIL entry %llu from the pack", (unsigned long long)k);
        mad_pack_get_stats(g_sc_pack_dxbc, &s);
        CHECK(s.entries == 60 && s.hits == 120 && !s.migrated && !s.stored, "DXBC pack: %llu hits", (unsigned long long)s.hits);
        mad_pack_get_stats(g_dxc_pack, &s);
        CHECK(s.entries == 30 && s.hits == 30 && !s.stored, "DXIL pack: %llu hits", (unsigned long long)s.hits);
    } else if (!strcmp(mode, "off")) {   /* switched off again: the packs are not read or written */
        CHECK(!mad_sc_pack_dxbc() && !mad_dxc_pack(), "the switch is off");
        for (k = 1; k <= 60; k++) CHECK(!load(k), "DXBC entry %llu is not looked for in the pack", (unsigned long long)k);
        for (k = 501; k <= 530; k++) CHECK(!dxil_load_loose(k), "DXIL entry %llu is not looked for in the pack", (unsigned long long)k);
        store(61);
        dxil_store(531);
        CHECK(exists(docs, 61, "mdsc") && load(61) && exists(docs, 531, "mdxc") && dxil_load_loose(531), "new entries are loose files again");
    } else if (!strcmp(mode, "rebuilt")) {   /* another converter identity, switch on */
        CHECK(mad_sc_pack_dxbc() && mad_dxc_pack(), "both packs open");
        mad_pack_get_stats(g_sc_pack_dxbc, &s);
        CHECK(s.entries == 0 && s.bytes == 128, "the DXBC pack of the earlier build was emptied");
        mad_pack_get_stats(g_dxc_pack, &s);
        CHECK(s.entries == 0 && s.bytes == 128, "the DXIL pack of the earlier build was emptied");
        CHECK(!load(41) && !dxil_load_pack(521, ~521ull), "the earlier build's entries are not served");
        settle(docs);   /* the loose prune this build's first lookup started */
    } else return 2;
    printf("%d failures\n", fails);
    return fails != 0;
}
'''


def build_and_run(tmp):
    t = Path(tmp)
    # --- 1. unit harness
    (t / 'unit.c').write_text(UNIT)
    exe = t / 'unit'
    r = subprocess.run([cc, '-std=c11', '-O1', '-g', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                        '-fno-sanitize-recover=undefined', '-pthread', '-DMAD_PACK_TAIL_CHECK=65536',
                        '-I' + str(unix_dir), str(t / 'unit.c'), str(pack_c), '-o', str(exe)],
                       capture_output=True, text=True)
    check(r.returncode == 0, 'madeira_sc_pack.c and its harness compile with -Wall -Wextra -Werror and ASan/UBSan'
          + ('' if not r.returncode else ':\n' + r.stderr[-3000:]))
    if r.returncode:
        return
    (t / 'unit-dir').mkdir()
    r = subprocess.run([str(exe), str(t / 'unit-dir')], capture_output=True, text=True, timeout=600,
                       env=clean_env(t / 'unit-dir'))
    sys.stdout.write(r.stdout)
    check(r.returncode == 0 and 'FAIL' not in r.stdout and 'runtime error' not in r.stderr,
          'pack unit tests pass under ASan/UBSan' + ('' if not r.returncode else ':\n' + r.stderr[-3000:]))
    log = r.stderr
    check(re.search(r'^\[madeira-ir\] shader pack many: 3000 entries, \d+\.\d MB, bound 256 MB$', log, re.M) is not None,
          'one open line: entries, MB and bound')
    check(re.search(r'^\[madeira-ir\] shader pack torn: 49 entries, \d+\.\d MB, torn tail of \d+ bytes cut, bound 256 MB$',
                    log, re.M) is not None, 'the open line names a torn tail')
    check('[madeira-ir] shader pack many: started empty (written by another build, ' in log and
          '[madeira-ir] shader pack many: started empty (unreadable header, ' in log,
          'the open line says why a pack starts empty')
    check(log.count('a new generation starts') >= 2, 'a dropped generation is logged')
    summaries = [l for l in log.splitlines() if ' lookups, ' in l]
    check(summaries and all(re.fullmatch(r'\[madeira-ir\] shader pack \w+: \d+ lookups, \d+ hits, \d+ misses, '
                                         r'\d+ moved in from loose files, \d+ stored; \d+ entries, \d+\.\d MB', l)
                            for l in summaries) and len(summaries) <= 12,
          f'hits/misses summaries: {len(summaries)} lines for the whole run, none per shader')

    # --- 1b. the concurrent part under ThreadSanitizer
    exe = t / 'unit-tsan'
    r = subprocess.run([cc, '-std=c11', '-O1', '-g', '-Wall', '-Werror', '-fsanitize=thread', '-pthread',
                        '-I' + str(unix_dir), str(t / 'unit.c'), str(pack_c), '-o', str(exe)],
                       capture_output=True, text=True)
    if r.returncode:
        print('SKIP: no ThreadSanitizer here (' + r.stderr.strip().splitlines()[-1][:200] + ')')
    else:
        (t / 'tsan-dir').mkdir()
        r = subprocess.run([str(exe), str(t / 'tsan-dir'), 'concurrent'], capture_output=True, text=True,
                           timeout=600, env=clean_env(t / 'tsan-dir'))
        if 'FATAL: ThreadSanitizer' in r.stderr:
            print('SKIP: ThreadSanitizer cannot run here (' + r.stderr.strip().splitlines()[0][:200] + ')')
        else:
            check(r.returncode == 0 and 'WARNING: ThreadSanitizer' not in r.stderr and 'FAIL' not in r.stdout,
                  'concurrent stores, loads and generation drops are race-free under ThreadSanitizer'
                  + ('' if not r.returncode else ':\n' + r.stdout[-1500:] + r.stderr[-3000:]))

    # --- 2. the service's cache code
    if not cxx:
        check(False, 'a C++ compiler (c++) on PATH')
        return
    obj = t / 'pack.o'
    r = subprocess.run([cc, '-std=c11', '-O1', '-g', '-Wall', '-Werror', '-fsanitize=address,undefined',
                        '-fno-sanitize-recover=undefined', '-c', str(pack_c), '-o', str(obj)],
                       capture_output=True, text=True)
    check(r.returncode == 0, 'madeira_sc_pack.c compiles for the service harness' + ('' if not r.returncode else ':\n' + r.stderr[-2000:]))
    exes = {}
    for name, ident in (('service', 'hosttest00000000'), ('service-rebuilt', 'hosttest11111111')):
        src = t / (name + '.cpp')
        src.write_text(SERVICE_PRELUDE.replace('TEST_CONVERTER_ID', '"' + ident + '"')
                       + REGION_DXBC + REGION_DXIL + SERVICE_HARNESS)
        exes[name] = t / name
        r = subprocess.run([cxx, '-std=c++20', '-O1', '-g', '-Wall', '-Werror', '-Wno-unused-function',
                            '-fsanitize=address,undefined', '-fno-sanitize-recover=undefined', '-pthread',
                            '-I' + str(root / 'build'), '-I' + str(root / 'madeira-d3d12/src'),
                            str(src), str(obj), '-o', str(exes[name])], capture_output=True, text=True)
        check(r.returncode == 0, f'the DXBC and DXIL cache code of madeira_ir_unix.mm compiles on the host ({name})'
              + ('' if not r.returncode else ':\n' + r.stderr[-3000:]))
        if r.returncode:
            return

    docs, ref = t / 'docs', t / 'ref'
    docs.mkdir()
    ref.mkdir()
    sc = docs / 'shadercache'
    cfg = docs / 'madeira.cfg'

    def launch(mode, cfg_text=None, game_text=None, exe='service'):
        if cfg_text is None:
            cfg.unlink(missing_ok=True)
        else:
            cfg.write_text(cfg_text)
        game = None
        if game_text is not None:
            game = t / 'game.cfg'
            game.write_text(game_text)
        r = subprocess.run([str(exes[exe]), mode, str(docs), str(ref)], capture_output=True, text=True,
                           timeout=300, env=clean_env(docs, game))
        ok = r.returncode == 0 and 'FAIL' not in r.stdout
        if not ok:
            print(r.stdout[-3000:] + r.stderr[-3000:])
        return ok, r.stdout, r.stderr

    def listing():
        return sorted(str(p.relative_to(sc)) for p in sc.rglob('*'))

    def digest(p):
        return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None

    ok, out, err = launch('loose')
    names = listing()
    check(ok and 'pack' not in names and 'shader pack' not in err and 'packed shader cache' not in err
          and len([n for n in names if n.endswith('.mdsc')]) == 40 and len([n for n in names if n.endswith('.mdxc')]) == 20,
          'switch off (no key): one loose file per entry as before, no pack directory, no pack log line')

    ok, out, err = launch('pack', 'gpu = 1\nd3d12-shader-pack = 1\n')
    names = listing()
    check(ok and names == ['.mdsc-build', 'pack', 'pack/dxbc.mdpk', 'pack/dxil.mdpk'],
          'switch on: earlier loose entries move into the packs as they are looked up, new ones go to the packs only, '
          'packed DXBC bytes equal the loose writer\'s; the directory holds two files: ' + ', '.join(names))
    check('[madeira-ir] packed shader cache ON (madeira.cfg d3d12-shader-pack)' in err
          and '[madeira-ir] shader pack dxbc: started empty (new file), bound 2048 MB' in err
          and '[madeira-ir] shader pack dxil: started empty (new file), bound 512 MB' in err,
          'switch on: the log names the switch and each pack as it opens (DXIL bound = the DXIL cache\'s 512 MB)')

    ok, out, err = launch('again', 'd3d12-shader-pack = 1\n')
    check(ok and listing() == names and re.search(r'shader pack dxbc: 60 entries, \d+\.\d MB, bound 2048 MB', err)
          and re.search(r'shader pack dxil: 30 entries, \d+\.\d MB, bound 512 MB', err),
          'next launch: all 60 DXBC and 30 DXIL entries come from the packs, nothing new on disk')

    before = (digest(sc / 'pack/dxbc.mdpk'), digest(sc / 'pack/dxil.mdpk'))
    ok, out, err = launch('off', 'd3d12-shader-pack = 0\n')
    check(ok and before == (digest(sc / 'pack/dxbc.mdpk'), digest(sc / 'pack/dxil.mdpk')) and 'shader pack' not in err
          and (sc / '000000000000003d.mdsc').exists(),
          'switch off again (= 0): the packs are neither read nor written, new entries are loose files')

    for cfg_text, game_text, want in ((None, 'd3d12-shader-pack = 1\n', 1),
                                      ('d3d12-shader-pack = 1\n', 'd3d12-shader-pack = 0\n', 0),
                                      ('d3d12-shader-pack = on\n', None, 1),
                                      ('d3d12-shader-pack = 2\n', None, 0),
                                      ('# d3d12-shader-pack = 1\n', None, 0)):
        ok, out, err = launch('switch', cfg_text, game_text)
        check(ok and out.strip() == f'switch={want}',
              f'switch: madeira.cfg {cfg_text!r}, game file {game_text!r} -> {want}')
    (t / 'game.cfg').unlink(missing_ok=True)

    ok, out, err = launch('rebuilt', 'd3d12-shader-pack = 1\n', exe='service-rebuilt')
    check(ok and '[madeira-ir] shader pack dxbc: started empty (written by another build, ' in err
          and '[madeira-ir] shader pack dxil: started empty (written by another build, ' in err,
          'another converter identity empties both packs when they open')


if not cc:
    check(False, 'a C compiler (cc) on PATH')
else:
    with tempfile.TemporaryDirectory() as tmp:
        build_and_run(tmp)

# ---------------------------------------------------------------------------
# 3. source checks
# ---------------------------------------------------------------------------
check(unix.count('madeira_cfg_bool("d3d12-shader-pack", 0)') == 1 and
      re.search(r'"d3d12-shader-pack"', (root / 'madeira-d3d12/src/pe/madeira_d3d12.c').read_text()) is None,
      'the switch is read once, by the service, with default 0 (madeira.cfg or the game\'s own file)')
for fn in ('static struct mad_pack *mad_sc_pack_dxbc(void)', 'static struct mad_pack *mad_dxc_pack(void)'):
    b = body(unix, fn)
    check(b.split('{', 1)[1].strip().startswith('if (!mad_sc_pack_on()) return NULL;'), fn + ': NULL unless switched on')
load = body(unix, 'static int mad_sc_load(uint64_t key, struct madeira_ir_convert_args *a,')
check(re.search(r'int fd;\s*struct mad_pack \*pack = mad_sc_pack_dxbc\(\);[^\n]*\n\s*if \(pack\) return mad_sc_load_packed\(pack, key, a, out_ranges\);\s*'
                r'if \(!mad_sc_path\(key, path, sizeof path\)\) return 0;\s*fd = open\(path, O_RDONLY\);', load) is not None
      and 'mad_sc_deliver(a, &h);' in load,
      'mad_sc_load: the pack branch comes first, then the loose reader as before')
store = body(unix, 'static void mad_sc_store(uint64_t key, const struct madeira_ir_convert_args *a,')
check(store.index('(a->ret_air_nranges && !ranges) || (a->ret_air_nranges2 && !a->out_air_ranges2)') <
      store.index('if ((pack = mad_sc_pack_dxbc()))') < store.index('if (!mad_sc_path(key, path, sizeof path)) return;')
      and 'mad_sc_header_fill(&h, a, entry, len);' in store and 'if (ok) rename(tmp, path); else unlink(tmp);' in store,
      'mad_sc_store: ml1146 first, then the pack branch, then the loose write-then-rename as before')
check('mad_sc_header_fill(&h, a, entry, len);' in body(unix, 'static void mad_sc_store_packed(')
      and 'mad_sc_deliver(a, &h);' in body(unix, 'static int mad_sc_load_mem('),
      'the packed writer and reader share the loose ones\' header code')
dstore = body(unix, 'static void mad_dxc_store(uint64_t key, const void *blob, size_t len)')
check(re.search(r'if \(pack\) \{ mad_pack_put\(pack, key, blob, len\); return; \}\s*'
                r'if \(!mad_sc_path_ext\(key, MAD_DXC_EXT, path, sizeof path\)\) return;', dstore) is not None,
      'mad_dxc_store: the pack branch, then the loose store as before')
check(re.search(r'int found = pack \? mad_dxc_pack_load\(pack, dxc_key, dxc_check, &hit, &hit_len\)\s*'
                r': \(mad_sc_path_ext\(dxc_key, MAD_DXC_EXT, path, sizeof path\) &&\s*'
                r'mad_dxc_file_load\(path, dxc_key, dxc_check, &hit, &hit_len\)\);', unix) is not None,
      'the DXIL lookup keeps its loose expression when the pack is off')
prune = body(unix, 'static void *mad_sc_prune_thread(void *arg)')
check('!strcmp(e->d_name + l - 5, ".mdsc")) || strstr(e->d_name, ".mdsc.tmp")' in prune,
      'the loose DXBC prune is unchanged')
check('opendir' not in pack_src and 'readdir' not in pack_src and
      'opendir' not in between(unix, 'madeira-bcd: the packed shader cache (madeira_sc_pack.c).', 'static int mad_sc_load('),
      'no bulk import of loose files (the switch can be per game)')
get = body(pack_src, 'int mad_pack_get(struct mad_pack *p, uint64_t key, void **data, size_t *len)')
append = body(pack_src, 'static int mad_pack_append(')
check('dprintf' not in get and get.count('mad_pack_summary(p)') == 1 and
      'if (lookups == 256 || lookups == 4096 || lookups == 65536) mad_pack_summary(p);' in get and
      'dprintf' not in body(pack_src, 'int mad_pack_put(') and append.count('dprintf(') == 2 and
      '    if (dropped)\n        dprintf(' in append and 'say = !p->write_fail++;' in append and
      '    if (say)\n        dprintf(' in append,
      'pack logging: no line per shader (three lookup summaries per pack and run; a dropped generation; '
      'the first failed write)')
block = between(build_sh, 'compile_objcxx_arc "$REPO_ROOT/madeira-d3d12/src/unix/madeira_ir_unix.mm"', '\nelse\n')
check('compile_c "$REPO_ROOT/madeira-d3d12/src/unix/madeira_sc_pack.c" madeira_sc_pack' in block
      and re.search(r'compile_c\(\) \{', build_sh) is not None,
      'build/dxmt-ios/build.sh compiles madeira_sc_pack.c with the service (into libdxmt_unix.a / libdxmt_combined.a)')
check('madeira_sc_pack.c' in roundtrip_sh and '"$OUT/sc_pack.o"' in roundtrip_sh,
      'build-ir-roundtrip.sh links it with the service too')
check(re.search(r'ConfigOption\(key: "d3d12-shader-pack", title: "[^"]+", kind: \.bool, defaultValue: "0", '
                r'category: "Direct3D 12", note: "[^"]*off by default[^"]*"', catalog, re.I) is not None
      and '"d3d12-shader-pack": {' in gen,
      'Settings catalog: d3d12-shader-pack, Direct3D 12, bool, default 0, off by default')

if failures:
    print('FAIL:')
    for f in failures:
        print('  - ' + f.splitlines()[0])
    sys.exit(1)
print('PASS: packed shader cache (d3d12-shader-pack): pack format, torn tails, build stamp, size bound, threads, '
      'migration, and the off path unchanged')
