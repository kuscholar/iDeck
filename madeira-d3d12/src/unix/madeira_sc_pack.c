/* madeira-bcd: the packed shader cache (madeira.cfg d3d12-shader-pack = 1);
 * what it is for and the interface are in madeira_sc_pack.h.
 *
 * FILE (native byte order: the file never leaves the device)
 *
 *   offset 0   header, 128 bytes: "MDPK", format version, header size, the
 *              record kind, creation time, the build stamp the entries were
 *              converted by (MAD_SC_BUILD) and a checksum of the header
 *   then       records, back to back: a 40-byte record header -- "MDPR",
 *              kind, payload length, key, payload checksum and a checksum of
 *              those fields -- followed by the payload, byte for byte what the
 *              loose file of the same key would hold
 *
 * WRITES. Appending is the only write. A record's place is reserved under the
 * lock (the end offset moves past it) and filled by one pwrite outside it; the
 * record enters the index only after that pwrite returned. A lookup copies
 * offset and length under the lock and reads with pread. Every Wine process
 * runs inside the one iOS process, so the lock covers them all, and the file
 * stays open for the life of the process.
 *
 * TORN WRITES. iOS can kill the app at any moment, and several conversion
 * threads may be between reserving and writing their records when it does (a
 * reservation that was never written reads back as zeros). Opening walks the
 * records from the start, and the first one that is not complete and
 * self-consistent ends the pack: magic, kind, a length inside the file, the
 * header checksum and -- for records in the last MAD_PACK_TAIL_CHECK bytes,
 * where an interrupted append can be -- the payload checksum. The file is cut
 * there, so later appends continue from a clean end. Every load checks the
 * payload checksum again, so damage further in is a miss, never a wrong shader.
 *
 * BUILD. The header names the build its entries belong to. Opening a pack of
 * another build empties it, as mad_sc_prune_thread deletes the loose DXBC
 * entries of an earlier build: their keys include the build stamp, so they
 * would never be looked up again.
 *
 * SIZE BOUND. An append that would take the file past `cap` drops every entry
 * (the file is cut back to its header) and starts a new generation. That is
 * cruder than the loose DXIL cache's least-recently-used eviction, so the bound
 * is meant to be met rarely: madeira_ir_unix.mm gives the DXIL pack the DXIL
 * cache's own bound (MADEIRA_D3D12_DXIL_CACHE_MB, 512 MB by default) and the
 * DXBC pack 2 GB, where the loose DXBC entries had no bound at all. */
#ifndef _DEFAULT_SOURCE
#define _DEFAULT_SOURCE   /* pread, pwrite, ftruncate, dprintf under -std=c11 with glibc */
#endif
#include "madeira_sc_pack.h"

#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

#define MAD_PACK_MAGIC     0x4b50444du   /* "MDPK" */
#define MAD_PACK_REC_MAGIC 0x5250444du   /* "MDPR" */
#define MAD_PACK_VERSION   1u
/* Opening re-checks the payloads of the records that start in this last
 * stretch of the file: far more than every conversion thread together can
 * have had in flight when the app was killed. */
#ifndef MAD_PACK_TAIL_CHECK
#define MAD_PACK_TAIL_CHECK (8u << 20)
#endif

struct mad_pack_fhdr {
    uint32_t magic, version, hdr_size, kind;
    uint64_t created;
    uint64_t sum;          /* of these 128 bytes with sum = 0 */
    char build[96];        /* NUL-terminated */
};

struct mad_pack_rec {
    uint32_t magic, kind, len, reserved;
    uint64_t key;
    uint64_t sum;          /* of the payload */
    uint64_t hsum;         /* of the 32 bytes above */
};

_Static_assert(sizeof(struct mad_pack_fhdr) == 128, "pack header layout");
_Static_assert(sizeof(struct mad_pack_rec) == 40, "pack record header layout");

#define MAD_PACK_SEED_FILE 0x4d44504b66696c65ull
#define MAD_PACK_SEED_REC  0x4d44505272656331ull
#define MAD_PACK_SEED_DATA 0x4d44505264617461ull

/* len 0: the record failed its checks at load. A lookup misses, and the next
 * store of the key appends a fresh record. */
struct mad_pack_slot { uint64_t key, off; uint32_t len, used; };

struct mad_pack {
    pthread_mutex_t mu;    /* the index, end, broken and the counters */
    pthread_rwlock_t io;   /* shared around each pread/pwrite, exclusive to drop a generation */
    int fd;
    int broken;            /* a write failed short of the end: no more appends this run */
    uint32_t kind;
    char name[16];
    uint64_t cap, end;
    struct mad_pack_slot *tab;
    size_t tab_cap, tab_n;
    uint64_t hits, misses, stored, migrated, bad, drops, torn, write_fail;
};

/* 64-bit checksum. Every step is a bijection of the state, so two inputs of
 * one length that differ in a single 8-byte word always sum apart. It only has
 * to catch torn and damaged writes; nobody chooses the bytes. */
static uint64_t mad_pack_sum(const void *data, size_t n, uint64_t seed)
{
    const unsigned char *b = (const unsigned char *)data;
    uint64_t h = seed ^ ((uint64_t)n * 0x9e3779b97f4a7c15ull);
    for (; n >= 8; b += 8, n -= 8) {
        uint64_t w;
        memcpy(&w, b, 8);
        h ^= w; h *= 0x9e3779b97f4a7c15ull; h ^= h >> 29;
    }
    for (; n; b++, n--) { h ^= *b; h *= 0x9e3779b97f4a7c15ull; h ^= h >> 29; }
    h ^= h >> 32; h *= 0xff51afd7ed558ccdull; h ^= h >> 33;
    return h;
}

static int mad_pack_pread_all(int fd, void *buf, size_t n, uint64_t off)
{
    unsigned char *b = (unsigned char *)buf;
    while (n) {
        ssize_t r = pread(fd, b, n, (off_t)off);
        if (r < 0 && errno == EINTR) continue;
        if (r <= 0) return 0;
        b += r; n -= (size_t)r; off += (uint64_t)r;
    }
    return 1;
}

static int mad_pack_pwrite_all(int fd, const void *buf, size_t n, uint64_t off)
{
    const unsigned char *b = (const unsigned char *)buf;
    while (n) {
        ssize_t r = pwrite(fd, b, n, (off_t)off);
        if (r < 0 && errno == EINTR) continue;
        if (r <= 0) return 0;
        b += r; n -= (size_t)r; off += (uint64_t)r;
    }
    return 1;
}

/* ---- index: open addressing, linear probing ------------------------------ */

static size_t mad_pack_mix(uint64_t k)
{
    k ^= k >> 33; k *= 0xff51afd7ed558ccdull; k ^= k >> 33;
    return (size_t)k;
}

/* The slot holding `key`, or the empty slot where it would go. `cap` is a
 * power of two and the table is never full. */
static struct mad_pack_slot *mad_pack_probe(struct mad_pack_slot *tab, size_t cap, uint64_t key)
{
    size_t i = mad_pack_mix(key) & (cap - 1);
    while (tab[i].used && tab[i].key != key) i = (i + 1) & (cap - 1);
    return &tab[i];
}

static struct mad_pack_slot *mad_pack_find(struct mad_pack *p, uint64_t key)
{
    struct mad_pack_slot *s;
    if (!p->tab_cap) return NULL;
    s = mad_pack_probe(p->tab, p->tab_cap, key);
    return s->used ? s : NULL;
}

/* With mu held, or before the pack is shared. A later record of a key
 * replaces the earlier one. 0 only when out of memory. */
static int mad_pack_index(struct mad_pack *p, uint64_t key, uint64_t off, uint32_t len)
{
    struct mad_pack_slot *s;
    if ((p->tab_n + 1) * 4 > p->tab_cap * 3) {
        size_t ncap = p->tab_cap ? p->tab_cap * 2 : 1024, i;
        struct mad_pack_slot *nt = (struct mad_pack_slot *)calloc(ncap, sizeof *nt);
        if (!nt) return 0;
        for (i = 0; i < p->tab_cap; i++)
            if (p->tab[i].used) *mad_pack_probe(nt, ncap, p->tab[i].key) = p->tab[i];
        free(p->tab);
        p->tab = nt;
        p->tab_cap = ncap;
    }
    s = mad_pack_probe(p->tab, p->tab_cap, key);
    if (!s->used) { s->used = 1; s->key = key; p->tab_n++; }
    s->off = off;
    s->len = len;
    return 1;
}

/* ---- file ---------------------------------------------------------------- */

static int mad_pack_rec_ok(const struct mad_pack_rec *r, uint32_t kind)
{
    return r->magic == MAD_PACK_REC_MAGIC && r->kind == kind && !r->reserved &&
           r->len && r->len <= MAD_PACK_MAX_PAYLOAD &&
           mad_pack_sum(r, offsetof(struct mad_pack_rec, hsum), MAD_PACK_SEED_REC) == r->hsum;
}

static int mad_pack_hdr_read(int fd, uint32_t kind, struct mad_pack_fhdr *h)
{
    uint64_t sum;
    if (!mad_pack_pread_all(fd, h, sizeof *h, 0)) return 0;
    sum = h->sum;
    h->sum = 0;
    return h->magic == MAD_PACK_MAGIC && h->version == MAD_PACK_VERSION && h->hdr_size == sizeof *h &&
           h->kind == kind && memchr(h->build, 0, sizeof h->build) != NULL &&
           mad_pack_sum(h, sizeof *h, MAD_PACK_SEED_FILE) == sum;
}

/* Empties the file and writes the header for `build`. */
static int mad_pack_start(struct mad_pack *p, const char *build)
{
    struct mad_pack_fhdr h;
    memset(&h, 0, sizeof h);
    h.magic = MAD_PACK_MAGIC;
    h.version = MAD_PACK_VERSION;
    h.hdr_size = sizeof h;
    h.kind = p->kind;
    h.created = (uint64_t)time(NULL);
    snprintf(h.build, sizeof h.build, "%s", build);
    h.sum = mad_pack_sum(&h, sizeof h, MAD_PACK_SEED_FILE);
    if (ftruncate(p->fd, 0) != 0 || !mad_pack_pwrite_all(p->fd, &h, sizeof h, 0)) return 0;
    p->end = sizeof h;
    return 1;
}

/* Rebuilds the index from the records and cuts a torn tail off. 0 when the
 * file could not be read or the index not allocated: the file is then left
 * as it is, since nothing says its tail is torn. */
static int mad_pack_scan(struct mad_pack *p, uint64_t size)
{
    uint64_t off = sizeof(struct mad_pack_fhdr);
    unsigned char *buf = NULL;
    size_t bufcap = 0;
    int ok = 1;
    while (size - off >= sizeof(struct mad_pack_rec)) {
        struct mad_pack_rec r;
        if (!mad_pack_pread_all(p->fd, &r, sizeof r, off)) { ok = 0; break; }
        if (!mad_pack_rec_ok(&r, p->kind) || r.len > size - off - sizeof r) break;
        if (size - off <= MAD_PACK_TAIL_CHECK) {
            if (r.len > bufcap) {
                free(buf);
                bufcap = 0;
                if (!(buf = (unsigned char *)malloc(r.len))) { ok = 0; break; }
                bufcap = r.len;
            }
            if (!mad_pack_pread_all(p->fd, buf, r.len, off + sizeof r)) { ok = 0; break; }
            if (mad_pack_sum(buf, r.len, MAD_PACK_SEED_DATA) != r.sum) break;
        }
        if (!mad_pack_index(p, r.key, off, r.len)) { ok = 0; break; }
        off += sizeof r + r.len;
    }
    free(buf);
    if (!ok) return 0;
    p->end = off;
    if (off < size) {
        p->torn = size - off;
        /* If the cut fails, the next append overwrites the torn bytes, and the
         * open after that cuts whatever is left of them. */
        (void)!ftruncate(p->fd, (off_t)off);
    }
    return 1;
}

static double mad_pack_mb(uint64_t bytes) { return (double)bytes / (1024.0 * 1024.0); }

struct mad_pack *mad_pack_open(const char *dir, const char *name, uint32_t kind,
                               const char *build, uint64_t cap)
{
    struct mad_pack *p;
    struct mad_pack_fhdr h;
    struct stat st;
    char path[1200];
    const char *why = NULL;   /* why the pack starts empty */
    int e;

    if (!dir || !name || !build || strlen(name) >= sizeof p->name || strlen(build) >= sizeof h.build ||
        cap < sizeof h + sizeof(struct mad_pack_rec) + 1 ||
        snprintf(path, sizeof path, "%s/%s.mdpk", dir, name) >= (int)sizeof path)
        return NULL;
    mkdir(dir, 0755);   /* harmless if it exists */
    if (!(p = (struct mad_pack *)calloc(1, sizeof *p))) return NULL;
    p->kind = kind;
    p->cap = cap;
    snprintf(p->name, sizeof p->name, "%s", name);
    p->fd = open(path, O_RDWR | O_CREAT | O_CLOEXEC, 0644);
    if (p->fd < 0 || fstat(p->fd, &st) != 0) {
        e = errno;
        dprintf(2, "[madeira-ir] shader pack %s: cannot open %s (errno %d); the loose files stay in use\n",
                name, path, e);
        if (p->fd >= 0) close(p->fd);
        free(p);
        return NULL;
    }
    if (!st.st_size) why = "new file";
    else if (!mad_pack_hdr_read(p->fd, kind, &h)) why = "unreadable header";
    else if (strcmp(h.build, build)) why = "written by another build";
    if (why ? !mad_pack_start(p, build) : !mad_pack_scan(p, (uint64_t)st.st_size)) {
        e = errno;
        dprintf(2, "[madeira-ir] shader pack %s: cannot %s %s (errno %d); the loose files stay in use\n",
                name, why ? "write" : "read", path, e);
        close(p->fd);
        free(p->tab);
        free(p);
        return NULL;
    }
    pthread_mutex_init(&p->mu, NULL);
    pthread_rwlock_init(&p->io, NULL);
    if (why) {
        char old[64] = "";
        if (st.st_size) snprintf(old, sizeof old, ", %.1f MB removed", mad_pack_mb((uint64_t)st.st_size));
        dprintf(2, "[madeira-ir] shader pack %s: started empty (%s%s), bound %llu MB\n",
                name, why, old, (unsigned long long)(cap >> 20));
    } else {
        char torn[64] = "";
        if (p->torn) snprintf(torn, sizeof torn, ", torn tail of %llu bytes cut", (unsigned long long)p->torn);
        dprintf(2, "[madeira-ir] shader pack %s: %llu entries, %.1f MB%s, bound %llu MB\n",
                name, (unsigned long long)p->tab_n, mad_pack_mb(p->end), torn, (unsigned long long)(cap >> 20));
    }
    return p;
}

void mad_pack_get_stats(struct mad_pack *p, struct mad_pack_stats *s)
{
    memset(s, 0, sizeof *s);
    if (!p) return;
    pthread_mutex_lock(&p->mu);
    s->entries = p->tab_n;
    s->bytes = p->end;
    s->hits = p->hits;
    s->misses = p->misses;
    s->stored = p->stored;
    s->migrated = p->migrated;
    s->bad = p->bad;
    s->drops = p->drops;
    s->torn = p->torn;
    pthread_mutex_unlock(&p->mu);
}

static void mad_pack_summary(struct mad_pack *p)
{
    struct mad_pack_stats s;
    mad_pack_get_stats(p, &s);
    dprintf(2, "[madeira-ir] shader pack %s: %llu lookups, %llu hits, %llu misses, %llu moved in from loose files, "
               "%llu stored; %llu entries, %.1f MB\n", p->name,
            (unsigned long long)(s.hits + s.misses), (unsigned long long)s.hits, (unsigned long long)s.misses,
            (unsigned long long)s.migrated, (unsigned long long)s.stored, (unsigned long long)s.entries,
            mad_pack_mb(s.bytes));
}

int mad_pack_get(struct mad_pack *p, uint64_t key, void **data, size_t *len)
{
    struct mad_pack_slot *s;
    struct mad_pack_rec r;
    unsigned char *buf = NULL;
    uint64_t off = 0, lookups;
    uint32_t n = 0;
    int ok = 0, refused = 0;

    *data = NULL;
    *len = 0;
    if (!p) return 0;
    pthread_rwlock_rdlock(&p->io);
    pthread_mutex_lock(&p->mu);
    if ((s = mad_pack_find(p, key)) && s->len) { off = s->off; n = s->len; }
    pthread_mutex_unlock(&p->mu);
    if (n && (buf = (unsigned char *)malloc(sizeof r + n))) {
        ok = mad_pack_pread_all(p->fd, buf, sizeof r + n, off);
        if (ok) {
            memcpy(&r, buf, sizeof r);
            ok = mad_pack_rec_ok(&r, p->kind) && r.key == key && r.len == n &&
                 mad_pack_sum(buf + sizeof r, n, MAD_PACK_SEED_DATA) == r.sum;
        }
        refused = !ok;
    }
    pthread_mutex_lock(&p->mu);
    if (ok) p->hits++;
    else p->misses++;
    if (refused) {
        p->bad++;
        if ((s = mad_pack_find(p, key)) && s->off == off) s->len = 0;
    }
    lookups = p->hits + p->misses;
    pthread_mutex_unlock(&p->mu);
    pthread_rwlock_unlock(&p->io);
    /* A few summaries per run, never a line per shader. */
    if (lookups == 256 || lookups == 4096 || lookups == 65536) mad_pack_summary(p);
    if (!ok) { free(buf); return 0; }
    memmove(buf, buf + sizeof r, n);
    *data = buf;
    *len = n;
    return 1;
}

enum { MAD_PACK_STORED, MAD_PACK_HAD, MAD_PACK_FULL, MAD_PACK_FAILED };

/* One attempt to append a finished record of `len` payload bytes. With the
 * shared lock -- the usual case, many threads at once -- a record past the
 * bound returns MAD_PACK_FULL. With the exclusive lock (the retry after that)
 * no other read or write runs, so the generation is dropped and this record
 * still lands in the new one, however busy the other threads are. */
static int mad_pack_append(struct mad_pack *p, uint64_t key, const unsigned char *rec, size_t len,
                           int exclusive)
{
    struct mad_pack_slot *s;
    size_t total = sizeof(struct mad_pack_rec) + len;
    uint64_t off = 0, entries = 0, bytes = 0;
    int res, e = 0, say = 0, stop = 0, dropped = 0;

    if (exclusive) pthread_rwlock_wrlock(&p->io);
    else pthread_rwlock_rdlock(&p->io);
    pthread_mutex_lock(&p->mu);
    if (p->broken) res = MAD_PACK_FAILED;
    else if ((s = mad_pack_find(p, key)) && s->len) res = MAD_PACK_HAD;   /* another thread stored it */
    else if (p->end + total <= p->cap) res = MAD_PACK_STORED;
    else if (!exclusive) res = MAD_PACK_FULL;
    else if (ftruncate(p->fd, (off_t)sizeof(struct mad_pack_fhdr)) == 0) {   /* SIZE BOUND */
        entries = p->tab_n;
        bytes = p->end;
        if (p->tab) memset(p->tab, 0, p->tab_cap * sizeof *p->tab);
        p->tab_n = 0;
        p->end = sizeof(struct mad_pack_fhdr);
        p->drops++;
        dropped = 1;
        res = MAD_PACK_STORED;
    } else {
        p->broken = 1;
        res = MAD_PACK_FAILED;
    }
    if (res == MAD_PACK_STORED) { off = p->end; p->end += total; }
    pthread_mutex_unlock(&p->mu);

    if (res == MAD_PACK_STORED) {
        /* The one write of this record. Dropping a generation takes the lock
         * exclusively, which waits for this write, so `off` stays ours. */
        int ok = mad_pack_pwrite_all(p->fd, rec, total, off);
        if (!ok) e = errno;
        pthread_mutex_lock(&p->mu);
        if (ok && mad_pack_index(p, key, off, (uint32_t)len)) p->stored++;
        else if (ok) res = MAD_PACK_FAILED;   /* no memory for the index: the record stays unreferenced */
        else {
            /* The last reservation is handed back; one with records after it
             * would leave a hole in mid-file, so appends stop for this run
             * (the next open cuts the pack at the hole). */
            if (p->end == off + total) p->end = off;
            else { p->broken = 1; stop = 1; }
            say = !p->write_fail++;
            res = MAD_PACK_FAILED;
        }
        pthread_mutex_unlock(&p->mu);
    }
    pthread_rwlock_unlock(&p->io);
    if (dropped)
        dprintf(2, "[madeira-ir] shader pack %s: bound of %llu MB reached, %llu entries (%.1f MB) dropped, "
                   "a new generation starts\n", p->name, (unsigned long long)(p->cap >> 20),
                (unsigned long long)entries, mad_pack_mb(bytes));
    if (say)
        dprintf(2, "[madeira-ir] shader pack %s: a write failed (errno %d)%s\n", p->name, e,
                stop ? "; no more entries are added this run" : "");
    return res;
}

int mad_pack_put(struct mad_pack *p, uint64_t key, const void *data, size_t len)
{
    struct mad_pack_rec r;
    unsigned char *rec;
    int res;

    if (!p || !data || !len || len > MAD_PACK_MAX_PAYLOAD ||
        sizeof(struct mad_pack_fhdr) + sizeof r + len > p->cap)
        return 0;
    if (!(rec = (unsigned char *)malloc(sizeof r + len))) return 0;
    memset(&r, 0, sizeof r);
    r.magic = MAD_PACK_REC_MAGIC;
    r.kind = p->kind;
    r.len = (uint32_t)len;
    r.key = key;
    r.sum = mad_pack_sum(data, len, MAD_PACK_SEED_DATA);
    r.hsum = mad_pack_sum(&r, offsetof(struct mad_pack_rec, hsum), MAD_PACK_SEED_REC);
    memcpy(rec, &r, sizeof r);
    memcpy(rec + sizeof r, data, len);
    res = mad_pack_append(p, key, rec, len, 0);
    if (res == MAD_PACK_FULL) res = mad_pack_append(p, key, rec, len, 1);
    free(rec);
    return res == MAD_PACK_STORED || res == MAD_PACK_HAD;
}

int mad_pack_adopt(struct mad_pack *p, uint64_t key, const void *data, size_t len,
                   const char *loose_path)
{
    if (!mad_pack_put(p, key, data, len)) return 0;
    if (loose_path && !unlink(loose_path)) {
        pthread_mutex_lock(&p->mu);
        p->migrated++;
        pthread_mutex_unlock(&p->mu);
    }
    return 1;
}

int mad_pack_read_file(const char *path, size_t max, void **data, size_t *len)
{
    struct stat st;
    unsigned char *b = NULL;
    int fd = open(path, O_RDONLY | O_CLOEXEC);
    *data = NULL;
    *len = 0;
    if (fd < 0) return 0;
    if (fstat(fd, &st) != 0 || !S_ISREG(st.st_mode) || st.st_size <= 0 || (uint64_t)st.st_size > max ||
        !(b = (unsigned char *)malloc((size_t)st.st_size)) ||
        !mad_pack_pread_all(fd, b, (size_t)st.st_size, 0)) {
        close(fd);
        free(b);
        return 0;
    }
    close(fd);
    *data = b;
    *len = (size_t)st.st_size;
    return 1;
}

void mad_pack_close(struct mad_pack *p)
{
    if (!p) return;
    close(p->fd);
    free(p->tab);
    pthread_rwlock_destroy(&p->io);
    pthread_mutex_destroy(&p->mu);
    free(p);
}
