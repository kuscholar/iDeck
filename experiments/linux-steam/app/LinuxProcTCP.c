/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * Optional Lab overlay included by fs/proc/net.c, never the ordinary runtime.
 * A best-effort snapshot of actual guest-owned TCP descriptions, not Darwin
 * process ownership or a fabricated Steam peer. No orphan/TIME_WAIT inventory,
 * queue/retransmit accounting, UDP, or separate network namespaces yet.
 */
#include <stdlib.h>
#include <netinet/tcp.h>
#include "kernel/task.h"
#include "fs/fd.h"
#include "kernel/fs.h"
#include "debug.h"

extern const struct fd_ops socket_fdops;
#define IDECK_TCP_SNAPSHOT_MAX 16384

static int ideck_tcp_state(int native) {
    /* Darwin TCP_CONNECTION_INFO tcpi_state uses the BSD state ABI (0..10),
     * documented in the macOS SDK tcp_fsm.h. That header is absent in iOS SDKs.
     * Translate the values, never report BSD numeric states as Linux states.
     * Physical iPad behavior is still a separate required control. */
    static const unsigned linux_state[] = {7,10,2,3,1,8,4,11,9,5,6};
    return native >= 0 && (unsigned)native < sizeof linux_state / sizeof *linux_state ? linux_state[native] : 0;
}

static void ideck_tcp_address(char *out, const struct sockaddr_storage *ss) {
    if (ss->ss_family == AF_INET) {
        const struct sockaddr_in *a = (const void *) ss;
        uint32_t word;
        memcpy(&word, &a->sin_addr, 4);
        snprintf(out, 40, "%08X:%04X", word, ntohs(a->sin_port));
    } else {
        const struct sockaddr_in6 *a = (const void *) ss;
        uint32_t word[4];
        memcpy(word, &a->sin6_addr, sizeof word);
        snprintf(out, 40, "%08X%08X%08X%08X:%04X", word[0], word[1], word[2], word[3], ntohs(a->sin6_port));
    }
}

static int ideck_proc_tcp_show(struct proc_data *buf, int family) {
    static atomic_uint observed;
    if (!atomic_fetch_add(&observed, 1)) printk("IDECK_TCP_VIEW_V1 guest-owned socket inventory\n");
    struct fdtable **tables = calloc(MAX_PID + 1, sizeof *tables);
    struct fd **sockets = calloc(IDECK_TCP_SNAPSHOT_MAX, sizeof *sockets);
    if (!tables || !sockets) { free(tables); free(sockets); return _ENOMEM; }
    size_t nt = 0, ns = 0;
    int err = 0;
    /* Never hold pids_lock while taking a table lock: proc fd scans use the
     * same retained-table ordering. Include non-leader unshared tables too. */
    lock(&pids_lock);
    for (unsigned i = 1; i <= MAX_PID; i++) {
        struct task *task = pid_get_task(i);
        if (!task || task->exiting || !task->files || !pid_view(i, current->pidns)) continue;
        size_t k = 0;
        while (k < nt && tables[k] != task->files) k++;
        if (k != nt) continue;
        tables[nt++] = task->files;
        task->files->refcount++;
    }
    unlock(&pids_lock);
    for (size_t i = 0; i < nt; i++) {
        lock(&tables[i]->lock);
        for (unsigned n = 0; n < tables[i]->size; n++) {
            struct fd *fd = tables[i]->files[n];
            if (!fd || fd->ops != &socket_fdops ||
                fd->socket.type != SOCK_STREAM ||
                fd->socket.domain != (family == AF_INET ? 2 : 10)) continue;
            size_t k = 0;
            while (k < ns && sockets[k] != fd) k++;
            if (k != ns) continue;
            if (ns == IDECK_TCP_SNAPSHOT_MAX) { err = _ENOSPC; break; }
            sockets[ns++] = fd_retain(fd);
        }
        unlock(&tables[i]->lock);
        if (err) break;
    }
    for (size_t i = 0; i < nt; i++) fdtable_release(tables[i]);
    free(tables);
    if (!err) {
        proc_printf(buf, "  sl  local_address %s st tx_queue rx_queue tr tm->when retrnsmt uid timeout inode\n",
                    family == AF_INET ? "rem_address" : "remote_address");
        for (size_t i = 0, row = 0; i < ns; i++) {
            struct fd *fd = sockets[i];
            struct sockaddr_storage local = {0}, peer = {0};
            socklen_t length = sizeof local;
            if (getsockname(fd->real_fd, (void *)&local, &length) || local.ss_family != family) continue;
            /* Linux does not list unbound TCP sockets in these hash tables. */
            if (!(family == AF_INET ? ((struct sockaddr_in *)&local)->sin_port :
                    ((struct sockaddr_in6 *)&local)->sin6_port)) continue;
            struct tcp_connection_info info = {0};
            length = sizeof info;
            if (getsockopt(fd->real_fd, IPPROTO_TCP, TCP_CONNECTION_INFO, &info, &length)) continue;
            int state = ideck_tcp_state(info.tcpi_state);
            if (!state) continue;
            length = sizeof peer;
            if (getpeername(fd->real_fd, (void *)&peer, &length)) peer.ss_family = family;
            char a[40], b[40];
            ideck_tcp_address(a, &local); ideck_tcp_address(b, &peer);
            proc_printf(buf, "%4zu: %s %s %02X 00000000:00000000 00:00000000 00000000 %u 0 %llu\n",
                row++, a, b, state, fd->stat.uid, (unsigned long long)fd->stat.inode);
        }
    }
    for (size_t i = 0; i < ns; i++) fd_close(sockets[i]);
    free(sockets);
    return err;
}
static int ideck_proc_tcp4(struct proc_entry *UNUSED(e), struct proc_data *buf) { return ideck_proc_tcp_show(buf, AF_INET); }
static int ideck_proc_tcp6(struct proc_entry *UNUSED(e), struct proc_data *buf) { return ideck_proc_tcp_show(buf, AF_INET6); }
