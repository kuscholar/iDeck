/* SPDX-License-Identifier: GPL-3.0-or-later
 * Experimental LinuxRunner packet-at-creation pipes, included only in a
 * generated lab translation unit. Original stream pipes remain unchanged.
 * Local datagrams preserve packets; endpoint state supplies Linux EOF/HUP.
 * Dynamic packet<->stream conversion is explicitly unsupported, never ignored.
 */
#include <sys/socket.h>
#include <sys/ioctl.h>
#include "fs/poll.h"

#define IDECK_PIPE_BUF 4096
struct packet_description;
struct packet_channel {
    pthread_mutex_t lock;
    struct list descriptions;
    atomic_uint readers, writers, descriptions_count;
    atomic_uint packets;
    atomic_uint payload_bytes;
    pthread_mutex_t io_lock;
    unsigned lengths[16], head, tail, queued_packets;
    lock_t capacity_lock;
    cond_t capacity_changed;
};
struct packet_description {
    struct packet_channel *channel;
    struct fd *fd;
    struct list link;
    bool writer;
};
static const struct fd_ops packet_pipe_ops;

/* The poll callback takes no channel lock: poll scans already hold poll->lock.
 * Notifications hold the channel list lock then fd->poll_lock/poll->lock.
 * Thus a readiness scan must never acquire the channel lock in reverse order. */
static void packet_notify(struct packet_channel *channel, bool writers, int events) {
    pthread_mutex_lock(&channel->lock);
    struct packet_description *description;
    list_for_each_entry(&channel->descriptions, description, link)
        if (description->writer == writers) poll_wakeup(description->fd, events);
    pthread_mutex_unlock(&channel->lock);
}
static int packet_poll(struct fd *fd) {
    struct packet_description *description = fd->data;
    struct packet_channel *channel = description->channel;
    if (description->writer) {
        int result=atomic_load(&channel->packets)<16 ? POLL_WRITE : 0;
        if (!atomic_load(&channel->readers)) result|=POLL_ERR;
        return result;
    }
    int result=atomic_load(&channel->payload_bytes)>0 ? POLL_READ : 0;
    if (!atomic_load(&channel->writers)) result |= POLL_HUP;
    return result;
}
static int packet_broken_pipe(void) { errno = EPIPE; return errno_map(); }
static int packet_reserve(struct fd *fd, struct packet_channel *channel) {
    lock(&channel->capacity_lock);
    for (;;) {
        if (!atomic_load(&channel->readers)) {unlock(&channel->capacity_lock);return _EPIPE;}
        if (atomic_load(&channel->packets)<16) {
            atomic_fetch_add(&channel->packets,1);
            unlock(&channel->capacity_lock);return 0;
        }
        if (pipe_getflags(fd)&O_NONBLOCK_) {unlock(&channel->capacity_lock);return _EAGAIN;}
        if (pipe_interrupted()) {unlock(&channel->capacity_lock);return _EINTR;}
        struct timespec cap={1,0};
        int error=wait_for(&channel->capacity_changed,&channel->capacity_lock,&cap);
        if (error && error!=_ETIMEDOUT) {unlock(&channel->capacity_lock);return error;}
    }
}
static void packet_release(struct packet_channel *channel) {
    lock(&channel->capacity_lock);
    atomic_fetch_sub(&channel->packets,1);
    notify(&channel->capacity_changed);
    unlock(&channel->capacity_lock);
}
static ssize_t packet_io(struct fd *fd, void *buffer, size_t size, bool writing) {
    struct packet_description *description = fd->data;
    struct packet_channel *channel = description->channel;
    if (description->writer != writing) return _EBADF;
    if (!size) return 0;
    size_t done = 0;
    for (;;) {
        if (writing && !atomic_load(&channel->readers))
            return done ? (ssize_t)done : packet_broken_pipe();
        if (writing) {
            int error=packet_reserve(fd,channel);
            if (error) return done ? (ssize_t)done : error==_EPIPE ? packet_broken_pipe() : error;
        }
        size_t count = writing && size - done > IDECK_PIPE_BUF ? IDECK_PIPE_BUF : size - done;
        pthread_mutex_lock(&channel->io_lock);
        ssize_t result = writing ? write(fd->real_fd, (char *)buffer + done, count) : read(fd->real_fd, buffer, count);
        int io_error=errno;
        if (result>0 && writing) {
            assert(channel->queued_packets<16);
            channel->lengths[channel->tail]=(unsigned)result;
            channel->tail=(channel->tail+1)%16;
            channel->queued_packets++;
            atomic_fetch_add(&channel->payload_bytes,(unsigned)result);
        } else if (result>0) {
            assert(channel->queued_packets>0);
            unsigned discarded_packet=channel->lengths[channel->head];
            channel->head=(channel->head+1)%16;
            channel->queued_packets--;
            atomic_fetch_sub(&channel->payload_bytes,discarded_packet);
        }
        pthread_mutex_unlock(&channel->io_lock);
        if (result >= 0) {
            if (!writing && result>0) packet_release(channel);
            packet_notify(channel, !writing, writing ? POLL_READ : POLL_WRITE);
            if (!writing) return result; /* Native datagram read discards a short-read tail. */
            done += (size_t)result;
            if (done == size) return (ssize_t)done;
            continue;
        }
        int error = io_error;
        if (writing) {packet_release(channel);packet_notify(channel,true,POLL_WRITE);}
        if (!writing && error == ECONNRESET && !atomic_load(&channel->writers)) return 0;
        if (writing && (error == ECONNRESET || error == EPIPE))
            return done ? (ssize_t)done : packet_broken_pipe();
        if (error == EINTR) {
            if (pipe_interrupted()) return done ? (ssize_t)done : _EINTR;
            continue;
        }
        if (error != EAGAIN && error != EWOULDBLOCK) { errno=error; return done ? (ssize_t)done : errno_map(); }
        if (!writing && !atomic_load(&channel->writers)) return 0;
        if (__atomic_load_n(&fd->flags, __ATOMIC_RELAXED) & O_NONBLOCK_)
            return done ? (ssize_t)done : _EAGAIN;
        if (pipe_interrupted()) return done ? (ssize_t)done : _EINTR;
        struct pollfd wait = {.fd=fd->real_fd, .events=writing ? POLLOUT : POLLIN};
        if (poll(&wait, 1, 1000) < 0 && errno != EINTR) return done ? (ssize_t)done : errno_map();
        if (pipe_interrupted()) return done ? (ssize_t)done : _EINTR;
    }
}
static ssize_t packet_read(struct fd *fd, void *buf, size_t size) { return packet_io(fd,buf,size,false); }
static ssize_t packet_write(struct fd *fd, const void *buf, size_t size) { return packet_io(fd,(void *)buf,size,true); }
static int packet_setflags(struct fd *fd, dword_t flags) {
    struct packet_description *description=fd->data;
    if (description->writer && !(flags & O_DIRECT_)) {
        static atomic_uint reports;
        if(atomic_fetch_add(&reports,1)<8) printk("IDECK_PACKET_CONVERSION_UNSUPPORTED flags=%#x guest_pid=%d\n",flags,current->tgid);
        return _EOPNOTSUPP;
    }
    unsigned old=__atomic_load_n(&fd->flags,__ATOMIC_RELAXED), updated;
    do { updated=(old & ~(O_DIRECT_|O_NONBLOCK_|O_APPEND_)) | (flags & (O_DIRECT_|O_NONBLOCK_|O_APPEND_)); }
    while (!__atomic_compare_exchange_n(&fd->flags,&old,updated,false,__ATOMIC_RELAXED,__ATOMIC_RELAXED));
    return 0;
}
static int packet_ioctl(struct fd *fd, int command, void *arg) {
    if (command == FIONBIO_)
        return packet_setflags(fd,(pipe_getflags(fd)&~O_NONBLOCK_) | (*(int *)arg ? O_NONBLOCK_ : 0));
    if(command==FIONREAD_) {
        struct packet_description *description=fd->data;
        *(int *)arg=(int)atomic_load(&description->channel->payload_bytes);
        return 0;
    }
    return realfs_ioctl(fd,command,arg);
}
static int packet_close(struct fd *fd) {
    struct packet_description *description=fd->data;
    struct packet_channel *channel=description->channel;
    pthread_mutex_lock(&channel->lock);
    list_remove(&description->link);
    unsigned remaining=atomic_fetch_sub(description->writer ? &channel->writers : &channel->readers,1)-1;
    bool last=atomic_fetch_sub(&channel->descriptions_count,1)==1;
    lock(&channel->capacity_lock);
    notify(&channel->capacity_changed);
    unlock(&channel->capacity_lock);
    if (!remaining) {
        struct packet_description *other;
        list_for_each_entry(&channel->descriptions,other,link)
            if (other->writer != description->writer)
                poll_wakeup(other->fd,description->writer ? POLL_READ|POLL_HUP : POLL_WRITE|POLL_ERR);
    }
    pthread_mutex_unlock(&channel->lock);
    int result=close(fd->real_fd);
    int error=result<0 ? errno_map() : 0;
    free(description);
    if (last) { cond_destroy(&channel->capacity_changed);pthread_mutex_destroy(&channel->capacity_lock.m);pthread_mutex_destroy(&channel->io_lock);pthread_mutex_destroy(&channel->lock); free(channel); }
    return error;
}
/* Consumes native on every path. Caller owns the channel's initial lifetime. */
static struct fd *packet_description_create(struct packet_channel *channel, int native, int flags, bool writer, qword_t inode) {
    struct packet_description *description=calloc(1,sizeof(*description));
    struct fd *fd=description ? adhoc_fd_create(&packet_pipe_ops) : NULL;
    if (!fd) { free(description); close(native); return ERR_PTR(_ENOMEM); }
    fd->real_fd=native;
    fd->data=description;
    fd->flags=(writer ? O_WRONLY_ : O_RDONLY_) | (flags&(O_DIRECT_|O_NONBLOCK_|O_APPEND_));
    fd->type=S_IFIFO;
    fd->stat.mode=S_IFIFO|0600;
    fd->stat.uid=current->euid; fd->stat.gid=current->egid; fd->stat.inode=inode;
    description->fd=fd; description->channel=channel; description->writer=writer;
    pthread_mutex_lock(&channel->lock);
    list_add(&channel->descriptions,&description->link);
    atomic_fetch_add(writer ? &channel->writers : &channel->readers,1);
    atomic_fetch_add(&channel->descriptions_count,1);
    pthread_mutex_unlock(&channel->lock);
    return fd;
}
static struct fd *packet_reopen(struct fd *source, int flags) {
    if ((flags&O_ACCMODE_) != (pipe_getflags(source)&O_ACCMODE_)) return ERR_PTR(_ENXIO);
    if ((pipe_getflags(source)&O_ACCMODE_) == O_WRONLY_ && !(flags&O_DIRECT_)) {
        static atomic_uint reports;
        if(atomic_fetch_add(&reports,1)<8) printk("IDECK_PACKET_REOPEN_UNSUPPORTED flags=%#x guest_pid=%d\n",flags,current->tgid);
        return ERR_PTR(_EOPNOTSUPP);
    }
    int native=dup(source->real_fd);
    if (native<0) return ERR_PTR(errno_map());
    struct packet_description *description=source->data;
    struct fd *fd=packet_description_create(description->channel,native,flags,description->writer,source->stat.inode);
    if (!IS_ERR(fd)) fd->stat=source->stat;
    return fd;
}
static const struct fd_ops packet_pipe_ops={
    .read=packet_read,.write=packet_write,.poll=packet_poll,.close=packet_close,
    .getflags=pipe_getflags,.setflags=packet_setflags,.reopen=packet_reopen,
    .ioctl_size=realfs_ioctl_size,.ioctl=packet_ioctl,
};
static int_t ideck_packet_pipe2(addr_t address, int_t flags) {
    if (flags & ~(O_DIRECT_|O_NONBLOCK_|O_CLOEXEC_)) return _EINVAL;
    int pair[2];
    if (socketpair(AF_UNIX,SOCK_DGRAM,0,pair)<0) return errno_map();
    /* Native datagram metadata consumes extra space. Enforce Linux's16 packet
     * slots ourselves rather than exposing native ENOBUFS or false POLLOUT. */
    int capacity=262144, yes=1;
    for (unsigned i=0;i<2;i++) {
        if (setsockopt(pair[i],SOL_SOCKET,SO_SNDBUF,&capacity,sizeof capacity)<0 ||
            setsockopt(pair[i],SOL_SOCKET,SO_RCVBUF,&capacity,sizeof capacity)<0 ||
            fcntl(pair[i],F_SETFL,O_NONBLOCK)<0
#ifdef SO_NOSIGPIPE
            || setsockopt(pair[i],SOL_SOCKET,SO_NOSIGPIPE,&yes,sizeof yes)<0
#endif
        ) { int error=errno_map(); close(pair[0]);close(pair[1]);return error; }
    }
    (void)yes;
    struct packet_channel *channel=calloc(1,sizeof(*channel));
    if (!channel) {close(pair[0]);close(pair[1]);return _ENOMEM;}
    int error=pthread_mutex_init(&channel->lock,NULL);
    if (error) {free(channel);close(pair[0]);close(pair[1]);return _ENOMEM;}
    if(pthread_mutex_init(&channel->io_lock,NULL)) {pthread_mutex_destroy(&channel->lock);free(channel);close(pair[0]);close(pair[1]);return _ENOMEM;}
    list_init(&channel->descriptions);
    lock_init(&channel->capacity_lock);
    cond_init(&channel->capacity_changed);
    static atomic_uint_fast64_t next_inode=0x100000000ULL;
    qword_t inode=atomic_fetch_add(&next_inode,1);
    struct fd *reader=packet_description_create(channel,pair[0],flags&~O_DIRECT_,false,inode);
    if (IS_ERR(reader)) {
        close(pair[1]);cond_destroy(&channel->capacity_changed);pthread_mutex_destroy(&channel->capacity_lock.m);pthread_mutex_destroy(&channel->io_lock);pthread_mutex_destroy(&channel->lock);free(channel);return PTR_ERR(reader);
    }
    struct fd *writer=packet_description_create(channel,pair[1],flags,true,inode);
    if (IS_ERR(writer)) {error=PTR_ERR(writer);fd_close(reader);return error;}
    int descriptors[2];
    /* Initial NONBLOCK is set above; f_install's generic setter omits DIRECT. */
    descriptors[0]=f_install(reader,flags&~O_NONBLOCK_);
    if (descriptors[0]<0) {fd_close(writer);return descriptors[0];}
    descriptors[1]=f_install(writer,flags&~O_NONBLOCK_);
    if (descriptors[1]<0) {f_close(descriptors[0]);return descriptors[1];}
    if (user_put(address,descriptors)) {f_close(descriptors[0]);f_close(descriptors[1]);return _EFAULT;}
    return 0;
}
