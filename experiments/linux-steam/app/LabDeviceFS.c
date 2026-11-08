/* SPDX-License-Identifier: GPL-3.0-or-later
 * Interoperates with the iSH/LinuxRunner fakefs v3 metadata format documented
 * in pinned tools/fakefs.c and fs/fake-db.h. Upstream grants remain unchanged.
 */
#include "LabDeviceFS.h"
#include <sqlite3.h>
#include <stdio.h>
#include <stdint.h>
#include <errno.h>
#include <sys/stat.h>
#include <string.h>

static int directory(const char *path) {
    if (mkdir(path, 0700) && errno != EEXIST) return -1;
    struct stat s;
    return lstat(path, &s) || !S_ISDIR(s.st_mode) ? -1 : 0;
}
int lab_device_fs_prepare(const char *root, char *data_path, unsigned capacity) {
    char base[4096], dbpath[4096];
    int n = snprintf(base, sizeof base, "%s.devices", root);
    if (n < 0 || n >= (int)sizeof base || directory(base)) return -1;
    n = snprintf(data_path, capacity, "%s/data", base);
    if (n < 0 || (unsigned)n >= capacity || directory(data_path)) return -1;
    n = snprintf(dbpath, sizeof dbpath, "%s/meta.db", base);
    if (n < 0 || n >= (int)sizeof dbpath) return -1;
    struct stat existing;
    if (!lstat(dbpath, &existing)) return S_ISREG(existing.st_mode) ? 0 : -1;
    if (errno != ENOENT) return -1;
    sqlite3 *db = NULL;
    if (sqlite3_open_v2(dbpath, &db, SQLITE_OPEN_READWRITE | SQLITE_OPEN_CREATE, NULL) != SQLITE_OK) {
        if (db) sqlite3_close(db);
        return -1;
    }
    const char *schema = "BEGIN;"
        "CREATE TABLE meta(id INTEGER UNIQUE DEFAULT 0,db_inode INTEGER);"
        "INSERT INTO meta(db_inode) VALUES(0);"
        "CREATE TABLE stats(inode INTEGER PRIMARY KEY,stat BLOB);"
        "CREATE TABLE paths(path BLOB PRIMARY KEY,inode INTEGER REFERENCES stats(inode));"
        "CREATE INDEX inode_to_path ON paths(inode,path);"
        "PRAGMA user_version=3;";
    int ok = sqlite3_exec(db, schema, NULL, NULL, NULL) == SQLITE_OK;
    sqlite3_stmt *insert = NULL;
    uint32_t info[4] = {0040700, 0, 0, 0};
    if (ok) ok = sqlite3_prepare_v2(db, "INSERT INTO stats(inode,stat) VALUES(1,?)", -1, &insert, NULL) == SQLITE_OK;
    if (ok) ok = sqlite3_bind_blob(insert, 1, info, sizeof info, SQLITE_TRANSIENT) == SQLITE_OK;
    if (ok) ok = sqlite3_step(insert) == SQLITE_DONE;
    sqlite3_finalize(insert);
    if (ok) ok = sqlite3_exec(db, "INSERT INTO paths(path,inode) VALUES(X'',1);COMMIT;", NULL, NULL, NULL) == SQLITE_OK;
    sqlite3_close(db);
    return ok ? 0 : -1;
}
