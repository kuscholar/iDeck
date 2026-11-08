/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "LaunchProtocol.h"
#include "fs/dev.h"
#include "kernel/errno.h"
#include <stdlib.h>
#include <string.h>
#include <stdatomic.h>
#include <pthread.h>

#define LAB_BRIDGE_MAJOR 242
struct transaction { struct ideck_launch_response response; size_t offset; int consumed; pthread_mutex_t lock; };
static atomic_uint requests;
unsigned ideck_lab_bridge_requests(void) { return atomic_load(&requests); }
static int open_bridge(int major, int minor, struct fd *fd) {
    (void)major;
    if (minor) return _ENODEV;
    fd->data = calloc(1, sizeof(struct transaction));
    if (!fd->data) return _ENOMEM;
    struct transaction *t = fd->data;
    if (pthread_mutex_init(&t->lock, NULL)) { free(t); fd->data = NULL; return _ENOMEM; }
    return 0;
}
static ssize_t write_bridge(struct fd *fd, const void *bytes, size_t size) {
    struct transaction *t = fd->data;
    if (ideck_launch_validate(bytes, size)) return _EINVAL;
    struct ideck_launch_request r;
    memcpy(&r, bytes, sizeof r);
    pthread_mutex_lock(&t->lock);
    if (t->consumed) { pthread_mutex_unlock(&t->lock); return _EBUSY; }
    /* Diagnostic handler only: 125 means NOT launched. Never pretend a game ran. */
    t->response = (struct ideck_launch_response){IDECK_LAUNCH_MAGIC, IDECK_LAUNCH_VERSION, r.appid, 125};
    t->consumed = 1;
    atomic_fetch_add(&requests, 1);
    pthread_mutex_unlock(&t->lock);
    return (ssize_t)size;
}
static ssize_t read_bridge(struct fd *fd, void *bytes, size_t size) {
    struct transaction *t = fd->data;
    pthread_mutex_lock(&t->lock);
    if (!t->consumed) { pthread_mutex_unlock(&t->lock); return _EAGAIN; }
    size_t left = sizeof t->response - t->offset;
    if (size > left) size = left;
    memcpy(bytes, (const char *)&t->response + t->offset, size);
    t->offset += size;
    pthread_mutex_unlock(&t->lock);
    return (ssize_t)size;
}
static int close_bridge(struct fd *fd) {
    struct transaction *t = fd->data;
    pthread_mutex_destroy(&t->lock);
    free(t); fd->data = NULL; return 0;
}
static struct dev_ops bridge = {.open=open_bridge, .fd={.read=read_bridge, .write=write_bridge, .close=close_bridge}};
int ideck_lab_bridge_install(void) {
    if (char_devs[LAB_BRIDGE_MAJOR]) return _EBUSY;
    char_devs[LAB_BRIDGE_MAJOR] = &bridge;
    return 0;
}
int ideck_lab_bridge_major(void) { return LAB_BRIDGE_MAJOR; }
