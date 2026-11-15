/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception
 * HOST exact realfs_mmap controls. Only its native calls and pt_map are injected.
 * "native" additionally uses a real unlinked own file for all four probes.
 */
#include "kernel/task.h"
#include "kernel/memory.h"
#include "kernel/calls.h"
#include "kernel/errno.h"
#include "fs/fd.h"
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

size_t real_page_size;
__thread struct task *current;
void (*runtime_memory_failure)(const char *, uint64_t, uint64_t, int, int, int);
static const char *mode;
static size_t requested;
static unsigned calls, releases, logs, pt_calls, active;
static void *last_mapping;
static size_t last_bytes;
static int native_fd = -1;

int errno_map(void) { return errno == ENOMEM ? _ENOMEM : _EINVAL; }
void fd_report_mapping_failure(struct fd *fd, int guest_fd, const char *stage,
        uint64_t address, uint64_t length, uint64_t offset, unsigned prot,
        unsigned flags, int host, int result) {
    (void)fd; (void)guest_fd; (void)stage; (void)address; (void)length;
    (void)offset; (void)prot; (void)flags; (void)host; (void)result;
}
void ish_printk(const char *format, ...) {
    char text[512]; va_list args; va_start(args, format);
    assert(vsnprintf(text, sizeof text, format, args) < (int)sizeof text);
    va_end(args);
    assert(strstr(text, "IDECK_FILE_MMAP_PROBE_V1"));
    assert(!strstr(text, "path=") && !strstr(text, "address="));
    logs++; fputs(text, stdout); errno = EIO; // Logger must not change caller errno.
}
int probe_fstat(int fd, struct stat *st) {
    static unsigned stats;
    stats++;
    if (!strcmp(mode, "native")) return fstat(fd, st);
    *st = (struct stat){.st_mode=S_IFREG | 0600, .st_size=(off_t)requested};
    if (!strcmp(mode, "not-regular") && stats > 1) st->st_mode=S_IFCHR;
    if (!strcmp(mode, "shrunk") && stats > 1) st->st_size=1;
    return 0;
}
void *probe_mmap(void *hint, size_t bytes, int prot, int flags, int fd, off_t off) {
    assert(hint == NULL); calls++;
    if (calls == 1 && strcmp(mode, "original-success")) {
        errno = !strcmp(mode, "other-errno") ? EINVAL : ENOMEM;
        return MAP_FAILED;
    }
    if (calls > 1) {
        unsigned trial = calls - 2;
        assert(trial < 4 && off == 0 && !active);
        assert(bytes == (trial == 0 ? real_page_size : requested));
        assert(prot == (trial == 1 ? PROT_READ : PROT_READ | PROT_WRITE));
        assert(flags == (trial < 2 ? MAP_SHARED : trial == 2 ? MAP_PRIVATE : MAP_PRIVATE | MAP_ANONYMOUS));
        assert(fd == (trial == 3 ? -1 : native_fd));
        if (!strcmp(mode, "all-fail") ||
                (!strcmp(mode, "shared-fail") && trial < 2)) {
            errno = ENOMEM; return MAP_FAILED;
        }
    }
    void *result = !strcmp(mode, "native") ? mmap(hint, bytes, prot, flags, fd, off) :
            (void *)(uintptr_t)(0x100000u + calls * 0x10000u);
    assert(result != MAP_FAILED); active++;
    last_mapping=result; last_bytes=bytes; return result;
}
int probe_munmap(void *ptr, size_t bytes) {
    assert(active == 1 && ptr == last_mapping && bytes == last_bytes);
    releases++;
    if (!strcmp(mode, "release-fail")) { errno=EINVAL; return -1; }
    int result = !strcmp(mode, "native") ? munmap(ptr, bytes) : 0;
    assert(!result); active--; return 0;
}
int ideck_test_pt_map(struct mem *mem, page_t start, pages_t pages,
        void *mapping, size_t offset, unsigned flags) {
    (void)mem; (void)start; (void)pages; (void)offset; (void)flags;
    assert(mapping == last_mapping); pt_calls++; return 0;
}
extern int realfs_mmap(struct fd *, struct mem *, page_t, pages_t, off_t, int, int);
int main(int argc, char **argv) {
    if (argc != 4) return 2;
    mode=argv[1]; int enabled=atoi(argv[2]);
    struct task task={.pid=12,.tgid=11}; current=&task;
    real_page_size=(size_t)sysconf(_SC_PAGESIZE);
    requested=9523200; native_fd=91;
    int prot=P_READ | P_WRITE, flags=MMAP_SHARED;
    off_t offset=0;
    if (!strcmp(mode,"private")) flags=MMAP_PRIVATE;
    if (!strcmp(mode,"read-only")) prot=P_READ;
    if (!strcmp(mode,"offset")) offset=(off_t)real_page_size;
    if (!strcmp(mode,"too-large")) requested=32u*1024u*1024u;
    if (!strcmp(mode,"too-small")) requested=PAGE_SIZE;
    if (!strcmp(mode,"bad-fd")) native_fd=-1;
    if (!strcmp(mode,"native")) {
        native_fd=open(argv[3],O_CREAT | O_EXCL | O_RDWR,0600); assert(native_fd>=0);
        assert(!ftruncate(native_fd,(off_t)requested));
        assert(pwrite(native_fd,"ideck-own-map",13,0)==13);
        assert(!unlink(argv[3])); // File backing remains live solely through the FD.
    }
    struct fd fd={.real_fd=native_fd};
    int result=realfs_mmap(&fd,NULL,32,requested/PAGE_SIZE,offset,prot,flags);
    if (!strcmp(mode,"original-success")) {
        assert(result==0 && calls==1 && pt_calls==1 && logs==0);
        assert(!probe_munmap(last_mapping,last_bytes));
    } else {
        assert(result==(!strcmp(mode,"other-errno")?_EINVAL:_ENOMEM));
        assert(errno==(!strcmp(mode,"other-errno")?EINVAL:ENOMEM));
        assert(pt_calls==0); // No diagnostic mapping may be installed in guest PTEs.
        if (!enabled || !strcmp(mode,"private") || !strcmp(mode,"read-only") ||
                !strcmp(mode,"offset") || !strcmp(mode,"too-large") ||
                !strcmp(mode,"too-small") || !strcmp(mode,"other-errno") ||
                !strcmp(mode,"bad-fd")) assert(calls==1 && logs==0 && releases==0);
        else if (!strcmp(mode,"not-regular") || !strcmp(mode,"shrunk")) assert(calls==1 && logs==1);
        else if (!strcmp(mode,"release-fail")) assert(calls==2 && releases==1 && active==1);
        else {
            assert(calls==5 && logs==6 && !active);
            assert(releases==(!strcmp(mode,"all-fail")?0:!strcmp(mode,"shared-fail")?2:4));
            // Once only, even if the original failed request is made again.
            calls=0; unsigned old_logs=logs;
            assert(realfs_mmap(&fd,NULL,32,requested/PAGE_SIZE,0,prot,flags)==_ENOMEM);
            assert(calls==1 && logs==old_logs);
        }
    }
    if (!strcmp(mode,"native")) {
        char text[13]; assert(pread(native_fd,text,sizeof text,0)==sizeof text);
        assert(!memcmp(text,"ideck-own-map",sizeof text));
        struct stat st;assert(!fstat(native_fd,&st)&&st.st_size==(off_t)requested);
        assert(lseek(native_fd,0,SEEK_CUR)==0); assert(!close(native_fd));
    }
    puts("original-result-preserved=1 diagnostic-address-never-installed=1 HOST-only=1");
    return 0;
}
