#!/usr/bin/env python3
"""get_handle_fd hands the descriptor over in its reply; per-descriptor server log lines
are sampled (both on by default, with kill switches); no Wine runs.

1. The client (build/ntdll-unix/server_ios.c server_get_unix_fd) leaves room for an int
   in the get_handle_fd reply and the server (build/wineserver/fd_ios.c) puts a
   F_DUPFD_CLOEXEC copy of the file's descriptor there, instead of sendmsg on the
   process socket and recvmsg + fcntl in the client. The server is a thread of the
   same process and shares its descriptor table, so the copy is what SCM_RIGHTS
   delivered: a new descriptor for the same open file, close-on-exec. In Horizon Zero
   Dawn's menu (build 493, 2026-10-11) ~940 get_handle_fd requests a second each paid
   sendmsg, recvmsg, fcntl and two server log lines. env.MADEIRA_SRV_FD_SOCKET = 1
   (read once) uses the socket as before.
2. ios_srv_log_sample (fd_ios.c): the add_poll_user and send_client_fd lines, written
   for every opened file and every descriptor sent (each a vsnprintf, localtime_r and
   an fflush on the server thread), are written for their first 64 occurrences and
   then every 1000th. env.MADEIRA_SRV_LOG_ALL = 1 writes every one, as before.

Compiles the production server_get_unix_fd and ios_fd_in_reply (client) and the
get_handle_fd handler (server) on this host with stand-ins that mirror wine/server.h
(SERVER_START_REQ, wine_server_set_reply, wine_server_reply_size) and a request call
that runs the handler and copies its reply data the way the protocol does, a real
socketpair for the process socket and real files, under AddressSanitizer + UBSan:
  - reply path (default): the client gets a different descriptor number for the same
    file (same inode), close-on-exec, sharing the file offset with the server's
    descriptor; nothing is sent on the socket; the descriptor is cached and a second
    call is served from the cache without a request; the type, access and options
    come from the reply;
  - socket path (MADEIRA_SRV_FD_SOCKET=1): the same results through sendmsg/recvmsg;
  - an uncacheable file: needs_close is set and the descriptor is the caller's;
  - the server's copy failing (descriptor table full): the client reports
    STATUS_TOO_MANY_OPENED_FILES, as the socket path does when the right is
    stripped, and no descriptor leaks; the reply buffer's allocation failing closes
    the copy;
  - an invalid handle: the error comes back and is cached as before (no fd read);
  - a client that offers no reply room (any other caller) still gets the socket path.
Then ios_srv_log_sample: 64 lines, then every 1000th; with the kill switch, all.
Textual: the call sites, the switch read once, catalog entries and the CI step.
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
FD = (ROOT / "build/wineserver/fd_ios.c").read_text(encoding="utf-8")
REQ = (ROOT / "build/wineserver/request_ios.c").read_text(encoding="utf-8")
NTDLL = (ROOT / "build/ntdll-unix/server_ios.c").read_text(encoding="utf-8")
BRIDGE = (ROOT / "app/Madeira/WineProcessBridge.m").read_text(encoding="utf-8")
CAT = (ROOT / "app/Madeira/ConfigCatalog.generated.swift").read_text(encoding="utf-8")
CI_FILE = ROOT / ".github/workflows/build-ipa.yml"   # the fork's CI only; upstream has no .github
CI = CI_FILE.read_text(encoding="utf-8") if CI_FILE.exists() else None

failures = []


def check(cond, what):
    print(("PASS " if cond else "FAIL ") + what)
    if not cond:
        failures.append(what)


def func_body(src, signature):
    i = src.find(signature)
    if i < 0:
        return ""
    j = src.find("{", i)
    depth = 0
    for k in range(j, len(src)):
        if src[k] == "{":
            depth += 1
        elif src[k] == "}":
            depth -= 1
            if depth == 0:
                return src[i:k + 1]
    return ""


client = func_body(NTDLL, "int server_get_unix_fd( HANDLE handle, unsigned int wanted_access, int *unix_fd,")
in_reply = func_body(NTDLL, "static int ios_fd_in_reply(void)")
handler = func_body(FD, "DECL_HANDLER(get_handle_fd)")
sample = func_body(FD, "int ios_srv_log_sample( unsigned long *count )")
check(all((client, in_reply, handler, sample)), "server_get_unix_fd, ios_fd_in_reply, the get_handle_fd handler and "
      "ios_srv_log_sample are found")

harness = r'''
#define _GNU_SOURCE
#define WINE_IOS 1
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <unistd.h>

typedef void *HANDLE;
typedef unsigned int obj_handle_t;
typedef unsigned int data_size_t;
typedef unsigned int NTSTATUS;
#define STATUS_SUCCESS 0
#define STATUS_INVALID_HANDLE 0xC0000008
#define STATUS_ACCESS_DENIED 0xC0000022
#define STATUS_TOO_MANY_OPENED_FILES 0xC000011F
#define STATUS_NO_MEMORY 0xC0000017
#define FILE_READ_DATA 1
#define FILE_WRITE_DATA 2
#define FILE_APPEND_DATA 4
enum server_fd_type { FD_TYPE_INVALID, FD_TYPE_FILE, FD_TYPE_DIR };
struct request_header { int req; data_size_t request_size; data_size_t reply_size; };
struct reply_header { unsigned int error; data_size_t reply_size; };
struct get_handle_fd_request { struct request_header __header; obj_handle_t handle; };
struct get_handle_fd_reply { struct reply_header __header; int type; int cacheable; unsigned int access; unsigned int options; };
union generic_request { struct request_header request_header; struct get_handle_fd_request get_handle_fd_request; char pad[64]; };
union generic_reply { struct reply_header reply_header; struct get_handle_fd_reply get_handle_fd_reply; char pad[64]; };
#define REQ_get_handle_fd 48
struct __server_request_info
{
    union { union generic_request req; union generic_reply reply; } u;
    unsigned int data_count;
    void *reply_data;
};
#define SERVER_START_REQ(type) \
    do { \
        struct __server_request_info __req; \
        struct type##_request * const req = &__req.u.req.type##_request; \
        const struct type##_reply * const reply = &__req.u.reply.type##_reply; \
        memset( &__req.u.req, 0, sizeof(__req.u.req) ); \
        __req.u.req.request_header.req = REQ_##type; \
        __req.data_count = 0; \
        (void)reply; \
        do
#define SERVER_END_REQ \
        while(0); \
    } while(0)
#define wine_server_set_reply(r, ptr, max) do { __req.reply_data = (ptr); __req.u.req.request_header.reply_size = (max); } while (0)
#define wine_server_reply_size(r) ((r)->__header.reply_size)
#define wine_server_call(r) fake_server_call( &__req )
static obj_handle_t wine_server_obj_handle( HANDLE h ) { return (obj_handle_t)(uintptr_t)h; }
static HANDLE wine_server_ptr_handle( obj_handle_t h ) { return (HANDLE)(intptr_t)(int)h; }
static void *ios_jit_current_peb(void) { return NULL; }
static pthread_mutex_t fd_cache_mutex = PTHREAD_MUTEX_INITIALIZER;
typedef int sigset_t_dummy;
static void server_enter_uninterrupted_section( pthread_mutex_t *m, void *s ) { (void)s; pthread_mutex_lock( m ); }
static void server_leave_uninterrupted_section( pthread_mutex_t *m, void *s ) { (void)s; pthread_mutex_unlock( m ); }
#define sigset_t int

/* fd cache: one entry per handle (as server_ios.c's, fd+1 in the stored word) */
static struct { int used, fd, type, access, options; } cache[64];
static NTSTATUS get_cached_fd( HANDLE h, int *fd, enum server_fd_type *type, unsigned int *access, unsigned int *options )
{
    unsigned int i = wine_server_obj_handle( h ) / 4;
    if (i >= 64 || !cache[i].used) return STATUS_INVALID_HANDLE;
    if (cache[i].type == FD_TYPE_INVALID) return (NTSTATUS)cache[i].fd;
    *fd = cache[i].fd;
    if (type) *type = cache[i].type;
    if (access) *access = cache[i].access;
    if (options) *options = cache[i].options;
    return STATUS_SUCCESS;
}
static int add_fd_to_cache( HANDLE h, int fd, enum server_fd_type type, unsigned int access, unsigned int options )
{
    unsigned int i = wine_server_obj_handle( h ) / 4;
    if (i >= 64) return 0;
    cache[i].used = 1; cache[i].fd = fd; cache[i].type = type; cache[i].access = access; cache[i].options = options;
    return 1;
}

/* the process socket */
static int sock[2];
static int sends, receives, requests;
int wine_server_receive_fd( obj_handle_t *handle )
{
    struct iovec vec; struct msghdr msg; char cbuf[256]; struct cmsghdr *c; int fd = -1;
    memset( &msg, 0, sizeof(msg) );
    vec.iov_base = handle; vec.iov_len = sizeof(*handle);
    msg.msg_iov = &vec; msg.msg_iovlen = 1; msg.msg_control = cbuf; msg.msg_controllen = sizeof(cbuf);
    receives++;
    if (recvmsg( sock[1], &msg, 0 ) <= 0) return -1;
    for (c = CMSG_FIRSTHDR( &msg ); c; c = CMSG_NXTHDR( &msg, c ))
        if (c->cmsg_level == SOL_SOCKET && c->cmsg_type == SCM_RIGHTS) fd = *(int *)CMSG_DATA( c );
    if (fd != -1) fcntl( fd, F_SETFD, FD_CLOEXEC );
    return fd;
}

/* ---- the server side ---- */
struct fd;   /* declared first: Apple clang rejects the function-scoped one as an incompatible pointer type */
struct fd_ops { enum server_fd_type (*get_fd_type)( struct fd *fd ); };
struct fd { int unix_fd; int cacheable; unsigned int options; const struct fd_ops *fd_ops; };
struct process { int id; };
struct thread { struct process *process; unsigned int error; void *reply_data; data_size_t reply_size; union generic_request req; };
static struct thread cur_thread; static struct process cur_process;
static struct thread *current = &cur_thread;
static enum server_fd_type file_type( struct fd *fd ) { (void)fd; return FD_TYPE_FILE; }
static const struct fd_ops file_ops = { file_type };
static struct fd files[8];
static int fail_dup, fail_alloc;
static void set_error( unsigned int e ) { current->error = e; }
static struct fd *get_handle_fd_obj( struct process *p, obj_handle_t h, unsigned int access )
{
    (void)p; (void)access;
    if (h / 4 >= 8 || !files[h / 4].fd_ops) { set_error( STATUS_INVALID_HANDLE ); return NULL; }
    return &files[h / 4];
}
static int get_unix_fd( struct fd *fd ) { if (fd->unix_fd == -1) set_error( 0xC0000010 ); return fd->unix_fd; }
static unsigned int get_handle_access( struct process *p, obj_handle_t h ) { (void)p; (void)h; return FILE_READ_DATA | FILE_WRITE_DATA; }
static void release_object( void *o ) { (void)o; }
static data_size_t get_reply_max_size(void) { return current->req.request_header.reply_size; }
static void *set_reply_data( const void *data, data_size_t size )
{
    assert( size <= get_reply_max_size() );
    if (fail_alloc) { set_error( STATUS_NO_MEMORY ); return NULL; }
    current->reply_data = malloc( size );
    memcpy( current->reply_data, data, size );
    current->reply_size = size;
    return current->reply_data;
}
static int fake_fcntl( int fd, int cmd, int arg )
{
    if (cmd == F_DUPFD_CLOEXEC && fail_dup) { errno = EMFILE; return -1; }
    return fcntl( fd, cmd, arg );
}
#define fcntl fake_fcntl
int send_client_fd( struct process *process, int fd, obj_handle_t handle )
{
    struct iovec vec; struct msghdr msg; char cbuf[256]; struct cmsghdr *c;
    (void)process;
    memset( &msg, 0, sizeof(msg) );
    vec.iov_base = &handle; vec.iov_len = sizeof(handle);
    msg.msg_iov = &vec; msg.msg_iovlen = 1; msg.msg_control = cbuf; msg.msg_controllen = sizeof(cbuf);
    c = CMSG_FIRSTHDR( &msg );
    c->cmsg_len = CMSG_LEN( sizeof(fd) ); c->cmsg_level = SOL_SOCKET; c->cmsg_type = SCM_RIGHTS;
    *(int *)CMSG_DATA( c ) = fd;
    msg.msg_controllen = c->cmsg_len;
    sends++;
    return sendmsg( sock[0], &msg, 0 ) == sizeof(handle) ? 0 : -1;
}
#define DECL_HANDLER(name) static void req_##name( const struct name##_request *req, struct name##_reply *reply )
@HANDLER@
#undef fcntl

/* one request: what read_request + call_req_handler + send_reply + wait_reply amount to */
static NTSTATUS fake_server_call( struct __server_request_info *r )
{
    union generic_reply reply;
    requests++;
    memset( &reply, 0, sizeof(reply) );
    cur_thread.process = &cur_process;
    cur_thread.req = r->u.req;
    cur_thread.error = 0; cur_thread.reply_size = 0; cur_thread.reply_data = NULL;
    req_get_handle_fd( &cur_thread.req.get_handle_fd_request, &reply.get_handle_fd_reply );
    reply.reply_header.error = cur_thread.error;
    reply.reply_header.reply_size = cur_thread.reply_size;
    r->u.reply = reply;
    if (cur_thread.reply_size) memcpy( r->reply_data, cur_thread.reply_data, cur_thread.reply_size );
    free( cur_thread.reply_data );
    return reply.reply_header.error;
}

/* ---- the client side ---- */
@IN_REPLY@
@CLIENT@

static int bad;
static void expect( int ok, const char *what ) { printf( "%s: %s\n", ok ? "PASS" : "FAIL", what ); if (!ok) bad = 1; }
static int open_fds(void) { int n = 0, fd; for (fd = 0; fd < 1024; fd++) if (fcntl( fd, F_GETFD ) != -1) n++; return n; }

int main( int argc, char **argv )
{
    char path[] = "/tmp/fdreplyXXXXXX";
    int sfd, cfd, nc, ret, flags, before;
    enum server_fd_type type; unsigned int options;
    struct stat a, b;
    const char *mode = argc > 1 ? argv[1] : "reply";
    int via_socket = !strcmp( mode, "socket" );

    if (socketpair( AF_UNIX, SOCK_STREAM, 0, sock )) return 2;
    sfd = mkstemp( path ); unlink( path );
    if (write( sfd, "0123456789", 10 ) != 10) return 2;
    files[1].unix_fd = sfd; files[1].cacheable = 1; files[1].options = 0x40; files[1].fd_ops = &file_ops;
    files[2].unix_fd = sfd; files[2].cacheable = 0; files[2].options = 0x20; files[2].fd_ops = &file_ops;

    ret = server_get_unix_fd( (HANDLE)(uintptr_t)4, FILE_READ_DATA, &cfd, &nc, &type, &options );
    expect( ret == 0 && cfd >= 0 && cfd != sfd, "the client gets its own descriptor" );
    fstat( sfd, &a ); fstat( cfd, &b );
    expect( a.st_ino == b.st_ino && a.st_dev == b.st_dev, "for the same file" );
    flags = fcntl( cfd, F_GETFD );
    expect( flags != -1 && (flags & FD_CLOEXEC), "close-on-exec, as SCM_RIGHTS + fcntl left it" );
    lseek( sfd, 3, SEEK_SET );
    expect( lseek( cfd, 0, SEEK_CUR ) == 3, "sharing the open file (offset) with the server's descriptor" );
    expect( type == FD_TYPE_FILE && options == 0x40 && !nc, "type and options from the reply; cached, so not the caller's to close" );
    expect( via_socket ? (sends == 1 && receives == 1) : (sends == 0 && receives == 0),
            via_socket ? "MADEIRA_SRV_FD_SOCKET=1: sent and received through the process socket"
                       : "nothing went through the process socket" );
    requests = 0;
    ret = server_get_unix_fd( (HANDLE)(uintptr_t)4, FILE_READ_DATA, &cfd, &nc, &type, &options );
    expect( ret == 0 && requests == 0, "the second call is served from the cache" );

    ret = server_get_unix_fd( (HANDLE)(uintptr_t)8, FILE_READ_DATA, &cfd, &nc, NULL, NULL );
    expect( ret == 0 && nc == 1 && cfd != sfd, "an uncacheable file: the caller closes the descriptor" );
    close( cfd );

    if (!via_socket)
    {
        before = open_fds();
        files[3] = files[1];
        fail_dup = 1;
        ret = server_get_unix_fd( (HANDLE)(uintptr_t)12, FILE_READ_DATA, &cfd, &nc, NULL, NULL );
        fail_dup = 0;
        expect( ret == STATUS_TOO_MANY_OPENED_FILES && cfd == -1 && open_fds() == before,
                "the server's copy failing: STATUS_TOO_MANY_OPENED_FILES, nothing leaks" );
        files[4] = files[1];
        fail_alloc = 1;
        ret = server_get_unix_fd( (HANDLE)(uintptr_t)16, FILE_READ_DATA, &cfd, &nc, NULL, NULL );
        fail_alloc = 0;
        expect( ret == STATUS_NO_MEMORY && cfd == -1 && open_fds() == before,
                "the reply buffer failing: the error comes back and the copy is closed" );
        /* a caller that leaves no room in the reply gets the socket path */
        sends = receives = 0;
        {
            obj_handle_t h;
            SERVER_START_REQ( get_handle_fd )
            {
                req->handle = 4 * 1;
                ret = wine_server_call( req );
            }
            SERVER_END_REQ;
            cfd = wine_server_receive_fd( &h );
            expect( ret == 0 && sends == 1 && cfd >= 0 && h == 4, "a request without reply room still gets the socket path" );
            close( cfd );
        }
    }
    ret = server_get_unix_fd( (HANDLE)(uintptr_t)36, FILE_READ_DATA, &cfd, &nc, NULL, NULL );
    expect( ret == STATUS_INVALID_HANDLE && cfd == -1 && !cache[9].used, "an invalid handle: the error comes back, nothing cached" );
    files[5].unix_fd = -1; files[5].cacheable = 1; files[5].fd_ops = &file_ops;
    sends = receives = 0;
    ret = server_get_unix_fd( (HANDLE)(uintptr_t)20, FILE_READ_DATA, &cfd, &nc, NULL, NULL );
    expect( ret == 0xC0000010 && cfd == -1 && cache[5].used && cache[5].type == FD_TYPE_INVALID && cache[5].fd == (int)0xC0000010
            && !sends && !receives, "an object without a descriptor: its status comes back and is cached as before, no fd read" );
    return bad;
}
'''

harness = (harness.replace("@HANDLER@", handler).replace("@IN_REPLY@", in_reply).replace("@CLIENT@", client))

cc = os.environ.get("CC") or shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
if not cc:
    check(False, "a C compiler is available")
else:
    tmp = Path(tempfile.mkdtemp(prefix="fdreply-"))
    (tmp / "h.c").write_text(harness)
    exe = tmp / "h"
    b = subprocess.run([cc, "-std=gnu11", "-g", "-O1", "-Wall", "-Wno-unused-function", "-Wno-unused-variable",
                        "-Werror=implicit-function-declaration", "-fsanitize=address,undefined",
                        "-fno-sanitize-recover=all", "-pthread", str(tmp / "h.c"), "-o", str(exe)],
                       capture_output=True, text=True)
    check(b.returncode == 0, "the harness compiles (ASan + UBSan)" + ("" if not b.returncode else ": " + b.stderr[-2000:]))
    if not b.returncode:
        leaks = "0" if sys.platform == "darwin" else "1"   # LeakSanitizer does not run on macOS
        env = dict(os.environ, ASAN_OPTIONS="detect_leaks=" + leaks)
        env.pop("MADEIRA_SRV_FD_SOCKET", None)
        for label, extra in (("default (reply)", {}), ("MADEIRA_SRV_FD_SOCKET=1", {"MADEIRA_SRV_FD_SOCKET": "1"})):
            r = subprocess.run([str(exe), "socket" if extra else "reply"], capture_output=True, text=True,
                               env=dict(env, **extra), timeout=120)
            print("\n".join("    " + l for l in r.stdout.strip().splitlines()))
            check(r.returncode == 0 and "FAIL" not in r.stdout,
                  label + ": every check passes, no sanitizer report" + ("" if not r.returncode else ": " + r.stderr[-1500:]))

    # ios_srv_log_sample
    h2 = r'''
#include <stdio.h>
volatile int g_madeira_srv_log_all;
@SAMPLE@
int main(void)
{
    unsigned long c = 0, n, yes = 0, first_after = 0;
    for (n = 1; n <= 10000; n++) if (ios_srv_log_sample( &c )) { yes++; if (n > 64 && !first_after) first_after = n; }
    printf( "%lu %lu\n", yes, first_after );
    g_madeira_srv_log_all = 1;
    for (n = 0; n < 500; n++) if (!ios_srv_log_sample( &c )) { puts( "dropped" ); return 1; }
    return 0;
}
'''.replace("@SAMPLE@", sample)
    (tmp / "s.c").write_text(h2)
    b = subprocess.run([cc, "-std=gnu11", "-O1", "-Wall", str(tmp / "s.c"), "-o", str(tmp / "s")], capture_output=True, text=True)
    check(b.returncode == 0, "ios_srv_log_sample compiles" + ("" if not b.returncode else ": " + b.stderr[-800:]))
    if not b.returncode:
        r = subprocess.run([str(tmp / "s")], capture_output=True, text=True)
        check(r.returncode == 0 and r.stdout.split() == ["74", "1000"],
              "64 lines, then every 1000th (74 of 10000); MADEIRA_SRV_LOG_ALL=1 writes all (%s)" % r.stdout.strip())
    shutil.rmtree(tmp, ignore_errors=True)

# ---- textual ---------------------------------------------------------------------
check("if (get_reply_max_size() == sizeof(int))" in handler and "F_DUPFD_CLOEXEC" in handler and
      handler.find("else\n#endif\n            send_client_fd( current->process, unix_fd, req->handle );") > 0,
      "the handler puts the copy in the reply only when the client left room for exactly an int, else the socket")
check("if (in_reply) wine_server_set_reply( req, &reply_fd, sizeof(reply_fd) );" in client and
      "fd = wine_server_reply_size( reply ) == sizeof(reply_fd) ? reply_fd : -1;" in client,
      "the client offers the room and never reads the socket when it did (a missing copy is no descriptor)")
check('const char *e = getenv( "MADEIRA_SRV_FD_SOCKET" );' in in_reply and "static int on = -1;" in in_reply,
      "MADEIRA_SRV_FD_SOCKET is read once")
check(NTDLL.count("server_enter_uninterrupted_section( &fd_cache_mutex") == 4,
      "the fd_cache_mutex sections are unchanged")
apu = func_body(FD, "static int add_poll_user( struct fd *fd )")
check("if (ios_srv_log_sample( &logged ))" in apu, "add_poll_user's line is sampled")
scf = func_body(REQ, "int send_client_fd( struct process *process, int fd, obj_handle_t handle )")
check("int log_this = ios_srv_log_sample( &logged );" in scf and "if (log_this)\n        ws_log(\"[wineserver] send_client_fd: fd=" in scf
      and "if (log_this || ret != sizeof(handle))" in scf,
      "send_client_fd's two lines are sampled, and a failed sendmsg is always logged")
check("volatile int g_madeira_srv_log_all = 0;" in BRIDGE and
      "g_madeira_srv_log_all = (la && la[0] == '1') ? 1 : 0;" in BRIDGE, "the bridge sets MADEIRA_SRV_LOG_ALL per launch")
for key in ("env.MADEIRA_SRV_FD_SOCKET", "env.MADEIRA_SRV_LOG_ALL"):
    check(re.search(r'key: "%s", title: "[^"]+", kind: \.bool, defaultValue: "0"' % re.escape(key), CAT) is not None,
          "the catalog documents %s (kill switch, default 0)" % key)
if CI is not None:
    check("python3 tests/host/check-srv-fd-reply.py" in CI, "CI runs this check")

print()
if failures:
    print("%d check(s) failed" % len(failures))
    sys.exit(1)
print("all checks passed")
