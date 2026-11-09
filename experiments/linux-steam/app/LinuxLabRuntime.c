/* SPDX-License-Identifier: GPL-3.0-or-later WITH Madeira-Converter-Exception */
#include "LinuxLabRuntime.h"
#include "LabDeviceFS.h"
#include "LaunchProtocol.h"
#include <pthread.h>
#include <stdatomic.h>
#include <string.h>
#include <stdio.h>
#include "kernel/init.h"
#include "kernel/calls.h"
#include "kernel/task.h"
#include "fs/real.h"
#include "fs/devices.h"
#include "fs/dev.h"
#include "fs/fd.h"
#include "fs/path.h"
#include "LinuxSteamSession.h"
#include "ToolInstall.h"
#if IDECK_LAB_GUEST_LIFETIME
#include "GuestLifetime.h"
#endif
#if IDECK_LAB_NATIVE_WORKERS
#include "NativeWorkers.h"
#endif
#if IDECK_LAB_NATIVE_LOG
#include "NativeKernelLog.h"
#endif

static atomic_bool consumed;
static atomic_int phase;
const char *ideck_linux_lab_stage(void) {
    static const char *names[] = {"idle", "mount-root", "init-task", "runtime-directories", "device-filesystem", "child-task", "elf-load", "guest-running", "guest-exited"};
    return names[atomic_load(&phase)];
}
static int wait_status = -1;
static struct task *initial_child;
extern int ideck_lab_bridge_install(void);
extern int ideck_lab_bridge_major(void);
extern const char *ideck_linuxrunner_dirfd_guard(void);
void restore_termios(void) {} /* This embedding never configures a host tty. */
static void observe_exit(struct task *task, int status) {
    if (task == initial_child) wait_status = status;
}
static void *run_guest(void *unused) {
    (void)unused;
    current = initial_child;
    current->thread = pthread_self();
    task_run_current();
    return NULL;
}
static int run(const char *root_path, int mode, const struct ideck_tool_payload *tool) {
    int steam_probe = mode == 1, compat_probe = mode == 2, distro_probe = mode == 3;
    int frontend = mode == 4, dependencies = mode == 5, tool_probe = mode == 6;
    int fake_root = distro_probe || frontend || dependencies || tool_probe;
    if (!root_path || root_path[0] != '/') return -22;
    if (atomic_exchange(&consumed, 1)) return -16;
    if (strcmp(ideck_linuxrunner_dirfd_guard(), "IDECK_LINUXRUNNER_DIRFD_GUARD_V3")) return -5;
#if IDECK_LAB_GUEST_LIFETIME
    if(strcmp(ideck_guest_lifetime_marker(),"IDECK_GUEST_LIFETIME_V1"))return -5;
#endif
#if IDECK_LAB_NATIVE_WORKERS
    if(strcmp(ideck_native_workers_marker(),"IDECK_NATIVE_WORKERS_V1"))return -5;
#endif
#if IDECK_LAB_NATIVE_LOG
    if(strcmp(ideck_native_log_bridge_marker(),"IDECK_NATIVE_LOG_BRIDGE_V1")||!ideck_native_log_name())return -5;
#endif
    atomic_store(&phase, 1);
    char distro_data[4096];
    int size = snprintf(distro_data, sizeof distro_data, "%s/data", root_path);
    if (size < 0 || size >= (int)sizeof distro_data) return -36;
    int err = mount_root(fake_root ? &fakefs : &realfs, fake_root ? distro_data : root_path);
    if (err < 0) return err;
    atomic_store(&phase, 2);
    if ((err = become_first_process()) < 0) return err;
    atomic_store(&phase, 3);
    const char *dirs[] = {"/proc", "/tmp", "/root", "/root/.steam", "/dev"};
    for (unsigned i = 0; i < sizeof dirs / sizeof dirs[0]; i++) {
        err = generic_mkdirat(AT_PWD, dirs[i], i == 1 ? 01777 : 0700);
        if (err < 0 && err != -17) return err;
    }
    if (frontend) {
        /* This is a fresh native app's first runtime and a private non-shared
         * root. No previous guest can survive here; never do this for arbitrary
         * host controls or any ordinary gaming path. Update fakefs via its API. */
        const char *stale[] = {"/tmp/.X99-lock", "/tmp/.X11-unix/X99", "/tmp/ideck-display-ready", "/tmp/ideck-vnc-password"};
        for (unsigned i=0;i<sizeof stale/sizeof stale[0];i++) {
            err=generic_unlinkat(AT_PWD,stale[i]);
            if(err<0&&err!=-2)return err;
        }
    }
    if ((err = do_mount(&procfs, "proc", "/proc", "", 0)) < 0) return err;
    atomic_store(&phase, 4);
    char devices_path[4096];
    if (!fake_root) {
        if (lab_device_fs_prepare(root_path, devices_path, sizeof devices_path)) return -5;
        if ((err = do_mount(&fakefs, devices_path, "/dev", "", 0)) < 0) return err;
    }
    const struct { const char *path; int minor; } devices[] = {
        {"/dev/null", DEV_NULL_MINOR}, {"/dev/zero", DEV_ZERO_MINOR},
        {"/dev/random", DEV_RANDOM_MINOR}, {"/dev/urandom", DEV_URANDOM_MINOR}
    };
    for (unsigned i = 0; i < sizeof devices / sizeof devices[0]; i++) {
        dev_t_ device = dev_make(MEM_MAJOR, devices[i].minor);
        err = generic_mknodat(AT_PWD, devices[i].path, S_IFCHR | 0666, device);
        if (err == -17 && fake_root) {
            struct statbuf st;
            err = generic_statat(AT_PWD, devices[i].path, &st, false);
            if (!err && (!S_ISCHR(st.mode) || st.rdev != device)) err = -5;
        }
        if (err < 0) return err;
    }
    if ((err = ideck_lab_bridge_install()) < 0) return err;
    dev_t_ bridge_device = dev_make(ideck_lab_bridge_major(), 0);
    err = generic_mknodat(AT_PWD, "/dev/ideck-madeira", S_IFCHR | 0600, bridge_device);
    if (err == -17 && fake_root) {
        struct statbuf st;
        err = generic_statat(AT_PWD, "/dev/ideck-madeira", &st, false);
        if (!err && (!S_ISCHR(st.mode) || st.rdev != bridge_device)) err = -5;
    }
    if (err < 0) return err;
    if (steam_probe || frontend) {
        const char *links[] = {"/root/.steam/steam", "/root/.steam/root"};
        for (unsigned i = 0; i < sizeof links / sizeof links[0]; i++) {
            err = generic_symlinkat("/Steam", AT_PWD, links[i]);
            if (err < 0 && err != -17) return err;
        }
    }
#if IDECK_LAB_COMPAT_TOOL
    if(tool) { int created=0; if((err=ideck_tool_install(tool,&created))<0)return err; }
#else
    if(tool)return -95;
#endif
    /* Keep PID 1 out of guest execution: its halt path calls host _exit(). */
    if ((err = prepare_guest_runtime_dirs()) < 0) return err;
    atomic_store(&phase, 5);
    if ((err = become_new_init_child()) < 0) return err;
    initial_child = current;
    if ((err = create_stdio("/dev/null", MEM_MAJOR, DEV_NULL_MINOR)) < 0) return err;
    if (compat_probe || tool_probe) {
        const char *fixture[] = {"/mnt", "/mnt/ideck", "/mnt/ideck/SteamLibrary", "/mnt/ideck/SteamLibrary/steamapps", "/mnt/ideck/SteamLibrary/steamapps/common", "/mnt/ideck/SteamLibrary/steamapps/common/Control"};
        for (unsigned i = 0; i < sizeof fixture / sizeof fixture[0]; i++) {
            err = generic_mkdirat(AT_PWD, fixture[i], 0700);
            if (err < 0 && err != -17) return err;
        }
        struct fd *dir = generic_open(fixture[5], O_RDONLY_ | O_DIRECTORY_, 0);
        if (IS_ERR(dir)) return (int)PTR_ERR(dir);
        fs_chdir(current->fs, dir);
    }
    const char *program = distro_probe || frontend || dependencies || tool_probe ? "/bin/sh" : steam_probe ? "/Steam/steamrtarm64/steam" : compat_probe ? "/ideck-madeira" : "/probe";
    const char frontend_args[] = IDECK_LINUX_STEAM_ARGS;
    const char tool_args[] = "/bin/sh\0-c\0"
        "set -eu; umask 077; exec > /tmp/ideck-compatibility-results.txt 2>&1; "
        "cd " IDECK_LAUNCH_ROOT "Control; "
        "export STEAM_COMPAT_APP_ID=480 STEAM_COMPAT_INSTALL_PATH=" IDECK_LAUNCH_ROOT "Control; "
        "set +e; " IDECK_COMPAT_TOOL_EXE " waitforexitandrun " IDECK_LAUNCH_ROOT "Control/control.exe; result=$?; set -e; "
        "test \"$result\" -eq 125; echo diagnostic-tool-roundtrip=PASS\0";
    const char dependency_args[] = "/bin/sh\0-c\0"
        "set -eu; umask 077; exec > /tmp/ideck-dependencies.log 2>&1; "
        "export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin; "
        "export DEBIAN_FRONTEND=noninteractive; mkdir -p /var/log/apt; "
        "apt-get -y --no-install-recommends -o Acquire::Retries=0 -o Acquire::http::Timeout=30 "
        "-o Acquire::https::Timeout=30 install libnm0=1.52.1-1; "
        "export LD_LIBRARY_PATH=/Steam/steamrtarm64:/Steam/steamrtarm64/libs:/Steam/steamrtarm64/panorama; "
        "ldd /Steam/steamrtarm64/steamclient.so > /tmp/ideck-client-ldd.txt; "
        "if grep -F '=> not found' /tmp/ideck-client-ldd.txt; then exit 1; fi; "
        "echo dependencies-complete=PASS\0";
    const char distro_args[] = "/bin/sh\0-c\0"
        "set -eu; umask 077; exec > /distro-probe-results.txt; "
        "test \"$(uname -m)\" = aarch64; echo distro-arm64=PASS; "
        "getconf GNU_LIBC_VERSION > /dev/null; /usr/bin/true; echo glibc-exec=PASS; "
        "mkdir -p /tmp/ideck-control; touch /tmp/ideck-control/file; "
        "test -f /tmp/ideck-control/file; rm /tmp/ideck-control/file; echo distro-filesystem=PASS; "
        "head -c 16 /dev/urandom > /dev/null; echo distro-entropy=PASS; "
        "curl --version > /dev/null; echo curl-link=PASS; echo complete=PASS\0";
    const char *args = steam_probe ? "/Steam/steamrtarm64/steam\0-clientbeta\0steamdeck_stable\0-nobigpicture\0" :
        compat_probe ? "/ideck-madeira\0waitforexitandrun\0" IDECK_LAUNCH_ROOT "Control/control.exe\0" : "/probe\0";
    const char env[] = "HOME=/root\0PATH=/usr/bin:/bin\0LANG=C\0STEAM_RUNTIME=1\0"
        "LD_LIBRARY_PATH=/Steam/steamrtarm64:/Steam/steamrtarm64/libs:/lib/aarch64-linux-gnu\0";
    const char compat_env[] = "HOME=/root\0PATH=/usr/bin:/bin\0LANG=C\0"
        "STEAM_COMPAT_APP_ID=480\0STEAM_COMPAT_INSTALL_PATH=" IDECK_LAUNCH_ROOT "Control\0";
    if (steam_probe) {
        struct fd *output = generic_open("/loader-probe-output.txt", O_WRONLY_ | O_CREAT_ | O_TRUNC_, 0600);
        if (IS_ERR(output)) return (int)PTR_ERR(output);
        fd_close(current->files->files[1]);
        fd_close(current->files->files[2]);
        current->files->files[1] = output;
        current->files->files[2] = fd_retain(output);
    }
    atomic_store(&phase, 6);
    if ((err = do_execve(program, distro_probe || frontend || dependencies || tool_probe ? 3 : steam_probe ? 4 : compat_probe ? 3 : 1,
                         frontend ? frontend_args : tool_probe ? tool_args : dependencies ? dependency_args : distro_probe ? distro_args : args, compat_probe ? compat_env : env)) < 0) return err;
    exit_hook = observe_exit;
    current = NULL;
    pthread_t worker;
    atomic_store(&phase, 7);
#if IDECK_LAB_GUEST_LIFETIME
    ideck_guest_lifetime_reserve();
#endif
    if ((err = pthread_create(&worker, NULL, run_guest, NULL))) {
#if IDECK_LAB_GUEST_LIFETIME
        ideck_guest_lifetime_retire(NULL);
#endif
        return -err;
    }
    if ((err = pthread_join(worker, NULL))) return -err;
    atomic_store(&phase, 8);
    return wait_status;
}
int ideck_linux_lab_run(const char *root_path) { return run(root_path, 0, NULL); }
int ideck_linux_lab_steam_probe(const char *root_path) { return run(root_path, 1, NULL); }
int ideck_linux_lab_compat_probe(const char *root_path) { return run(root_path, 2, NULL); }
int ideck_linux_lab_distro_probe(const char *root_path) { return run(root_path, 3, NULL); }
int ideck_linux_lab_steam_frontend(const char *root_path) {
#if IDECK_LAB_STEAM_FRONTEND
    return run(root_path, 4, NULL);
#else
    (void)root_path; return -95;
#endif
}

int ideck_linux_lab_dependencies(const char *root_path) {
#if IDECK_LAB_STEAM_FRONTEND
    return run(root_path, 5, NULL);
#else
    (void)root_path; return -95;
#endif
}

int ideck_linux_lab_live_guest_threads(void) {
#if IDECK_LAB_GUEST_LIFETIME
    unsigned live=ideck_guest_lifetime_live();
    return live>32768?-5:(int)live;
#else
    return -95;
#endif
}

int ideck_linux_lab_native_worker_entries(void) {
#if IDECK_LAB_NATIVE_WORKERS
    return ideck_native_workers_total();
#else
    return -95;
#endif
}

int ideck_linux_lab_steam_frontend_with_tool(const char *root_path,const struct ideck_tool_payload *tool) {
#if IDECK_LAB_STEAM_FRONTEND && IDECK_LAB_COMPAT_TOOL
    if(!tool)return -22;
    return run(root_path,4,tool);
#else
    (void)root_path;(void)tool;return -95;
#endif
}
int ideck_linux_lab_compatibility_tool_probe(const char *root_path,const struct ideck_tool_payload *tool) {
#if IDECK_LAB_STEAM_FRONTEND && IDECK_LAB_COMPAT_TOOL
    if(!tool)return -22;
    return run(root_path,6,tool);
#else
    (void)root_path;(void)tool;return -95;
#endif
}
