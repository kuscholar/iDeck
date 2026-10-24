/* iOS-Madeira: a userspace stand-in for Linux's <linux/ntsync.h>.
 *
 * Wine's in-process synchronisation (server/inproc_sync.c, ntdll/unix/sync.c)
 * is written against the ntsync character device: the server creates the
 * objects, hands clients a descriptor, and every wait / release / set after
 * that is one ioctl with NO server round trip. iOS has no such driver, but here
 * the wineserver is a thread of the same process, so the "driver" can simply be
 * a library both sides call (build/madsync/madsync.c).
 *
 * Descriptors are PSEUDO fds (MADSYNC_FD_BASE | index): never a kernel fd, so
 * thousands of events cost no descriptors and identity survives being handed
 * from server to client. ioctl() and close() are redirected for the two files
 * that include this header; anything that is not ours falls through to libc. */
#ifndef MADSYNC_LINUX_NTSYNC_H
#define MADSYNC_LINUX_NTSYNC_H

#include <stdint.h>
#include <sys/ioctl.h>   /* before the macros below, so libc's prototypes stay intact */
#include <unistd.h>

typedef uint32_t __u32;
typedef uint64_t __u64;

struct ntsync_sem_args   { __u32 count; __u32 max; };
struct ntsync_mutex_args { __u32 owner; __u32 count; };
struct ntsync_event_args { __u32 manual; __u32 signaled; };

#define NTSYNC_WAIT_REALTIME 0x1
struct ntsync_wait_args
{
    __u64 timeout;   /* absolute ns, CLOCK_MONOTONIC unless REALTIME; ~0 = forever */
    __u64 objs;      /* pointer to an array of int descriptors */
    __u32 count;
    __u32 index;     /* out: which object; == count means the alert fired */
    __u32 flags;
    __u32 owner;
    __u32 alert;     /* 0 = none */
    __u32 pad;
};
#define NTSYNC_MAX_WAIT_COUNT 64

/* Request codes are private to this shim; only uniqueness matters. */
#define MADSYNC_IOC(n)            (0x4d530000ul | (n))
#define NTSYNC_IOC_CREATE_SEM     MADSYNC_IOC(0x80)
#define NTSYNC_IOC_SEM_RELEASE    MADSYNC_IOC(0x81)
#define NTSYNC_IOC_WAIT_ANY       MADSYNC_IOC(0x82)
#define NTSYNC_IOC_WAIT_ALL       MADSYNC_IOC(0x83)
#define NTSYNC_IOC_CREATE_MUTEX   MADSYNC_IOC(0x84)
#define NTSYNC_IOC_MUTEX_UNLOCK   MADSYNC_IOC(0x85)
#define NTSYNC_IOC_MUTEX_KILL     MADSYNC_IOC(0x86)
#define NTSYNC_IOC_CREATE_EVENT   MADSYNC_IOC(0x87)
#define NTSYNC_IOC_EVENT_SET      MADSYNC_IOC(0x88)
#define NTSYNC_IOC_EVENT_RESET    MADSYNC_IOC(0x89)
#define NTSYNC_IOC_EVENT_PULSE    MADSYNC_IOC(0x8a)
#define NTSYNC_IOC_SEM_READ       MADSYNC_IOC(0x8b)
#define NTSYNC_IOC_MUTEX_READ     MADSYNC_IOC(0x8c)
#define NTSYNC_IOC_EVENT_READ     MADSYNC_IOC(0x8d)

#define MADSYNC_FD_BASE   0x70000000
#define MADSYNC_DEVICE_FD 0x6fffffff
#define MADSYNC_IS_FD(fd) (((unsigned int)(fd) & 0xf0000000u) == (unsigned int)MADSYNC_FD_BASE)

extern int  madsync_enabled(void);
extern int  madsync_ioctl( int fd, unsigned long req, void *arg );
extern int  madsync_close( int fd );
extern int  madsync_ref( int fd );                                   /* another holder of the same object */
/* The server->client hand-off that replaces SCM_RIGHTS for pseudo fds. */
extern void madsync_post( unsigned int pid, unsigned int handle, int fd );
extern int  madsync_take( unsigned int pid, unsigned int handle );

#ifndef MADSYNC_IMPLEMENTATION
#define ioctl(fd, req, arg) madsync_ioctl( (fd), (unsigned long)(req), (void *)(arg) )
#define close(fd)           madsync_close( fd )
#endif

#endif
