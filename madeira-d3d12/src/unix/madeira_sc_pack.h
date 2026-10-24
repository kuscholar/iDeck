/* madeira-bcd: the packed shader cache (madeira.cfg d3d12-shader-pack = 1).
 *
 * The persistent caches of madeira_ir_unix.mm -- the DXBC entries of ml1020
 * (".mdsc") and the DXIL entries of ml1990 (".mdxc") -- write one file per
 * converted shader into Documents/shadercache; two Red Dead Redemption 2 runs
 * left 11,095 of them there. A pack keeps the entries of one kind in a single
 * append-only file instead, with an index (key -> offset, length) that is
 * rebuilt in memory when the process opens the file. See madeira_sc_pack.c
 * for the file format, torn writes, the build stamp and the size bound.
 *
 * Plain POSIX C with no converter or Objective-C types, so
 * tests/host/check-shader-pack.py builds and runs it on Linux. */
#ifndef MADEIRA_SC_PACK_H
#define MADEIRA_SC_PACK_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* What a record's payload is: byte for byte, the loose cache file of that kind. */
#define MAD_PACK_KIND_DXBC 1u   /* an ml1020 ".mdsc" entry */
#define MAD_PACK_KIND_DXIL 2u   /* an ml1990 ".mdxc" entry */

/* The largest payload a pack stores or trusts (MAD_DXC_MAX_FILE's value). */
#define MAD_PACK_MAX_PAYLOAD (64u << 20)

struct mad_pack;

struct mad_pack_stats {
    uint64_t entries;    /* keys in the index */
    uint64_t bytes;      /* the file: header and every record, live or not */
    uint64_t hits, misses, stored;
    uint64_t migrated;   /* loose files moved in (mad_pack_adopt) */
    uint64_t bad;        /* records refused at load (header or payload checksum) */
    uint64_t drops;      /* generations dropped at the size bound */
    uint64_t torn;       /* bytes cut off the tail when the pack was opened */
};

/* Opens dir/name.mdpk for records of `kind`, creating dir and the file when
 * needed. `build` is the build stamp the entries belong to; a pack written by
 * another build is emptied. `cap` bounds the file's size. NULL (and one log
 * line) when the pack cannot be used; the caller then keeps the loose files. */
struct mad_pack *mad_pack_open(const char *dir, const char *name, uint32_t kind,
                               const char *build, uint64_t cap);

/* 1 and a malloc'd copy of the payload stored under `key`, checked against its
 * checksum; else 0. The caller frees *data. */
int mad_pack_get(struct mad_pack *p, uint64_t key, void **data, size_t *len);

/* Appends `data` under `key` unless the key is already stored. 1 when the key
 * is in the pack afterwards. */
int mad_pack_put(struct mad_pack *p, uint64_t key, const void *data, size_t len);

/* Moves a loose entry in: mad_pack_put, then -- once the key is in the pack --
 * unlink(loose_path). */
int mad_pack_adopt(struct mad_pack *p, uint64_t key, const void *data, size_t len,
                   const char *loose_path);

/* Reads a whole regular file of 1..max bytes; the caller frees *data. */
int mad_pack_read_file(const char *path, size_t max, void **data, size_t *len);

void mad_pack_get_stats(struct mad_pack *p, struct mad_pack_stats *out);

/* Closes the file and frees the index. The runtime keeps its packs open for
 * the life of the process; this is for tests. */
void mad_pack_close(struct mad_pack *p);

#ifdef __cplusplus
}
#endif

#endif /* MADEIRA_SC_PACK_H */
